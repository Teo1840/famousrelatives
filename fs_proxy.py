from flask import Flask, request, jsonify, Response
import requests
import os
import threading
import time
from dotenv import load_dotenv

load_dotenv()

# https://developers.familysearch.org/main/docs/throttling
RATE_LIMIT_INTERVAL = float(os.getenv("RATE_LIMIT_INTERVAL", "0.5"))
MAX_RETRIES_429 = 3

_rate_lock = threading.Lock()
_last_request_time: dict[str, float] = {}
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)
FS_USER_AGENT_CHAIN = os.getenv("FS_USER_AGENT_CHAIN")
DEFAULT_REFERER = os.getenv("DEFAULT_REFERER", "https://www.familysearch.org/")
SEC_CH_UA = os.getenv("SEC_CH_UA", '"Chromium";v="148", "Brave";v="148", "Not/A)Brand";v="99"')
SEC_CH_UA_MOBILE = os.getenv("SEC_CH_UA_MOBILE", "?0")
SEC_CH_UA_PLATFORM = os.getenv("SEC_CH_UA_PLATFORM", '"Windows"')
SEC_GPC = os.getenv("SEC_GPC", "1")
SEC_FETCH_SITE = os.getenv("SEC_FETCH_SITE", "same-origin")

app = Flask(__name__)

fs_session = requests.Session()

@app.route('/proxy/<persona_id>', methods=['GET'])
def proxy(persona_id):
    token = request.args.get('token')
    endpoint = request.args.get('endpoint', 'user-relationship')

    if not token:
        return "Falta token", 400

    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.7',
        'Connection': 'keep-alive',
        'User-Agent': USER_AGENT,
        'Referer': DEFAULT_REFERER,
        'Authorization': f'Bearer {token}',
        'sec-ch-ua': SEC_CH_UA,
        'sec-ch-ua-mobile': SEC_CH_UA_MOBILE,
        'sec-ch-ua-platform': SEC_CH_UA_PLATFORM,
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': SEC_FETCH_SITE,
        'sec-gpc': SEC_GPC,
    }

    if FS_USER_AGENT_CHAIN:
        headers['FS-User-Agent-Chain'] = FS_USER_AGENT_CHAIN

    cookies = {'fssessionid': token}

    if endpoint == "family-members":
        url = f"https://www.familysearch.org/service/tree/tree-data/r9/family-members/person/{persona_id}"
        params = {
            'includePhotos': request.args.get('includePhotos', 'true'),
            'treeId': request.args.get('treeId', 'PRIVATE'),
        }
    elif endpoint == "portrait":
        url = f"https://www.familysearch.org/service/memories/tps/persons/{persona_id}/portrait"
        params = {}
    else:
        url = f"https://www.familysearch.org/service/tree/tree-data/user-relationship/v2/person/{persona_id}"
        params = {
            'showPortraits': request.args.get('showPortraits', 'true'),
            'enforceTemplePolicyEx': request.args.get('enforceTemplePolicyEx', 'true'),
        }

    with _rate_lock:
        now = time.time()
        last = _last_request_time.get(token, 0)
        wait = RATE_LIMIT_INTERVAL - (now - last)
        _last_request_time[token] = max(now, last + RATE_LIMIT_INTERVAL)

    if wait > 0:
        time.sleep(wait)

    try:
        for attempt in range(MAX_RETRIES_429):
            t0 = time.time()
            resp = fs_session.get(url, headers=headers, cookies=cookies, params=params, timeout=20)
            elapsed = time.time() - t0
            processing_ms = resp.headers.get("X-Processing-Time", "?")
            status = resp.status_code
            print(
                f"[proxy] {persona_id} ({endpoint}) → {status} in {elapsed:.2f}s (processing: {processing_ms}ms)",
                flush=True
            )

            if resp.status_code != 429:
                break

            retry_after = int(resp.headers.get("Retry-After", 10))
            print(f"[proxy] 429 — waiting {retry_after}s (attempt {attempt + 1}/{MAX_RETRIES_429})", flush=True)
            with _rate_lock:
                _last_request_time[token] = time.time() + retry_after
            time.sleep(retry_after)

        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get('Content-Type', 'application/json')
        )
    except requests.exceptions.RequestException as e:
        print(f"[proxy] {persona_id} ({endpoint}) → ERROR: {e}", flush=True)
        return jsonify({"error": str(e)}), 500
        #https://developers.familysearch.org/main/docs/http-status-codes

if __name__ == "__main__":
    # Correr proxy local en el puerto 5001 (puedes cambiarlo)
    app.run(host='127.0.0.1', port=5001, debug=True)