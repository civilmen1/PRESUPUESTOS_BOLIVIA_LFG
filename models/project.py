"""Modelos de Proyecto y Módulo."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from config import settings


@dataclass
class Proyecto:
    id: Optional[int] = None
    nombre: str = ""
    region: str = ""
    moneda: str = settings.MONEDA_DEFAULT
    factor_indirectos: float = settings.FACTOR_INDIRECTOS_DEFAULT
    factor_utilidad: float = settings.FACTOR_UTILIDAD_DEFAULT
    factor_impuestos: float = settings.FACTOR_IMPUESTOS_DEFAULT
    fecha_creacion: Optional[str] = None
    estado: str = "activo"


@dataclass
class Modulo:
    id: Optional[int] = None
    proyecto_id: Optional[int] = None
    nombre: str = ""
    orden: int = 0
    items: list = field(default_factory=list)
