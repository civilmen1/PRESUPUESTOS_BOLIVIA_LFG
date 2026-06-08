"""La mano de obra debe expresarse SIEMPRE en horas, con precio realista."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.unit_converter import canonica, factor_conversion, homologar_precio  # noqa: E402


def test_conversion_jornal_hora():
    assert factor_conversion("jornal", "hora") == 8.0
    # un jornal de 150 Bs equivale a 18.75 Bs/hora
    precio, factor = homologar_precio(150.0, "jornal", "hora")
    assert precio == 18.75


def test_alias_de_horas():
    for u in ("HR.", "HRS.", "Hra", "h", "horas"):
        assert canonica(u) == "hora"


def test_salarios_en_horas():
    from core import data_loader
    sal = data_loader.salarios()
    assert sal.get("_unidad") == "hora"
    for clave, val in sal.items():
        if clave.startswith("_"):
            continue
        assert val["unidad"] == "hora"
        # precio horario realista en Bolivia (no jornal de cientos de Bs)
        assert val["precio"] < 60


def test_plantilla_minima_mano_obra_en_horas():
    from core.apu_engine import _garantizar_minimos
    from models.item import Item
    from models.apu_resource import TIPO_MANO_OBRA
    item = Item(descripcion="Muro de ladrillo", unidad="m2", cantidad=1)
    recursos = _garantizar_minimos(item, [])
    mo = [r for r in recursos if r.tipo == TIPO_MANO_OBRA]
    assert mo and all(r.unidad == "hora" for r in mo)
