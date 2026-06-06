"""Importa un Formulario B-2 (APU) oficial como banco de conocimiento.

Extrae cada actividad con sus materiales, mano de obra y equipo (descripcion,
codigo, unidad, cantidad y precio productivo) y los guarda en
data/banco_apu.json. Este banco sirve de:
  - referencia de RENDIMIENTOS y PRECIOS para el motor de APU,
  - ejemplos para la IA,
  - precios elementales para el cotizador (Nivel 1: base propia).

Uso:
    python -m scripts.importar_apu_banco <ruta_excel> [--proyecto "Nombre"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook  # noqa: E402

from config import settings  # noqa: E402
from core.text_cleaner import normalizar  # noqa: E402

# Mapeo de la seccion al tipo de recurso del programa.
_TIPO = {"MATERIALES": "material", "MANO DE OBRA": "mano_obra",
         "EQUIPO": "equipo"}


def _txt(v):
    return str(v).strip() if v is not None else ""


def _num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def importar(ruta: str) -> list[dict]:
    """Devuelve la lista de APUs extraidos del Excel B-2."""
    wb = load_workbook(ruta, data_only=True)
    ws = wb[wb.sheetnames[0]]
    filas = list(ws.iter_rows(values_only=True))

    apus: list[dict] = []
    actual = None
    seccion = None  # material | mano_obra | equipo
    for row in filas:
        cols = [_txt(c) for c in row]
        # texto util de la fila (saltando vacios)
        a = cols[0] if len(cols) > 0 else ""
        c = cols[2] if len(cols) > 2 else ""
        e = cols[4] if len(cols) > 4 else ""
        f = cols[5] if len(cols) > 5 else ""
        h = cols[7] if len(cols) > 7 else ""
        i = cols[8] if len(cols) > 8 else ""

        # Nueva actividad
        if c == "Actividad" and e:
            if actual and (actual["materiales"] or actual["mano_obra"]
                           or actual["equipo"]):
                apus.append(actual)
            actual = {"actividad": e, "unidad": "", "cantidad": 1.0,
                      "materiales": [], "mano_obra": [], "equipo": []}
            seccion = None
            continue
        if actual is None:
            continue
        if c == "Unidad" and e:
            actual["unidad"] = e
            continue
        if c == "Cantidad" and e:
            actual["cantidad"] = _num(e) or 1.0
            continue

        # Cambios de seccion (clave del dict del APU)
        cu = normalizar(c)
        if "materiales" in cu and a == "1":
            seccion = "materiales"
            continue
        if "mano de obra" in cu and a == "2":
            seccion = "mano_obra"
            continue
        if ("equipo" in cu or "maquinaria" in cu) and a == "3":
            seccion = "equipo"
            continue
        # Fin del APU al llegar a Gastos generales
        if "gastos generales" in cu and a in ("4", "5", "6"):
            seccion = None
            continue

        # Fila de recurso: tiene codigo en B y descripcion en C, unidad en F
        b = cols[1] if len(cols) > 1 else ""
        if seccion and b and c and f and a not in ("*", ""):
            actual[seccion].append({
                "codigo": b, "descripcion": c, "unidad": f,
                "cantidad": _num(h), "precio": _num(i)})

    if actual and (actual["materiales"] or actual["mano_obra"]
                   or actual["equipo"]):
        apus.append(actual)
    return apus


def guardar_banco(apus: list[dict], proyecto: str = "",
                  reemplazar: bool = True) -> Path:
    """Guarda los APUs en el banco. Si reemplazar=False, los AGREGA a lo existente
    (evitando duplicados por nombre de actividad)."""
    ruta = settings.DATA_DIR / "banco_apu.json"
    existentes: list[dict] = []
    if not reemplazar and ruta.exists():
        try:
            existentes = json.loads(ruta.read_text(encoding="utf-8")).get(
                "apus", [])
        except Exception:
            existentes = []
    vistos = {normalizar(a.get("actividad", "")) for a in existentes}
    for a in apus:
        clave = normalizar(a.get("actividad", ""))
        if clave and clave not in vistos:
            existentes.append(a)
            vistos.add(clave)
    banco = {"_descripcion": "Banco de APU de referencia (rendimientos y precios "
             "reales). Usado por el motor y la IA.", "proyecto": proyecto,
             "apus": existentes}
    ruta.write_text(json.dumps(banco, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return ruta


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.importar_apu_banco <ruta_excel>")
        return
    ruta = sys.argv[1]
    proyecto = ""
    if "--proyecto" in sys.argv:
        proyecto = sys.argv[sys.argv.index("--proyecto") + 1]
    apus = importar(ruta)
    salida = guardar_banco(apus, proyecto)
    print(f"Importados {len(apus)} APUs -> {salida}")
    # resumen
    for a in apus[:5]:
        print(f"  - {a['actividad'][:50]} [{a['unidad']}] "
              f"M:{len(a['materiales'])} MO:{len(a['mano_obra'])} "
              f"EQ:{len(a['equipo'])}")
    if len(apus) > 5:
        print(f"  ... y {len(apus) - 5} mas")


if __name__ == "__main__":
    main()
