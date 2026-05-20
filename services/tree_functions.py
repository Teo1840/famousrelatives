import time
from datetime import datetime, timedelta
from db.db import obtener_arbol, guardar_arbol
import os
import requests

# --Simplificar JSON--
#def viewer_person
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
        is_coParentIsPathPerson=False
        if asc_side:
            person=build_person(asc_side.get("person"))
            if asc_side.get("coParentIsPathPerson", False):  # Target Person es pariente de mi conyugue
                is_coParentIsPathPerson=True
                coParent=build_person(asc_side.get("coParent"))
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
                desc.append(person)
                desc.append(coParent)
            else:
                desc.append(person)

    return asc, desc, ancestor, viewer_id, is_coParentIsPathPerson

# --Generar Session--
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROXY_HOST = os.getenv("PROXY_HOST", "localhost")

def get_session():
    session = requests.Session()

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

# --Generar un Arbol por codigo incluyendo su JSON respectivo--
def generate_trees(codigos, token, on_progress=None):
    session = get_session()
    trees = []

    current = 0
    total = len(codigos)

    viewer_person_id = None  # ⚠️
    viewer_portrait_url = None
    viewer_portrait_fetched = False

    for codigo in codigos:
        persona_id = codigo["person_code"]
        name = codigo.get("name", persona_id)
        t_start = time.time()

        # 🔹 Cache
        cached = get_cached_tree(persona_id, viewer_person_id)
        if cached:
            if viewer_person_id and not viewer_portrait_fetched:
                viewer_portrait_url = fetch_viewer_portrait(session, viewer_person_id, token)
                viewer_portrait_fetched = True
            if viewer_portrait_url:
                _apply_viewer_portrait(cached, viewer_person_id, viewer_portrait_url)
            trees.append(cached)
            current += 1
            if on_progress:
                on_progress(current)
            elapsed = time.time() - t_start
            print(f"[{current}/{total}] {name} — cache ({elapsed:.2f}s)", flush=True)
            continue

        # 🔹 API
        try:
            data = fetch_tree_from_api(session, persona_id, token)
        except Exception as e:
            if str(e) == "SESSION_EXPIRED":
                print("⚠️ La sesión expiró. Interrumpiendo proceso.", flush=True)
                break
            continue

        if not data:
            current += 1
            if on_progress:
                on_progress(current)
            elapsed = time.time() - t_start
            print(f"[{current}/{total}] {name} — sin datos ({elapsed:.2f}s)", flush=True)
            continue

        # 🔹 Parse
        parsed = parse_tree_data(data)
        if not parsed:
            current += 1
            if on_progress:
                on_progress(current)
            continue

        # ⚠️ actualizar viewer_id dinámicamente
        viewer_person_id = parsed["viewer_id"]

        # 🔹 Fetch viewer portrait once
        if viewer_person_id and not viewer_portrait_fetched:
            viewer_portrait_url = fetch_viewer_portrait(session, viewer_person_id, token)
            viewer_portrait_fetched = True

        # 🔹 Build
        target = parsed["target"]
        coParentIsTargetPerson = target.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE")
        extra_parsed = None
        if coParentIsTargetPerson:
            parent_id = fetch_parent_id(session, persona_id, token)
            if parent_id:
                try:
                    extra_data = fetch_tree_from_api(session, parent_id, token)
                    if extra_data:
                        extra_parsed = parse_tree_data(extra_data)

                except Exception as e:
                    if str(e) == "SESSION_EXPIRED":
                        print("⚠️ Sesión expirada en fetch de padres", flush=True)
                        break

        tree = build_tree_data(parsed, codigo, extra_parsed)

        if viewer_portrait_url:
            _apply_viewer_portrait(tree, viewer_person_id, viewer_portrait_url)

        # 🔹 Save
        save_tree(persona_id, viewer_person_id, tree)

        trees.append(tree)
        current += 1
        if on_progress:
            on_progress(current)
        elapsed = time.time() - t_start
        print(f"[{current}/{total}] {name} — {elapsed:.2f}s", flush=True)

    print(f"{len(trees)}/{total} mini árboles procesados", flush=True)
    return trees

#CACHE
TTL_SECONDS = 604800  # 1 semana

def get_cached_tree(persona_id, viewer_person_id):
    if not viewer_person_id:
        return None

    cached_data, created_at = obtener_arbol(persona_id, viewer_person_id)

    if not cached_data or not created_at:
        return None

    if datetime.now() - created_at > timedelta(seconds=TTL_SECONDS):
        print(f"♻️ Cache expirado para {persona_id}", flush=True)
        return None

    if cached_data.get("name") and cached_data.get("person_code"):
        print(f"💾 Cache válido para {persona_id}", flush=True)
        return cached_data

    print(f"♻️ Cache inválido para {persona_id}", flush=True)
    return None


def save_tree(persona_id, viewer_person_id, tree_data):
    guardar_arbol(persona_id, viewer_person_id, tree_data)

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
        return None

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

    if coParentIsTargetPerson and extra_parsed:
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


def _apply_viewer_portrait(tree, viewer_id, portrait_url):
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
    try:
        data = fetch_tree_from_api(
            session,
            person_id,
            token,
            endpoint="family-members"
        )
    except Exception as e:
        if str(e) == "SESSION_EXPIRED":
            raise
        return None

    if not data:
        return None

    parents = data.get("parents", [])
    if not parents:
        return None

    parent1 = parents[0].get("parent1")
    parent2 = parents[0].get("parent2")

    if parent1 and parent1.get("id"):
        return parent1.get("id")

    if parent2 and parent2.get("id"):
        return parent2.get("id")

    return None