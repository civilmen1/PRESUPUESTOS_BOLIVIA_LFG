"""Scraping web seguro y parametrizable (soporte para Nivel 2).

En modo SCRAPER_DRY_RUN (por defecto) NO sale a internet: devuelve resultados
simulados deterministas para permitir ejecutar el sistema localmente sin red.
Desactivando el dry-run y proveyendo `fuentes`, hace requests reales y parsea
precios con heurísticas simples (sustituibles por parsers por sitio).
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import List, Optional

from config import settings
from config.logging_config import get_logger

logger = get_logger(__name__)

_PRECIO_RE = re.compile(r"(?:bs\.?|bob|\$us|\$)\s*([\d\.,]+)", re.IGNORECASE)


@dataclass
class ResultadoWeb:
    descripcion: str
    precio: float
    unidad: str
    moneda: str
    proveedor: str
    url: str
    region: str = ""


def _simular(descripcion: str, unidad: str, categoria: str) -> List[ResultadoWeb]:
    """Genera 1-3 resultados simulados deterministas según la descripción."""
    rnd = random.Random(hash(descripcion) & 0xFFFFFFFF)
    base = 50 + (abs(hash(categoria or descripcion)) % 400)
    n = rnd.randint(1, 3)
    out = []
    for i in range(n):
        precio = round(base * (0.9 + 0.2 * rnd.random()), 2)
        out.append(ResultadoWeb(
            descripcion=descripcion,
            precio=precio,
            unidad=unidad or "glb",
            moneda="BOB",
            proveedor=f"Proveedor web simulado {i + 1}",
            url=f"https://example.bo/producto/{abs(hash(descripcion)) % 10000}",
            region="Santa Cruz",
        ))
    logger.info("[DRY-RUN] %d resultados simulados para '%s'", len(out), descripcion)
    return out


def _parse_precio(texto: str) -> Optional[float]:
    m = _PRECIO_RE.search(texto or "")
    if not m:
        return None
    valor = m.group(1).replace(".", "").replace(",", ".") if "," in m.group(1) else m.group(1).replace(",", "")
    try:
        return float(valor)
    except ValueError:
        return None


def buscar_en_web(descripcion: str, unidad: str = "", categoria: str = "",
                  fuentes: Optional[List[str]] = None) -> List[ResultadoWeb]:
    """Busca precios en la web. Respeta SCRAPER_DRY_RUN."""
    if settings.SCRAPER_DRY_RUN or not fuentes:
        return _simular(descripcion, unidad, categoria)

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        logger.warning("requests/bs4 no instalados; usando simulación")
        return _simular(descripcion, unidad, categoria)

    resultados: List[ResultadoWeb] = []
    headers = {"User-Agent": settings.SCRAPER_USER_AGENT}
    for url in fuentes:
        try:
            resp = requests.get(url, headers=headers, timeout=settings.SCRAPER_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            precio = _parse_precio(soup.get_text(" ", strip=True))
            if precio:
                resultados.append(ResultadoWeb(
                    descripcion=descripcion, precio=precio, unidad=unidad or "glb",
                    moneda="BOB", proveedor=url.split("/")[2], url=url))
        except Exception:
            logger.exception("Error haciendo scraping de %s", url)
    return resultados or _simular(descripcion, unidad, categoria)
