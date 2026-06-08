"""Importador del catalogo CWICR (DataDrivenConstruction, CC BY 4.0) al banco.

QUE HACE Y QUE NO:
  - CONSERVA los RENDIMIENTOS (cantidades de material, horas-hombre, horas de
    equipo por unidad de obra): son normas tecnicas reutilizables en Bolivia.
  - DESCARTA los precios del CWICR (estan en EUR / regiones extranjeras): cada
    recurso entra con precio 0, para repreciarlo con tus tarifas bolivianas.
  - Normaliza la mano de obra (sin 'peon' -> 'ayudante', unidad en horas).

USO:
  1) Descarga el dataset (Parquet recomendado, ~55 MB) desde:
     https://github.com/datadrivenconstruction/OpenConstructionEstimate-DDC-CWICR
  2) python -m scripts.importar_cwicr <archivo.parquet|csv> \
         [--contiene hormigon,acero,pintura] [--idioma es] [--guardar]

  --contiene  filtra solo las partidas cuya descripcion contenga alguna palabra
              (curado para Bolivia; evita traer las 55.000 completas).
  --guardar   agrega el resultado al banco (sin reemplazar). Sin esta bandera,
              solo muestra un resumen (modo prueba).

Atribucion (CC BY 4.0): los datos provienen de DataDrivenConstruction CWICR.
"""
from __future__ import annotations

import sys
from typing import Optional

from config.logging_config import get_logger

logger = get_logger(__name__)

# Posibles nombres de columna (el dataset varia por formato/idioma).
_COLS = {
    "rate_code": ["rate_code", "work_code", "position_code", "code"],
    "rate_name": ["rate_final_name", "rate_original_name", "rate_name",
                  "work_name", "position_name", "description"],
    "rate_unit": ["rate_unit", "work_unit", "position_unit", "unit"],
    "res_name": ["resource_name", "resource_final_name", "material_name"],
    "res_unit": ["resource_unit", "res_unit"],
    "res_qty": ["resource_quantity", "quantity", "consumption", "res_quantity"],
    "labor_hours": ["labor_hours_construction_workers", "labor_hours",
                    "man_hours", "work_hours"],
}

_KW_MANO_OBRA = ("obrero", "peon", "peón", "ayudante", "oficial", "albanil",
                 "albañil", "maestro", "capataz", "worker", "labor", "labour",
                 "operator", "operario", "plomero", "electricista", "pintor",
                 "fierrista", "soldador", "carpintero", "mason", "helper")
_KW_EQUIPO = ("maquina", "máquina", "equipo", "machine", "equipment", "mixer",
              "mezcladora", "excavator", "excavadora", "grua", "grúa", "crane",
              "compresor", "compressor", "vibrador", "vibrador", "retroexcavadora",
              "volqueta", "camion", "camión", "truck", "loader", "cargador",
              "herramient", "tool")


def _detectar(columnas, claves) -> Optional[str]:
    cols_lower = {c.lower(): c for c in columnas}
    for cand in claves:
        if cand in cols_lower:
            return cols_lower[cand]
    return None


def _tipo_recurso(nombre: str, unidad: str, labor_hours) -> str:
    n, u = (nombre or "").lower(), (unidad or "").lower()
    try:
        lh = float(labor_hours)
    except (TypeError, ValueError):
        lh = 0.0
    if any(k in n for k in _KW_MANO_OBRA) or (lh > 0 and not n):
        return "mano_obra"
    if any(k in n for k in _KW_EQUIPO):
        return "equipo"
    return "material"


def _leer_tabla(ruta: str):
    import pandas as pd
    if ruta.lower().endswith(".parquet"):
        return pd.read_parquet(ruta)  # requiere pyarrow
    if ruta.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(ruta)
    return pd.read_csv(ruta)


def importar_cwicr(ruta: str, contiene: Optional[list] = None) -> list[dict]:
    """Lee el CWICR y devuelve APUs con rendimientos y precio 0 (sin precios)."""
    import pandas as pd
    from core import mano_obra

    df = _leer_tabla(ruta)
    cols = {k: _detectar(df.columns, v) for k, v in _COLS.items()}
    faltan = [k for k in ("rate_code", "rate_name", "res_name") if not cols[k]]
    if faltan:
        raise ValueError(
            f"No se reconocieron columnas {faltan}. Columnas del archivo: "
            f"{list(df.columns)[:20]}... Renombra o ajusta _COLS.")

    contiene = [c.strip().lower() for c in (contiene or []) if c.strip()]
    apus: dict[str, dict] = {}
    for _, fila in df.iterrows():
        nombre_rate = str(fila.get(cols["rate_name"]) or "").strip()
        if not nombre_rate:
            continue
        if contiene and not any(p in nombre_rate.lower() for p in contiene):
            continue
        code = str(fila.get(cols["rate_code"]) or nombre_rate)
        apu = apus.setdefault(code, {
            "actividad": nombre_rate,
            "unidad": str(fila.get(cols["rate_unit"]) or "") if cols["rate_unit"] else "",
            "materiales": [], "mano_obra": [], "equipo": [],
            "fuente": "CWICR (DataDrivenConstruction, CC BY 4.0)"})

        res_name = str(fila.get(cols["res_name"]) or "").strip()
        if not res_name:
            continue
        res_unit = str(fila.get(cols["res_unit"]) or "") if cols["res_unit"] else ""
        try:
            qty = float(fila.get(cols["res_qty"]) or 0) if cols["res_qty"] else 0.0
        except (TypeError, ValueError):
            qty = 0.0
        lh = fila.get(cols["labor_hours"]) if cols["labor_hours"] else 0
        tipo = _tipo_recurso(res_name, res_unit, lh)

        recurso = {"descripcion": res_name, "unidad": res_unit,
                   "cantidad": qty, "precio": 0}  # PRECIO DESCARTADO a proposito
        if tipo == "mano_obra":
            recurso["descripcion"] = mano_obra.limpiar_descripcion(res_name)
            recurso["unidad"] = "HR"
        grupo = {"material": "materiales", "mano_obra": "mano_obra",
                 "equipo": "equipo"}[tipo]
        apus[code][grupo].append(recurso)

    return list(apus.values())


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.importar_cwicr <archivo> "
              "[--contiene a,b,c] [--guardar]")
        return
    ruta = sys.argv[1]
    contiene = None
    if "--contiene" in sys.argv:
        contiene = sys.argv[sys.argv.index("--contiene") + 1].split(",")
    apus = importar_cwicr(ruta, contiene=contiene)
    print(f"Partidas CWICR leidas (rendimientos, sin precios): {len(apus)}")
    for a in apus[:5]:
        print(f"  - {a['actividad'][:60]} [{a['unidad']}] "
              f"M:{len(a['materiales'])} MO:{len(a['mano_obra'])} "
              f"EQ:{len(a['equipo'])}")
    if "--guardar" in sys.argv and apus:
        from scripts.importar_apu_banco import guardar_banco
        res = guardar_banco(apus, proyecto="CWICR", reemplazar=False)
        from core import banco_apu
        banco_apu._cargar.cache_clear()
        print(f"Agregados {res['agregados']}, actualizados {res['actualizados']}, "
              f"omitidos {res['omitidos']}. Total en banco: {res['total']}. "
              "Recuerda repreciar con tarifas bolivianas (los precios entran en 0).")


if __name__ == "__main__":
    main()
