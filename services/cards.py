import json

def generate_html(TEMPLATE_PATH, arboles_ordenados):
    defaultPortraitUrl = 'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png'

    arboles_js = json.dumps([
        {
            "person_code": a.get('person_code'),
            "name": a.get('name',''),
            "info": a.get('info',''),
            "topics": a.get('topics', []),
            "cercania": a.get('cercania',0),
            "relationshipDescription": a.get('relationshipDescription',''),

            "portraitUrl": a.get('portraitUrl', defaultPortraitUrl),

            "coParentIsPathPerson": a.get('coParentIsPathPerson', False),
            "coParentIsTargetPerson": a.get('coParentIsTargetPerson', False),

            "mainPath": a.get("mainPath", {"asc": [], "desc": []}),
            "directPath": a.get("directPath", None),
            "direct_length": a.get("direct_length", 0),

            "antepasado_comun": a.get("antepasado_comun", {}),
            "detalle": a.get('texto','')
        }
        for a in arboles_ordenados
    ], ensure_ascii=False)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace(
        "// const arboles = {{ARBOL_JS}};",
        f"window.arboles = {arboles_js};"
    )

    return html