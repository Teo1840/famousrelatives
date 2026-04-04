#Futuras implementaciones:Flask.session

#venv\Scripts\activate
#python fs_proxy.py
#py app.py

#docker-compose build app
#docker-compose up -d
#docker logs -f famousrelatives-app-1

from dotenv import load_dotenv
import os
from flask import Response, Flask, render_template, request
from tree_functions import generate_trees, generate_html
import csv

load_dotenv()
#Levantar BD
from db import init_db
init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # carpeta /app en el contenedor
CSV_PATH = os.path.join(BASE_DIR, "famosos.csv")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "plantilla_arboles.html")
INDEX_PATH = os.path.join(TEMPLATE_DIR, "index.html")

app = Flask(__name__, template_folder=TEMPLATE_DIR)

@app.route('/')
def index():
    # Página inicial donde el usuario inserta su token
    return render_template("index.html")

@app.route('/famousrelatives', methods=['POST'])
def famousrelatives():
    # Headers y cookies con el token del usuario
    token = request.form['token']
    
    # Leer códigos desde CSV
    codigos = []
    with open(CSV_PATH, encoding="cp1252") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0] != "codigo_persona;nombre;info":
                codigos.append(row[0])

    # Procesar datos
    mini_arboles = generate_trees(codigos, token)
    mini_arboles_ordenados = sorted(mini_arboles, key=lambda a: a["cercania"])

    # Generar HTML final con tu plantilla y devolver al usuario
    html_content = generate_html(TEMPLATE_PATH,mini_arboles_ordenados)
    return Response(html_content, mimetype='text/html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)