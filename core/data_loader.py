"""Carga de archivos de datos base (rendimientos, salarios, equipos, categorías)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from config import settings
from core.text_cleaner import normalizar


def _load(path: Path) -> dict:
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def rendimientos() -> dict:
    return _load(settings.RENDIMIENTOS_JSON)


@lru_cache(maxsize=1)
def salarios() -> dict:
    return _load(settings.SALARIOS_JSON)


@lru_cache(maxsize=1)
def equipos() -> dict:
    return _load(settings.EQUIPOS_JSON)


@lru_cache(maxsize=1)
def categorias_materiales() -> dict:
    return _load(settings.CATEGORIAS_JSON)


def precio_local_recurso(categoria: str, descripcion: str) -> dict | None:
    """Busca un precio local para mano de obra o equipos en los JSON base.

    Devuelve {precio, unidad, descripcion, fuente} o None.
    """
    cat = normalizar(categoria)
    desc = normalizar(descripcion)

    for tabla, fuente in ((salarios(), "salarios_json"), (equipos(), "equipos_json")):
        for clave, val in tabla.items():
            if clave.startswith("_") or not isinstance(val, dict):
                continue
            if normalizar(clave) == cat or normalizar(clave) in desc or \
               normalizar(val.get("descripcion", "")) in desc or \
               desc in normalizar(val.get("descripcion", "")):
                descripcion = val.get("descripcion", clave)
                precio = float(val.get("precio", 0))
                unidad = val.get("unidad", "")
                # Mano de obra: aplicar reglas (sin 'peón', Bs/hora, 20-50).
                if fuente == "salarios_json":
                    from core import mano_obra
                    descripcion = mano_obra.limpiar_descripcion(descripcion)
                    precio = mano_obra.precio_valido(descripcion, precio)
                return {
                    "precio": precio,
                    "unidad": unidad,
                    "descripcion": descripcion,
                    "fuente": fuente,
                }
    return None
