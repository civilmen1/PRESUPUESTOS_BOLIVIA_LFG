"""Importador masivo de precios de referencia (Nivel 1) desde CSV/XLSX.

El usuario carga su PROPIA lista de precios reales de materiales y se registran
en la BD de referencia que usa el cotizador (Nivel 1). El sistema NO inventa
precios: solo carga los que tú provees.

Columnas reconocidas (flexible, no distingue mayúsculas/acentos):
  - descripcion  (obligatoria): "descripcion", "material", "insumo", "detalle"...
  - unidad       (obligatoria): "unidad", "und", "u"
  - precio       (obligatoria): "precio", "precio (bs)", "costo", "valor"...
  - categoria    (opcional)
  - region       (opcional): "region", "departamento", "ciudad"
  - moneda       (opcional, por defecto BOB)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from config.logging_config import get_logger
from core.text_cleaner import normalizar
from providers import supplier_repository

logger = get_logger(__name__)


def _detectar_columna(col_norm: str) -> Optional[str]:
    """Mapea el nombre de una columna a su campo canónico (o None)."""
    if col_norm.startswith("descrip") or col_norm in (
            "material", "insumo", "item", "detalle", "producto",
            "nombre", "nombre del material"):
        return "descripcion"
    if col_norm.startswith("unid") or col_norm in ("und", "u", "ud"):
        return "unidad"
    if col_norm.startswith("precio") or col_norm in (
            "costo", "valor", "p.u.", "p. unit.", "punit"):
        return "precio"
    if col_norm.startswith("categ") or col_norm in ("rubro", "tipo"):
        return "categoria"
    if col_norm.startswith("region") or col_norm in (
            "departamento", "depto", "ciudad"):
        return "region"
    if col_norm.startswith("moneda"):
        return "moneda"
    return None


def _mapear_columnas(columnas) -> dict:
    """Devuelve {campo_canonico: nombre_columna_original}. Primera en ganar."""
    mapa: dict = {}
    for c in columnas:
        campo = _detectar_columna(normalizar(str(c)).strip())
        if campo and campo not in mapa:
            mapa[campo] = c
    return mapa


def _a_float(valor) -> float:
    """Convierte un texto de precio a float, tolerando 'Bs', miles y decimales."""
    if valor is None:
        return 0.0
    s = str(valor).strip()
    for tok in ("bs", "bs.", "bob", "$us", "$", " "):
        s = s.lower().replace(tok, "")
    if not s:
        return 0.0
    # Normaliza separadores: "1.234,56" -> "1234.56"; "1,234.56" -> "1234.56"
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _val(fila, mapa, campo, default="") -> str:
    col = mapa.get(campo)
    if not col:
        return default
    v = fila.get(col)
    if v is None:
        return default
    txt = str(v).strip()
    return txt if txt and txt.lower() != "nan" else default


def importar_precios_df(df, fuente: str = "importado",
                        persistir: bool = True) -> dict:
    """Registra los precios de un DataFrame. Devuelve un resumen.

    {importados, omitidos, errores: [..], total}. Omite filas sin descripción
    o con precio <= 0 (no se inventan precios).
    """
    mapa = _mapear_columnas(list(df.columns))
    faltan = [c for c in ("descripcion", "unidad", "precio") if c not in mapa]
    if faltan:
        raise ValueError(
            "Faltan columnas obligatorias: " + ", ".join(faltan) +
            ". Se requieren al menos: descripcion, unidad, precio.")

    importados, omitidos, errores = 0, 0, []
    for i, fila in df.iterrows():
        desc = _val(fila, mapa, "descripcion")
        unidad = _val(fila, mapa, "unidad")
        precio = _a_float(_val(fila, mapa, "precio"))
        if not desc or precio <= 0:
            omitidos += 1
            continue
        categoria = _val(fila, mapa, "categoria")
        region = _val(fila, mapa, "region")
        moneda = _val(fila, mapa, "moneda", "BOB") or "BOB"
        if persistir:
            try:
                supplier_repository.registrar_precio(
                    descripcion=desc, categoria=categoria, unidad=unidad,
                    precio=precio, moneda=moneda, region=region, fuente=fuente)
            except Exception as exc:  # fila mala no debe frenar el lote
                errores.append(f"Fila {int(i) + 2}: {exc}")
                continue
        importados += 1

    logger.info("Importación de precios: %d importados, %d omitidos, %d errores",
                importados, omitidos, len(errores))
    return {"importados": importados, "omitidos": omitidos,
            "errores": errores, "total": int(len(df))}


def importar_precios(ruta, fuente: str = "importado",
                     persistir: bool = True) -> dict:
    """Lee un CSV/XLSX de precios y los registra. Devuelve el resumen."""
    import pandas as pd

    ruta = Path(ruta)
    if ruta.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(ruta, dtype=str)
    else:
        df = pd.read_csv(ruta, dtype=str)
    return importar_precios_df(df, fuente=fuente, persistir=persistir)
