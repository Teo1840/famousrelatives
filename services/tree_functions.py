import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from db.db import obtener_arbol, guardar_arbol, guardar_retrato_usuario
import os
import requests

# --Simplificar JSON--
def build_person(person):
    if not person:
        return {"nombre": "", "id": "", "lifespan": "", "portraitUrl": None, "gender": ""}

    name = person.get("nameConclusion", {})
    details = name.get("details", {})

    person_id = person.get("id", "")
    is_me = person.get("relationshipToPrevious") == "ME"

    # viewer portrait URL from the API requires auth headers and can't load in <img>
    # it gets replaced later via the /portrait endpoint → _links.thumbSquare.href
    portrait = None if is_me else person.get("portraitUrl")

    return {
        "nombre": details.get("fullText", ""),
        "id": person_id,
        "lifespan": person.get("lifespan", ""),
        "portraitUrl": portrait,
        "gender": person.get("gender", "")
    }

# --Pasar de JSON a lists--
def process_json(generations):
    asc = []
    desc = []
    ancestor = build_person(None)
    viewer_id = None
    is_coParentIsPathPerson = False

    for gen in generations:
        #ANTEPASADO COMUN
        if "apex" in gen:
            person = gen["apex"].get("person", {})
            if person.get("commonAncestor", False):
                ancestor = build_person(person)
            else:
                asc.append(build_person(person))
            continue
        # Ascendentes
        asc_side = gen.get("ascendingSide")
        if asc_side:
            person=build_person(asc_side.get("person"))
            if asc_side.get("coParentIsPathPerson", False):  # Target Person es pariente de mi conyugue
                is_coParentIsPathPerson=True
                coParent=build_person(asc_side.get("coParent"))
                # "conyuge": la unión de este nodo con el anterior (más cerca del
                # antepasado común) es un matrimonio, no un vínculo de sangre.
                person["conyuge"] = True
                asc.append(coParent)
                asc.append(person)

            else:
                asc.append(person)

            if asc_side.get("indexInPath")==0: # Puedo preguntar por la ultima persona en asc_side??
                viewer_id=person.get("id") # Obtener viewer_id
        # Descendentes
        desc_side = gen.get("descendingSide")
        if desc_side:
            person=build_person(desc_side.get("person"))
            if desc_side.get("coParentIsTargetPerson", False):  # Target Person es conyugue de mi pariente
                coParent=build_person(desc_side.get("coParent"))
                coParent["conyuge"] = True
                desc.append(person)
                desc.append(coParent)
            else:
                desc.append(person)

    return asc, desc, ancestor, viewer_id, is_coParentIsPathPerson

# --Generar Session--
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 127.0.0.1 y no "localhost": en Windows "localhost" va primero a IPv6 (::1),
# y si otro programa (ej. un contenedor Docker) usa el puerto 5001 en ::1,
# las consultas le llegan a él en vez de a fs_proxy.py (que escucha solo en 127.0.0.1).
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
# Consultas en paralelo a FamilySearch. Más hilos = más rápido pero más 429.
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
# Segundos entre consultas a FamilySearch durante "Actualizar mis árboles".
FORCE_REFRESH_RATE_INTERVAL = float(os.getenv("FORCE_REFRESH_RATE_INTERVAL", "0.5"))

def get_session(rate_interval=None):
    session = requests.Session()
    if rate_interval is not None:
        # Se agrega como ?rate=... a cada consulta al proxy.
        session.params = {"rate": str(rate_interval)}

    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)

    return session


# --Sentinel: API confirmed no relationship (HTTP 204). Distinct from None
# (transient/unexpected error), which must never be cached.--
class _NoRelationship:
    pass

NO_RELATIONSHIP = _NoRelationship()


# --Thread-safe viewer id state--
class ViewerState:
    def __init__(self):
        self._lock = threading.Lock()
        self.person_id = None

    def try_set_person_id(self, pid):
        with self._lock:
            if self.person_id is None and pid:
                self.person_id = pid


# --Per-person processing (called from thread pool)--
def _process_one(codigo, session, token, viewer_state, user_id, force_refresh, counter, total, on_progress):
    persona_id = codigo["person_code"]
    name = codigo.get("name", persona_id)
    t_start = time.time()

    # Cache
    cached = get_cached_tree(persona_id, user_id, force_refresh=force_refresh)
    if cached is NO_RELATIONSHIP:
        n = counter()
        if on_progress:
            on_progress(n)
        print(f"[{n}/{total}] {name} — cache negativo ({time.time() - t_start:.2f}s)", flush=True)
        return None
    if cached:
        cached["topics"] = codigo.get("topics", [])
        n = counter()
        if on_progress:
            on_progress(n)
        print(f"[{n}/{total}] {name} — cache ({time.time() - t_start:.2f}s)", flush=True)
        return cached

    # API
    try:
        data = fetch_tree_from_api(session, persona_id, token)
    except Exception as e:
        if str(e) == "SESSION_EXPIRED":
            raise
        return None

    if data is None:
        n = counter()
        if on_progress:
            on_progress(n)
        print(f"[{n}/{total}] {name} — error transitorio ({time.time() - t_start:.2f}s)", flush=True)
        return None

    if data is NO_RELATIONSHIP:
        _maybe_cache_negative(persona_id, user_id, viewer_state.person_id)
        n = counter()
        if on_progress:
            on_progress(n)
        print(f"[{n}/{total}] {name} — sin relación confirmada ({time.time() - t_start:.2f}s)", flush=True)
        return None

    parsed = parse_tree_data(data)
    if not parsed:
        _maybe_cache_negative(persona_id, user_id, viewer_state.person_id)
        n = counter()
        if on_progress:
            on_progress(n)
        print(f"[{n}/{total}] {name} — sin relación confirmada ({time.time() - t_start:.2f}s)", flush=True)
        return None

    viewer_state.try_set_person_id(parsed["viewer_id"])

    # Build (coParentIsTargetPerson / coParentIsPathPerson path)
    target = parsed["target"]
    coParentIsTargetPerson = target.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE")
    coParentIsPathPerson = parsed["coParentIsPathPerson"]
    extra_parsed = None
    # False si el camino directo no se pudo buscar por un error pasajero:
    # el árbol se guarda igual, pero el cache lo vuelve a buscar la próxima vez.
    direct_checked = True
    if coParentIsTargetPerson or coParentIsPathPerson:
        parent_id, parent_ok = fetch_parent_id(session, persona_id, token)
        if parent_id:
            extra_data = fetch_tree_from_api(session, parent_id, token)
            if extra_data is None:
                direct_checked = False
            elif extra_data is not NO_RELATIONSHIP:
                extra_parsed = parse_tree_data(extra_data)
        elif not parent_ok:
            direct_checked = False

    tree = build_tree_data(parsed, codigo, extra_parsed)
    tree["directPathChecked"] = direct_checked

    save_tree(persona_id, user_id, viewer_state.person_id, tree)

    n = counter()
    if on_progress:
        on_progress(n)
    print(f"[{n}/{total}] {name} — {time.time() - t_start:.2f}s", flush=True)
    return tree


# --Generar un Arbol por codigo incluyendo su JSON respectivo--
def generate_trees(codigos, token, user_id, force_refresh=False, on_progress=None):
    session = get_session(FORCE_REFRESH_RATE_INTERVAL if force_refresh else None)
    total = len(codigos)
    viewer_state = ViewerState()

    _cnt_lock = threading.Lock()
    _cnt = [0]

    def counter():
        with _cnt_lock:
            _cnt[0] += 1
            return _cnt[0]

    session_expired = threading.Event()
    results = {}

    def submit_one(i, codigo):
        if session_expired.is_set():
            return i, None
        try:
            tree = _process_one(codigo, session, token, viewer_state, user_id,
                                force_refresh, counter, total, on_progress)
            return i, tree
        except Exception as e:
            if str(e) == "SESSION_EXPIRED":
                session_expired.set()
                print("⚠️ La sesión expiró. Interrumpiendo proceso.", flush=True)
            else:
                print(f"❌ Error procesando {codigo.get('name', codigo.get('person_code'))}: {e!r}", flush=True)
            return i, None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(submit_one, i, c): i for i, c in enumerate(codigos)}
        for fut in as_completed(futures):
            i, tree = fut.result()
            if tree:
                results[i] = tree

    trees = [results[i] for i in sorted(results)]

    # Foto de perfil del usuario: se guarda aparte (no dentro de cada árbol, que
    # ya se guardó) y se aplica al servir los árboles (ver app.py). Si todo vino
    # del cache no hubo respuesta de la API con el ID: se toma de un árbol.
    viewer_id = viewer_state.person_id or _viewer_id_from_trees(trees)
    if viewer_id and not session_expired.is_set():
        try:
            portrait_url = fetch_viewer_portrait(session, viewer_id, token)
        except Exception as e:
            print(f"⚠️ No se pudo obtener la foto de perfil: {e!r}", flush=True)
            portrait_url = None
        if portrait_url:
            guardar_retrato_usuario(user_id, viewer_id, portrait_url)
            for tree in trees:
                apply_viewer_portrait(tree, viewer_id, portrait_url)
        else:
            print("⚠️ FamilySearch no devolvió foto de perfil para el usuario", flush=True)

    print(f"{len(trees)}/{total} mini árboles procesados", flush=True)
    return trees


#CACHE
# Cache never expires on its own: a person's cached result (found or not) is
# reused indefinitely once written. It's only bypassed by force_refresh, or
# naturally missed for a person_code that has no row yet for this user_id
# (e.g. newly added to famosos.csv).
def get_cached_tree(persona_id, user_id, force_refresh=False):
    if force_refresh:
        return None

    cached_data, created_at, found = obtener_arbol(persona_id, user_id)

    if created_at is None:
        return None

    if not found:
        print(f"💾 Cache negativo válido para {persona_id}", flush=True)
        return NO_RELATIONSHIP

    if cached_data and cached_data.get("name") and cached_data.get("person_code"):
        if _direct_path_pending(cached_data):
            print(f"♻️ Falta el camino directo para {persona_id}, se vuelve a buscar", flush=True)
            return None
        print(f"💾 Cache válido para {persona_id}", flush=True)
        return cached_data

    print(f"♻️ Cache inválido para {persona_id}", flush=True)
    return None


def _direct_path_pending(tree):
    """Árbol que necesita camino directo, no lo tiene y no se confirmó que no exista
    (falló la consulta extra, o se guardó antes de existir este chequeo)."""
    needs_direct = tree.get("coParentIsTargetPerson") or (tree.get("mainPath") or {}).get("coParentIsPathPerson")
    return bool(needs_direct) and tree.get("directPath") is None and not tree.get("directPathChecked")


def save_tree(persona_id, user_id, viewer_person_id, tree_data):
    guardar_arbol(persona_id, user_id, viewer_person_id, tree_data)


def save_negative_tree(persona_id, user_id, viewer_person_id):
    guardar_arbol(persona_id, user_id, viewer_person_id, None, found_relationship=False)


def _maybe_cache_negative(persona_id, user_id, viewer_person_id):
    save_negative_tree(persona_id, user_id, viewer_person_id)

#FETCHING API
def fetch_tree_from_api(session, person_id, token, endpoint=None):
    base_url = f"http://{PROXY_HOST}:5001/proxy/{person_id}?token={token}"

    if endpoint:
        base_url += f"&endpoint={endpoint}"

    try:
        response = session.get(base_url, timeout=20)
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout para {person_id}", flush=True)
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión para {person_id}: {e}", flush=True)
        return None

    if response.status_code == 200:
        return response.json()

    if response.status_code == 204:
        return NO_RELATIONSHIP

    if response.status_code == 401:
        raise Exception("SESSION_EXPIRED")

    print(f"❌ Error {response.status_code}: {response.text}", flush=True)
    return None

#PARSER
def parse_tree_data(data):
    generations = data.get("generations", [])
    if not generations:
        return None

    asc, desc, ancestor, viewer_id, coParentIsPathPerson = process_json(generations)

    return {
        "asc": asc,
        "desc": desc,
        "ancestor": ancestor,
        "viewer_id": viewer_id,
        "coParentIsPathPerson": coParentIsPathPerson,
        "target": data.get("targetPerson", {}),
        "relationship": data.get("relationshipDescription")
    }

#BUILDER
def build_tree_data(parsed, codigo, extra_parsed=None):

    asc = parsed["asc"]
    desc = parsed["desc"]
    apex = parsed["ancestor"] or {}
    coParentIsPathPerson = parsed["coParentIsPathPerson"]
    main_path = {
        "asc": asc,
        "desc": desc,
        "antepasado_comun": apex,
        "coParentIsPathPerson": coParentIsPathPerson
    }
    main_length = getPathLength(main_path)

    direct_path = None
    direct_length = main_length

    target = parsed["target"]
    coParentIsTargetPerson = target.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE")

    if (coParentIsTargetPerson or coParentIsPathPerson) and extra_parsed:
        extra_asc = extra_parsed["asc"]
        extra_desc = extra_parsed["desc"][:]
        extra_apex = extra_parsed["ancestor"]

        if len(extra_desc) > 0:
            extra_desc.pop()

        extra_target = build_person(target)
        extra_desc.append(extra_target)

        extra_coParentIsPathPerson = extra_parsed["coParentIsPathPerson"]

        direct_path = {
            "asc": extra_asc,
            "desc": extra_desc,
            "antepasado_comun": extra_apex,
            "coParentIsPathPerson": extra_coParentIsPathPerson
        }

        direct_length = getPathLength(direct_path)

    return {
        "person_code": codigo["person_code"],
        "name": codigo["name"],
        "info": codigo["info"],
        "topics": codigo.get("topics", []),

        "cercania": main_length,

        "relationshipDescription": parsed["relationship"],

        "portraitUrl": target.get(
            "portraitUrl",
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png"
        ),

        "coParentIsTargetPerson": coParentIsTargetPerson,

        "mainPath": main_path,
        "directPath": direct_path,

        "direct_length": direct_length
    }

def getPathLength(path):
    return len(path.get("asc", [])) + len(path.get("desc", []))

def fetch_viewer_portrait(session, person_id, token):
    data = fetch_tree_from_api(session, person_id, token, endpoint="portrait")
    if not data:
        return None
    return data.get("_links", {}).get("thumbSquare", {}).get("href")


def fetch_current_user(token):
    """(person_id, nombre) de la cuenta de FamilySearch dueña del token.
    None si no se pudo consultar; lanza SESSION_EXPIRED si el token no sirve."""
    data = fetch_tree_from_api(get_session(), "me", token, endpoint="current-user")
    if not isinstance(data, dict):
        return None
    user = (data.get("users") or [{}])[0]
    person_id = user.get("personId")
    if not person_id:
        return None
    name = user.get("displayName") or user.get("contactName") or person_id
    return person_id, name


def _viewer_id_from_trees(trees):
    for tree in trees:
        asc = (tree.get("mainPath") or {}).get("asc") or []
        if asc and asc[-1].get("id"):
            return asc[-1]["id"]
    return None


def apply_viewer_portrait(tree, viewer_id, portrait_url):
    for path_key in ("mainPath", "directPath"):
        path = tree.get(path_key)
        if not path:
            continue
        for node_list in (path.get("asc", []), path.get("desc", [])):
            for node in node_list:
                if node.get("id") == viewer_id:
                    node["portraitUrl"] = portrait_url


#GET PARENT FOR DIRECT PATH
def fetch_parent_id(session, person_id, token):
    """Devuelve (parent_id, ok). ok=False si la consulta falló (error pasajero);
    ok=True con parent_id=None si FamilySearch confirma que no tiene padres."""
    data = fetch_tree_from_api(
        session,
        person_id,
        token,
        endpoint="family-members"
    )

    if data is None:
        return None, False

    if data is NO_RELATIONSHIP:
        return None, True

    parents = data.get("parents", [])
    if not parents:
        return None, True

    parent1 = parents[0].get("parent1")
    parent2 = parents[0].get("parent2")

    if parent1 and parent1.get("id"):
        return parent1.get("id"), True

    if parent2 and parent2.get("id"):
        return parent2.get("id"), True

    return None, True
