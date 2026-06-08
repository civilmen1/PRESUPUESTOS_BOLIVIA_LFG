"""Modelo de Cotización (resultado del cotizador jerárquico)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Niveles del cotizador jerárquico
NIVEL_BD = 1
NIVEL_WEB = 2
NIVEL_EMAIL = 3
NIVEL_MANUAL = 0  # precio cargado manualmente por el ingeniero (prioridad máxima)


@dataclass
class Cotizacion:
    id: Optional[int] = None
    recurso_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    descripcion: str = ""
    nivel_busqueda: int = NIVEL_BD
    precio_bruto: float = 0.0
    unidad_origen: str = ""
    factor_conversion: float = 1.0
    precio_adoptado: float = 0.0
    moneda: str = "BOB"
    fecha_consulta: Optional[str] = None
    vigencia_dias: int = 30
    url_fuente: str = ""
    estado: str = "obtenida"  # obtenida | desactualizada | pendiente | sin_resultado
    nivel_confianza: float = 0.0
    observaciones: str = ""
