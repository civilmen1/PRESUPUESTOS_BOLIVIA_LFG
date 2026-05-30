"""Limpieza y normalización de texto."""
from __future__ import annotations

import re
import unicodedata

_MULTISPACE = re.compile(r"[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


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
