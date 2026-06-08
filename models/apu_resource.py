"""Modelo de Recurso de un APU (material, mano de obra o equipo)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

TIPO_MATERIAL = "material"
TIPO_MANO_OBRA = "mano_obra"
TIPO_EQUIPO = "equipo"

TIPOS_RECURSO = [TIPO_MATERIAL, TIPO_MANO_OBRA, TIPO_EQUIPO]


@dataclass
class RecursoAPU:
    id: Optional[int] = None
    item_id: Optional[int] = None
    tipo: str = TIPO_MATERIAL
    descripcion: str = ""
    unidad: str = ""
    rendimiento: float = 1.0
    cantidad_apu: float = 0.0
    precio_unitario: float = 0.0
    subtotal: float = 0.0
    fuente_precio: str = ""  # bd | web | email | manual | sin_precio
    cotizacion_id: Optional[int] = None
    bloqueado: bool = False

    def calcular_subtotal(self) -> float:
        self.subtotal = round(self.cantidad_apu * self.precio_unitario, 4)
        return self.subtotal
