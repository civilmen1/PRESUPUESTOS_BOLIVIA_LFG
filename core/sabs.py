"""Estructura de costos boliviana NB-SABS (DS 0181) — Formulario B-2.

Calcula el desglose oficial de un APU a partir de sus recursos:

  1. MATERIALES                          = Σ subtotales de materiales
  2. MANO DE OBRA
       - subtotal mano de obra           = Σ subtotales de mano de obra
       - beneficios sociales             = % · subtotal MO
       - IVA sobre mano de obra          = % · (subtotal MO + beneficios)
       - total mano de obra
  3. EQUIPO, MAQUINARIA Y HERRAMIENTAS
       - subtotal equipo                 = Σ subtotales de equipo
       - herramientas menores            = % · total mano de obra
       - total equipo
  4. COSTO DIRECTO                        = 1 + 2 + 3
  5. GASTOS GENERALES                     = % · costo directo
  6. UTILIDAD                             = % · (costo directo + gastos generales)
  7. IMPUESTOS (IT)                       = % · (costo directo + GG + utilidad)
  8. PRECIO UNITARIO TOTAL                = 4 + 5 + 6 + 7

Todos los porcentajes provienen del proyecto (configurables en la UI).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from models.apu_resource import (TIPO_EQUIPO, TIPO_MANO_OBRA, TIPO_MATERIAL,
                                  RecursoAPU)
from models.project import Proyecto


@dataclass
class DesgloseSABS:
    materiales: float = 0.0
    mano_obra_neta: float = 0.0
    beneficios_sociales: float = 0.0
    iva_mano_obra: float = 0.0
    mano_obra_total: float = 0.0
    equipo_neto: float = 0.0
    herramientas: float = 0.0
    iva_equipo: float = 0.0
    equipo_total: float = 0.0
    costo_directo: float = 0.0
    gastos_generales: float = 0.0
    utilidad: float = 0.0
    impuestos_it: float = 0.0
    precio_unitario_total: float = 0.0


def calcular_desglose(recursos: List[RecursoAPU], proyecto: Proyecto) -> DesgloseSABS:
    """Devuelve el desglose B-2 completo según la estructura NB-SABS."""
    materiales = sum(r.subtotal for r in recursos if r.tipo == TIPO_MATERIAL)
    mo_neta = sum(r.subtotal for r in recursos if r.tipo == TIPO_MANO_OBRA)
    eq_neto = sum(r.subtotal for r in recursos if r.tipo == TIPO_EQUIPO)

    # 2) Mano de obra: beneficios sociales + IVA
    beneficios = mo_neta * proyecto.factor_beneficios_sociales
    iva_mo = (mo_neta + beneficios) * proyecto.factor_iva_mano_obra
    mo_total = mo_neta + beneficios + iva_mo

    # 3) Equipo: herramientas menores (% sobre mano de obra total) + IVA equipo
    herramientas = mo_total * proyecto.factor_herramientas
    iva_eq = eq_neto * proyecto.factor_iva_equipo
    eq_total = eq_neto + herramientas + iva_eq

    # 4) Costo directo
    costo_directo = materiales + mo_total + eq_total

    # 5-7) Gastos generales, utilidad, IT (en cascada)
    gastos_generales = costo_directo * proyecto.factor_gastos_generales
    utilidad = (costo_directo + gastos_generales) * proyecto.factor_utilidad_sabs
    base_it = costo_directo + gastos_generales + utilidad
    it = base_it * proyecto.factor_it

    total = base_it + it

    return DesgloseSABS(
        materiales=round(materiales, 2),
        mano_obra_neta=round(mo_neta, 2),
        beneficios_sociales=round(beneficios, 2),
        iva_mano_obra=round(iva_mo, 2),
        mano_obra_total=round(mo_total, 2),
        equipo_neto=round(eq_neto, 2),
        herramientas=round(herramientas, 2),
        iva_equipo=round(iva_eq, 2),
        equipo_total=round(eq_total, 2),
        costo_directo=round(costo_directo, 2),
        gastos_generales=round(gastos_generales, 2),
        utilidad=round(utilidad, 2),
        impuestos_it=round(it, 2),
        precio_unitario_total=round(total, 2),
    )
