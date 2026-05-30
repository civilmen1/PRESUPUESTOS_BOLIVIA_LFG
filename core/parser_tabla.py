"""Parser de tabla de cantidades (CSV / XLSX / XLS).

Detecta columnas de forma flexible (módulo, número, descripción, unidad,
cantidad, código, observaciones) y devuelve una lista de objetos Item.
Detecta además filas de TÍTULO DE MÓDULO (sin unidad ni cantidad), típicas de
las tablas de cantidades bolivianas, y las usa para agrupar los ítems.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from config.logging_config import get_logger
from core.text_cleaner import extraer_keywords
from models.item import Item

logger = get_logger(__name__)

# Sinónimos de columnas -> campo canónico.
# OJO: "item"/"ítem" se tratan como DESCRIPCIÓN (uso común en tablas bolivianas),
# mientras que "n°"/"nro" son el NÚMERO de ítem.
_COLUMN_MAP = {
    "modulo": ["modulo", "módulo", "module", "capitulo", "capítulo", "grupo",
               "rubro", "seccion", "sección"],
    "numero": ["numero", "número", "nro", "n°", "no", "num", "item_nro", "orden"],
    "codigo": ["codigo", "código", "code", "cod", "codigo especificacion",
               "codigo de especificacion", "cod especificacion",
               "especificacion", "especificación"],
    "descripcion": ["descripcion", "descripción", "description", "detalle",
                    "concepto", "actividad", "item", "ítem", "designacion",
                    "designación", "descripcion del item", "obra", "tarea"],
    "unidad": ["unidad", "und", "unit", "u", "medida", "um", "und."],
    "cantidad": ["cantidad", "cant", "qty", "quantity", "volumen", "vol",
                 "cant.", "metrado"],
}


def _normaliza_col(nombre: str) -> str:
    return str(nombre).strip().lower().replace(".", "").replace(":", "")


def _mapear_columnas(columnas: List[str]) -> dict:
    """Mapea columnas reales del archivo a campos canónicos.

    Dos pasadas: primero coincidencias exactas (sin reusar columnas), luego
    parciales (solo con sinónimos de 3+ caracteres) para evitar falsos positivos.
    """
    mapeo: dict[str, str] = {}
    claimed: set[str] = set()
    normalizadas = {c: _normaliza_col(c) for c in columnas}

    for campo, sinonimos in _COLUMN_MAP.items():
        for original, norm in normalizadas.items():
            if original in claimed:
                continue
            if norm in sinonimos:
                mapeo[campo] = original
                claimed.add(original)
                break

    for campo, sinonimos in _COLUMN_MAP.items():
        if campo in mapeo:
            continue
        for original, norm in normalizadas.items():
            if original in claimed:
                continue
            if any(s in norm for s in sinonimos if len(s) >= 3):
                mapeo[campo] = original
                claimed.add(original)
                break
    return mapeo


def leer_dataframe(ruta: str | Path) -> pd.DataFrame:
    """Lee CSV/XLSX/XLS a DataFrame."""
    ruta = Path(ruta)
    suf = ruta.suffix.lower()
    if suf == ".csv":
        try:
            return pd.read_csv(ruta, sep=None, engine="python")
        except Exception:
            return pd.read_csv(ruta, sep=";")
    if suf in {".xlsx", ".xlsm"}:
        return pd.read_excel(ruta, engine="openpyxl")
    if suf == ".xls":
        return pd.read_excel(ruta)
    raise ValueError(f"Formato de tabla no soportado: {suf}")


def parsear_items(ruta: str | Path, proyecto_id: int | None = None) -> List[Item]:
    """Lee un archivo y devuelve una lista de Item lista para guardar."""
    df = leer_dataframe(ruta)
    return dataframe_a_items(df, proyecto_id)


def dataframe_a_items(df: pd.DataFrame, proyecto_id: int | None = None) -> List[Item]:
    """Convierte un DataFrame en lista de Item, detectando columnas y módulos.

    Una fila se considera **título de módulo** cuando tiene descripción pero
    NO tiene número, ni unidad, ni cantidad. Esos títulos agrupan a los ítems
    que vienen debajo (campo auxiliar ``_modulo_nombre``).
    """
    if df is None or df.empty:
        return []
    df = df.dropna(how="all")
    mapeo = _mapear_columnas(list(df.columns))
    logger.info("Mapeo de columnas detectado: %s", mapeo)

    if "descripcion" not in mapeo:
        raise ValueError(
            "No se encontró columna de descripción. Columnas detectadas: %s. "
            "Usa la plantilla descargable o renombra la columna de descripción "
            "a 'ITEM' o 'DESCRIPCION'." % list(df.columns)
        )

    items: List[Item] = []
    modulo_actual = ""
    for _, fila in df.iterrows():
        desc = _to_str(fila.get(mapeo["descripcion"]))
        if not desc:
            continue

        numero = _to_str(fila.get(mapeo["numero"])) if "numero" in mapeo else ""
        unidad = _to_str(fila.get(mapeo["unidad"])) if "unidad" in mapeo else ""
        cantidad = _to_float(fila.get(mapeo["cantidad"])) if "cantidad" in mapeo else 0.0
        modulo_col = _to_str(fila.get(mapeo["modulo"])) if "modulo" in mapeo else ""

        # Si hay columna de módulo explícita, se usa directamente
        if modulo_col:
            modulo_actual = modulo_col

        # Fila de TÍTULO DE MÓDULO: tiene texto pero sin número/unidad/cantidad
        es_titulo_modulo = (not modulo_col and not numero and not unidad
                            and cantidad == 0.0)
        if es_titulo_modulo:
            modulo_actual = desc
            logger.info("Módulo detectado: %s", desc)
            continue

        item = Item(
            proyecto_id=proyecto_id,
            numero=numero,
            codigo=_to_str(fila.get(mapeo["codigo"])) if "codigo" in mapeo else "",
            descripcion=desc,
            unidad=unidad,
            cantidad=cantidad,
            observaciones=_to_str(fila.get(mapeo["observaciones"])) if "observaciones" in mapeo else "",
            palabras_clave=", ".join(extraer_keywords(desc, max_kw=8)),
        )
        item._modulo_nombre = modulo_actual  # auxiliar para crear módulos
        items.append(item)

    logger.info("Se parsearon %d ítems (módulos detectados incluidos)", len(items))
    return items


def _to_float(valor) -> float:
    if valor is None:
        return 0.0
    try:
        s = str(valor).replace(",", ".").strip()
        return float(s) if s and s.lower() != "nan" else 0.0
    except (ValueError, TypeError):
        return 0.0


def _to_str(valor) -> str:
    if valor is None:
        return ""
    s = str(valor).strip()
    return "" if s.lower() == "nan" else s
