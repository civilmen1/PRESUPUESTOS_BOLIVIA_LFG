"""Exportación de los Formularios B-1 a B-5 (NB-SABS / DS 0181) a Excel.

  B-1  Presupuesto General de la Obra (por ítems y módulos)
  B-2  Análisis de Precios Unitarios (estructura boliviana completa)
  B-3  Precios Unitarios de Elementales (materiales, mano de obra, equipo)
  B-4  Equipo Mínimo Comprometido
  B-5  Cronograma de Ejecución de Obra

Cada formulario se escribe en una hoja del libro .xlsx.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config import settings
from core import repositories
from core.sabs import calcular_desglose
from models.apu_resource import TIPO_EQUIPO, TIPO_MANO_OBRA, TIPO_MATERIAL

# ---------------------------------------------------------------- estilos
_AZUL = "1F4E78"
_GRIS = "D9D9D9"
_BORDE = Border(*[Side(style="thin", color="999999")] * 4)
_F_TITULO = Font(bold=True, size=14, color="1F4E78")
_F_HEAD = Font(bold=True, color="FFFFFF", size=9)
_F_BOLD = Font(bold=True, size=9)
_F_NORM = Font(size=9)
_FILL_HEAD = PatternFill("solid", fgColor=_AZUL)
_FILL_GRIS = PatternFill("solid", fgColor=_GRIS)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_RIGHT = Alignment(horizontal="right")
_LEFT = Alignment(horizontal="left", wrap_text=True)


def _set(ws, celda, valor, font=_F_NORM, align=None, fill=None, fmt=None):
    c = ws[celda]
    c.value = valor
    c.font = font
    if align:
        c.alignment = align
    if fill:
        c.fill = fill
    if fmt:
        c.number_format = fmt
    return c


def _encabezado(ws, codigo: str, titulo: str, proyecto, ncols: int = 6):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    _set(ws, "A1", f"FORMULARIO {codigo}", _F_TITULO, _CENTER)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    _set(ws, "A2", titulo.upper(), _F_BOLD, _CENTER)
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=ncols)
    _set(ws, "A3", f"Proyecto: {proyecto.nombre}   |   Entidad: "
                   f"{proyecto.entidad or '—'}   |   Moneda: {proyecto.moneda}",
         _F_NORM, _CENTER)
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=ncols)
    _set(ws, "A4", f"Proponente: {proyecto.proponente or '—'}   |   "
                   f"Departamento: {proyecto.region or '—'}", _F_NORM, _CENTER)
    return 6  # primera fila de contenido


def _fila_headers(ws, fila, headers, anchos):
    for i, (h, w) in enumerate(zip(headers, anchos), start=1):
        col = get_column_letter(i)
        ws.column_dimensions[col].width = w
        _set(ws, f"{col}{fila}", h, _F_HEAD, _CENTER, _FILL_HEAD)
        ws[f"{col}{fila}"].border = _BORDE


# ===================================================================== B-1
def _b1_presupuesto(ws, proyecto, items):
    fila = _encabezado(ws, "B-1", "Presupuesto General de la Obra", proyecto, 6)
    _fila_headers(ws, fila, ["N°", "Ítem / Descripción", "Unidad", "Cantidad",
                             "Precio Unitario (Bs)", "Precio Total (Bs)"],
                  [6, 50, 10, 12, 16, 18])
    fila += 1
    total_general = 0.0
    modulo_actual = None
    for it in items:
        mod = _modulo_nombre(it)
        if mod and mod != modulo_actual:
            modulo_actual = mod
            ws.merge_cells(start_row=fila, start_column=1, end_row=fila,
                           end_column=6)
            _set(ws, f"A{fila}", mod, _F_BOLD, _LEFT, _FILL_GRIS)
            fila += 1
        res = repositories.obtener_resultado(it.id)
        pu = res.precio_unitario_total if res else 0.0
        total = pu * it.cantidad
        total_general += total
        _set(ws, f"A{fila}", it.numero, _F_NORM, _CENTER)
        _set(ws, f"B{fila}", it.descripcion, _F_NORM, _LEFT)
        _set(ws, f"C{fila}", it.unidad, _F_NORM, _CENTER)
        _set(ws, f"D{fila}", it.cantidad, _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"E{fila}", pu, _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"F{fila}", total, _F_NORM, _RIGHT, fmt="#,##0.00")
        for c in "ABCDEF":
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=5)
    _set(ws, f"A{fila}", "TOTAL GENERAL (Bs)", _F_BOLD, _RIGHT, _FILL_GRIS)
    _set(ws, f"F{fila}", total_general, _F_BOLD, _RIGHT, _FILL_GRIS, "#,##0.00")
    fila += 2
    _set(ws, f"A{fila}", f"Son: {_a_letras(total_general)} bolivianos.", _F_NORM,
         _LEFT)
    return total_general


# ===================================================================== B-2
def _b2_apus(ws, proyecto, items):
    fila = _encabezado(ws, "B-2", "Análisis de Precios Unitarios", proyecto, 6)
    for it in items:
        recursos = repositories.listar_recursos(it.id)
        if not recursos:
            continue
        d = calcular_desglose(recursos, proyecto)

        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=6)
        _set(ws, f"A{fila}", f"ÍTEM {it.numero}: {it.descripcion}", _F_BOLD,
             _LEFT, _FILL_GRIS)
        fila += 1
        _set(ws, f"A{fila}", f"Unidad: {it.unidad}", _F_NORM, _LEFT)
        _set(ws, f"D{fila}", f"Cantidad: {it.cantidad:g}", _F_NORM, _RIGHT)
        fila += 1

        _fila_headers(ws, fila, ["Descripción", "Unidad", "Cantidad",
                                 "Precio Unit. (Bs)", "Parcial (Bs)", "Tipo"],
                      [44, 10, 12, 14, 14, 12])
        fila += 1

        for etiqueta, tipo in (("1. MATERIALES", TIPO_MATERIAL),
                               ("2. MANO DE OBRA", TIPO_MANO_OBRA),
                               ("3. EQUIPO, MAQUINARIA Y HERRAMIENTAS", TIPO_EQUIPO)):
            ws.merge_cells(start_row=fila, start_column=1, end_row=fila,
                           end_column=6)
            _set(ws, f"A{fila}", etiqueta, _F_BOLD, _LEFT)
            fila += 1
            for r in [x for x in recursos if x.tipo == tipo]:
                _set(ws, f"A{fila}", r.descripcion, _F_NORM, _LEFT)
                _set(ws, f"B{fila}", r.unidad, _F_NORM, _CENTER)
                _set(ws, f"C{fila}", r.cantidad_apu, _F_NORM, _RIGHT, fmt="#,##0.0000")
                _set(ws, f"D{fila}", r.precio_unitario, _F_NORM, _RIGHT, fmt="#,##0.00")
                _set(ws, f"E{fila}", r.subtotal, _F_NORM, _RIGHT, fmt="#,##0.00")
                _set(ws, f"F{fila}", r.tipo, _F_NORM, _CENTER)
                fila += 1
            # subtotales y cargas por grupo
            if tipo == TIPO_MATERIAL:
                fila = _subtotal(ws, fila, "SUBTOTAL MATERIALES (A)", d.materiales)
            elif tipo == TIPO_MANO_OBRA:
                fila = _subtotal(ws, fila, "  Subtotal mano de obra", d.mano_obra_neta)
                fila = _subtotal(ws, fila,
                                 f"  Beneficios sociales ({proyecto.factor_beneficios_sociales*100:.2f}%)",
                                 d.beneficios_sociales)
                fila = _subtotal(ws, fila,
                                 f"  IVA mano de obra ({proyecto.factor_iva_mano_obra*100:.2f}%)",
                                 d.iva_mano_obra)
                fila = _subtotal(ws, fila, "SUBTOTAL MANO DE OBRA (B)",
                                 d.mano_obra_total, negrita=True)
            else:
                fila = _subtotal(ws, fila, "  Subtotal equipo", d.equipo_neto)
                fila = _subtotal(ws, fila,
                                 f"  Herramientas menores ({proyecto.factor_herramientas*100:.2f}% de B)",
                                 d.herramientas)
                if d.iva_equipo:
                    fila = _subtotal(ws, fila, "  IVA equipo", d.iva_equipo)
                fila = _subtotal(ws, fila, "SUBTOTAL EQUIPO Y HERRAMIENTAS (C)",
                                 d.equipo_total, negrita=True)

        # Totales finales del ítem
        fila = _subtotal(ws, fila, "4. COSTO DIRECTO (A+B+C)", d.costo_directo,
                         negrita=True, fill=True)
        fila = _subtotal(ws, fila,
                         f"5. GASTOS GENERALES ({proyecto.factor_gastos_generales*100:.2f}%)",
                         d.gastos_generales)
        fila = _subtotal(ws, fila,
                         f"6. UTILIDAD ({proyecto.factor_utilidad_sabs*100:.2f}%)",
                         d.utilidad)
        fila = _subtotal(ws, fila,
                         f"7. IMPUESTOS IT ({proyecto.factor_it*100:.2f}%)",
                         d.impuestos_it)
        fila = _subtotal(ws, fila, "PRECIO UNITARIO TOTAL (Bs)",
                         d.precio_unitario_total, negrita=True, fill=True)
        fila += 2


def _subtotal(ws, fila, etiqueta, valor, negrita=False, fill=False):
    font = _F_BOLD if negrita else _F_NORM
    relleno = _FILL_GRIS if fill else None
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    _set(ws, f"A{fila}", etiqueta, font, _RIGHT, relleno)
    _set(ws, f"E{fila}", valor, font, _RIGHT, relleno, "#,##0.00")
    return fila + 1


# ===================================================================== B-3
def _b3_elementales(ws, proyecto, items):
    fila = _encabezado(ws, "B-3", "Precios Unitarios de Elementales", proyecto, 5)
    _fila_headers(ws, fila, ["Tipo", "Descripción del insumo", "Unidad",
                             "Precio Unitario (Bs)", "Fuente del precio"],
                  [14, 46, 10, 16, 20])
    fila += 1
    vistos: dict[tuple, dict] = {}
    for it in items:
        for r in repositories.listar_recursos(it.id):
            clave = (r.tipo, r.descripcion.strip().lower(), r.unidad.strip().lower())
            if clave not in vistos or r.precio_unitario > 0:
                vistos[clave] = {"tipo": r.tipo, "desc": r.descripcion,
                                 "unidad": r.unidad, "precio": r.precio_unitario,
                                 "fuente": r.fuente_precio}
    etiqueta_tipo = {TIPO_MATERIAL: "Material", TIPO_MANO_OBRA: "Mano de obra",
                     TIPO_EQUIPO: "Equipo/Herr."}
    for v in sorted(vistos.values(), key=lambda x: (x["tipo"], x["desc"])):
        _set(ws, f"A{fila}", etiqueta_tipo.get(v["tipo"], v["tipo"]), _F_NORM,
             _CENTER)
        _set(ws, f"B{fila}", v["desc"], _F_NORM, _LEFT)
        _set(ws, f"C{fila}", v["unidad"], _F_NORM, _CENTER)
        _set(ws, f"D{fila}", v["precio"], _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"E{fila}", v["fuente"] or "—", _F_NORM, _CENTER)
        for c in "ABCDE":
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1


# ===================================================================== B-4
def _b4_equipo(ws, proyecto, items):
    fila = _encabezado(ws, "B-4", "Equipo Mínimo Comprometido", proyecto, 5)
    _fila_headers(ws, fila, ["N°", "Equipo / Maquinaria", "Unidad",
                             "Cantidad (ref.)", "Observaciones"],
                  [6, 46, 12, 14, 28])
    fila += 1
    # consolida equipos del proyecto
    equipos: dict[str, dict] = {}
    for it in items:
        for r in repositories.listar_recursos(it.id):
            if r.tipo == TIPO_EQUIPO:
                k = r.descripcion.strip().lower()
                equipos.setdefault(k, {"desc": r.descripcion, "unidad": r.unidad,
                                       "cant": 0.0})
                equipos[k]["cant"] += r.cantidad_apu * _cantidad_item(it)
    if not equipos:
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=5)
        _set(ws, f"A{fila}", "Sin equipo registrado en los APU. Complete según el "
                             "requerimiento del DBC.", _F_NORM, _LEFT)
        return
    for i, v in enumerate(sorted(equipos.values(), key=lambda x: x["desc"]), 1):
        _set(ws, f"A{fila}", i, _F_NORM, _CENTER)
        _set(ws, f"B{fila}", v["desc"], _F_NORM, _LEFT)
        _set(ws, f"C{fila}", v["unidad"], _F_NORM, _CENTER)
        _set(ws, f"D{fila}", round(v["cant"], 2), _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"E{fila}", "Propio / Alquilado", _F_NORM, _LEFT)
        for c in "ABCDE":
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1


# ===================================================================== B-5
def _b5_cronograma(ws, proyecto, items):
    n_periodos = 6  # meses por defecto
    ncols = 4 + n_periodos
    fila = _encabezado(ws, "B-5", "Cronograma de Ejecución de Obra", proyecto, ncols)
    headers = ["N°", "Ítem", "Unidad", "Cantidad"] + [f"Mes {i}" for i in
                                                      range(1, n_periodos + 1)]
    anchos = [6, 40, 10, 12] + [9] * n_periodos
    _fila_headers(ws, fila, headers, anchos)
    fila += 1
    for idx, it in enumerate(items):
        _set(ws, f"A{fila}", it.numero, _F_NORM, _CENTER)
        _set(ws, f"B{fila}", it.descripcion, _F_NORM, _LEFT)
        _set(ws, f"C{fila}", it.unidad, _F_NORM, _CENTER)
        _set(ws, f"D{fila}", it.cantidad, _F_NORM, _RIGHT, fmt="#,##0.00")
        # barra de Gantt simple: distribuye el ítem en 1-2 meses según su posición
        mes = min(n_periodos, 1 + int(idx * n_periodos / max(len(items), 1)))
        for m in range(1, n_periodos + 1):
            col = get_column_letter(4 + m)
            marca = "■" if m == mes else ""
            _set(ws, f"{col}{fila}", marca, _F_NORM, _CENTER)
            ws[f"{col}{fila}"].border = _BORDE
        for c in "ABCD":
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1
    fila += 1
    _set(ws, f"A{fila}", "Nota: cronograma referencial. Ajuste los períodos y la "
                         "distribución según el plazo del contrato.", _F_NORM, _LEFT)


# ---------------------------------------------------------------- helpers
def _modulo_nombre(item):
    """Devuelve el nombre del módulo del ítem o None."""
    if not item.modulo_id:
        return None
    try:
        from core.database import db_session
        with db_session() as conn:
            r = conn.execute("SELECT nombre FROM modulos WHERE id=?",
                             (item.modulo_id,)).fetchone()
            return r["nombre"] if r else None
    except Exception:
        return None


def _cantidad_item(item):
    return item.cantidad or 0.0


def _a_letras(monto: float) -> str:
    """Convierte un monto a una expresión simple (entero + centavos)."""
    entero = int(monto)
    centavos = int(round((monto - entero) * 100))
    return f"{entero:,} con {centavos:02d}/100"


# ---------------------------------------------------------------- API
def exportar_formularios(proyecto_id: int, ruta: str | Path | None = None) -> Path:
    """Genera el libro Excel con los Formularios B-1 a B-5."""
    proyecto = repositories.obtener_proyecto(proyecto_id)
    if not proyecto:
        raise ValueError(f"Proyecto {proyecto_id} no encontrado")
    if ruta is None:
        ruta = settings.EXPORT_DIR / f"formularios_B1_B5_proyecto_{proyecto_id}.xlsx"
    ruta = Path(ruta)

    items = repositories.listar_items(proyecto_id)

    wb = Workbook()
    wb.remove(wb.active)
    _b1_presupuesto(wb.create_sheet("B-1 Presupuesto"), proyecto, items)
    _b2_apus(wb.create_sheet("B-2 APU"), proyecto, items)
    _b3_elementales(wb.create_sheet("B-3 Elementales"), proyecto, items)
    _b4_equipo(wb.create_sheet("B-4 Equipo"), proyecto, items)
    _b5_cronograma(wb.create_sheet("B-5 Cronograma"), proyecto, items)
    wb.save(ruta)
    return ruta
