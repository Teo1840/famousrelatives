"""Cache local de la versión Flask, en un archivo SQLite (sin servidor ni Docker).

El archivo se crea solo la primera vez. Por defecto es data/famousrelatives.db;
se puede cambiar con DB_PATH en .env. Contiene árboles familiares: está en
.gitignore y no se sube al repo.
"""
import json
import os
import sqlite3
from contextlib import closing

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH") or os.path.join(BASE_DIR, "data", "famousrelatives.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    username            TEXT NOT NULL UNIQUE,
    viewer_person_id    TEXT,
    viewer_portrait_url TEXT,
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usuarios_viewer ON usuarios(viewer_person_id);

CREATE TABLE IF NOT EXISTS arboles (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id         TEXT NOT NULL,
    user_id            INTEGER NOT NULL REFERENCES usuarios(id),
    viewer_person_id   TEXT,
    data_json          TEXT,
    found_relationship INTEGER,
    -- Con milisegundos: obtener_version_arboles detecta dos guardados en el mismo segundo.
    created_at         TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now')),
    UNIQUE (persona_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_arboles_user ON arboles(user_id);
"""


def _connect():
    # Una conexión por llamada: Flask y el hilo que busca los árboles escriben a
    # la vez, y SQLite no permite compartir una conexión entre hilos.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(_connect()) as conn:
        # WAL: se puede leer (dashboard) mientras se escribe (búsqueda en curso).
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.commit()


def obtener_o_crear_usuario_fs(person_id):
    """Id del usuario de la app para una cuenta de FamilySearch (su personId)."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT id FROM usuarios WHERE viewer_person_id = ? ORDER BY id LIMIT 1",
            (person_id,)
        ).fetchone()
        if row:
            return row[0]
        cur = conn.execute(
            "INSERT INTO usuarios (username, viewer_person_id) VALUES (?, ?)",
            (f"fs:{person_id}", person_id)
        )
        conn.commit()
        return cur.lastrowid


def guardar_retrato_usuario(user_id, viewer_person_id, portrait_url):
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE usuarios SET viewer_person_id = ?, viewer_portrait_url = ? WHERE id = ?",
            (viewer_person_id, portrait_url, user_id)
        )
        conn.commit()


def obtener_retrato_usuario(user_id):
    """(viewer_person_id, viewer_portrait_url) del usuario, o (None, None)."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT viewer_person_id, viewer_portrait_url FROM usuarios WHERE id = ?",
            (user_id,)
        ).fetchone()
    return (row[0], row[1]) if row else (None, None)


def guardar_arbol(persona_id, user_id, viewer_person_id, data, found_relationship=True):
    data_json = json.dumps(data) if data is not None else None
    with closing(_connect()) as conn:
        conn.execute("""
            INSERT INTO arboles (persona_id, user_id, viewer_person_id, data_json, found_relationship)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (persona_id, user_id) DO UPDATE SET
                viewer_person_id   = excluded.viewer_person_id,
                data_json          = excluded.data_json,
                found_relationship = excluded.found_relationship,
                created_at         = strftime('%Y-%m-%d %H:%M:%f', 'now')
        """, (persona_id, user_id, viewer_person_id, data_json, int(found_relationship)))
        conn.commit()


def _fila_a_arbol(data_json, found_relationship):
    data = json.loads(data_json) if data_json else None
    found = True if found_relationship is None else bool(found_relationship)
    return data, found


def obtener_arboles_usuario(user_id):
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT persona_id, data_json, found_relationship, created_at FROM arboles WHERE user_id = ?",
            (user_id,)
        ).fetchall()

    result = []
    for persona_id, data_json, found_relationship, created_at in rows:
        data, found = _fila_a_arbol(data_json, found_relationship)
        result.append({
            "persona_id": persona_id,
            "data": data,
            "found": found,
            "created_at": created_at,
        })
    return result


def obtener_ids_procesados(user_id):
    """IDs de personas ya consultadas para este usuario (con o sin parentesco)."""
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT persona_id FROM arboles WHERE user_id = ?", (user_id,)).fetchall()
    return {row[0] for row in rows}


def obtener_version_arboles(user_id):
    """Texto que cambia cada vez que se guarda algún árbol del usuario.
    El navegador lo compara con su copia local para saber si está al día."""
    with closing(_connect()) as conn:
        count, last = conn.execute(
            "SELECT COUNT(*), MAX(created_at) FROM arboles WHERE user_id = ?",
            (user_id,)
        ).fetchone()
    return f"{count}-{last or ''}"


def obtener_arbol(persona_id, user_id):
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT data_json, created_at, found_relationship FROM arboles WHERE persona_id = ? AND user_id = ?",
            (persona_id, user_id)
        ).fetchone()

    if row:
        data_json, created_at, found_relationship = row
        data, found = _fila_a_arbol(data_json, found_relationship)
        return data, created_at, found

    return None, None, None
