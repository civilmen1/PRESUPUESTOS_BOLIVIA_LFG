"""Modelo de Proveedor (Bolivia)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Tipos de proveedor soportados (clasificación por rubro)
TIPOS_PROVEEDOR = [
    "ferreteria",
    "cemento",
    "acero",
    "aridos",
    "tuberias",
    "valvulas",
    "electricos",
    "acabados",
    "alquiler_maquinaria",
    "transporte",
    "mano_obra",
    "otros",
]


@dataclass
class Proveedor:
    id: Optional[int] = None
    nombre: str = ""
    razon_social: str = ""
    nit: str = ""
    email: str = ""
    telefono: str = ""
    whatsapp: str = ""
    region: str = ""
    ciudad: str = ""
    direccion: str = ""
    sitio_web: str = ""
    categoria: str = "otros"
    materiales_servicios: str = ""
    estado: str = "activo"
    verificado: bool = False
    fuente_alta: str = "manual"  # manual | web | email
    observaciones: str = ""
    fecha_creacion: Optional[str] = None
    ultima_actualizacion: Optional[str] = None
