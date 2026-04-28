# --Simplificar JSON--
#def viewer_person
def build_person(person):
    if not person:
        return {"nombre": "", "id": "", "lifespan": "", "portraitUrl": None}

    name = person.get("nameConclusion", {})
    details = name.get("details", {})

    person_id = person.get("id", "")
    is_me = person.get("relationshipToPrevious") == "ME"

    portrait = (
        f"https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png"
        if is_me
        else person.get("portraitUrl")
    )
    #https://sg30p0.familysearch.org/service/memories/tps/persons/{person_id}/portrait/original

    return {
        "nombre": details.get("fullText", ""),
        "id": person_id,
        "lifespan": person.get("lifespan", ""),
        "portraitUrl": portrait
    }

# --Pasar de JSON a lists--
def process_json(generations):
    asc = []
    desc = []
    ancestor = build_person(None) 
    viewer_person_id = None

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
                coParent=build_person(asc_side.get("coParent"))
                asc.append(coParent)
                asc.append(person)
            else:
                asc.append(person)

            if asc_side.get("indexInPath")==0: # Puedo preguntar por la ultima persona en asc_side??
                viewer_id=person.get("id") # Obtener viewer_person_id
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

def fetch_tree_from_api(session, person_id, token, endpoint=None):
    base_url = f"http://host.docker.internal:5001/proxy/{person_id}?token={token}"

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
def build_tree_data(parsed, codigo, extra_parsed=None):
    asc = parsed["asc"]
    desc = parsed["desc"]
    apex = parsed["ancestor"] or {}
    target = parsed["target"]
    coParentIsTargetPerson = target.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE")
    extra_asc = extra_parsed["asc"] if extra_parsed else []
    extra_desc = extra_parsed["desc"] if extra_parsed else []
    extra_apex = extra_parsed["ancestor"] if extra_parsed else []
    return {
        "person_code": codigo["person_code"],
        "name": codigo["name"],
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
        "coParentIsTargetPerson": coParentIsTargetPerson,
        "mainPath": {"asc": asc, "desc": desc, "antepasado_comun": apex},
        "directPath": (
            {"asc": extra_asc, "desc": extra_desc, "antepasado_comun": extra_apex}
            if coParentIsTargetPerson and extra_parsed
            else None
        )
    }

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