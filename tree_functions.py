# --Simplificar JSON para (en el futuro) guardar en la BD--
def simplify_info(person_obj,coParentIsTargetPerson=False):
    if not person_obj:
        return {
            "nombre": "Desconocido",
            "lifespan": "",
            "portraitUrl": None,
            "coParentIsPathPerson": False,
            "coParentIsTargetPerson": False
        }
    return {
        "nombre": person_obj.get("nameConclusion", {}).get("details", {}).get("fullText", "Desconocido"),
        "lifespan": person_obj.get("lifespan", ""),
        "portraitUrl": person_obj.get("portraitUrl", None),
        "coParentIsPathPerson": person_obj.get("relationshipToPrevious") in ("HUSBAND", "WIFE", "SPOUSE"),
        "coParentIsTargetPerson": coParentIsTargetPerson
    }

# --Pasar de JSON a lists--
def process_json(generations):
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
            if asc_side.get("coParentIsPathPerson", False):  # Parentesco político
                camino_ascendente.append(simplify_info(asc_side.get("coParent")))
                camino_ascendente.append(simplify_info(asc_side.get("person")))
            else:
                camino_ascendente.append(simplify_info(asc_side.get("person")))

        desc_side = gen.get("descendingSide") # Descendentes
        if desc_side:
            if desc_side.get("coParentIsTargetPerson", False):  # Parentesco político
                camino_descendente.append(simplify_info(desc_side.get("person"),True))
                camino_descendente.append(simplify_info(desc_side.get("coParent")))
            else:
                camino_descendente.append(simplify_info(desc_side.get("person")))

    return camino_ascendente, camino_descendente, antepasado_comun

# --Generar un Arbol por codigo incluyendo su JSON respectivo--
import requests
def generate_trees(codigos: list[str], params: dict, headers: dict, cookies: dict) -> list[dict]:
    trees = []
    current = 0
    total = len(codigos)

    for codigo in codigos:
        #tests
        if "LZ6T-MWF" in codigo: break

        persona_id = codigo.split(';')[0]
        url = f"https://www.familysearch.org/service/tree/tree-data/user-relationship/v2/person/{persona_id}?showPortraits=true&enforceTemplePolicyEx=true"
        try:
            response = requests.get(url,
            params=params,
            cookies=cookies,
            headers=headers,
            timeout=20, #10 seems too short
        )
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
            camino_ascendente, camino_descendente, antepasado_comun = process_json(generations)

            trees.append({
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
            })

            current += 1
            print(f"{current}/{total}")

        elif response.status_code == 204:
            current += 1
            print(f"{current}/{total}")
        elif response.status_code == 401:
            print("⚠️ La sesión expiró. Interrumpiendo proceso.")
            break
        else:
            print(f"Error {response.status_code} para {codigo}: {response.text}")

    print(f"{len(trees)}/{total} mini árboles procesados")
    return trees

# --Generar Tarjetas e Inserirlas en template--
import json
def generate_html(TEMPLATE_PATH,arboles_ordenados):
    #TARJETEAS POPUP
    tarjetas = "\n".join(
        f"""<div class="card"
            style="background-color:{'#fc9999' if a.get('coParentIsPathPerson') else '#fccccc' if a.get('parentescoPolitico') else 'white'};"
            onclick="openPopup({i}); event.stopPropagation();"
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