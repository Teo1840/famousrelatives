# --Generar Tarjetas e Inserirlas en template--
import json
def get_card_color(a):
    if a.get('coParentIsPathPerson'):
        return '#fc9999'
    if a.get('coParentIsTargetPerson'):
        return '#fccccc'
    return 'white'

def generate_html(TEMPLATE_PATH,arboles_ordenados):
    defaultPortraitUrl='https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png'
    #TARJETEAS POPUP
    tarjetas = "\n".join(
        f"""<div class="card"
            style="background-color:{get_card_color(a)};"
            data-co-parent="{str(a.get('coParentIsPathPerson', False)).lower()}"
            data-co-parent-target="{str(a.get('coParentIsTargetPerson', False)).lower()}"
            data-has-direct-path="{str(a.get('directPath') is not None).lower()}">
            
            <img src="{a.get('portraitUrl',defaultPortraitUrl)}" alt="Mini" width="150">
            <h3>{a.get('name')}</h3>
            <small><i>{a.get('relationshipDescription','')}</i></small><br>
            <small>Cercanía: {a.get('cercania',0)}</small><br>
            <small>{a.get('info')}</small>
        </div>"""
        for a in arboles_ordenados
    )

    arboles_js = json.dumps([
        {
            "person_code": a.get('person_code'),
            "nombre": a.get('name',''),
            "info": a.get('info',''),
            "cercania": a.get('cercania',0),
            "relacion": a.get('relationshipDescription',''),

            "portraitUrl": a.get(
                'portraitUrl',
                defaultPortraitUrl
            ),

            # 🔥 CLAVES PARA FILTRO
            "coParentIsPathPerson": a.get('coParentIsPathPerson', False),
            "coParentIsTargetPerson": a.get('coParentIsTargetPerson', False),

            # 🔥 PATHS
            "mainPath": a.get("mainPath", {"asc": [], "desc": []}),
            "directPath": a.get("directPath", None),

            # 🔥 OTROS
            "antepasado_comun": a.get("antepasado_comun", {}),
            "detalle": a.get('texto','')  # si lo usás
        }
        for a in arboles_ordenados
    ], ensure_ascii=False)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{TARJETAS}}", tarjetas)
    html = html.replace("// const arboles = {{ARBOL_JS}};", f"window.arboles = {arboles_js};") #Por algun motivo no pude hacerlo de otra manera.
    return html