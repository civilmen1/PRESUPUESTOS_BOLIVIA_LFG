"""Extracción de texto desde documentos técnicos (PDF/DOC/DOCX/TXT).

Las dependencias de parsing se importan de forma perezosa para que la
aplicación arranque aunque falte alguna librería opcional.
"""
from __future__ import annotations

from pathlib import Path

from config.logging_config import get_logger
from core.text_cleaner import limpiar_texto

logger = get_logger(__name__)


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
        for i, page in enumerate(reader.pages):
            # marca de página para permitir segmentación por página
            partes.append(f"\n[[PAGINA {i + 1}]]\n{page.extract_text() or ''}")
        return "\n".join(partes)
    except Exception:
        logger.exception("Error extrayendo PDF %s", ruta)
        return ""


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
