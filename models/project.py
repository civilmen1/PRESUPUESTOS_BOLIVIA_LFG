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
    tipo_cambio: float = settings.TIPO_CAMBIO_USD   # BOB por 1 USD
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
    proponente: str = ""           # nombre de la empresa proponente
    representante_legal: str = ""  # nombre del rep. legal (pie de firma)
    ci_representante: str = ""     # cédula de identidad del rep. legal
    # Plazo y cronogramas (A-8, A-9, B-5)
    plazo_dias: int = 180          # plazo de ejecución de obra (calendario)
    # Anticipo (afecta el Formulario B-5 desembolsos)
    solicita_anticipo: bool = False
    porcentaje_anticipo: float = 0.0   # ej. 0.20 = 20%
    usuario_id: Optional[int] = None   # empresa/entidad dueña del proyecto
    fecha_creacion: Optional[str] = None
    estado: str = "activo"


@dataclass
class Modulo:
    id: Optional[int] = None
    proyecto_id: Optional[int] = None
    nombre: str = ""
    orden: int = 0
    items: list = field(default_factory=list)
