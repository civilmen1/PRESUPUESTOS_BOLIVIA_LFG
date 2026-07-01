"""Pruebas de parsing/limpieza/segmentación de documentos técnicos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import types  # noqa: E402

import core.parser_documento as pdoc  # noqa: E402
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


def _instalar_ocr_falso(monkeypatch, total_paginas):
    """Inyecta pytesseract y pdf2image falsos para probar el OCR sin binarios."""
    llamadas = {"convert": []}

    class _ImgFalsa:
        def __init__(self, n):
            self.n = n
            self.cerrada = False

        def close(self):
            self.cerrada = True

    def convert_from_path(ruta, dpi=200, first_page=None, last_page=None):
        # El arreglo procesa PÁGINA POR PÁGINA: first_page == last_page.
        llamadas["convert"].append((first_page, last_page, dpi))
        if first_page and first_page > total_paginas:
            return []
        return [_ImgFalsa(first_page or 1)]

    def pdfinfo_from_path(ruta):
        return {"Pages": total_paginas}

    pdf2image = types.ModuleType("pdf2image")
    pdf2image.convert_from_path = convert_from_path
    pdf2image.pdfinfo_from_path = pdfinfo_from_path

    pytesseract = types.ModuleType("pytesseract")
    pytesseract.image_to_string = lambda img, lang=None: f"texto p{img.n}"
    pytesseract.get_languages = lambda config="": ["spa", "eng"]

    monkeypatch.setitem(sys.modules, "pdf2image", pdf2image)
    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract)
    return llamadas


def test_ocr_pdf_pagina_por_pagina(monkeypatch, tmp_path):
    """El OCR convierte una página a la vez (no todo el PDF de golpe)."""
    from config import settings
    llamadas = _instalar_ocr_falso(monkeypatch, total_paginas=3)
    monkeypatch.setattr(settings, "OCR_MAX_PAGINAS", 40, raising=False)
    monkeypatch.setattr(settings, "OCR_DPI", 150, raising=False)
    ruta = tmp_path / "escaneado.pdf"
    ruta.write_bytes(b"%PDF-1.4 fake")
    texto = pdoc._ocr_pdf(ruta)
    # Una conversión por página, cada una con first_page == last_page.
    assert len(llamadas["convert"]) == 3
    assert all(fp == lp for fp, lp, _ in llamadas["convert"])
    assert all(dpi == 150 for _, _, dpi in llamadas["convert"])
    assert "texto p1" in texto and "texto p3" in texto


def test_ocr_pdf_respeta_tope_paginas(monkeypatch, tmp_path):
    """Un PDF enorme no se procesa entero: respeta OCR_MAX_PAGINAS (anti-OOM)."""
    from config import settings
    llamadas = _instalar_ocr_falso(monkeypatch, total_paginas=100)
    monkeypatch.setattr(settings, "OCR_MAX_PAGINAS", 5, raising=False)
    ruta = tmp_path / "largo.pdf"
    ruta.write_bytes(b"%PDF-1.4 fake")
    pdoc._ocr_pdf(ruta)
    assert len(llamadas["convert"]) == 5


def test_segmentar_por_numerales():
    texto = ("1. ALCANCE\nEl item comprende excavación.\n"
             "2. MATERIALES\nCemento y arena.\n"
             "3. MEDICION\nSe mide por metro cúbico.")
    secciones = segmentar(texto, fuente_id=1)
    assert len(secciones) >= 2
    titulos = " ".join(s.titulo for s in secciones)
    assert "MATERIALES" in titulos or "ALCANCE" in titulos
