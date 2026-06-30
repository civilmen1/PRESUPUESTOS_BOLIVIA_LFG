"""Pruebas del importador masivo de precios de referencia (Nivel 1)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.importar_precios import (_a_float, _mapear_columnas,  # noqa: E402
                                   importar_precios_df)


def test_a_float_formatos():
    assert _a_float("1.234,56") == 1234.56   # formato boliviano (miles . dec ,)
    assert _a_float("1,234.56") == 1234.56   # formato anglosajón
    assert _a_float("Bs 55,00") == 55.0
    assert _a_float("120.50") == 120.5
    assert _a_float("") == 0.0
    assert _a_float(None) == 0.0


def test_mapeo_columnas_flexible():
    cols = ["Descripción", "Unidad", "Precio (Bs)", "Categoría", "Departamento"]
    mapa = _mapear_columnas(cols)
    assert mapa["descripcion"] == "Descripción"
    assert mapa["unidad"] == "Unidad"
    assert mapa["precio"] == "Precio (Bs)"
    assert mapa["categoria"] == "Categoría"
    assert mapa["region"] == "Departamento"


def test_importar_df_cuenta_y_omite():
    df = pd.DataFrame({
        "Material": ["Cemento Portland", "Arena fina", "Fila mala"],
        "Unidad": ["kg", "m3", "kg"],
        "Precio (Bs)": ["1,10", "120.50", "0"],   # la última tiene precio 0
    })
    res = importar_precios_df(df, persistir=False)
    assert res["importados"] == 2
    assert res["omitidos"] == 1
    assert res["total"] == 3


def test_importar_df_columnas_faltantes():
    df = pd.DataFrame({"Material": ["x"], "Precio": ["10"]})  # falta unidad
    with pytest.raises(ValueError):
        importar_precios_df(df, persistir=False)


def test_fuentes_para_respeta_dry_run(monkeypatch):
    from config import settings
    from providers import search_online
    monkeypatch.setattr(settings, "SCRAPER_FUENTES",
                        ["https://t.bo/buscar?q={q}"], raising=False)
    # En DRY-RUN no devuelve fuentes (simula).
    monkeypatch.setattr(settings, "SCRAPER_DRY_RUN", True, raising=False)
    assert search_online._fuentes_para("cemento portland") is None
    # Fuera de DRY-RUN, sustituye {q} por el término codificado.
    monkeypatch.setattr(settings, "SCRAPER_DRY_RUN", False, raising=False)
    urls = search_online._fuentes_para("cemento portland")
    assert urls == ["https://t.bo/buscar?q=cemento+portland"]
