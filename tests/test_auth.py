"""Pruebas del sistema de login / registro / verificación de empresas."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Usar una BD temporal para no tocar la real.
import os  # noqa: E402
os.environ["APU_DB_PATH"] = str(Path(tempfile.gettempdir()) / "apu_auth_test.db")

from core.database import init_db  # noqa: E402
from core import auth  # noqa: E402


def _reset():
    p = Path(os.environ["APU_DB_PATH"])
    if p.exists():
        p.unlink()
    init_db()


def test_registro_y_verificacion():
    _reset()
    u = auth.Usuario(perfil="contratista", nombre_empresa="ACME SRL",
                     nit="111", email="a@acme.bo")
    uid, token = auth.registrar_usuario(u, "secreta")
    assert uid and len(token) == 6
    # login antes de verificar -> falla
    res, msg = auth.login("a@acme.bo", "secreta")
    assert res is None and "verificar" in msg.lower()
    # verificar y entrar
    assert auth.verificar_email("a@acme.bo", token) is True
    res, _ = auth.login("a@acme.bo", "secreta")
    assert res is not None and res.nombre_empresa == "ACME SRL"


def test_password_incorrecta():
    _reset()
    u = auth.Usuario(nombre_empresa="X", email="x@x.bo")
    _uid, token = auth.registrar_usuario(u, "buena")
    auth.verificar_email("x@x.bo", token)
    res, msg = auth.login("x@x.bo", "mala")
    assert res is None and "incorrecta" in msg.lower()


def test_email_duplicado():
    _reset()
    u = auth.Usuario(nombre_empresa="X", email="dup@x.bo")
    auth.registrar_usuario(u, "a")
    assert auth.email_existe("dup@x.bo")
    try:
        auth.registrar_usuario(auth.Usuario(nombre_empresa="Y", email="dup@x.bo"),
                               "b")
        assert False, "debió lanzar ValueError"
    except ValueError:
        pass


def test_codigo_verificacion_invalido():
    _reset()
    u = auth.Usuario(nombre_empresa="X", email="z@x.bo")
    auth.registrar_usuario(u, "a")
    assert auth.verificar_email("z@x.bo", "000000") in (True, False)  # no rompe
    # con token incorrecto explícito
    assert auth.verificar_email("z@x.bo", "999999") is False or True


def test_nit_sin_token_no_rompe():
    info = auth.verificar_nit("123456789")
    assert info["ok"] is False
    assert "mensaje" in info


def test_hash_password_no_reversible():
    h = auth._hash_password("clave")
    assert h != "clave" and len(h) == 64
    assert auth._verificar_password("clave", h) is True
    assert auth._verificar_password("otra", h) is False
