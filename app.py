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

import os
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
