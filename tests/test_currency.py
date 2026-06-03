"""Pruebas del manejo de monedas (BOB / USD)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import currency  # noqa: E402
from models.project import Proyecto  # noqa: E402


def test_convertir_bob_a_usd():
    # 696 Bs / 6.96 = 100 $us
    assert currency.convertir(696, "USD", 6.96) == 100.0
    assert currency.convertir(696, "BOB", 6.96) == 696.0


def test_a_bob_desde_usd():
    assert currency.a_bob(100, "USD", 6.96) == 696.0
    assert currency.a_bob(500, "BOB") == 500.0


def test_formateo_con_simbolo():
    assert currency.formatear(1000, "BOB") == "Bs 1,000.00"
    assert currency.formatear(696, "USD", 6.96) == "$us 100.00"


def test_tipo_cambio_del_proyecto():
    p = Proyecto(nombre="X", moneda="USD", tipo_cambio=7.10)
    assert currency.tipo_cambio(p) == 7.10
    # sin proyecto usa el global por defecto (6.96)
    assert currency.tipo_cambio(None) == 6.96


def test_simbolos():
    assert currency.simbolo("BOB") == "Bs"
    assert currency.simbolo("USD") == "$us"
