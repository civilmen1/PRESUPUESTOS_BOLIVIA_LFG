"""Parser de tabla de cantidades (CSV / XLSX / XLS).

Detecta columnas de forma flexible (módulo, número, descripción, unidad,
cantidad, código, observaciones) y devuelve una lista de objetos Item.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from config.logging_config import get_logger
from core.text_cleaner import extraer_keywords
from models.item import Item

logger = get_logger(__name__)

# Sinónimos de columnas -> campo canónico
_COLUMN_MAP = {
    "modulo": ["modulo", "módulo", "module", "capitulo", "capítulo", "grupo"],
    "numero": ["numero", "número", "nro", "n°", "item_nro", "no", "num", "ítem", "item"],
    "codigo": ["codigo", "código", "code", "cod"],
    "descripcion": ["descripcion", "descripción", "description", "detalle", "concepto", "actividad"],
    "unidad": ["unidad", "und", "unit", "u", "medida", "um"],
    "cantidad": ["cantidad", "cant", "qty", "quantity", "volumen", "vol"],
    "observaciones": ["observaciones", "obs", "observacion", "notas", "comentarios"],
}


def _normaliza_col(nombre: str) -> str:
    return str(nombre).strip().lower().replace(".", "").replace(":", "")


def _mapear_columnas(columnas: List[str]) -> dict:
    """Mapea columnas reales del archivo a campos canónicos."""
    mapeo: dict[str, str] = {}
    normalizadas = {c: _normaliza_col(c) for c in columnas}
    for campo, sinonimos in _COLUMN_MAP.items():
        for original, norm in normalizadas.items():
            if norm in sinonimos or any(norm == s for s in sinonimos):
                mapeo[campo] = original
                break
        if campo not in mapeo:
            # coincidencia parcial
            for original, norm in normalizadas.items():
                if any(s in norm for s in sinonimos):
                    mapeo[campo] = original
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
    """Convierte un DataFrame en lista de Item, detectando columnas."""
    if df is None or df.empty:
        return []
    df = df.dropna(how="all")
    mapeo = _mapear_columnas(list(df.columns))
    logger.info("Mapeo de columnas detectado: %s", mapeo)

    if "descripcion" not in mapeo:
        raise ValueError(
            "No se encontró columna de descripción. Columnas: %s" % list(df.columns)
        )

    items: List[Item] = []
    for _, fila in df.iterrows():
        desc = str(fila.get(mapeo["descripcion"], "")).strip()
        if not desc or desc.lower() == "nan":
            continue
        cantidad = _to_float(fila.get(mapeo["cantidad"])) if "cantidad" in mapeo else 0.0
        item = Item(
            proyecto_id=proyecto_id,
            numero=_to_str(fila.get(mapeo["numero"])) if "numero" in mapeo else "",
            codigo=_to_str(fila.get(mapeo["codigo"])) if "codigo" in mapeo else "",
            descripcion=desc,
            unidad=_to_str(fila.get(mapeo["unidad"])) if "unidad" in mapeo else "",
            cantidad=cantidad,
            observaciones=_to_str(fila.get(mapeo["observaciones"])) if "observaciones" in mapeo else "",
            palabras_clave=", ".join(extraer_keywords(desc, max_kw=8)),
        )
        item._modulo_nombre = (
            _to_str(fila.get(mapeo["modulo"])) if "modulo" in mapeo else ""
        )  # auxiliar para crear módulos
        items.append(item)
    logger.info("Se parsearon %d ítems desde la tabla", len(items))
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
