#py app.py

#Futuras implementaciones:
#Flask.session

from flask import Response, Flask, render_template, request
from arboles_funciones import procesar_codigos, generar_arbol_html
import csv

app = Flask(__name__)

CSV_PATH = "C:/Users/Usuario/Desktop/famousrelatives/famosos.csv"

@app.route('/')
def index():
    # Página inicial donde el usuario inserta su token
    return render_template('index.html')

@app.route('/procesar', methods=['POST'])
def procesar():
    token = request.form['token']

    # Headers y cookies con el token del usuario
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    cookies = {"fssessionid": token}

    # Leer códigos desde CSV
    codigos = []
    with open(CSV_PATH, encoding="cp1252") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0] != "codigo_persona;nombre;info":
                codigos.append(row[0])

    # Procesar datos
    mini_arboles = procesar_codigos(codigos, headers, cookies)
    mini_arboles_ordenados = sorted(mini_arboles, key=lambda a: a["cercania"])

    # Generar HTML final con tu plantilla
    html_content = generar_arbol_html(mini_arboles_ordenados)

    # ✅ Devolver directamente el HTML generado al usuario
    return Response(html_content, mimetype='text/html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)