"""Conversión y homologación de unidades para cotizaciones.

Permite homologar la unidad de un precio encontrado (web/BD) con la unidad
del recurso del APU. Devuelve un factor de conversión multiplicativo.
"""
from __future__ import annotations

from core.text_cleaner import normalizar

# Alias de unidades -> unidad canónica
_ALIAS = {
    "m3": ["m3", "m³", "metro cubico", "metros cubicos", "mc"],
    "m2": ["m2", "m²", "metro cuadrado", "metros cuadrados"],
    "ml": ["ml", "m", "metro", "metros", "metro lineal", "mts"],
    "kg": ["kg", "kilo", "kilos", "kilogramo", "kilogramos"],
    "ton": ["ton", "tonelada", "toneladas", "tn", "t"],
    "bolsa": ["bolsa", "bolsas", "saco", "sacos", "bls"],
    "pieza": ["pieza", "piezas", "pza", "unidad", "und", "u", "c/u", "cu"],
    "lt": ["lt", "l", "litro", "litros"],
    "gal": ["gal", "galon", "galones"],
    "hora": ["hora", "horas", "hr", "hrs", "hra", "hras", "h", "hm"],
    "jornal": ["jornal", "jornales", "dia", "día", "dias"],
    "glb": ["glb", "global", "gbl"],
    "p2": ["p2", "pie2", "pie cuadrado", "pies cuadrados"],
}

# Factores de conversión entre unidades de la misma magnitud
# factor: cuántas unidades destino hay en 1 unidad origen
_CONVERSIONES = {
    ("ton", "kg"): 1000.0,
    ("kg", "ton"): 0.001,
    ("gal", "lt"): 3.785,
    ("lt", "gal"): 1 / 3.785,
    # 1 jornal laboral = 8 horas (mano de obra y equipo se manejan en horas).
    ("jornal", "hora"): 8.0,
    ("hora", "jornal"): 1 / 8.0,
}


def canonica(unidad: str) -> str:
    """Devuelve la unidad canónica de un texto de unidad."""
    n = normalizar(unidad).strip().strip(".").strip()
    for canon, alias in _ALIAS.items():
        if n in alias or n == canon:
            return canon
    return n or "glb"


def factor_conversion(unidad_origen: str, unidad_destino: str) -> float | None:
    """Factor para pasar de unidad_origen a unidad_destino.

    Devuelve None si las unidades no son homologables (inconsistencia).
    """
    o = canonica(unidad_origen)
    d = canonica(unidad_destino)
    if o == d:
        return 1.0
    if (o, d) in _CONVERSIONES:
        return _CONVERSIONES[(o, d)]
    return None


def homologar_precio(
    precio: float, unidad_origen: str, unidad_destino: str
) -> tuple[float | None, float | None]:
    """Convierte un precio de unidad_origen a unidad_destino.

    Retorna (precio_convertido, factor). Si no es homologable, (None, None).
    El precio se divide por el factor: si 1 ton = 1000 kg, precio/ton -> precio/kg.
    """
    factor = factor_conversion(unidad_origen, unidad_destino)
    if factor is None:
        return None, None
    return round(precio / factor, 4), factor
