"""Segmentación de texto técnico en secciones (capítulos / numerales / páginas)."""
from __future__ import annotations

import re
from typing import List

from core.text_cleaner import extraer_keywords
from models.technical_source import SeccionTecnica

# Detecta encabezados de tipo numeral (1, 1.1, 2.3.4), ítem, capítulo, artículo
_HEADING = re.compile(
    r"^\s*("
    r"(?:cap[ií]tulo|secci[oó]n|art[ií]culo|[ií]tem|numeral|t[ií]tulo)\s+[\w\.\-]+"
    r"|\d+(?:\.\d+){0,3}\s*[\.\-)]?\s+[A-ZÁÉÍÓÚÑ]"
    r")",
    re.IGNORECASE,
)
_PAGINA = re.compile(r"\[\[PAGINA (\d+)\]\]")


def segmentar(texto: str, fuente_id: int | None = None, max_chars: int = 4000) -> List[SeccionTecnica]:
    """Divide el texto en secciones según encabezados y marcas de página.

    Si no detecta encabezados, segmenta por bloques de párrafos respetando
    `max_chars` para no generar secciones gigantes.
    """
    if not texto:
        return []

    secciones: List[SeccionTecnica] = []
    lineas = texto.split("\n")
    titulo_actual = "Introducción"
    buffer: list[str] = []
    pagina_inicio = 1
    pagina_actual = 1

    def _flush():
        contenido = "\n".join(buffer).strip()
        if contenido:
            secciones.append(
                SeccionTecnica(
                    fuente_id=fuente_id,
                    titulo=titulo_actual[:200],
                    contenido=contenido,
                    pagina_inicio=pagina_inicio,
                    pagina_fin=pagina_actual,
                    keywords=", ".join(extraer_keywords(contenido, max_kw=12)),
                )
            )

    for linea in lineas:
        m_pag = _PAGINA.search(linea)
        if m_pag:
            pagina_actual = int(m_pag.group(1))
            continue  # no agregamos la marca al contenido

        es_heading = bool(_HEADING.match(linea)) and len(linea.strip()) < 120
        muy_largo = sum(len(b) for b in buffer) > max_chars

        if (es_heading or muy_largo) and buffer:
            _flush()
            buffer = []
            pagina_inicio = pagina_actual
            if es_heading:
                titulo_actual = linea.strip()
                continue
        if es_heading and not buffer:
            titulo_actual = linea.strip()
            pagina_inicio = pagina_actual
            continue
        buffer.append(linea)

    _flush()
    return secciones
