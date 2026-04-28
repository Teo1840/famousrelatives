from flask import Flask, request, jsonify, Response
import requests
import os
from dotenv import load_dotenv

import time

load_dotenv()
USER_AGENT=os.getenv("USER_AGENT")

app = Flask(__name__)

@app.route('/proxy/<persona_id>', methods=['GET'])
def proxy(persona_id):
    token = request.args.get('token')
    endpoint = request.args.get('endpoint', 'user-relationship')

    if not token:
        return "Falta token", 400

    headers = {
        'Accept': 'application/json',
        'User-Agent': USER_AGENT,
    }

    cookies = {'fssessionid': token}

    if endpoint == "family-members":
        url = f"https://www.familysearch.org/service/tree/tree-data/r9/family-members/person/{persona_id}"
        params = {
            'includePhotos': request.args.get('includePhotos', 'true'),
            'treeId': request.args.get('treeId', 'PRIVATE'),
        }
    else:
        url = f"https://www.familysearch.org/service/tree/tree-data/user-relationship/v2/person/{persona_id}"
        params = {
            'showPortraits': request.args.get('showPortraits', 'true'),
            'enforceTemplePolicyEx': request.args.get('enforceTemplePolicyEx', 'true'),
        }

    try:
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=20)
        time.sleep(0.25)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'application/json')
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500
        #https://developers.familysearch.org/main/docs/http-status-codes

if __name__ == "__main__":
    # Correr proxy local en el puerto 5001 (puedes cambiarlo)
    app.run(host='127.0.0.1', port=5001, debug=True)