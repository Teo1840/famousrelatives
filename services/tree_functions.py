# --Simplificar JSON--
def simplify_person(person):
    if not person:
        return {"nombre": "", "id": "", "lifespan": "", "portraitUrl": None}
    name=person.get("nameConclusion", {})
    details=name.get("details", {})
    return {
        "nombre": details.get("fullText", ""),
        "id": person.get("id",""),
        "lifespan": person.get("lifespan", ""),
        "portraitUrl": person.get("portraitUrl")
    }

# --Pasar de JSON a lists--
def process_json(generations):
    asc = []
    desc = []
    ancestor = simplify_person(None) 
    viewer_person_id = None

    for gen in generations:
        #ANTEPASADO COMUN
        if "apex" in gen:
            person = gen["apex"].get("person", {})
            if person.get("commonAncestor", False):
                ancestor = simplify_person(person)
            else:
                asc.append(simplify_person(person))
            continue
        # Ascendentes
        asc_side = gen.get("ascendingSide")
        if asc_side:
            person=simplify_person(asc_side.get("person"))
            if asc_side.get("coParentIsPathPerson", False):  # Target Person es pariente de mi conyugue
                coParent=simplify_person(asc_side.get("coParent"))
                asc.append(coParent)
                asc.append(person)
            else:
                asc.append(person)

            if asc_side.get("indexInPath")==0: # Puedo preguntar por la ultima persona en asc_side??
                viewer_id=person.get("id") # Obtener viewer_person_id
        # Descendentes
        desc_side = gen.get("descendingSide")
        if desc_side:
            person=simplify_person(desc_side.get("person"))
            if desc_side.get("coParentIsTargetPerson", False):  # Target Person es conyugue de mi pariente
                coParent=simplify_person(desc_side.get("coParent"))
                desc.append(person)
                desc.append(coParent)
            else:
                desc.append(person)

    return asc, desc, ancestor, viewer_id

# --Generar Session--
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_session():
    session = requests.Session()

    retries = Retry(
        total=3,  # 🔁 reintenta hasta 3 veces
        connect=3,   # 🔥 retry si no conecta
        read=3,      # 🔥 retry si timeout leyendo
        backoff_factor=1,  # ⏱️ espera: 1s, 2s, 4s
        status_forcelist=[500, 502, 503, 504],  # solo errores de servidor
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    return session

# --Generar un Arbol por codigo incluyendo su JSON respectivo--
from datetime import datetime, timedelta
from db.db import obtener_arbol, guardar_arbol

def generate_trees(codigos, token):
    session = get_session()
    trees = []

    current = 0
    total = len(codigos)

    viewer_person_id = None  # ⚠️

    for codigo in codigos:
        persona_id = codigo["person_code"]

        # 🔹 Cache
        cached = get_cached_tree(persona_id, viewer_person_id)
        if cached:
            trees.append(cached)
            current += 1
            print(f"{current}/{total} (cache)", flush=True)
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
            print(f"{current}/{total}", flush=True)
            continue

        # 🔹 Parse
        parsed = parse_tree_data(data)
        if not parsed:
            current += 1
            continue

        # ⚠️ actualizar viewer_id dinámicamente
        viewer_person_id = parsed["viewer_id"]

        # 🔹 Build
        tree = build_tree_data(parsed, codigo)

        # 🔹 Save
        save_tree(persona_id, viewer_person_id, tree)

        trees.append(tree)

        current += 1
        print(f"{current}/{total}", flush=True)

    print(f"{len(trees)}/{total} mini árboles procesados", flush=True)
    return trees

#CACHE
from datetime import datetime, timedelta
from db.db import obtener_arbol, guardar_arbol

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
import requests

def fetch_tree_from_api(session, person_id, token):
    url = f"http://host.docker.internal:5001/proxy/{person_id}?token={token}"

    try:
        response = session.get(url, timeout=20)
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

    asc, desc, ancestor, viewer_id = process_json(generations)

    return {
        "asc": asc,
        "desc": desc,
        "ancestor": ancestor,
        "viewer_id": viewer_id,
        "target": data.get("targetPerson", {}),
        "relationship": data.get("relationshipDescription")
    }

#BUILDER
def build_tree_data(parsed, codigo):
    asc = parsed["asc"]
    desc = parsed["desc"]
    target = parsed["target"]

    return {
        "person_code": codigo["person_code"],
        "name": codigo["name"],
        "parent_code": codigo["parent_code"],
        "info": codigo["info"],
        "cercania": len(asc) + len(desc),
        "relationshipDescription": parsed["relationship"],
        "portraitUrl": target.get(
            "portraitUrl",
            "https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png"
        ),
        "coParentIsPathPerson": (
            asc[-2].get("coParentIsPathPerson") if len(asc) >= 2 else False
        ),
        "coParentIsTargetPerson": target.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE"),
        "camino_ascendente": asc,
        "camino_descendente": desc,
        "antepasado_comun": parsed["ancestor"] or {}
    }