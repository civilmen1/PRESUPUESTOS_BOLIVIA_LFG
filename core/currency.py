"""Manejo de monedas: Bolivianos (BOB) y Dólares (USD).

Tipo de cambio referencial: 6.96 Bs por 1 USD (configurable por proyecto).
Todos los cálculos internos del APU se realizan en BOB; estas utilidades
convierten y formatean a la moneda del proyecto cuando se muestra o exporta.
"""
from __future__ import annotations

from config import settings

BOB = "BOB"
USD = "USD"
MONEDAS = [BOB, USD]

SIMBOLO = {BOB: "Bs", USD: "$us"}


def tipo_cambio(proyecto=None) -> float:
    """BOB por 1 USD. Toma el del proyecto si existe, si no el global."""
    if proyecto is not None and getattr(proyecto, "tipo_cambio", 0):
        return float(proyecto.tipo_cambio)
    return settings.TIPO_CAMBIO_USD


def convertir(monto_bob: float, moneda_destino: str, tc: float | None = None) -> float:
    """Convierte un monto en BOB a la moneda destino (BOB o USD)."""
    if moneda_destino == USD:
        tc = tc or settings.TIPO_CAMBIO_USD
        return round(monto_bob / tc, 2) if tc else 0.0
    return round(monto_bob, 2)


def a_bob(monto: float, moneda_origen: str, tc: float | None = None) -> float:
    """Convierte un monto de su moneda de origen a BOB (base de cálculo)."""
    if moneda_origen == USD:
        tc = tc or settings.TIPO_CAMBIO_USD
        return round(monto * tc, 2)
    return round(monto, 2)


def formatear(monto_bob: float, moneda: str, tc: float | None = None,
              con_simbolo: bool = True) -> str:
    """Formatea un monto (dado en BOB) en la moneda indicada."""
    valor = convertir(monto_bob, moneda, tc)
    texto = f"{valor:,.2f}"
    return f"{SIMBOLO.get(moneda, '')} {texto}".strip() if con_simbolo else texto


def simbolo(moneda: str) -> str:
    return SIMBOLO.get(moneda, moneda)
