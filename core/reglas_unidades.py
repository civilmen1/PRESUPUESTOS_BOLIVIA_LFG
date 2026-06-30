"""Reglas deterministas de normalización de unidades de los recursos.

Garantizan convenciones del APU sin depender de lo que devuelva la IA. La regla
principal: el CEMENTO siempre se expresa en kg (no en bolsa). Se aplica sobre
los recursos ya armados, antes de persistir y cotizar.

IMPORTANTE: se conserva el costo. Al pasar de bolsa a kg se multiplica la
cantidad por el factor (1 bolsa = N kg) y se divide el precio por el mismo
factor, de modo que el subtotal (cantidad × precio) no cambia.
"""
from __future__ import annotations

from typing import Iterable, List

from config import settings
from core.text_cleaner import normalizar
from core.unit_converter import canonica
from models.apu_resource import TIPO_MATERIAL

_CEMENTO_CLAVES = ("cemento", "portland")


def es_cemento(descripcion: str) -> bool:
    """True si la descripción corresponde a cemento (cemento / Portland)."""
    n = normalizar(descripcion or "")
    return any(clave in n for clave in _CEMENTO_CLAVES)


def forzar_cemento_kg(recursos: Iterable) -> List:
    """Convierte el cemento que esté en 'bolsa' a 'kg' conservando el costo.

    - Solo afecta MATERIALES cuya descripción sea cemento y cuya unidad sea bolsa.
    - cantidad ×N, precio ÷N, unidad='kg' (N = settings.KG_POR_BOLSA_CEMENTO).
    - Es idempotente: si ya está en kg, no hace nada.
    - Si la regla está desactivada (FORZAR_CEMENTO_KG=false), no toca nada.
    """
    recursos = list(recursos)
    if not settings.FORZAR_CEMENTO_KG:
        return recursos
    factor = settings.KG_POR_BOLSA_CEMENTO or 50.0
    for r in recursos:
        try:
            if getattr(r, "tipo", "") != TIPO_MATERIAL:
                continue
            if not es_cemento(getattr(r, "descripcion", "")):
                continue
            if canonica(getattr(r, "unidad", "") or "") != "bolsa":
                continue
            r.cantidad_apu = float(getattr(r, "cantidad_apu", 0) or 0) * factor
            r.rendimiento = float(getattr(r, "rendimiento", 0) or 0) * factor
            pu = float(getattr(r, "precio_unitario", 0) or 0)
            if pu:
                r.precio_unitario = pu / factor
            r.unidad = "kg"
            if hasattr(r, "calcular_subtotal"):
                r.calcular_subtotal()
        except Exception:
            # Una conversión que falle no debe frenar el armado del APU.
            continue
    return recursos
