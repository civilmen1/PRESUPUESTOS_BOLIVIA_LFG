"""Pruebas del parser de tabla de cantidades."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from core.parser_tabla import dataframe_a_items  # noqa: E402


def test_mapeo_columnas_basico():
    df = pd.DataFrame({
        "Módulo": ["Estructura"],
        "N°": ["1"],
        "Descripción": ["Hormigón armado para columnas"],
        "Unidad": ["m3"],
        "Cantidad": [12.5],
    })
    items = dataframe_a_items(df, proyecto_id=1)
    assert len(items) == 1
    it = items[0]
    assert it.descripcion.startswith("Hormigón")
    assert it.unidad == "m3"
    assert it.cantidad == 12.5
    assert it.palabras_clave  # se extrajeron keywords


def test_columnas_alternativas():
    df = pd.DataFrame({
        "detalle": ["Excavación de zanja"],
        "und": ["m3"],
        "cant": ["3,5"],  # coma decimal
    })
    items = dataframe_a_items(df)
    assert len(items) == 1
    assert items[0].cantidad == 3.5


def test_filas_vacias_se_ignoran():
    df = pd.DataFrame({"descripcion": ["Item A", "", None], "unidad": ["m2", "", ""]})
    items = dataframe_a_items(df)
    assert len(items) == 1
