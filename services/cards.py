import json

DEFAULT_PORTRAIT_URL = 'https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png'


def serializar_arboles(arboles_ordenados):
    """Arma la lista de árboles tal como la usa el dashboard (window.arboles)."""
    return [
        {
            "person_code": a.get('person_code'),
            "name": a.get('name', ''),
            "info": a.get('info', ''),
            "topics": a.get('topics', []),
            "wiki": a.get('wiki'),
            "paises": a.get('paises', []),
            "cercania": a.get('cercania', 0),
            "relationshipDescription": a.get('relationshipDescription', ''),

            "portraitUrl": a.get('portraitUrl', DEFAULT_PORTRAIT_URL),

            "coParentIsPathPerson": a.get('coParentIsPathPerson', False),
            "coParentIsTargetPerson": a.get('coParentIsTargetPerson', False),

            "mainPath": a.get("mainPath", {"asc": [], "desc": []}),
            "directPath": a.get("directPath", None),
            "direct_length": a.get("direct_length", 0),

            "antepasado_comun": a.get("antepasado_comun", {}),
            "detalle": a.get('texto', '')
        }
        for a in arboles_ordenados
    ]


def generate_html(TEMPLATE_PATH, user_id, header_html=""):
    """Página del dashboard sin datos: static/js/arboles-cache.js los trae
    de /api/arboles (o de la copia guardada en el navegador)."""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace(
        "// const arboles = {{ARBOL_JS}};",
        f"window.ARBOLES_USER_ID = {json.dumps(user_id)};"
    )

    html = html.replace("<!-- DASHBOARD_HEADER -->", header_html)

    return html
