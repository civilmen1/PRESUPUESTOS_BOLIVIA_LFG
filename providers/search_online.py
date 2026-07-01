"""Orquestador de búsqueda online de precios (Nivel 2).

Llama al scraper, homologa unidades con la unidad del recurso y registra los
resultados como referencias provisionales en la BD interna.
"""
from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote_plus

from config import settings
from config.logging_config import get_logger
from core.unit_converter import homologar_precio
from providers import supplier_repository
from providers.web_scraper import buscar_en_web

logger = get_logger(__name__)


def _fuentes_para(descripcion: str) -> Optional[List[str]]:
    """URLs reales a consultar para una descripción, según SCRAPER_FUENTES.

    Sustituye {q} por el término de búsqueda. Devuelve None si no hay sitios
    configurados o si el scraper está en modo simulación (DRY-RUN), en cuyo caso
    el scraper devuelve datos simulados.
    """
    if settings.SCRAPER_DRY_RUN or not settings.SCRAPER_FUENTES:
        return None
    q = quote_plus(descripcion or "")
    return [u.replace("{q}", q) for u in settings.SCRAPER_FUENTES]


def buscar_precios_online(descripcion: str, unidad_destino: str, categoria: str = "",
                          region: str = "", persistir: bool = True) -> List[dict]:
    """Devuelve precios homologados a `unidad_destino` desde la web.

    Cada resultado: {precio, unidad_origen, factor, unidad, url, proveedor, ...}
    """
    crudos = buscar_en_web(descripcion, unidad=unidad_destino, categoria=categoria,
                           fuentes=_fuentes_para(descripcion))
    resultados: List[dict] = []
    for r in crudos:
        precio_homol, factor = homologar_precio(r.precio, r.unidad, unidad_destino)
        inconsistencia = precio_homol is None
        precio_final = precio_homol if precio_homol is not None else r.precio
        factor_final = factor if factor is not None else 1.0

        if persistir:
            try:
                supplier_repository.registrar_precio(
                    descripcion=descripcion, categoria=categoria,
                    unidad=unidad_destino, precio=precio_final, moneda=r.moneda,
                    region=r.region or region, url=r.url, fuente="web",
                )
            except Exception:
                logger.exception("No se pudo persistir precio web provisional")

        resultados.append({
            "precio": precio_final,
            "precio_bruto": r.precio,
            "unidad_origen": r.unidad,
            "factor": factor_final,
            "unidad": unidad_destino,
            "moneda": r.moneda,
            "proveedor": r.proveedor,
            "url": r.url,
            "region": r.region or region,
            "inconsistencia_unidad": inconsistencia,
        })
    logger.info("Búsqueda online '%s': %d resultados", descripcion, len(resultados))
    return resultados
