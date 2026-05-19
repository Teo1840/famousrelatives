from dotenv import load_dotenv
import os
import threading
from flask import Response, Flask, render_template, request, jsonify

from services.tree_functions import generate_trees
from services.cards import generate_html
from services.csv_validation import validate_csv_file

# -------------------
# CARGA DE .ENV
# -------------------

# 1. .env principal
load_dotenv()

# 2. .env del listener (montado como /app/listener.env en Docker)
load_dotenv("/app/listener.env", override=True)

# -------------------
# DB
# -------------------
from db.db import init_db
init_db()

# -------------------
# PATHS
# -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "famosos.csv")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "plantilla_arboles.html")

app = Flask(__name__, template_folder=TEMPLATE_DIR)

_progress_lock = threading.Lock()
_progress = {"current": 0, "total": 0}

# -------------------
# UTIL
# -------------------
def get_token():
    load_dotenv(override=True)  # Reload .env each time to get latest token
    load_dotenv("/app/listener.env", override=True)
    token = os.getenv("FAMILYSEARCH_TOKEN")
    if not token:
        return None
    return token


def save_token(token):
    env_path = os.path.join(BASE_DIR, ".env")
    lines = []

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f.readlines()]

    token_line = f"FAMILYSEARCH_TOKEN={token}"
    found = False

    for i, line in enumerate(lines):
        if line.startswith("FAMILYSEARCH_TOKEN="):
            lines[i] = token_line
            found = True
            break

    if not found:
        lines.append(token_line)

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")

# -------------------
# ROUTES
# -------------------

@app.route('/')
def index():
    # Página inicial donde el usuario inserta su token
    try:
        with open(CSV_PATH, encoding="utf-8") as f:
            f.read()
        print("Es UTF-8")
    except Exception:
        print("No es UTF-8, probá cp1252")

    token = get_token()
    return render_template("index.html", has_token=bool(token), token=token)


@app.route('/famousrelatives', methods=['POST'])
def famousrelatives():
    token = request.form.get("token") or get_token()

    if not token:
        return render_template(
            "error.html",
            error="No hay token. Pega tu token o ejecuta el listener."
        ), 400

    save_token(token)
    return render_template("loading.html", token=token)


@app.route('/progress')
def progress():
    with _progress_lock:
        return jsonify(dict(_progress))


@app.route('/process', methods=['POST'])
def process():
    token = request.form.get("token") or get_token()

    if not token:
        return render_template(
            "error.html",
            error="No hay token. Pega tu token o ejecuta el listener."
        ), 400

    # Leer CSV
    try:
        rows = validate_csv_file(CSV_PATH)
    except ValueError as e:
        return render_template("error.html", error=str(e)), 400

    total = len(rows)
    with _progress_lock:
        _progress["current"] = 0
        _progress["total"] = total

    def on_progress(current):
        with _progress_lock:
            _progress["current"] = current

    # Procesar
    arboles = generate_trees(rows, token, on_progress=on_progress)

    with _progress_lock:
        _progress["current"] = total

    arboles_ordenados = sorted(arboles, key=lambda a: a["cercania"])

    # Generar HTML
    html_content = generate_html(TEMPLATE_PATH, arboles_ordenados)

    return Response(html_content, mimetype='text/html')


# -------------------
# RUN
# -------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)