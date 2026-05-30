"""Modelo de Resultado de un APU (costos consolidados por ítem)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ResultadoAPU:
    id: Optional[int] = None
    item_id: Optional[int] = None
    costo_materiales: float = 0.0
    costo_mano_obra: float = 0.0
    costo_equipos: float = 0.0
    costo_directo: float = 0.0
    indirectos: float = 0.0
    utilidad: float = 0.0
    impuestos: float = 0.0
    precio_unitario_total: float = 0.0
    alertas: List[str] = field(default_factory=list)
    fecha_generacion: Optional[str] = None
