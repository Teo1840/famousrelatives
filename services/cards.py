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
            data-co-parent="{str(a.get('coParentIsPathPerson', False)).lower()}">
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
    html = html.replace("// const arboles = {{ARBOL_JS}};", f"window.arboles = {arboles_js};") #Por algun motivo no pude hacerlo de otra manera.
    return html