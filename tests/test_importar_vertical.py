"""Prueba del importador de B-2 en formato vertical (ACTIVIDAD:/UNITARIO:...)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import Workbook  # noqa: E402

from scripts.importar_apu_banco import importar  # noqa: E402


def _crear_xlsx(ruta):
    wb = Workbook()
    wb.active.title = "PRESUPUESTO"  # primera hoja (resumen, sin APU)
    ws = wb.create_sheet("APU")
    filas = [
        [None, "ANÁLISIS DE PRECIO UNITARIO"],
        ["ACTIVIDAD:     1.1    Hormigón Armado"],
        ["UNITARIO:     M3"],
        ["CANTIDAD:     25"],
        ["Moneda: Bolivianos"],
        [None, "Descripción", "Und.", "Cantidad", "%", "P.Improd", "P.Prod", "Total"],
        ["1.- ", "MATERIALES"],
        [None, "Cemento Portland", "kg", 320, None, None, 1.2, 384],
        [None, None, None, None, None, None, "TOTAL MATERIALES", 384],
        ["2.- ", "MANO DE OBRA"],
        [None, "Albañil", "hr", 8, None, None, 18.75, 150],
        [None, "BENEFICIOS SOCIALES - % ", None, None, None, 0.55, 82.5, None],
        [None, None, None, None, None, None, "SUBTOTAL MANO DE OBRA", 150],
        ["3.- ", "EQUIPO Y HERRAMIENTAS"],
        [None, "Mezcladora", "hr", 2, None, None, 25, 50],
        [None, "HERRAMIENTAS - % DEL TOTAL", None, None, None, 0.05, 7.5, None],
        ["4.- ", "GASTOS GENERALES"],
        [None, "GASTOS GENERALES - % DE 1+2+3", None, None, None, 0.1, 58, None],
    ]
    for f in filas:
        ws.append(f)
    wb.save(ruta)


def test_importa_formato_vertical(tmp_path):
    ruta = tmp_path / "vertical.xlsx"
    _crear_xlsx(str(ruta))
    apus = importar(str(ruta))
    assert len(apus) == 1
    a = apus[0]
    assert "Hormigón Armado" in a["actividad"]
    assert a["unidad"] == "M3"
    assert a["cantidad"] == 25
    # recursos reales, sin colar totales ni lineas de %
    assert [m["descripcion"] for m in a["materiales"]] == ["Cemento Portland"]
    assert [m["descripcion"] for m in a["mano_obra"]] == ["Albañil"]
    assert [m["descripcion"] for m in a["equipo"]] == ["Mezcladora"]
    assert a["materiales"][0]["precio"] == 1.2
    assert a["materiales"][0]["cantidad"] == 320
    assert a["mano_obra"][0]["unidad"] == "hr"


def _crear_xlsx_flexible(ruta):
    """Formato B-2 oficial desplazado: col A vacia, etiquetas 'Actividad :' en B,
    numero de item antes de la descripcion."""
    wb = Workbook()
    ws = wb.active
    ws.title = "B-2"
    filas = [
        [None, "FORMULARIO B-2"],
        [None, "ANÁLISIS DE PRECIOS UNITARIOS"],
        [None, "Proyecto :", "OBRA X"],
        [None, "Actividad :", "1. Provisión e instalación de cable"],
        [None, "Cantidad  :", 53],
        [None, "Unidad :", "PIEZA"],
        [None, "Moneda :", "BOLIVIANOS"],
        [None, "1.        MATERIALES"],
        [None, "DESCRIPCIÓN", None, "UNIDAD", "CANTIDAD", "PRECIO PRODUCTIVO",
         "COSTO TOTAL"],
        [None, "1", "Cable UTP Cat 6", "Mts", 45, 4.74, 213.3],
        [None, "2", "Conector Jack RJ-45", "Pza", 1, 38.4, 38.4],
        [None, "TOTAL MATERIALES", None, None, None, None, 251.7],
        [None, "2.        MANO DE OBRA"],
        [None, "DESCRIPCIÓN", None, "UNIDAD", "CANTIDAD", "PRECIO PRODUCTIVO",
         "COSTO TOTAL"],
        [None, "1", "Tecnico Especialista", "HR", 1.88, 30, 56.6],
        [None, "CARGAS SOCIALES = (% ", None, None, 0.7118, 40.3],
        [None, "TOTAL MANO DE OBRA", None, None, None, None, 96.9],
        [None, "3.        EQUIPO, MAQUINARIA Y HERRAMIENTAS"],
        [None, "DESCRIPCIÓN", None, "UNIDAD", "CANTIDAD", "PRECIO PRODUCTIVO",
         "COSTO TOTAL"],
        [None, "0.03", "HERRAMIENTAS = (% DE M.O.)", None, None, 2.9],
        [None, "4.        GASTOS GENERALES"],
        [None, "0.07", "GASTOS GENERALES = % DE 1+2+3", None, None, 31.9],
    ]
    for f in filas:
        ws.append(f)
    wb.save(ruta)


def test_importa_formato_flexible(tmp_path):
    ruta = tmp_path / "flexible.xlsx"
    _crear_xlsx_flexible(str(ruta))
    apus = importar(str(ruta))
    assert len(apus) == 1
    a = apus[0]
    assert a["actividad"].startswith("1. Provisión")
    assert a["unidad"] == "PIEZA"
    assert a["cantidad"] == 53
    # toma la descripcion (no el numero de item) y excluye totales/% /herramientas
    assert [m["descripcion"] for m in a["materiales"]] == [
        "Cable UTP Cat 6", "Conector Jack RJ-45"]
    assert [m["descripcion"] for m in a["mano_obra"]] == ["Tecnico Especialista"]
    assert a["equipo"] == []
    assert a["materiales"][0]["unidad"] == "Mts"
    assert a["materiales"][0]["cantidad"] == 45
    assert a["materiales"][0]["precio"] == 4.74
