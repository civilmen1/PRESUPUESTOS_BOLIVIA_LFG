"""Modelos de fuente técnica, sección y vínculo técnico."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FuenteTecnica:
    id: Optional[int] = None
    proyecto_id: Optional[int] = None
    tipo_documento: str = ""  # DBC, especificacion, TDR, pliego, anexo, memoria
    nombre_archivo: str = ""
    ruta: str = ""
    texto_extraido: str = ""
    fecha_carga: Optional[str] = None


@dataclass
class SeccionTecnica:
    id: Optional[int] = None
    fuente_id: Optional[int] = None
    titulo: str = ""
    contenido: str = ""
    pagina_inicio: Optional[int] = None
    pagina_fin: Optional[int] = None
    keywords: str = ""


@dataclass
class VinculoTecnico:
    id: Optional[int] = None
    item_id: Optional[int] = None
    seccion_id: Optional[int] = None
    score_confianza: float = 0.0
    validado_manual: bool = False
    observaciones: str = ""
    # campos auxiliares para la UI (no persistidos)
    titulo_seccion: str = field(default="", compare=False)
    extracto: str = field(default="", compare=False)
