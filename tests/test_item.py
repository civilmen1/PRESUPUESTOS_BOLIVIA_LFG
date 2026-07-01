"""Pruebas del modelo Item (incluye la etiqueta de unidad para la UI)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.item import Item  # noqa: E402


def test_etiqueta_unidad_con_unidad():
    it = Item(descripcion="Hormigón armado H21", unidad="m3", cantidad=12.0)
    assert it.etiqueta_unidad == "[m3]"


def test_etiqueta_unidad_sin_unidad():
    # Muchos ítems importados llegan sin unidad: debe indicarse, no quedar vacío.
    it = Item(descripcion="Actividad sin unidad", unidad="", cantidad=5.0)
    assert it.etiqueta_unidad == "[sin unidad]"


def test_etiqueta_unidad_ignora_espacios():
    it = Item(descripcion="Pintura", unidad="  m2  ", cantidad=1.0)
    assert it.etiqueta_unidad == "[m2]"
