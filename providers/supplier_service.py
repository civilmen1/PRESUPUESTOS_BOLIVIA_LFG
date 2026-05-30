"""Servicio de gestión de proveedores (capa de orquestación)."""
from __future__ import annotations

from typing import List, Optional

from config.logging_config import get_logger
from models.supplier import Proveedor
from providers import supplier_repository
from providers.supplier_classifier import clasificar

logger = get_logger(__name__)


def alta_manual(proveedor: Proveedor) -> int:
    if not proveedor.categoria or proveedor.categoria == "otros":
        proveedor.categoria = clasificar(
            f"{proveedor.nombre} {proveedor.materiales_servicios}"
        )
    proveedor.fuente_alta = "manual"
    pid = supplier_repository.crear_proveedor(proveedor)
    logger.info("Proveedor manual creado id=%s (%s)", pid, proveedor.nombre)
    return pid


def alta_automatica(nombre: str, email: str = "", sitio_web: str = "",
                    materiales: str = "", region: str = "",
                    fuente: str = "web") -> int:
    """Alta de proveedor desde scraping web o respuesta de email."""
    categoria = clasificar(f"{nombre} {materiales}")
    p = Proveedor(nombre=nombre, email=email, sitio_web=sitio_web,
                  materiales_servicios=materiales, region=region,
                  categoria=categoria, estado="pendiente", fuente_alta=fuente)
    pid = supplier_repository.crear_proveedor(p)
    logger.info("Proveedor automático (%s) creado id=%s (%s)", fuente, pid, nombre)
    return pid


def verificar(proveedor_id: int) -> None:
    p = supplier_repository.obtener_proveedor(proveedor_id)
    if p:
        p.verificado = True
        p.estado = "activo"
        supplier_repository.actualizar_proveedor(p)


def desactivar(proveedor_id: int) -> None:
    p = supplier_repository.obtener_proveedor(proveedor_id)
    if p:
        p.estado = "inactivo"
        supplier_repository.actualizar_proveedor(p)


def candidatos_para_cotizar(categoria: str,
                            region: Optional[str] = None) -> List[Proveedor]:
    return supplier_repository.buscar_proveedores_por_categoria(categoria, region)
