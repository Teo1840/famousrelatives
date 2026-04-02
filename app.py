#Futuras implementaciones:Flask.session
#venv\Scripts\activate

from dotenv import load_dotenv
import os
from flask import Response, Flask, render_template, request
from tree_functions import generate_trees, generate_html
import csv

app = Flask(__name__)

PATH = "C:/Users/abc/Desktop/famousrelatives/"
TEMPLATE_PATH = PATH+"templates/plantilla_arboles.html"
CSV_PATH = PATH+"famosos.csv"

@app.route('/')
def index():
    # Página inicial donde el usuario inserta su token
    return render_template('index.html')

@app.route('/famousrelatives', methods=['POST'])
def famousrelatives():
    # Headers y cookies con el token del usuario
    token = request.form['token']
    load_dotenv()

    cookies = {
        'fssessionid': token,
    }

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': os.getenv("USER_AGENT"),
    }

    params = {
        'showPortraits': 'true',
        'enforceTemplePolicyEx': 'true',
    }

    # Leer códigos desde CSV
    codigos = []
    with open(CSV_PATH, encoding="cp1252") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0] != "codigo_persona;nombre;info":
                codigos.append(row[0])

    # Procesar datos
    mini_arboles = generate_trees(codigos, params, headers, cookies)
    mini_arboles_ordenados = sorted(mini_arboles, key=lambda a: a["cercania"])

    # Generar HTML final con tu plantilla
    html_content = generate_html(TEMPLATE_PATH,mini_arboles_ordenados)

    # ✅ Devolver directamente el HTML generado al usuario
    return Response(html_content, mimetype='text/html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

import mysql.connector
import json

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS arboles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            persona_id VARCHAR(255),
            data_json LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def guardar_arbol(persona_id, data):
    conn = get_connection()
    cur = conn.cursor()

    query = "INSERT INTO arboles (persona_id, data_json) VALUES (%s, %s)"
    cur.execute(query, (persona_id, json.dumps(data)))

    conn.commit()
    conn.close()

def obtener_arbol(persona_id):
    conn = get_connection()
    cur = conn.cursor()

    query = """
      SELECT data_json FROM arboles
      WHERE persona_id = %s
      ORDER BY created_at DESC
      LIMIT 1
    """
    cur.execute(query, (persona_id,))
    row = cur.fetchone()

    conn.close()

    if row:
        return json.loads(row[0])
    return None
