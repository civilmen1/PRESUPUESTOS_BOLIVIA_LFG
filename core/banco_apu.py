"""Banco de APU de referencia (rendimientos y precios reales de Bolivia).

Carga data/banco_apu.json (importado de formularios B-2 oficiales) y lo expone
para:
  - buscar un APU de referencia por similitud con la descripcion de un item,
  - alimentar precios elementales reales (Nivel 1 del cotizador),
  - dar contexto/ejemplos a la IA.
"""
from __future__ import annotations

from functools import lru_cache

from config import settings
from core.text_cleaner import normalizar, tokenizar

_RUTA = settings.DATA_DIR / "banco_apu.json"


@lru_cache(maxsize=1)
def _cargar() -> dict:
    import json
    try:
        if _RUTA.exists():
            return json.loads(_RUTA.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"apus": []}


def hay_banco() -> bool:
    return bool(_cargar().get("apus"))


def listar_apus() -> list[dict]:
    return _cargar().get("apus", [])


def _limpiar_desc(actividad: str) -> str:
    """Quita la numeracion inicial '3.- ' de la actividad."""
    txt = actividad.split("-", 1)[-1] if "-" in actividad[:6] else actividad
    return txt.strip()


def buscar_apu(descripcion: str, umbral: float = 0.3) -> dict | None:
    """Devuelve el APU del banco mas parecido a la descripcion (o None)."""
    apus = listar_apus()
    if not apus:
        return None
    q = set(tokenizar(descripcion))
    if not q:
        return None
    mejor, mejor_score = None, umbral
    for a in apus:
        toks = set(tokenizar(_limpiar_desc(a.get("actividad", ""))))
        if not toks:
            continue
        # similitud de Jaccard
        inter = len(q & toks)
        union = len(q | toks) or 1
        score = inter / union
        if score > mejor_score:
            mejor, mejor_score = a, score
    return mejor


def precios_elementales() -> dict:
    """Diccionario {descripcion_normalizada: {precio, unidad, descripcion}} con
    todos los insumos del banco (para usar como precios de referencia)."""
    out: dict[str, dict] = {}
    for a in listar_apus():
        for grupo in ("materiales", "mano_obra", "equipo"):
            for r in a.get(grupo, []):
                desc = r.get("descripcion", "").strip()
                if not desc or not r.get("precio"):
                    continue
                clave = normalizar(desc)
                # conservar el de mayor precio si se repite (mas conservador)
                if clave not in out or r["precio"] > out[clave]["precio"]:
                    out[clave] = {"precio": float(r["precio"]),
                                  "unidad": r.get("unidad", ""),
                                  "descripcion": desc}
    return out


def buscar_precio(descripcion: str) -> dict | None:
    """Busca el precio de un insumo en el banco por coincidencia de palabras."""
    elem = precios_elementales()
    desc_norm = normalizar(descripcion)
    # coincidencia exacta
    if desc_norm in elem:
        return elem[desc_norm]
    # coincidencia por palabras clave
    palabras = [w for w in desc_norm.split() if len(w) >= 4]
    if not palabras:
        return None
    mejor, mejor_score = None, 0
    for clave, info in elem.items():
        score = sum(1 for w in palabras if w in clave)
        if score > mejor_score:
            mejor, mejor_score = info, score
    return mejor if mejor_score >= 1 else None
