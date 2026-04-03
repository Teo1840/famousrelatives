import mysql.connector
import json
import os

from dotenv import load_dotenv
load_dotenv()

def get_connection():
    #print("DB_HOST:", os.getenv("DB_HOST"),flush=True)
    #print("DB_USER:", os.getenv("DB_USER"),flush=True)
    #print("DB_PASSWORD:", os.getenv("DB_PASSWORD"),flush=True)
    return mysql.connector.connect(
        host=os.getenv("DB_HOST","localhost"),      # "db" en docker-compose
        user=os.getenv("DB_USER"),      # "root"
        password=os.getenv("DB_PASSWORD"),  # "secret"
        database=os.getenv("DB_NAME"),       # "famousrelatives"
        port=3306
    )

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