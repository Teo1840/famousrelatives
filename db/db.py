import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from werkzeug.security import generate_password_hash
import json
import os
import time

from dotenv import load_dotenv
load_dotenv()


class DuplicateUsernameError(Exception):
    pass

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        for i in range(10):
            try:
                _pool = MySQLConnectionPool(
                    pool_name="famrel_pool",
                    pool_size=10,
                    host=os.getenv("DB_HOST", "localhost"),
                    user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASSWORD"),
                    database=os.getenv("DB_NAME"),
                    port=3306
                )
                print("-> 🐳 MySQL pool created", flush=True)
                break
            except Exception as e:
                print(f"Pool error: {e}... intento {i + 1}", flush=True)
                time.sleep(2)
        else:
            raise Exception("No se pudo conectar a MySQL")
    return _pool

def init_db():
    conn = get_pool().get_connection()
    cur = conn.cursor()

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

    cur.execute("""
        SELECT COUNT(1) ColumnIsThere
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema=DATABASE()
          AND table_name='arboles'
          AND column_name='found_relationship';
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("""
            ALTER TABLE arboles
            ADD COLUMN found_relationship TINYINT(1) NULL DEFAULT NULL
            AFTER data_json
        """)

    conn.commit()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            familysearch_token VARCHAR(1024) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    cur.execute("""
        SELECT COUNT(1) ColumnIsThere
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema=DATABASE()
          AND table_name='usuarios'
          AND column_name='token_updated_at';
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("""
            ALTER TABLE usuarios
            ADD COLUMN token_updated_at TIMESTAMP NULL DEFAULT NULL
            AFTER familysearch_token
        """)

    conn.commit()

    # Tokens saved without a timestamp (from before this column existed, or
    # from an install that already ran the ALTER above) get back-filled to
    # "now" so they get a fresh TTL window instead of being treated as
    # expired the moment the TTL check runs.
    cur.execute("""
        UPDATE usuarios
        SET token_updated_at = CURRENT_TIMESTAMP
        WHERE familysearch_token IS NOT NULL
          AND token_updated_at IS NULL
    """)

    conn.commit()

    # Foto de perfil del usuario en FamilySearch (y su ID ahí), para mostrarla
    # en su nodo de cada árbol, también en los que ya están en cache.
    for column, definition in (
        ("viewer_person_id", "VARCHAR(255) NULL"),
        ("viewer_portrait_url", "VARCHAR(1024) NULL"),
    ):
        cur.execute("""
            SELECT COUNT(1) ColumnIsThere
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema=DATABASE()
              AND table_name='usuarios'
              AND column_name=%s;
        """, (column,))
        if cur.fetchone()[0] == 0:
            cur.execute(f"ALTER TABLE usuarios ADD COLUMN {column} {definition}")

    conn.commit()

    cur.execute("""
        SELECT COUNT(1) ColumnIsThere
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE table_schema=DATABASE()
          AND table_name='arboles'
          AND column_name='user_id';
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("""
            ALTER TABLE arboles
            ADD COLUMN user_id INT NULL
            AFTER viewer_person_id
        """)

    conn.commit()

    cur.execute("""
        SELECT COUNT(1) IndexIsThere
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE table_schema=DATABASE()
          AND table_name='arboles'
          AND index_name='idx_persona_user';
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("""
            CREATE INDEX idx_persona_user
            ON arboles(persona_id, user_id)
        """)

    conn.commit()

    # Una sola fila por (persona_id, user_id). Antes cada "Actualizar todo"
    # insertaba filas nuevas y las viejas quedaban sin usar; acá se borran
    # (quedándose con la más nueva) y el índice único evita que vuelva a pasar.
    cur.execute("""
        SELECT COUNT(1) IndexIsThere
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE table_schema=DATABASE()
          AND table_name='arboles'
          AND index_name='uq_persona_user';
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("""
            DELETE a FROM arboles a
            JOIN arboles b
              ON a.persona_id = b.persona_id
             AND a.user_id = b.user_id
             AND (a.created_at < b.created_at
                  OR (a.created_at = b.created_at AND a.id < b.id))
        """)
        print(f"-> 🧹 {cur.rowcount} árboles duplicados borrados", flush=True)
        cur.execute("""
            CREATE UNIQUE INDEX uq_persona_user
            ON arboles(persona_id, user_id)
        """)

    conn.commit()
    conn.close()

def crear_usuario(username, personal_id):
    conn = get_pool().get_connection()
    cur = conn.cursor()

    password_hash = generate_password_hash(personal_id)
    try:
        cur.execute(
            "INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)",
            (username, password_hash)
        )
        conn.commit()
        return cur.lastrowid
    except mysql.connector.IntegrityError:
        conn.rollback()
        raise DuplicateUsernameError(f"El usuario '{username}' ya existe")
    finally:
        conn.close()

def _row_to_usuario(row):
    if not row:
        return None
    id_, username, password_hash = row
    return {
        "id": id_,
        "username": username,
        "password_hash": password_hash
    }

def obtener_usuario_por_username(username):
    conn = get_pool().get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, username, password_hash FROM usuarios WHERE username=%s",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

    return _row_to_usuario(row)

def guardar_retrato_usuario(user_id, viewer_person_id, portrait_url):
    conn = get_pool().get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE usuarios SET viewer_person_id=%s, viewer_portrait_url=%s WHERE id=%s",
        (viewer_person_id, portrait_url, user_id)
    )
    conn.commit()
    conn.close()

def obtener_retrato_usuario(user_id):
    """(viewer_person_id, viewer_portrait_url) del usuario, o (None, None)."""
    conn = get_pool().get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT viewer_person_id, viewer_portrait_url FROM usuarios WHERE id=%s",
        (user_id,)
    )
    row = cur.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)

def guardar_arbol(persona_id, user_id, viewer_person_id, data, found_relationship=True):
    conn = get_pool().get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO arboles (persona_id, user_id, viewer_person_id, data_json, found_relationship)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            viewer_person_id = VALUES(viewer_person_id),
            data_json = VALUES(data_json),
            found_relationship = VALUES(found_relationship),
            created_at = CURRENT_TIMESTAMP
    """
    data_json = json.dumps(data) if data is not None else None
    cur.execute(query, (persona_id, user_id, viewer_person_id, data_json, int(found_relationship)))

    conn.commit()
    conn.close()

def obtener_arboles_usuario(user_id):
    conn = get_pool().get_connection()
    cur = conn.cursor()

    query = """
      SELECT persona_id, data_json, found_relationship, created_at
      FROM arboles
      WHERE user_id = %s
    """
    cur.execute(query, (user_id,))
    rows = cur.fetchall()

    conn.close()

    result = []
    for persona_id, data_json, found_relationship, created_at in rows:
        data = json.loads(data_json) if data_json else None
        found = True if found_relationship is None else bool(found_relationship)
        result.append({
            "persona_id": persona_id,
            "data": data,
            "found": found,
            "created_at": created_at
        })
    return result

def obtener_ids_procesados(user_id):
    """IDs de personas ya consultadas para este usuario (con o sin parentesco)."""
    conn = get_pool().get_connection()
    cur = conn.cursor()

    cur.execute("SELECT persona_id FROM arboles WHERE user_id = %s", (user_id,))
    ids = {row[0] for row in cur.fetchall()}

    conn.close()
    return ids

def obtener_version_arboles(user_id):
    """Texto que cambia cada vez que se guarda algún árbol del usuario.
    El navegador lo compara con su copia local para saber si está al día."""
    conn = get_pool().get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*), MAX(created_at) FROM arboles WHERE user_id = %s",
        (user_id,)
    )
    count, last = cur.fetchone()

    conn.close()

    return f"{count}-{last.isoformat() if last else ''}"

def obtener_arbol(persona_id, user_id):
    conn = get_pool().get_connection()
    cur = conn.cursor()

    query = """
      SELECT data_json, created_at, found_relationship FROM arboles
      WHERE persona_id = %s AND user_id = %s
      ORDER BY created_at DESC
      LIMIT 1
    """
    cur.execute(query, (persona_id, user_id))
    row = cur.fetchone()

    conn.close()

    if row:
        data_json, created_at, found_relationship = row
        data = json.loads(data_json) if data_json else None
        found = True if found_relationship is None else bool(found_relationship)
        return data, created_at, found

    return None, None, None
