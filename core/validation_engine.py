"""Validaciones del sistema: columnas mínimas, unidades, respaldo técnico."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from core import repositories
from core.unit_converter import factor_conversion
from models.item import Item

COLUMNAS_MINIMAS = ["descripcion"]
COLUMNAS_RECOMENDADAS = ["unidad", "cantidad"]


@dataclass
class Validacion:
    ok: bool
    errores: List[str] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)


def validar_columnas(columnas_mapeadas: dict) -> Validacion:
    """Valida que existan las columnas mínimas tras el mapeo del parser."""
    errores, advertencias = [], []
    for c in COLUMNAS_MINIMAS:
        if c not in columnas_mapeadas:
            errores.append(f"Falta columna mínima: '{c}'")
    for c in COLUMNAS_RECOMENDADAS:
        if c not in columnas_mapeadas:
            advertencias.append(f"Falta columna recomendada: '{c}'")
    return Validacion(ok=not errores, errores=errores, advertencias=advertencias)


def validar_items(items: List[Item]) -> Validacion:
    """Valida una lista de ítems (datos faltantes)."""
    errores, advertencias = [], []
    for it in items:
        etiqueta = it.numero or it.descripcion[:30]
        if not it.descripcion:
            errores.append(f"Ítem {etiqueta}: sin descripción")
        if not it.unidad:
            advertencias.append(f"Ítem {etiqueta}: sin unidad")
        if it.cantidad <= 0:
            advertencias.append(f"Ítem {etiqueta}: cantidad <= 0")
    return Validacion(ok=not errores, errores=errores, advertencias=advertencias)


def validar_inconsistencias_unidad(item_id: int) -> List[str]:
    """Detecta recursos cuya unidad no es homologable con su cotización."""
    problemas = []
    for r in repositories.listar_recursos(item_id):
        if r.cotizacion_id:
            # si no se pudo homologar, factor_conversion devuelve None
            if r.unidad and factor_conversion(r.unidad, r.unidad) is None:
                problemas.append(
                    f"Recurso '{r.descripcion}': unidad '{r.unidad}' no reconocida")
    return problemas


def items_sin_respaldo_tecnico(proyecto_id: int) -> List[Item]:
    """Ítems sin ningún vínculo técnico validado o sugerido."""
    sin_respaldo = []
    for it in repositories.listar_items(proyecto_id):
        vinculos = repositories.listar_vinculos(it.id)
        if not vinculos:
            sin_respaldo.append(it)
    return sin_respaldo
