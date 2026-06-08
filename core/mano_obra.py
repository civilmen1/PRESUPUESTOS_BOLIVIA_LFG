"""Reglas de MANO DE OBRA para presupuestos en Bolivia.

Principios (no negociables en el banco APU):
  * La mano de obra se expresa SIEMPRE en horas (Bs/hora). Nunca en "jornal".
  * No se usa el término "peón": se reemplaza por "ayudante".
  * El costo horario válido está acotado al rango 20–50 Bs/hora.

Salarios horarios de referencia (Bs/hora):
  * Ayudante (incluye ayudante de máquina y de topografía): 20
  * Albañil: 25   |   Maestro / albañil especializado: 30
  * Especialistas (soldador, cerrajero, carpintero, vidriero, plomero,
    acabados en seco, instalaciones, electricista): 35
Cualquier otro oficio (operadores, choferes, topógrafo) conserva su valor
pero se recorta al rango 20–50.
"""
from __future__ import annotations

import re

# Rango permitido de costo horario de mano de obra (Bs/hora).
MIN_BS_HORA = 20.0
MAX_BS_HORA = 50.0

# "peón" / "peones" -> "ayudante" / "ayudantes" (respetando mayúsculas).
_PEON_RE = re.compile(r"\bpe[oó]n(es)?\b", re.IGNORECASE)

# Precio horario fijo por categoría de oficio (Bs/hora).
_PRECIO_OFICIO = {
    "ayudante": 20.0,
    "albañil": 25.0,
    "maestro": 30.0,
    "especialista": 35.0,
}


def limpiar_descripcion(desc: str) -> str:
    """Reemplaza el término prohibido 'peón' por 'ayudante'."""
    if not desc:
        return desc

    def _rep(m: "re.Match") -> str:
        original = m.group(0)
        base = "ayudantes" if m.group(1) else "ayudante"
        if original.isupper():
            return base.upper()
        if original[:1].isupper():
            return base.capitalize()
        return base

    return _PEON_RE.sub(_rep, desc)


def _categoria_oficio(desc: str) -> str:
    d = (desc or "").lower()
    if any(k in d for k in ("ayudante", "peon", "peón", "alarife")):
        return "ayudante"
    if "maestro" in d:
        return "maestro"
    if "albañil" in d or "albanil" in d:
        return "albañil"
    if any(k in d for k in ("soldador", "cerrajero", "carpinter", "vidrier",
                            "plomer", "gasfiter", "acabado", "drywall", "yeso",
                            "instalacion", "instalación", "electric")):
        return "especialista"
    return "otros"


def precio_valido(desc: str, precio) -> float:
    """Costo horario (Bs/hora) que cumple las reglas de oficio y el rango."""
    cat = _categoria_oficio(desc)
    if cat in _PRECIO_OFICIO:
        return _PRECIO_OFICIO[cat]
    # 'otros' (operadores, choferes, topógrafo...): respetar pero acotar al rango.
    try:
        p = float(precio)
    except (TypeError, ValueError):
        p = MIN_BS_HORA
    if p <= 0:
        p = MIN_BS_HORA
    return round(min(MAX_BS_HORA, max(MIN_BS_HORA, p)), 2)


def normalizar(descripcion: str, precio=None, unidad: str = "HR") -> tuple:
    """Devuelve (descripcion_limpia, precio_valido, 'HR'). Unidad SIEMPRE horas."""
    desc = limpiar_descripcion(descripcion or "")
    return desc, precio_valido(desc, precio), "HR"
