# --Simplificar JSON--
def simplify_person(person):
    if not person:
        return {
            "nombre": "",
            "id": "",
            "lifespan": "",
            "portraitUrl": None
        }
    return {
        "nombre": person.get("nameConclusion", {}).get("details", {}).get("fullText", ""),
        "id": person.get("id",""),
        "lifespan": person.get("lifespan", ""),
        "portraitUrl": person.get("portraitUrl", None)
    }

# --Pasar de JSON a lists--
def process_json(generations):
    camino_ascendente = []
    camino_descendente = []
    antepasado_comun = simplify_person(None) 
    viewer_person_id = None

    for gen in generations:
        if "apex" in gen: # Antepasado común
            persona = gen["apex"].get("person")
            if persona.get("commonAncestor", False):
                antepasado_comun = simplify_person(persona)
            else:
                camino_ascendente.append(simplify_person(persona))
            continue  # sigue con la siguiente generación

        asc_side = gen.get("ascendingSide") # Ascendentes
        if asc_side:
            person=simplify_person(asc_side.get("person"))
            if asc_side.get("coParentIsPathPerson", False):  # Target Person es pariente de mi conyugue
                coParent=simplify_person(asc_side.get("coParent"))
                camino_ascendente.append(coParent)
                camino_ascendente.append(person)
            else:
                camino_ascendente.append(person)

            if asc_side.get("indexInPath")==0: # Puedo preguntar por la ultima persona en asc_side??
                viewer_person_id=person.get("id") # Obtener viewer_person_id

        desc_side = gen.get("descendingSide") # Descendentes
        if desc_side:
            person=simplify_person(desc_side.get("person"))
            if desc_side.get("coParentIsTargetPerson", False):  # Target Person es conyugue de mi pariente
                camino_descendente.append(person)
                coParent=simplify_person(desc_side.get("coParent"))
                camino_descendente.append(coParent)
            else:
                camino_descendente.append(simplify_person(desc_side.get("person")))

    return camino_ascendente, camino_descendente, antepasado_comun, viewer_person_id

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

def generate_trees(codigos: list[str], token: str) -> list[dict]:
    session = get_session()
    trees = []
    current = 0
    total = len(codigos)
    TTL_SECONDS = 604800  # 1 week
    viewer_person_id=None

    for codigo in codigos:
        persona_id = codigo["person_code"]
        if viewer_person_id!=None:
            cached_data, created_at = obtener_arbol(persona_id, viewer_person_id)
            if cached_data and created_at:
                if datetime.now() - created_at < timedelta(seconds=TTL_SECONDS):
                    if cached_data.get("name","")!="" and cached_data.get("person_code","")!="":
                        print(f"💾 Cache válido para {persona_id}", flush=True)
                        trees.append(cached_data)
                        current+=1
                        print(f"{current}/{total} (cache)", flush=True)
                        continue
                    else:
                        print(f"♻️ Cache invalido para {persona_id}", flush=True)
                else:
                    print(f"♻️ Cache expirado para {persona_id}", flush=True)

        print(f"🌐 Request a API para {persona_id}", flush=True)
        url = f"http://host.docker.internal:5001/proxy/{persona_id}?token={token}"

        try:
            response = session.get(url, timeout=20) #10 seems too short
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout para {codigo}", flush=True)
            current+=1
            continue
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión para {codigo}: {e}", flush=True)
            current+=1
            continue

        if response.status_code == 200:
            data = response.json()
            generations = data.get("generations", [])
            if not generations:
                print(f"No hay generaciones para {persona_id}", flush=True)
                current+=1
                continue

            target = data.get("targetPerson", {})
            camino_ascendente, camino_descendente, antepasado_comun, viewer_person_id = process_json(generations)

            tree_data={
                "person_code": persona_id,
                "name": codigo["name"],
                "parent_code": codigo["parent_code"],
                "info": codigo["info"],
                "cercania": len(camino_ascendente) + len(camino_descendente),
                "relationshipDescription": data.get("relationshipDescription"),
                "portraitUrl": target.get("portraitUrl",'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png'),
                "coParentIsPathPerson": (
                    camino_ascendente[-2].get("coParentIsPathPerson")
                    if len(camino_ascendente) >= 2 else False
                ), #Mi conyugue es pariente de la persona
                "coParentIsTargetPerson": target.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE"), #Soy pariente del conyuge de la perona
                "camino_ascendente": camino_ascendente,
                "camino_descendente": camino_descendente,
                "antepasado_comun": antepasado_comun or {}
            }
            print(f"{tree_data.get("name")}", flush=True)
            guardar_arbol(persona_id, viewer_person_id, tree_data)
            trees.append(tree_data)
            current+=1
            print(f"{current}/{total}", flush=True)

        elif response.status_code == 204:
            current+=1
            print(f"{current}/{total}", flush=True)
        elif response.status_code == 401:
            print("⚠️ La sesión expiró. Interrumpiendo proceso.", flush=True)
            break
        else:
            print(f"Error {response.status_code} para {codigo}: {response.text}", flush=True)
            current+=1

    print(f"{len(trees)}/{total} mini árboles procesados", flush=True)
    return trees

# --Generar Tarjetas e Inserirlas en template--
import json
def generate_html(TEMPLATE_PATH,arboles_ordenados):
    defaultPortraitUrl='https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png'
    #TARJETEAS POPUP
    tarjetas = "\n".join(
        f"""<div class="card"
            style="background-color:{'#fc9999' if a.get('coParentIsPathPerson') else '#fccccc' if a.get('coParentIsTargetPerson') else 'white'};"
            data-co-parent="{str(a.get('coParentIsPathPerson', False)).lower()}">
            <img src="{a.get('portraitUrl',defaultPortraitUrl)}" alt="Mini" width="150">
            <h3>{a.get('name')}</h3>
            <small><i>{a.get('relationshipDescription','')}</i></small><br>
            <small>Cercanía: {a.get('cercania',0)}</small><br>
            <small>{a.get('info')}</small>
        </div>""" for i, a in enumerate(arboles_ordenados) # Necesario?? Todo un solo for??
    )

    arboles_js = json.dumps([
        {
            "nombre": a.get('name',''),
            "portraitUrl": a.get('portraitUrl',defaultPortraitUrl),
            "relacion": a.get('relationshipDescription',''),
            "cercania": a.get('cercania',0),
            "extra": a.get('info',''),
            "detalle": a.get('texto',''),
            "camino_ascendente": a.get("camino_ascendente", []),
            "camino_descendente": a.get("camino_descendente", []),
            "antepasado_comun": a.get("antepasado_comun", {})
        } for a in arboles_ordenados
    ], ensure_ascii=False)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{TARJETAS}}", tarjetas)
    html = html.replace("// const arboles = {{ARBOL_JS}};", f"const arboles = {arboles_js};") #Por algun motivo no pude hacerlo de otra manera.
    return html