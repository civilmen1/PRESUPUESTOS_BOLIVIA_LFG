"""Pruebas del manejo de monedas (BOB / USD / extensible)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import currency  # noqa: E402
from models.project import Proyecto  # noqa: E402


def test_convertir_bob_a_usd():
    # 696 Bs / 6.96 = 100 $us
    assert currency.convertir(696, "USD") == 100.0
    assert currency.convertir(696, "BOB") == 696.0


def test_a_bob_desde_usd():
    assert currency.a_bob(100, "USD") == 696.0
    assert currency.a_bob(500, "BOB") == 500.0


def test_formateo_con_simbolo():
    assert currency.formatear(1000, "BOB") == "Bs 1,000.00"
    assert currency.formatear(696, "USD") == "$us 100.00"


def test_nombre_y_etiqueta():
    assert currency.nombre("BOB") == "Bolivianos"
    assert currency.simbolo("BOB") == "Bs"
    assert currency.etiqueta("USD") == "Dólares Americanos ($us)"


def test_tipo_cambio_del_proyecto():
    p = Proyecto(nombre="X", moneda="USD", tipo_cambio=7.10)
    assert currency.tipo_cambio(p) == 7.10
    assert currency.tipo_cambio(None) == 6.96


def test_agregar_y_convertir_moneda_nueva():
    currency.agregar_moneda("PEN", "Soles", "S/", 3.75)
    try:
        assert "PEN" in currency.codigos()
        # 696 BOB -> 100 USD -> 375 PEN
        assert currency.convertir(696, "PEN") == 375.0
    finally:
        currency.eliminar_moneda("PEN")
    assert "PEN" not in currency.codigos()


def test_no_elimina_monedas_base():
    currency.eliminar_moneda("BOB")
    currency.eliminar_moneda("USD")
    assert "BOB" in currency.codigos()
    assert "USD" in currency.codigos()
