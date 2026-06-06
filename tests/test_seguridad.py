"""Pruebas de seguridad: saneo de nombre de archivo y validacion de GA."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.text_cleaner import nombre_archivo_seguro  # noqa: E402


def test_bloquea_path_traversal():
    assert "/" not in nombre_archivo_seguro("../../etc/passwd")
    assert ".." not in nombre_archivo_seguro("../../etc/passwd")
    assert nombre_archivo_seguro("../../etc/passwd") == "passwd"


def test_bloquea_ruta_windows():
    r = nombre_archivo_seguro(r"C:\Windows\system32\evil.xlsx")
    assert "\\" not in r and ":" not in r
    assert r.endswith("evil.xlsx")


def test_conserva_nombre_normal():
    assert nombre_archivo_seguro("Formulario_B-2.xlsx") == "Formulario_B-2.xlsx"


def test_nombre_vacio_o_oculto_da_defecto():
    assert nombre_archivo_seguro("") == "archivo"
    assert nombre_archivo_seguro("...") == "archivo"
    assert nombre_archivo_seguro("/") == "archivo"


def test_ga_solo_acepta_id_valido():
    from core import analytics
    assert analytics._ID_VALIDO.match("G-ABC12345")
    assert not analytics._ID_VALIDO.match("G-<script>")
    assert not analytics._ID_VALIDO.match("'; alert(1)//")
