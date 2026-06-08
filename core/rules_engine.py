"""Reglas de negocio: precio adoptado y vigencia.

Implementa las reglas configurables del prompt:
- 1 fuente: usar precio único con advertencia.
- 2-3 fuentes: usar mediana.
- 4+ fuentes: mediana depurada (descarta outliers por IQR).
- precio manual validado: prioridad máxima.
- precio por email confirmado: prioridad sobre scraping web.
- precio > vigencia_dias: alerta de vigencia.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from config import settings


@dataclass
class FuentePrecio:
    """Una observación de precio proveniente de cualquier nivel."""
    precio: float
    nivel: int           # 0 manual, 1 BD, 2 web, 3 email
    fecha: Optional[str] = None
    fuente: str = ""
    proveedor_id: Optional[int] = None
    validado: bool = False
    url: str = ""


@dataclass
class PrecioAdoptado:
    precio: float
    regla: str
    nivel: int
    fuente: str
    n_fuentes: int
    alertas: List[str]
    proveedor_id: Optional[int] = None
    url: str = ""


def _dias_desde(fecha: Optional[str]) -> Optional[int]:
    if not fecha:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            d = datetime.strptime(fecha[: len(fmt) + 2].strip(), fmt)
            return (datetime.now() - d).days
        except ValueError:
            continue
    return None


def _mediana_depurada(valores: List[float]) -> float:
    """Mediana descartando outliers por rango intercuartílico (IQR)."""
    if len(valores) < 4:
        return statistics.median(valores)
    ordenados = sorted(valores)
    q1 = statistics.quantiles(ordenados, n=4)[0]
    q3 = statistics.quantiles(ordenados, n=4)[2]
    iqr = q3 - q1
    bajo, alto = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    filtrados = [v for v in ordenados if bajo <= v <= alto] or ordenados
    return statistics.median(filtrados)


def calcular_precio_adoptado(
    fuentes: List[FuentePrecio], vigencia_dias: int = settings.VIGENCIA_DIAS_DEFAULT
) -> PrecioAdoptado:
    """Aplica la jerarquía de reglas y devuelve el precio adoptado con alertas."""
    alertas: List[str] = []
    fuentes = [f for f in fuentes if f.precio and f.precio > 0]

    if not fuentes:
        return PrecioAdoptado(0.0, "sin_precio", -1, "ninguna", 0,
                              ["Sin precio disponible en ningún nivel"])

    # 1) Precio manual validado tiene prioridad máxima
    manuales = [f for f in fuentes if f.nivel == 0 and f.validado]
    if manuales:
        f = manuales[0]
        return PrecioAdoptado(f.precio, "manual_validado", 0, "manual", 1,
                              alertas, f.proveedor_id, f.url)

    # 2) Email confirmado tiene prioridad sobre web
    emails = [f for f in fuentes if f.nivel == 3]
    if emails and not [f for f in fuentes if f.nivel in (0, 1)]:
        valores = [f.precio for f in emails]
        precio = statistics.median(valores)
        if len(emails) == 1:
            alertas.append("Precio basado en una sola cotización por email")
        return PrecioAdoptado(round(precio, 2), "email_confirmado", 3, "email",
                              len(emails), alertas, emails[0].proveedor_id, emails[0].url)

    # 3) Reglas por cantidad de fuentes (BD/web)
    valores = [f.precio for f in fuentes]
    n = len(valores)
    if n == 1:
        f = fuentes[0]
        alertas.append("Precio basado en una única fuente (verificar)")
        regla = "fuente_unica"
        precio = valores[0]
    elif n <= 3:
        regla = "mediana"
        precio = statistics.median(valores)
    else:
        regla = "mediana_depurada"
        precio = _mediana_depurada(valores)

    # Alerta de vigencia (usa la fuente más antigua adoptada)
    for f in fuentes:
        dias = _dias_desde(f.fecha)
        if dias is not None and dias > vigencia_dias:
            alertas.append(f"Fuente con {dias} días de antigüedad (> {vigencia_dias})")
            break

    nivel_repr = min(f.nivel for f in fuentes)
    fuente_repr = next((f for f in fuentes if f.nivel == nivel_repr), fuentes[0])
    return PrecioAdoptado(round(precio, 2), regla, nivel_repr, fuente_repr.fuente,
                          n, alertas, fuente_repr.proveedor_id, fuente_repr.url)
