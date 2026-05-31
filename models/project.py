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
    # Estructura NB-SABS (DS 0181) — Formulario B-2
    factor_beneficios_sociales: float = settings.FACTOR_BENEFICIOS_SOCIALES
    factor_iva_mano_obra: float = settings.FACTOR_IVA_MANO_OBRA
    factor_herramientas: float = settings.FACTOR_HERRAMIENTAS
    factor_iva_equipo: float = settings.FACTOR_IVA_EQUIPO
    factor_gastos_generales: float = settings.FACTOR_GASTOS_GENERALES
    factor_utilidad_sabs: float = settings.FACTOR_UTILIDAD_SABS
    factor_it: float = settings.FACTOR_IT
    # Datos de cabecera para formularios oficiales
    entidad: str = ""
    proponente: str = ""
    fecha_creacion: Optional[str] = None
    estado: str = "activo"


@dataclass
class Modulo:
    id: Optional[int] = None
    proyecto_id: Optional[int] = None
    nombre: str = ""
    orden: int = 0
    items: list = field(default_factory=list)
