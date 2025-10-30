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

def generar_arbol_texto(antepasado, ascendente, descendente):

    lines = [f"{antepasado['nombre']} ({antepasado['lifespan']}) ← Antepasado en común"]
    lines.append("|") # Espacio

    for i, persona in enumerate(ascendente): # Rama ascendente
        prefijo = ("|   " + "    " * (i-1) + "└─ " if i != 0 else "├─ ")
        lines.append(f"{prefijo}{persona['nombre']} ({persona['lifespan']})")
        if persona.get("coParentIsPathPerson"):
            n=len(ascendente)
            prefijo = ("|   " + "    " * (n-2) + "|  ")
            lines.append(prefijo)
            prefijo = ("|   " + "    " * (n-3) + "   ")
            lines.append(f"{prefijo}{ascendente[n-1]['nombre']} ({persona['lifespan']})")
            break

    lines.append("|") # Espacio

    for i, persona in enumerate(descendente): # Rama descendente
        prefijo = "    " * (i-1) + ("└─ " if i == 0 else "    └─ ")
        lines.append(prefijo + f"{persona['nombre']} ({persona['lifespan']})")
        if persona.get("coParentIsTargetPerson"):
            n=len(descendente)
            prefijo = ("    " + "    " * (n-2) + "|  ")
            lines.append(prefijo)
            prefijo = ("    " + "    " * (n-3) + "   ")
            lines.append(f"{prefijo}{descendente[n-1]['nombre']} ({persona['lifespan']})")
            break

    return "\n".join(lines)

# ---------------------------------------------------------------

import json

def generar_arbol_html(arboles_ordenados):
    # Tarjetas HTML
    tarjetas = "\n".join(
        f"""<div class="card"
            style="background-color:{'#fc9999' if a.get('coParentIsPathPerson') else '#fccccc' if a.get('parentescoPolitico') else 'white'};"
            onclick="openPopup({i})"
            data-co-parent="{str(a.get('coParentIsPathPerson', False)).lower()}">
            <img src="{a.get('portraitUrl','')}" alt="Mini" width="120">
            <h3>{a['codigo'].split(';')[1].strip()}</h3>
            <small><i>{a.get('relationshipDescription','')}</i></small><br>
            <small style="color:#555;">Cercanía: {a.get('cercania','')}</small><br>
            <small>{a['codigo'].split(';')[2].strip()}</small>
        </div>""" for i, a in enumerate(arboles_ordenados)
    )

    # Generar array JS de árboles como JSON
    arboles_js = json.dumps([
        {
            "nombre": a['codigo'].split(';')[1].strip(),
            "detalle": a.get('texto',''),
            "foto": a.get('portraitUrl',''),
            "relacion": a.get('relationshipDescription',''),
            "cercania": a.get('cercania',''),
            "extra": a['codigo'].split(';')[2].strip()
        } for a in arboles_ordenados
    ], ensure_ascii=False)

    # Leer plantilla HTML
    with open(r"C:\Users\Usuario\Desktop\famousrelatives\plantilla_arboles.html", "r", encoding="utf-8") as f:
        template = f.read()

    # Reemplazar marcador de tarjetas y de array JS
    html = template.replace("{{TARJETAS}}", tarjetas)
    html = html.replace("const arboles = [];", f"const arboles = {arboles_js};")

    return html

# ---------------------------------------------------------------

import requests

def procesar_codigos(codigos: list[str], headers: dict, cookies: dict) -> list[dict]:
    mini_arboles = []
    current=0
    total=len(codigos)
    for codigo in codigos:
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
                continue

            target = data.get("targetPerson", {})
            camino_ascendente, camino_descendente, antepasado_comun = procesar_generaciones(generations)
            texto_arbol = generar_arbol_texto(antepasado_comun, camino_ascendente, camino_descendente)

            parentesco_politico = target.get("relationshipToPrevious") in ("HUSBAND", "WIFE")

            mini_arboles.append({
                "codigo": codigo,
                "texto": texto_arbol,
                "cercania": len(camino_ascendente) + len(camino_descendente),
                "relationshipDescription": data.get("relationshipDescription"),
                "portraitUrl": target.get("portraitUrl"),
                "coParentIsPathPerson": (
                    camino_ascendente[-2].get("coParentIsPathPerson")
                    if len(camino_ascendente) >= 2 else None
                ),
                "parentescoPolitico": parentesco_politico,
            })
            current+=1
            print(f"{current}/{total}")
        elif response.status_code == 204:
            current+=1
            print(f"No hay parentesco disponible para {codigo.split(';')[1]}")
        elif response.status_code == 401:
            print("⚠️ La sesión expiró. Interrumpiendo proceso.")
            break
        else:
            print(f"Error {response.status_code} para {codigo}: {response.text}")
    print(f"{len(mini_arboles)}/{total}")

    return mini_arboles
