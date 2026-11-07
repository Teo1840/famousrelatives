from dotenv import load_dotenv
import os
import subprocess
import threading
import time
import urllib.request
import zlib
import logging
from functools import wraps
from flask import Response, Flask, render_template, request, jsonify, session, redirect, url_for

from services.tree_functions import generate_trees, apply_viewer_portrait, fetch_current_user
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
    obtener_o_crear_usuario_fs,
    obtener_arboles_usuario,
    obtener_version_arboles,
    obtener_ids_procesados,
    obtener_retrato_usuario,
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
        msg = record.getMessage()
        return not any(p in msg for p in ("/progress", "/api/personas-nuevas", "/capture-status"))

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
    """Corta un `node listen.js` que haya quedado de un intento anterior
    (por ejemplo, si el reloader de Werkzeug reinició a mitad de captura).
    No toca el navegador: es la misma ventana donde está abierta la app."""
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


def _debug_browser_running():
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2):
            return True
    except Exception:
        return False


def _run_capture():
    """Abre FamilySearch en una pestaña nueva del navegador donde está la app
    (start-system.bat lo abre con el puerto de depuración 9222). Si ese
    navegador no está abierto, lo abre con el mismo perfil."""
    global _capture_status
    try:
        _kill_stale_capture_state()
        _clear_env_token()

        if not _debug_browser_running():
            subprocess.Popen([
                BRAVE_PATH,
                "--remote-debugging-port=9222",
                f"--user-data-dir={PROFILE_DIR}",
                "--no-first-run",
                "--start-maximized",
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
        with _capture_lock:
            if returncode == 0 and token:
                _capture_status = {"state": "done", "error": None}
            else:
                _capture_status = {"state": "error", "error": "El listener no pudo capturar el token"}
    except FileNotFoundError as e:
        with _capture_lock:
            _capture_status = {"state": "error", "error": f"No se pudo iniciar el proceso: {e}"}
    except Exception as e:
        with _capture_lock:
            _capture_status = {"state": "error", "error": str(e)}


def _found_trees(user_id):
    cache_rows = obtener_arboles_usuario(user_id)
    trees = [r["data"] for r in cache_rows if r["found"] and r["data"]]

    # Datos del CSV (temas, descripción, link a Wikipedia) siempre al día, sin
    # tener que volver a consultar FamilySearch al editar famosos.csv.
    try:
        csv_rows = {r["person_code"]: r for r in validate_csv_file(CSV_PATH)}
    except ValueError:
        csv_rows = {}
    for tree in trees:
        row = csv_rows.get(tree.get("person_code"))
        if row:
            tree["topics"] = row["topics"]
            tree["info"] = row["info"]
            tree["wiki"] = row["wiki"]
            tree["paises"] = row["paises"]
    viewer_id, portrait_url = obtener_retrato_usuario(user_id)
    if viewer_id and portrait_url:
        for tree in trees:
            apply_viewer_portrait(tree, viewer_id, portrait_url)
    return trees


def _version_arboles(user_id):
    # Incluye la foto de perfil y famosos.csv: si cambian, el navegador vuelve
    # a pedir los árboles en vez de usar su copia local.
    _, portrait_url = obtener_retrato_usuario(user_id)
    try:
        csv_mtime = int(os.path.getmtime(CSV_PATH))
    except OSError:
        csv_mtime = 0
    return f"{obtener_version_arboles(user_id)}-{zlib.crc32((portrait_url or '').encode()):x}-{csv_mtime}"


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

def _iniciar_sesion_fs(token):
    """Abre la sesión de la app con la cuenta de FamilySearch dueña del token.
    No hay usuario ni contraseña propios: la cuenta de FamilySearch es el usuario.
    Devuelve None si salió bien, o el mensaje de error."""
    try:
        cuenta = fetch_current_user(token)
    except Exception as e:
        if str(e) == "SESSION_EXPIRED":
            return "FamilySearch rechazó el token. Volvé a iniciar sesión."
        return f"No se pudo consultar FamilySearch: {e}"
    if not cuenta:
        return "No se pudo saber qué cuenta de FamilySearch inició sesión. ¿Está corriendo el proxy?"

    person_id, nombre = cuenta
    user_id = obtener_o_crear_usuario_fs(person_id)
    if session.get("user_id") != user_id:
        session.clear()  # otra cuenta: no mezclar nada de la anterior
    session["user_id"] = user_id
    session["username"] = nombre
    session["familysearch_token"] = token
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if "user_id" in session:
            return redirect(url_for("index"))
        # Después de cerrar sesión no se abre FamilySearch solo.
        return render_template("login.html", auto_start=request.args.get("salir") is None)

    # Token pegado a mano (alternativa al capturador).
    token = request.form.get("token", "").strip()
    if not token:
        return render_template("login.html", error="Pegá un token.", auto_start=False), 400
    error = _iniciar_sesion_fs(token)
    if error:
        return render_template("login.html", error=error, auto_start=False), 400
    return redirect(url_for("index"))


@app.route('/logout')
def logout():
    session.clear()
    # Si no, el próximo inicio de sesión tomaría el mismo token sin pasar por FamilySearch.
    _clear_env_token()
    return redirect(url_for("login", salir=1))


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
    return jsonify({"version": _version_arboles(session["user_id"])})


@app.route('/api/arboles')
@login_required
def arboles_api():
    user_id = session["user_id"]
    # La versión se lee antes que los datos: si algo se guarda en el medio,
    # el navegador queda con una versión vieja y los vuelve a pedir la próxima vez.
    version = _version_arboles(user_id)
    return jsonify({
        "version": version,
        "arboles": serializar_arboles(_found_trees(user_id)),
    })


@app.route('/api/personas-nuevas')
@login_required
def personas_nuevas():
    """Cuántas personas del CSV todavía no se consultaron para este usuario.
    El header lo usa para mostrar el punto rojo en "Buscar personas nuevas"."""
    try:
        rows = validate_csv_file(CSV_PATH)
    except ValueError:
        return jsonify({"count": 0})
    procesados = obtener_ids_procesados(session["user_id"])
    nuevas = [r["person_code"] for r in rows if r["person_code"] not in procesados]
    return jsonify({"count": len(nuevas)})


@app.route('/progress')
@login_required
def progress():
    with _progress_lock:
        state = _progress.get(session["user_id"], {"current": 0, "total": 0, "running": False})
        return jsonify(dict(state))


@app.route('/capture-token', methods=['POST'])
def capture_token():
    global _capture_status
    with _capture_lock:
        if _capture_status["state"] == "waiting":
            # Ya hay una captura abierta: esta página espera la misma.
            return jsonify({"started": True})
        _capture_status = {"state": "waiting", "error": None}

    threading.Thread(target=_run_capture, daemon=True).start()
    return jsonify({"started": True})


@app.route('/capture-status')
def capture_status():
    with _capture_lock:
        status = dict(_capture_status)

    if status["state"] == "done":
        # El token queda solo en la sesión de este navegador, nunca en la BD.
        # Con él se sabe qué cuenta de FamilySearch entró y se abre la sesión.
        token = get_env_captured_token()
        error = _iniciar_sesion_fs(token) if token else "No se encontró el token capturado."
        if error:
            status = {"state": "error", "error": error}

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