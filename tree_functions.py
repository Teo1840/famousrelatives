# --Simplificar JSON para (en el futuro) guardar en la BD--
def simplify_info(person,coParentIsTargetPerson=False):
    if not person:
        return {
            "nombre": "Desconocido",
            "id": "",
            "lifespan": "",
            "portraitUrl": None,
            "coParentIsPathPerson": False,
            "coParentIsTargetPerson": False
        }
    return {
        "nombre": person.get("nameConclusion", {}).get("details", {}).get("fullText", "Desconocido"),
        "id": person.get("id"),
        "lifespan": person.get("lifespan", ""),
        "portraitUrl": person.get("portraitUrl", None),
        "coParentIsPathPerson": person.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE"),
        "coParentIsTargetPerson": coParentIsTargetPerson
    }

# --Pasar de JSON a lists--
def process_json(generations):
    viewer_person_id = None
    camino_ascendente = []
    camino_descendente = []
    antepasado_comun = simplify_info(None)  # vacío por defecto

    for gen in generations:
        if "apex" in gen: # Antepasado común
            persona = gen["apex"].get("person")
            if persona.get("commonAncestor", False):
                antepasado_comun = simplify_info(persona)
            else:
                camino_ascendente.append(simplify_info(persona))
            continue  # sigue con la siguiente generación

        asc_side = gen.get("ascendingSide") # Ascendentes
        if asc_side:
            person=simplify_info(asc_side.get("person"))
            if asc_side.get("coParentIsPathPerson", False):  # Parentesco político
                coParent=simplify_info(asc_side.get("coParent"))
                camino_ascendente.append(coParent)
                camino_ascendente.append(person)
            else:
                camino_ascendente.append(person)
            if asc_side.get("indexInPath")==0:
                viewer_person_id=person.get("id")

        desc_side = gen.get("descendingSide") # Descendentes
        if desc_side:
            if desc_side.get("coParentIsTargetPerson", False):  # Parentesco político
                camino_descendente.append(simplify_info(desc_side.get("person"),True))
                camino_descendente.append(simplify_info(desc_side.get("coParent")))
            else:
                camino_descendente.append(simplify_info(desc_side.get("person")))

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
import time
import random
from datetime import datetime, timedelta
from db import obtener_arbol, guardar_arbol

def generate_trees(codigos: list[str], token: str) -> list[dict]:
    session = get_session()
    trees = []
    current = 0
    total = len(codigos)
    TTL_SECONDS = 604800  # 1 week
    viewer_person_id=None

    for codigo in codigos:
        if "LZ6T-MWF" in codigo: break #tests
        persona_id = codigo.split(';')[0]
        if viewer_person_id!=None:
            cached_data, created_at = obtener_arbol(persona_id, viewer_person_id)
            if cached_data and created_at:
                if datetime.now() - created_at < timedelta(seconds=TTL_SECONDS):
                    print(f"💾 Cache válido para {codigo}", flush=True)
                    trees.append(cached_data)
                    print(f"{current}/{total} (cache)", flush=True)
                    continue
                else:
                    print(f"♻️ Cache expirado para {codigo}", flush=True)
        print(f"🌐 Request a API para {persona_id}", flush=True)
        time.sleep(random.random()) #evitar ser blockeado?
        url = f"http://host.docker.internal:5001/proxy/{persona_id}?token={token}"
        try:
            response = session.get(url, timeout=20) #10 seems too short
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout para {codigo}", flush=True)
            continue
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión para {codigo}: {e}", flush=True)
            continue

        if response.status_code == 200:
            data = response.json()
            generations = data.get("generations", [])

            if not generations:
                print(f"No hay generaciones para {codigo}", flush=True)
                current += 1
                continue

            target = data.get("targetPerson", {})
            camino_ascendente, camino_descendente, antepasado_comun, viewer_person_id = process_json(generations)

            tree_data={
                "codigo": codigo,
                "cercania": len(camino_ascendente) + len(camino_descendente),
                "relationshipDescription": data.get("relationshipDescription"),
                "portraitUrl": target.get("portraitUrl",'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png'),
                "coParentIsPathPerson": (
                    camino_ascendente[-2].get("coParentIsPathPerson")
                    if len(camino_ascendente) >= 2 else False
                ), #Pariente de mi conyugue
                "parentescoPolitico": target.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE"), #Conyugue de mi pariente
                "camino_ascendente": camino_ascendente,
                "camino_descendente": camino_descendente,
                "antepasado_comun": antepasado_comun or {}
            }
            guardar_arbol(persona_id, viewer_person_id, tree_data)
            trees.append(tree_data)
            current += 1
            print(f"{current}/{total}", flush=True)

        elif response.status_code == 204:
            current += 1
            print(f"{current}/{total}", flush=True)
        elif response.status_code == 401:
            print("⚠️ La sesión expiró. Interrumpiendo proceso.", flush=True)
            break
        else:
            print(f"Error {response.status_code} para {codigo}: {response.text}", flush=True)

    print(f"{len(trees)}/{total} mini árboles procesados", flush=True)
    return trees

# --Generar Tarjetas e Inserirlas en template--
import json
def generate_html(TEMPLATE_PATH,arboles_ordenados):
    #TARJETEAS POPUP
    tarjetas = "\n".join(
        f"""<div class="card"
            style="background-color:{'#fc9999' if a.get('coParentIsPathPerson') else '#fccccc' if a.get('parentescoPolitico') else 'white'};"
            data-co-parent="{str(a.get('coParentIsPathPerson', False)).lower()}">
            <img src="{a.get('portraitUrl','https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png')}" alt="Mini" width="120">
            <h3>{a['codigo'].split(';')[1].strip()}</h3>
            <small><i>{a.get('relationshipDescription','')}</i></small><br>
            <small>Cercanía: {a.get('cercania','')}</small><br>
            <small>{a['codigo'].split(';')[2].strip()}</small>
        </div>""" for i, a in enumerate(arboles_ordenados)
    )

    arboles_js = json.dumps([
        {
            "nombre": a['codigo'].split(';')[1].strip(),
            "portraitUrl": a.get('portraitUrl','https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png'),
            "relacion": a.get('relationshipDescription',''),
            "cercania": a.get('cercania',''),
            "extra": a['codigo'].split(';')[2].strip(),
            "detalle": a.get('texto',''),
            "camino_ascendente": a.get("camino_ascendente", []),
            "camino_descendente": a.get("camino_descendente", []),
            "antepasado_comun": a.get("antepasado_comun", {})
        } for a in arboles_ordenados
    ], ensure_ascii=False)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    html = template.replace("{{TARJETAS}}", tarjetas)
    html = html.replace(
        "// const arboles = {{ARBOL_JS}}; // <-- Python debe reemplazar este marcador con JSON válido",
        f"const arboles = {arboles_js};"
    ) #IMPORTANTE, por algun omtivo no se hacerlo de otra manera.

    return html