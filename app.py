from dotenv import load_dotenv
import os
import shutil
import subprocess
import threading
import time
import logging
from functools import wraps
from flask import Response, Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash

from services.tree_functions import generate_trees
from services.cards import generate_html, serializar_arboles
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
from db.db import (
    init_db,
    crear_usuario,
    obtener_usuario_por_username,
    obtener_arboles_usuario,
    obtener_version_arboles,
    DuplicateUsernameError,
)
init_db()

# -------------------
# PATHS
# -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "famosos.csv")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "plantilla_arboles.html")

app = Flask(__name__, template_folder=TEMPLATE_DIR)

app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY must be set in .env for session support")


def login_required(view_fn):
    @wraps(view_fn)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_fn(*args, **kwargs)
    return wrapped

class _SuppressProgressLogs(logging.Filter):
    def filter(self, record):
        return "/progress" not in record.getMessage()

logging.getLogger("werkzeug").addFilter(_SuppressProgressLogs())

# Progreso del procesamiento en segundo plano, por usuario:
# user_id -> {"current", "total", "running"}
_progress_lock = threading.Lock()
_progress = {}

# "Actualizar todo" (force_refresh) re-fetches every person from FamilySearch
# instead of using the cache, so it's rate-limited per account.
FORCE_REFRESH_COOLDOWN_SECONDS = 5 * 60
_force_refresh_lock = threading.Lock()
_last_force_refresh = {}  # user_id -> last time.time() it ran

# -------------------
# UTIL
# -------------------

def get_token():
    """Returns the FamilySearch token captured/pasted during this browser
    session, or None. Never persisted server-side: it lives only in the
    session cookie, so it's gone once the browser closes or the user logs out."""
    return session.get("familysearch_token")


def get_env_captured_token():
    """Reads whatever the browser-capture listener most recently wrote to .env."""
    load_dotenv(override=True)  # Reload .env each time to get latest token
    load_dotenv("/app/listener.env", override=True)
    return os.getenv("FAMILYSEARCH_TOKEN") or None


# -------------------
# TOKEN CAPTURE AUTOMATION
# -------------------
# LIMITATION: listener/listen.js captures one FamilySearch login into .env at a
# time via a single shared Chrome debug profile on this machine. Two accounts
# cannot capture two different FamilySearch identities simultaneously - usage
# must be sequential: log in via the browser, then whoever polls /capture-status
# next claims the captured token into their own session.
LISTENER_DIR = os.path.join(BASE_DIR, "listener")
PROFILE_DIR = os.path.join(BASE_DIR, "chrome_debug_profile")
BRAVE_PATH = os.getenv(
    "BRAVE_PATH",
    r"C:\Users\abc\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
)

_capture_lock = threading.Lock()
_capture_status = {"state": "idle", "error": None}  # idle | waiting | done | error | timeout


def _clear_env_token():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    lines = [line for line in lines if not line.startswith("FAMILYSEARCH_TOKEN=")]
    lines.append("FAMILYSEARCH_TOKEN=")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")


def _kill_stale_capture_state():
    """Defensively clear any leftover Brave (9222 debug port /
    chrome_debug_profile) or `node listen.js` process from a previous capture
    attempt - including one orphaned by the Werkzeug reloader restarting
    mid-capture - so every attempt starts from a clean state. Best-effort:
    must never block a capture attempt if the cleanup itself fails."""
    try:
        subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", os.path.join(BASE_DIR, "stop-system.ps1"),
                "-Scope", "CaptureOnly", "-Quiet",
            ],
            timeout=30,
        )
    except Exception:
        pass


def _run_capture():
    global _capture_status
    brave_proc = None
    close_brave_on_exit = True
    try:
        _kill_stale_capture_state()
        _clear_env_token()
        shutil.rmtree(PROFILE_DIR, ignore_errors=True)

        brave_proc = subprocess.Popen([
            BRAVE_PATH,
            "--remote-debugging-port=9222",
            f"--user-data-dir={PROFILE_DIR}",
            "--disable-session-restore",
            "--no-first-run",
            "--new-window",
            "--start-maximized",
            "https://www.familysearch.org/en/global",
        ])

        listener_proc = subprocess.Popen(["node", "listen.js"], cwd=LISTENER_DIR)

        try:
            returncode = listener_proc.wait(timeout=600)
        except subprocess.TimeoutExpired:
            listener_proc.kill()
            with _capture_lock:
                _capture_status = {"state": "timeout", "error": "Tiempo de espera agotado"}
            return

        token = get_env_captured_token()
        if returncode == 0 and token:
            with _capture_lock:
                _capture_status = {"state": "done", "error": None}
            close_brave_on_exit = False  # capture succeeded, leave the window open
        else:
            with _capture_lock:
                _capture_status = {"state": "error", "error": "El listener no pudo capturar el token"}
    except FileNotFoundError as e:
        with _capture_lock:
            _capture_status = {"state": "error", "error": f"No se pudo iniciar el proceso: {e}"}
    except Exception as e:
        with _capture_lock:
            _capture_status = {"state": "error", "error": str(e)}
    finally:
        if close_brave_on_exit and brave_proc is not None and brave_proc.poll() is None:
            try:
                brave_proc.kill()
            except Exception:
                pass


def _found_trees(user_id):
    cache_rows = obtener_arboles_usuario(user_id)
    return [r["data"] for r in cache_rows if r["found"] and r["data"]]


def _build_dashboard_page():
    token = get_token()
    header_html = render_template(
        "dashboard_header.html",
        has_token=bool(token)
    )
    return generate_html(TEMPLATE_PATH, session["user_id"], header_html=header_html)


# -------------------
# ROUTES
# -------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    personal_id = request.form.get("personal_id", "")

    if not username or not personal_id:
        return render_template("register.html", error="Usuario e ID personal son obligatorios"), 400

    try:
        user_id = crear_usuario(username, personal_id)
    except DuplicateUsernameError:
        return render_template("register.html", error="Ese usuario ya existe"), 400

    session["user_id"] = user_id
    session["username"] = username
    return redirect(url_for("index"))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    personal_id = request.form.get("personal_id", "")

    user = obtener_usuario_por_username(username)
    if not user or not check_password_hash(user["password_hash"], personal_id):
        return render_template("login.html", error="Usuario o ID personal incorrecto"), 400

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect(url_for("index"))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route('/')
@login_required
def index():
    return Response(_build_dashboard_page(), mimetype='text/html')


@app.route('/famousrelatives', methods=['POST'])
@login_required
def famousrelatives():
    submitted = request.form.get("token")
    captured = submitted or get_token() or get_env_captured_token()

    if not captured:
        return render_template(
            "error.html",
            error="No hay token. Pega tu token o ejecuta el capturador."
        ), 400

    session["familysearch_token"] = captured
    force_refresh = request.form.get("force_refresh") == "on"
    return render_template("loading.html", token=get_token(), force_refresh=force_refresh)


@app.route('/api/arboles/version')
@login_required
def arboles_version():
    return jsonify({"version": obtener_version_arboles(session["user_id"])})


@app.route('/api/arboles')
@login_required
def arboles_api():
    user_id = session["user_id"]
    # La versión se lee antes que los datos: si algo se guarda en el medio,
    # el navegador queda con una versión vieja y los vuelve a pedir la próxima vez.
    version = obtener_version_arboles(user_id)
    return jsonify({
        "version": version,
        "arboles": serializar_arboles(_found_trees(user_id)),
    })


@app.route('/progress')
@login_required
def progress():
    with _progress_lock:
        state = _progress.get(session["user_id"], {"current": 0, "total": 0, "running": False})
        return jsonify(dict(state))


@app.route('/capture-token', methods=['POST'])
@login_required
def capture_token():
    global _capture_status
    with _capture_lock:
        if _capture_status["state"] == "waiting":
            return jsonify({"started": False, "error": "Ya hay una captura en curso."})
        _capture_status = {"state": "waiting", "error": None}

    threading.Thread(target=_run_capture, daemon=True).start()
    return jsonify({"started": True})


@app.route('/capture-status')
@login_required
def capture_status():
    with _capture_lock:
        status = dict(_capture_status)

    if status["state"] == "done":
        # Claim the capture into *this* browser session only - never the DB.
        token = get_env_captured_token()
        if token:
            session["familysearch_token"] = token

    return jsonify(status)


@app.route('/process', methods=['POST'])
@login_required
def process():
    token = request.form.get("token") or get_token()

    if not token:
        return render_template(
            "error.html",
            error="No hay token. Pega tu token o ejecuta el capturador."
        ), 400

    force_refresh = request.form.get("force_refresh") == "on"
    user_id = session["user_id"]

    # Si ya se está procesando para este usuario, solo mostrar el dashboard:
    # sigue recibiendo los árboles nuevos a medida que se guardan.
    with _progress_lock:
        if _progress.get(user_id, {}).get("running"):
            return Response(_build_dashboard_page(), mimetype='text/html')

    if force_refresh:
        with _force_refresh_lock:
            now = time.time()
            last = _last_force_refresh.get(session["user_id"])
            elapsed = now - last if last is not None else None
            if elapsed is not None and elapsed < FORCE_REFRESH_COOLDOWN_SECONDS:
                remaining = int(FORCE_REFRESH_COOLDOWN_SECONDS - elapsed)
                mins, secs = divmod(remaining, 60)
                return render_template(
                    "error.html",
                    error=f"Actualizar todo está limitado a una vez cada 5 minutos. Esperá {mins}m {secs}s."
                ), 429
            _last_force_refresh[session["user_id"]] = now

    # Leer CSV
    try:
        rows = validate_csv_file(CSV_PATH)
    except ValueError as e:
        return render_template("error.html", error=str(e)), 400

    total = len(rows)
    with _progress_lock:
        if _progress.get(user_id, {}).get("running"):
            return Response(_build_dashboard_page(), mimetype='text/html')
        _progress[user_id] = {"current": 0, "total": total, "running": True}

    def on_progress(current):
        with _progress_lock:
            _progress[user_id]["current"] = current

    # Procesar en segundo plano: cada árbol se guarda en la BD al terminarlo y
    # el dashboard los va pidiendo mientras /progress diga running.
    def run():
        try:
            generate_trees(rows, token, user_id, force_refresh=force_refresh, on_progress=on_progress)
        except Exception as e:
            print(f"❌ Error procesando árboles: {e}", flush=True)
        finally:
            with _progress_lock:
                _progress[user_id] = {"current": total, "total": total, "running": False}

    threading.Thread(target=run, daemon=True).start()

    return Response(_build_dashboard_page(), mimetype='text/html')


# -------------------
# RUN
# -------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)