from dotenv import load_dotenv
import os
from flask import Response, Flask, render_template, request
from services.tree_functions import generate_trees
from services.cards import generate_html
from services.csv_validation import validate_csv_file

load_dotenv()

#Levantar BD
from db.db import init_db
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
    try:
        with open(CSV_PATH, encoding="utf-8") as f:
            f.read()
        print("Es UTF-8")
    except Exception as e:
        print("No es UTF-8, probá cp1252")
    return render_template("index.html")

@app.route('/famousrelatives', methods=['POST'])
def famousrelatives():
    #LOADING page
    token = request.form['token']
    return render_template("loading.html", token=token)

@app.route('/process', methods=['POST'])
def process():
    # Headers y cookies con el token del usuario
    token = request.form['token']
    
    # Leer códigos desde CSV
    try:
        rows = validate_csv_file(CSV_PATH)
    except ValueError as e:
        return render_template("error.html", error=str(e)), 400

    # Procesar datos
    arboles = generate_trees(rows, token)
    arboles_ordenados = sorted(arboles, key=lambda a: a["cercania"])

    # Generar HTML final con tu plantilla y devolver al usuario
    html_content = generate_html(TEMPLATE_PATH,arboles_ordenados)
    return Response(html_content, mimetype='text/html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)