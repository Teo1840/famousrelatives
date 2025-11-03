# --------------------------------- Funciones auxiliares de procesamiento de arboles

def procesar_generaciones(generations):

    camino_ascendente = []
    camino_descendente = []
    antepasado_comun = get_info(None)  # vacío por defecto

    for gen in generations:
        
        if "apex" in gen: # Antepasado común
            persona = gen["apex"].get("person")
            if persona.get("commonAncestor", False):
                antepasado_comun = get_info(persona)
            else:
                camino_ascendente.append(get_info(persona))
            continue  # sigue con la siguiente generación

        asc_side = gen.get("ascendingSide") # Ascendentes
        if asc_side:
            if asc_side.get("coParentIsPathPerson", False):  # Parentesco político
                camino_ascendente.append(get_info(asc_side.get("coParent")))
                camino_ascendente.append(get_info(asc_side.get("person")))
            else:
                camino_ascendente.append(get_info(asc_side.get("person")))

        desc_side = gen.get("descendingSide") # Descendentes
        if desc_side:
            if desc_side.get("coParentIsTargetPerson", False):  # Parentesco político
                camino_descendente.append(get_info(desc_side.get("person"),True))
                camino_descendente.append(get_info(desc_side.get("coParent")))
            else:
                camino_descendente.append(get_info(desc_side.get("person")))

    return camino_ascendente, camino_descendente, antepasado_comun

# ---------------------------------------------------------------

def get_info(person_obj,coParentIsTargetPerson=False):
    if not person_obj:
        return {
            "nombre": "Desconocido",
            "lifespan": "",
            "portraitUrl": None,
            "coParentIsPathPerson": False,
            "coParentIsTargetPerson": False
        }

    # Conseguir el nombre de la persona
    name_details = person_obj.get("nameConclusion", {}).get("details", {})
    full_text = name_details.get("fullText", "Desconocido")

    return {
        "nombre": full_text,
        "lifespan": person_obj.get("lifespan", ""),
        "portraitUrl": person_obj.get("portraitUrl", None),
        "coParentIsPathPerson": person_obj.get("relationshipToPrevious") in ("HUSBAND", "WIFE"),
        "coParentIsTargetPerson": coParentIsTargetPerson
    }

# ---------------------------------------------------------------

import json

def generar_arbol_html(arboles_ordenados):
    """
    Genera el HTML final de los árboles familiares con popups y grafo vis.js.
    - arboles_ordenados: lista de diccionarios con la info de cada persona.
    - plantilla_path: ruta al archivo plantilla HTML.
    """
    # 1️⃣ Generar tarjetas HTML
    tarjetas = "\n".join(
        f"""<div class="card"
            style="background-color:{'#fc9999' if a.get('coParentIsPathPerson') else '#fccccc' if a.get('parentescoPolitico') else 'white'};"
            onclick="openPopup({i}); event.stopPropagation();"
            data-co-parent="{str(a.get('coParentIsPathPerson', False)).lower()}">
            <img src="{a.get('portraitUrl','https://via.placeholder.com/120')}" alt="Mini" width="120">
            <h3>{a['codigo'].split(';')[1].strip()}</h3>
            <small><i>{a.get('relationshipDescription','')}</i></small><br>
            <small style="color:#555;">Cercanía: {a.get('cercania','')}</small><br>
            <small>{a['codigo'].split(';')[2].strip()}</small>
        </div>""" for i, a in enumerate(arboles_ordenados)
    )

    # 2️⃣ Generar array JS de árboles (JSON)
    arboles_js = json.dumps([
        {
            "nombre": a['codigo'].split(';')[1].strip(),
            "foto": a.get('portraitUrl',''),
            "relacion": a.get('relationshipDescription',''),
            "cercania": a.get('cercania',''),
            "extra": a['codigo'].split(';')[2].strip(),
            "detalle": a.get('texto',''),
            "camino_ascendente": a.get("camino_ascendente", []),
            "camino_descendente": a.get("camino_descendente", []),
            "antepasado_comun": a.get("antepasado_comun", {})
        } for a in arboles_ordenados
    ], ensure_ascii=False)

    # 3️⃣ Leer plantilla
    with open(r"C:\Users\Usuario\Desktop\famousrelatives\plantilla_arboles.html", "r", encoding="utf-8") as f:
        template = f.read()

    # 4️⃣ Reemplazar marcador de tarjetas
    html = template.replace("{{TARJETAS}}", tarjetas)

    # 5️⃣ Reemplazar marcador de arboles JS dentro del comentario
    html = html.replace(
        "// const arboles = {{ARBOL_JS}}; // <-- Python debe reemplazar este marcador con JSON válido",
        f"const arboles = {arboles_js};"
    )

    return html

# ---------------------------------------------------------------

import requests

def procesar_codigos(codigos: list[str], headers: dict, cookies: dict) -> list[dict]:
    mini_arboles = []
    current = 0
    total = len(codigos)

    for codigo in codigos:
        if codigo == "LZ6T-MWF;Carlos Gardel;Cantante":
            break
        persona_id = codigo.split(';')[0]
        url = f"https://www.familysearch.org/service/tree/tree-data/user-relationship/v2/person/{persona_id}?showPortraits=true&enforceTemplePolicyEx=true"

        try:
            response = requests.get(url, headers=headers, cookies=cookies)
        except requests.RequestException as e:
            print(f"Error de conexión para {codigo}: {e}")
            continue

        if response.status_code == 200:
            data = response.json()
            generations = data.get("generations", [])

            if not generations:
                print(f"No hay generaciones para {codigo}")
                current += 1
                continue

            target = data.get("targetPerson", {})
            camino_ascendente, camino_descendente, antepasado_comun = procesar_generaciones(generations)

            parentesco_politico = target.get("relationshipToPrevious") in ("HUSBAND", "WIFE")

            mini_arboles.append({
                "codigo": codigo,
                "cercania": len(camino_ascendente) + len(camino_descendente),
                "relationshipDescription": data.get("relationshipDescription"),
                "portraitUrl": target.get("portraitUrl"),
                "coParentIsPathPerson": (
                    camino_ascendente[-2].get("coParentIsPathPerson")
                    if len(camino_ascendente) >= 2 else False
                ),
                "parentescoPolitico": parentesco_politico,
                "camino_ascendente": camino_ascendente,
                "camino_descendente": camino_descendente,
                "antepasado_comun": antepasado_comun or {}
            })

            current += 1
            print(f"{current}/{total}")

        elif response.status_code == 204:
            current += 1
            print(f"No hay parentesco disponible para {codigo.split(';')[1]}")

        elif response.status_code == 401:
            print("⚠️ La sesión expiró. Interrumpiendo proceso.")
            break

        else:
            print(f"Error {response.status_code} para {codigo}: {response.text}")

    print(f"{len(mini_arboles)}/{total} mini árboles procesados")
    return mini_arboles