"""Embeddings para busqueda semantica (vincular por SIGNIFICADO, no palabras).

Diseno para Render (sin torch ni paquetes pesados): los vectores se obtienen
via API/Ollama usando solo `requests`. Proveedor por prioridad:

  1. Ollama local (gratis, en tu PC)   ->  modelo OLLAMA_EMBED_MODEL
  2. Gemini (gratis, online en Render) ->  modelo GEMINI_EMBED_MODEL
  3. OpenAI (de pago)                  ->  modelo OPENAI_EMBED_MODEL

Si ningun proveedor responde, `embed()` devuelve None y el llamador cae al
matcher TF-IDF de siempre. Los vectores se cachean en disco por hash del texto
para no recalcular (clave: proveedor:modelo:sha1(texto))."""
from __future__ import annotations

import hashlib
import json
import math
from typing import List, Optional

from config import settings
from config.logging_config import get_logger

logger = get_logger(__name__)

_CACHE_PATH = settings.PERSIST_DIR / "embeddings_cache.json"
_cache: Optional[dict] = None


# --------------------------------------------------------------------------- #
# Proveedor activo
# --------------------------------------------------------------------------- #
def _proveedor() -> Optional[tuple]:
    """Devuelve (nombre, modelo) del proveedor de embeddings disponible."""
    if not settings.USAR_EMBEDDINGS:
        return None
    try:
        from core.llm_extractor import ollama_disponible
        if settings.USAR_OLLAMA and ollama_disponible():
            return ("ollama", settings.OLLAMA_EMBED_MODEL)
    except Exception:
        pass
    if settings.GEMINI_API_KEY:
        return ("gemini", settings.GEMINI_EMBED_MODEL)
    if settings.OPENAI_API_KEY:
        return ("openai", settings.OPENAI_EMBED_MODEL)
    return None


def disponible() -> bool:
    return _proveedor() is not None


# --------------------------------------------------------------------------- #
# Cache en disco
# --------------------------------------------------------------------------- #
def _cargar_cache() -> dict:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_CACHE_PATH.read_text(encoding="utf-8")) \
                if _CACHE_PATH.exists() else {}
        except Exception:
            _cache = {}
    return _cache


def _guardar_cache() -> None:
    try:
        _CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass


def _clave(prov: str, modelo: str, texto: str) -> str:
    h = hashlib.sha1(texto.strip().lower().encode("utf-8")).hexdigest()
    return f"{prov}:{modelo}:{h}"


# --------------------------------------------------------------------------- #
# Llamadas por proveedor (devuelven lista de vectores o None)
# --------------------------------------------------------------------------- #
def _ollama_embed(textos: List[str], modelo: str) -> Optional[List[List[float]]]:
    import requests
    try:
        r = requests.post(f"{settings.OLLAMA_HOST}/api/embed",
                          json={"model": modelo, "input": textos},
                          timeout=settings.OLLAMA_TIMEOUT)
        r.raise_for_status()
        return r.json().get("embeddings")
    except Exception:
        logger.exception("Error en embeddings Ollama")
        return None


def _gemini_embed(textos: List[str], modelo: str) -> Optional[List[List[float]]]:
    import requests
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{modelo}:batchEmbedContents")
    reqs = [{"model": f"models/{modelo}",
             "content": {"parts": [{"text": t}]}} for t in textos]
    try:
        r = requests.post(url, params={"key": settings.GEMINI_API_KEY},
                          json={"requests": reqs}, timeout=settings.GEMINI_TIMEOUT)
        r.raise_for_status()
        return [e["values"] for e in r.json().get("embeddings", [])]
    except Exception:
        logger.exception("Error en embeddings Gemini")
        return None


def _openai_embed(textos: List[str], modelo: str) -> Optional[List[List[float]]]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.embeddings.create(model=modelo, input=textos)
        return [d.embedding for d in resp.data]
    except Exception:
        logger.exception("Error en embeddings OpenAI")
        return None


_LOTE = 64  # textos por llamada (Gemini/Ollama aceptan lotes)


def embed(textos: List[str]) -> Optional[List[List[float]]]:
    """Vectoriza una lista de textos. Usa cache; solo pide los nuevos al
    proveedor en lotes. Devuelve None si no hay proveedor o falla todo."""
    prov = _proveedor()
    if not prov or not textos:
        return None
    nombre, modelo = prov
    cache = _cargar_cache()
    resultado: List[Optional[List[float]]] = [None] * len(textos)
    faltan_idx, faltan_txt = [], []
    for i, t in enumerate(textos):
        v = cache.get(_clave(nombre, modelo, t))
        if v is not None:
            resultado[i] = v
        else:
            faltan_idx.append(i)
            faltan_txt.append(t)

    fn = {"ollama": _ollama_embed, "gemini": _gemini_embed,
          "openai": _openai_embed}[nombre]
    hubo_nuevos = False
    for arranque in range(0, len(faltan_txt), _LOTE):
        sub = faltan_txt[arranque:arranque + _LOTE]
        vects = fn(sub, modelo)
        if not vects or len(vects) != len(sub):
            return None  # fallo del proveedor: el llamador usara TF-IDF
        for j, v in enumerate(vects):
            idx = faltan_idx[arranque + j]
            resultado[idx] = v
            cache[_clave(nombre, modelo, faltan_txt[arranque + j])] = v
            hubo_nuevos = True
    if hubo_nuevos:
        _guardar_cache()
    if any(v is None for v in resultado):
        return None
    return resultado  # type: ignore[return-value]


def embed_uno(texto: str) -> Optional[List[float]]:
    vs = embed([texto])
    return vs[0] if vs else None


# --------------------------------------------------------------------------- #
# Similitud
# --------------------------------------------------------------------------- #
def coseno(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return num / (na * nb) if na and nb else 0.0
