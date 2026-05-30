"""Modelo de Ítem de la tabla de cantidades."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    id: Optional[int] = None
    modulo_id: Optional[int] = None
    proyecto_id: Optional[int] = None
    numero: str = ""
    codigo: str = ""
    descripcion: str = ""
    unidad: str = ""
    cantidad: float = 0.0
    observaciones: str = ""
    estado: str = "pendiente"
    palabras_clave: str = ""

    @property
    def keywords(self) -> list[str]:
        return [k.strip() for k in (self.palabras_clave or "").split(",") if k.strip()]
