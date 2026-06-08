"""Pruebas de parsing/limpieza/segmentación de documentos técnicos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.parser_documento import detectar_tipo, extraer_texto  # noqa: E402
from core.segmentador import segmentar  # noqa: E402
from core.text_cleaner import limpiar_texto, normalizar  # noqa: E402


def test_detectar_tipo():
    assert detectar_tipo("DBC_obra.pdf") == "DBC"
    assert detectar_tipo("especificaciones_tecnicas.docx") == "especificacion"
    assert detectar_tipo("TDR_proyecto.pdf") == "TDR"


def test_limpiar_y_normalizar():
    sucio = "Hormigón   Armado\n\n\n\nH21-\nResistente"
    limpio = limpiar_texto(sucio)
    assert "Hormigón Armado" in limpio
    assert "H21Resistente" in limpio  # une guion de fin de línea
    assert normalizar("Hörmigón Ñandú") == "hormigon ñandu".replace("ñ", "n")


def test_extraer_txt(tmp_path):
    ruta = tmp_path / "espec.txt"
    ruta.write_text("1. ALCANCE\nEl hormigón será H21.\n2. MEDICION\nPor m3.",
                    encoding="utf-8")
    texto = extraer_texto(ruta)
    assert "ALCANCE" in texto


def test_segmentar_por_numerales():
    texto = ("1. ALCANCE\nEl item comprende excavación.\n"
             "2. MATERIALES\nCemento y arena.\n"
             "3. MEDICION\nSe mide por metro cúbico.")
    secciones = segmentar(texto, fuente_id=1)
    assert len(secciones) >= 2
    titulos = " ".join(s.titulo for s in secciones)
    assert "MATERIALES" in titulos or "ALCANCE" in titulos
