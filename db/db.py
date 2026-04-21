import mysql.connector
import json
import os

from dotenv import load_dotenv
load_dotenv()

import time
import mysql.connector
import os

#docker exec -it famousrelatives-db-1 mysql -u root -p

def get_connection():
    for i in range(10):  # intenta 10 veces
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                port=3306
            )
            print("-> 🐳 Conectado a MySQL",flush=True)
            return conn
        except Exception as e:
            print(f"-> ⏳ Esperando MySQL... intento {i+1}",flush=True)
            time.sleep(2)

    raise Exception("-> ❌ No se pudo conectar a MySQL",flush=True)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Crear tabla
    cur.execute("""
        CREATE TABLE IF NOT EXISTS arboles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            persona_id VARCHAR(255),
            data_json LONGTEXT,
            viewer_person_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # Crear índice si no existe (chequeando primero)
    cur.execute("""
        SELECT COUNT(1) IndexIsThere
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE table_schema=DATABASE()
          AND table_name='arboles'
          AND index_name='idx_persona_viewer';
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("""
            CREATE INDEX idx_persona_viewer
            ON arboles(persona_id, viewer_person_id)
        """)

    conn.commit()
    conn.close()

def guardar_arbol(persona_id, viewer_person_id, data):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO arboles (persona_id, viewer_person_id, data_json)
        VALUES (%s, %s, %s)
    """
    cur.execute(query, (persona_id, viewer_person_id, json.dumps(data)))

    conn.commit()
    conn.close()

def obtener_arbol(persona_id, viewer_person_id):
    conn = get_connection()
    cur = conn.cursor()

    query = """
      SELECT data_json, created_at FROM arboles
      WHERE persona_id = %s AND viewer_person_id = %s
      ORDER BY created_at DESC
      LIMIT 1
    """
    cur.execute(query, (persona_id, viewer_person_id))
    row = cur.fetchone()

    conn.close()

    if row:
        data_json, created_at = row
        return json.loads(data_json), created_at

    return None, None