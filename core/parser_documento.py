"""Extracción de texto desde documentos técnicos (PDF/DOC/DOCX/TXT/imágenes).

Las dependencias de parsing se importan de forma perezosa para que la
aplicación arranque aunque falte alguna librería opcional.

Incluye OCR (pytesseract) para leer DBCs **escaneados** (PDFs que en realidad
son imágenes) y archivos de imagen (PNG/JPG/TIFF). El OCR se activa
automáticamente cuando un PDF tiene poco o ningún texto digital.
"""
from __future__ import annotations

from pathlib import Path

from config.logging_config import get_logger
from core.text_cleaner import limpiar_texto

logger = get_logger(__name__)

# Si una página de PDF tiene menos de estos caracteres, se considera escaneada
# y se intenta OCR.
_MIN_CHARS_PAGINA = 30
_IMG_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def detectar_tipo(nombre_archivo: str) -> str:
    """Infiere el tipo de documento técnico por el nombre del archivo."""
    n = nombre_archivo.lower()
    if "dbc" in n:
        return "DBC"
    if "tdr" in n or "referencia" in n:
        return "TDR"
    if "espec" in n:
        return "especificacion"
    if "pliego" in n:
        return "pliego"
    if "memoria" in n:
        return "memoria"
    if "anexo" in n:
        return "anexo"
    return "documento"


def extraer_texto(ruta: str | Path) -> str:
    """Extrae texto plano de un documento según su extensión."""
    ruta = Path(ruta)
    suf = ruta.suffix.lower()
    if suf == ".pdf":
        texto = _extraer_pdf(ruta)
    elif suf == ".docx":
        texto = _extraer_docx(ruta)
    elif suf == ".doc":
        texto = _extraer_doc(ruta)
    elif suf in {".txt", ".md"}:
        texto = ruta.read_text(encoding="utf-8", errors="ignore")
    elif suf in _IMG_EXTS:
        texto = _ocr_imagen(ruta)
    else:
        raise ValueError(f"Formato de documento no soportado: {suf}")
    return limpiar_texto(texto)


def _extraer_pdf(ruta: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        logger.warning("pypdf no instalado; no se puede leer PDF %s", ruta)
        return ""
    try:
        reader = PdfReader(str(ruta))
        partes = []
        paginas_escaneadas = []
        for i, page in enumerate(reader.pages):
            texto = page.extract_text() or ""
            if len(texto.strip()) < _MIN_CHARS_PAGINA:
                paginas_escaneadas.append(i)  # candidata a OCR
            partes.append(f"\n[[PAGINA {i + 1}]]\n{texto}")

        # Si hay páginas con poco texto (PDF escaneado), intentar OCR de todo
        if paginas_escaneadas:
            logger.info("PDF %s: %d página(s) parecen escaneadas; intentando OCR",
                        ruta.name, len(paginas_escaneadas))
            texto_ocr = _ocr_pdf(ruta, paginas_escaneadas)
            if texto_ocr:
                return texto_ocr
        return "\n".join(partes)
    except Exception:
        logger.exception("Error extrayendo PDF %s", ruta)
        return ""


def _ocr_pdf(ruta: Path, paginas: list[int] | None = None) -> str:
    """OCR de un PDF escaneado, procesando PÁGINA POR PÁGINA.

    Convertir todo el PDF a imágenes de golpe puede consumir cientos de MB y
    tumbar el contenedor por falta de memoria (OOM), lo que reinicia la app y
    desconecta a los usuarios. Para evitarlo, se convierte y reconoce una sola
    página a la vez, liberando cada imagen antes de pasar a la siguiente, con un
    DPI y un tope de páginas configurables (config.settings).
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning(
            "OCR no disponible (instale pytesseract, pdf2image y Tesseract) "
            "para leer PDFs escaneados: %s", ruta.name)
        return ""

    from config import settings
    dpi = settings.OCR_DPI
    max_pag = settings.OCR_MAX_PAGINAS

    # Total de páginas (para acotar el recorrido sin cargar el PDF entero).
    total = None
    try:
        from pdf2image import pdfinfo_from_path
        total = int(pdfinfo_from_path(str(ruta)).get("Pages", 0)) or None
    except Exception:
        total = None

    limite = max_pag if max_pag > 0 else (total or 0)
    if total and max_pag > 0:
        limite = min(total, max_pag)
        if total > max_pag:
            logger.warning(
                "PDF %s tiene %d páginas; OCR procesa solo las primeras %d "
                "(OCR_MAX_PAGINAS).", ruta.name, total, max_pag)

    partes = []
    pagina = 0
    while limite == 0 or pagina < limite:
        idx = pagina  # 0-indexed para la selección de `paginas`
        pagina += 1
        if paginas is not None and idx not in paginas:
            continue
        try:
            imgs = convert_from_path(str(ruta), dpi=dpi,
                                     first_page=pagina, last_page=pagina)
        except Exception:
            # Página fuera de rango o error puntual: si no sabíamos el total,
            # esto marca el fin del documento.
            if total is None:
                break
            logger.exception("Error convirtiendo página %d de %s",
                             pagina, ruta.name)
            continue
        if not imgs:
            break  # no hay más páginas
        for img in imgs:
            try:
                texto = pytesseract.image_to_string(img, lang=_idioma_ocr())
                partes.append(f"\n[[PAGINA {pagina}]]\n{texto}")
            except Exception:
                logger.exception("Error en OCR de la página %d de %s",
                                 pagina, ruta.name)
            finally:
                try:
                    img.close()  # libera la imagen de inmediato (memoria)
                except Exception:
                    pass
    return "\n".join(partes)


def _ocr_imagen(ruta: Path) -> str:
    """OCR de un archivo de imagen (PNG/JPG/TIFF)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("OCR no disponible para imagen %s (instale pytesseract "
                       "y Tesseract).", ruta.name)
        return ""
    try:
        return pytesseract.image_to_string(Image.open(ruta), lang=_idioma_ocr())
    except Exception:
        logger.exception("Error en OCR de la imagen %s", ruta)
        return ""


def _idioma_ocr() -> str:
    """Idioma para Tesseract (español si está disponible, si no inglés)."""
    try:
        import pytesseract
        idiomas = pytesseract.get_languages(config="")
        return "spa" if "spa" in idiomas else "eng"
    except Exception:
        return "eng"


def _extraer_docx(ruta: Path) -> str:
    try:
        import docx  # python-docx
    except ImportError:  # pragma: no cover
        logger.warning("python-docx no instalado; no se puede leer %s", ruta)
        return ""
    try:
        doc = docx.Document(str(ruta))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        logger.exception("Error extrayendo DOCX %s", ruta)
        return ""


def _extraer_doc(ruta: Path) -> str:
    """.doc heredado: intenta textract; si no, avisa."""
    try:
        import textract  # type: ignore

        return textract.process(str(ruta)).decode("utf-8", errors="ignore")
    except Exception:
        logger.warning(
            "No se pudo leer .doc %s (instale textract o convierta a .docx)", ruta
        )
        return ""
