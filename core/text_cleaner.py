"""Limpieza y normalización de texto."""
from __future__ import annotations

import os
import re
import unicodedata

_MULTISPACE = re.compile(r"[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_NOMBRE_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")


def nombre_archivo_seguro(nombre: str, por_defecto: str = "archivo") -> str:
    """Devuelve un nombre de archivo seguro (sin rutas ni caracteres raros).

    Evita 'path traversal': descarta cualquier componente de directorio
    (../, /etc/passwd, C:\\...) y deja solo el nombre base saneado.
    """
    base = os.path.basename((nombre or "").replace("\\", "/").strip())
    base = _NOMBRE_SEGURO.sub("_", base).strip("._")
    # Evita nombres ocultos o vacios tras el saneo.
    if not base or base in (".", ".."):
        return por_defecto
    return base[:120]


def limpiar_texto(texto: str) -> str:
    """Normaliza saltos de línea, espacios y caracteres de control."""
    if not texto:
        return ""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = _CONTROL.sub("", texto)
    # une palabras partidas por guion al final de línea
    texto = re.sub(r"-\n(\w)", r"\1", texto)
    texto = _MULTISPACE.sub(" ", texto)
    texto = _MULTINEWLINE.sub("\n\n", texto)
    lineas = [ln.strip() for ln in texto.split("\n")]
    return "\n".join(lineas).strip()


def normalizar(texto: str) -> str:
    """Pasa a minúsculas y elimina tildes para comparación de keywords."""
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


_STOPWORDS = {
    "de", "la", "el", "los", "las", "y", "o", "a", "en", "con", "para",
    "por", "del", "al", "un", "una", "unos", "unas", "se", "su", "sus",
    "que", "es", "como", "mas", "más", "este", "esta", "estos", "estas",
}


def tokenizar(texto: str, min_len: int = 3) -> list[str]:
    """Devuelve tokens normalizados sin stopwords (para matching semántico)."""
    norm = normalizar(texto)
    tokens = re.findall(r"[a-z0-9]+", norm)
    return [t for t in tokens if len(t) >= min_len and t not in _STOPWORDS]


def extraer_keywords(texto: str, max_kw: int = 15) -> list[str]:
    """Extrae keywords frecuentes preservando orden de aparición."""
    tokens = tokenizar(texto)
    vistos: dict[str, int] = {}
    for t in tokens:
        vistos[t] = vistos.get(t, 0) + 1
    ordenados = sorted(vistos.items(), key=lambda x: (-x[1]))
    return [t for t, _ in ordenados[:max_kw]]
