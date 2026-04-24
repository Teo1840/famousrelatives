from flask import Flask, request, jsonify, Response
import requests
import os
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

load_dotenv()
USER_AGENT = os.getenv("USER_AGENT")

app = Flask(__name__)

# 🔹 Headers base (no recrearlos cada vez)
BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'User-Agent': USER_AGENT,
}

# 🔹 Session global con pool + retries
session = requests.Session()

retries = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)

adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=retries
)

session.mount("https://", adapter)


@app.route('/proxy/<persona_id>', methods=['GET'])
def proxy(persona_id):

    token = request.args.get('token')
    if not token:
        return "Falta token", 400

    # 🔹 params dinámicos
    params = {
        'showPortraits': request.args.get('showPortraits', 'true'),
        'enforceTemplePolicyEx': request.args.get('enforceTemplePolicyEx', 'true'),
    }

    cookies = {'fssessionid': token}

    url = f"https://www.familysearch.org/service/tree/tree-data/user-relationship/v2/person/{persona_id}"

    try:
        resp = session.get(
            url,
            headers=BASE_HEADERS,
            cookies=cookies,
            params=params,
            timeout=20
        )

        # 🔹 throttling simple (evitar bloqueo)
        time.sleep(0.25)

        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'application/json')
        )

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5001, debug=True)