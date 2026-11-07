import importlib

import pytest


@pytest.fixture
def db(tmp_path, monkeypatch):
    """db.db apuntando a un archivo SQLite temporal y vacío."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "sub" / "test.db"))
    import db.db as module
    module = importlib.reload(module)
    module.init_db()
    return module


def test_init_db_crea_archivo_y_es_repetible(db, tmp_path):
    assert (tmp_path / "sub" / "test.db").exists()
    db.init_db()  # correr dos veces no falla


def test_usuario_se_crea_una_sola_vez(db):
    a = db.obtener_o_crear_usuario_fs("ABCD-123")
    b = db.obtener_o_crear_usuario_fs("ABCD-123")
    c = db.obtener_o_crear_usuario_fs("WXYZ-999")
    assert a == b
    assert a != c


def test_retrato(db):
    uid = db.obtener_o_crear_usuario_fs("ABCD-123")
    assert db.obtener_retrato_usuario(uid) == ("ABCD-123", None)
    db.guardar_retrato_usuario(uid, "ABCD-123", "https://example.com/foto.jpg")
    assert db.obtener_retrato_usuario(uid) == ("ABCD-123", "https://example.com/foto.jpg")
    assert db.obtener_retrato_usuario(9999) == (None, None)


def test_guardar_y_leer_arboles(db):
    uid = db.obtener_o_crear_usuario_fs("ABCD-123")
    assert db.obtener_arbol("P1", uid) == (None, None, None)

    db.guardar_arbol("P1", uid, "ABCD-123", {"name": "Artigas"})
    db.guardar_arbol("P2", uid, "ABCD-123", None, found_relationship=False)

    data, created_at, found = db.obtener_arbol("P1", uid)
    assert data == {"name": "Artigas"} and found is True and created_at
    assert db.obtener_arbol("P2", uid)[2] is False
    assert db.obtener_ids_procesados(uid) == {"P1", "P2"}

    arboles = {a["persona_id"]: a for a in db.obtener_arboles_usuario(uid)}
    assert arboles["P1"]["data"] == {"name": "Artigas"}
    assert arboles["P2"]["found"] is False


def test_guardar_dos_veces_actualiza_y_cambia_version(db):
    uid = db.obtener_o_crear_usuario_fs("ABCD-123")
    db.guardar_arbol("P1", uid, "ABCD-123", {"v": 1})
    v1 = db.obtener_version_arboles(uid)
    db.guardar_arbol("P1", uid, "ABCD-123", {"v": 2})
    v2 = db.obtener_version_arboles(uid)

    assert db.obtener_arbol("P1", uid)[0] == {"v": 2}
    assert len(db.obtener_arboles_usuario(uid)) == 1
    assert v1 != v2


def test_usuarios_no_ven_arboles_ajenos(db):
    a = db.obtener_o_crear_usuario_fs("ABCD-123")
    b = db.obtener_o_crear_usuario_fs("WXYZ-999")
    db.guardar_arbol("P1", a, "ABCD-123", {"x": 1})
    assert db.obtener_arboles_usuario(b) == []
    assert db.obtener_arbol("P1", b) == (None, None, None)
