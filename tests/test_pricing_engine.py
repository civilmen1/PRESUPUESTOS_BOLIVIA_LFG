"""Pruebas de las reglas de precio adoptado (rules_engine)."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.rules_engine import (FuentePrecio, calcular_precio_adoptado)  # noqa: E402
from core.unit_converter import factor_conversion, homologar_precio  # noqa: E402


def _f(precio, nivel=1, fecha=None, validado=False):
    return FuentePrecio(precio=precio, nivel=nivel,
                        fecha=fecha or datetime.now().strftime("%Y-%m-%d"),
                        fuente=f"n{nivel}", validado=validado)


def test_fuente_unica_con_advertencia():
    r = calcular_precio_adoptado([_f(100)])
    assert r.precio == 100
    assert r.regla == "fuente_unica"
    assert any("única" in a for a in r.alertas)


def test_mediana_dos_o_tres_fuentes():
    r = calcular_precio_adoptado([_f(100), _f(120), _f(110)])
    assert r.regla == "mediana"
    assert r.precio == 110


def test_mediana_depurada_descarta_outliers():
    r = calcular_precio_adoptado([_f(100), _f(105), _f(110), _f(115), _f(1000)])
    assert r.regla == "mediana_depurada"
    assert r.precio < 200  # el outlier 1000 fue descartado


def test_precio_manual_validado_tiene_prioridad():
    fuentes = [_f(100, nivel=1), _f(999, nivel=0, validado=True)]
    r = calcular_precio_adoptado(fuentes)
    assert r.precio == 999
    assert r.regla == "manual_validado"


def test_email_prioriza_sobre_web():
    fuentes = [_f(50, nivel=2), _f(80, nivel=3)]
    r = calcular_precio_adoptado(fuentes)
    assert r.regla == "email_confirmado"
    assert r.precio == 80


def test_alerta_vigencia():
    vieja = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
    r = calcular_precio_adoptado([_f(100, fecha=vieja), _f(110, fecha=vieja)])
    assert any("antigüedad" in a for a in r.alertas)


def test_sin_fuentes():
    r = calcular_precio_adoptado([])
    assert r.precio == 0
    assert r.regla == "sin_precio"


def test_conversion_unidades():
    assert factor_conversion("ton", "kg") == 1000.0
    precio, factor = homologar_precio(1000.0, "ton", "kg")
    assert precio == 1.0  # 1000 BOB/ton -> 1 BOB/kg
    assert factor_conversion("m3", "kg") is None  # no homologable
