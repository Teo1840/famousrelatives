from flask import Flask, request, jsonify, Response
import requests
import os
from dotenv import load_dotenv

load_dotenv()
USER_AGENT=os.getenv("USER_AGENT")

app = Flask(__name__)

@app.route('/proxy/<persona_id>', methods=['GET'])
def proxy(persona_id):
    # Leer headers y cookies desde query params
    token = request.args.get('token')
    if not token:
        return "Falta token", 400
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': USER_AGENT,
    }
    cookies = {'fssessionid': token}
    show_portraits = request.args.get('showPortraits', 'true')
    enforce_temple = request.args.get('enforceTemplePolicyEx', 'true')
    params = {
        'showPortraits': show_portraits,
        'enforceTemplePolicyEx': enforce_temple,
    }
    url = f"https://www.familysearch.org/service/tree/tree-data/user-relationship/v2/person/{persona_id}"
    #https://www.familysearch.org/service/tree/tree-data/user-relationship/v2/person/{persona_id}?showPortraits=true&enforceTemplePolicyEx=true

    try:
        resp = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=20)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'application/json')
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Correr proxy local en el puerto 5001 (puedes cambiarlo)
    app.run(host='127.0.0.1', port=5001, debug=True)