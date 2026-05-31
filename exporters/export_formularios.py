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
    _pie_firma(ws, fila + 2, proyecto, 6)
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


# ============================================================ cronograma base
def _calcular_cronograma(proyecto, items):
    """Calcula el cronograma base (compartido por A-8, A-9 y B-5).

    Devuelve (n_periodos, datos) donde datos es una lista por ítem con:
      {item, periodo (1..n), monto_total}
    El plazo (proyecto.plazo_dias) define n_periodos = ceil(plazo/30) meses.
    Cada ítem se asigna a un mes según su posición secuencial en la obra.
    """
    import math
    plazo = max(int(getattr(proyecto, "plazo_dias", 180) or 180), 30)
    n_periodos = max(1, math.ceil(plazo / 30))

    reales = [it for it in items if it.descripcion]
    total_items = max(len(reales), 1)
    datos = []
    for idx, it in enumerate(reales):
        periodo = min(n_periodos, 1 + int(idx * n_periodos / total_items))
        res = repositories.obtener_resultado(it.id)
        pu = res.precio_unitario_total if res else 0.0
        datos.append({"item": it, "periodo": periodo,
                      "monto_total": pu * (it.cantidad or 0.0)})
    return n_periodos, datos


def _montos_por_periodo(n_periodos, datos):
    """Suma el monto de obra ejecutado en cada período (1..n)."""
    montos = [0.0] * (n_periodos + 1)  # índice 0 sin uso
    for d in datos:
        montos[d["periodo"]] += d["monto_total"]
    return montos


# ===================================================================== A-8
def _a8_cronograma_obra(ws, proyecto, items):
    n_periodos, datos = _calcular_cronograma(proyecto, items)
    ncols = 4 + n_periodos
    fila = _encabezado(ws, "A-8", "Cronograma de Ejecución de Obra", proyecto, ncols)
    _set(ws, f"A{fila-1}", f"Plazo de ejecución: {proyecto.plazo_dias} días "
                           f"calendario ({n_periodos} meses)", _F_NORM, _LEFT)
    fila += 1
    headers = ["N°", "Ítem / Actividad", "Unidad", "Cantidad"] + \
              [f"Mes {i}" for i in range(1, n_periodos + 1)]
    anchos = [6, 38, 9, 11] + [8] * n_periodos
    _fila_headers(ws, fila, headers, anchos)
    fila += 1
    for d in datos:
        it = d["item"]
        _set(ws, f"A{fila}", it.numero, _F_NORM, _CENTER)
        _set(ws, f"B{fila}", it.descripcion, _F_NORM, _LEFT)
        _set(ws, f"C{fila}", it.unidad, _F_NORM, _CENTER)
        _set(ws, f"D{fila}", it.cantidad, _F_NORM, _RIGHT, fmt="#,##0.00")
        for m in range(1, n_periodos + 1):
            col = get_column_letter(4 + m)
            _set(ws, f"{col}{fila}", "■" if m == d["periodo"] else "", _F_NORM,
                 _CENTER)
            ws[f"{col}{fila}"].border = _BORDE
        for c in "ABCD":
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1

    # Fila de avance valorado y % por período
    montos = _montos_por_periodo(n_periodos, datos)
    total = sum(montos)
    _set(ws, f"A{fila}", "AVANCE VALORADO (Bs)", _F_BOLD, _RIGHT, _FILL_GRIS)
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    for m in range(1, n_periodos + 1):
        col = get_column_letter(4 + m)
        _set(ws, f"{col}{fila}", round(montos[m], 2), _F_BOLD, _RIGHT, _FILL_GRIS,
             "#,##0")
    fila += 1
    _set(ws, f"A{fila}", "AVANCE (%)", _F_BOLD, _RIGHT, _FILL_GRIS)
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    for m in range(1, n_periodos + 1):
        col = get_column_letter(4 + m)
        pct = (montos[m] / total * 100) if total else 0.0
        _set(ws, f"{col}{fila}", round(pct, 1), _F_BOLD, _RIGHT, _FILL_GRIS, "0.0")
    fila += 2
    _pie_firma(ws, fila, proyecto, ncols)


# ===================================================================== A-9
def _a9_movilizacion(ws, proyecto, items):
    """Cronograma de movilización de equipos (en función del equipo del B-2)."""
    n_periodos, datos = _calcular_cronograma(proyecto, items)
    ncols = 2 + n_periodos
    fila = _encabezado(ws, "A-9", "Cronograma de Movilización de Equipo",
                       proyecto, ncols)
    fila += 1
    headers = ["N°", "Equipo / Maquinaria"] + [f"Mes {i}" for i in
                                               range(1, n_periodos + 1)]
    anchos = [6, 40] + [8] * n_periodos
    _fila_headers(ws, fila, headers, anchos)
    fila += 1

    # Para cada equipo (del B-2), determinar en qué meses se usa: los meses de
    # los ítems que contienen ese equipo.
    periodo_por_item = {d["item"].id: d["periodo"] for d in datos}
    equipos: dict[str, set] = {}
    for it in items:
        for r in repositories.listar_recursos(it.id):
            if r.tipo == TIPO_EQUIPO:
                k = r.descripcion.strip()
                equipos.setdefault(k, set())
                if it.id in periodo_por_item:
                    equipos[k].add(periodo_por_item[it.id])

    if not equipos:
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ncols)
        _set(ws, f"A{fila}", "Sin equipo registrado en los APU (Formulario B-2).",
             _F_NORM, _LEFT)
        fila += 2
        _pie_firma(ws, fila, proyecto, ncols)
        return

    for i, (nombre, meses) in enumerate(sorted(equipos.items()), 1):
        _set(ws, f"A{fila}", i, _F_NORM, _CENTER)
        _set(ws, f"B{fila}", nombre, _F_NORM, _LEFT)
        # el equipo permanece movilizado desde el primer hasta el último mes de uso
        m_ini, m_fin = (min(meses), max(meses)) if meses else (1, 1)
        for m in range(1, n_periodos + 1):
            col = get_column_letter(2 + m)
            marca = "■" if m_ini <= m <= m_fin else ""
            _set(ws, f"{col}{fila}", marca, _F_NORM, _CENTER)
            ws[f"{col}{fila}"].border = _BORDE
        for c in ("A", "B"):
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1
    fila += 1
    _set(ws, f"A{fila}", "Nota: la movilización abarca desde el primer hasta el "
                         "último mes de uso de cada equipo según el A-8.", _F_NORM,
         _LEFT)
    fila += 2
    _pie_firma(ws, fila, proyecto, ncols)


# ===================================================================== B-5
def _b5_desembolsos(ws, proyecto, items):
    """Cronograma de desembolsos. Depende del A-8 y del anticipo solicitado."""
    n_periodos, datos = _calcular_cronograma(proyecto, items)
    fila = _encabezado(ws, "B-5", "Cronograma de Desembolsos", proyecto, 5)

    montos = _montos_por_periodo(n_periodos, datos)
    total_obra = sum(montos)

    anticipo = (total_obra * proyecto.porcentaje_anticipo
                if proyecto.solicita_anticipo else 0.0)

    # Mensaje de anticipo
    if proyecto.solicita_anticipo:
        _set(ws, f"A{fila}", f"Anticipo solicitado: SÍ  ·  "
                             f"{proyecto.porcentaje_anticipo*100:.0f}% = "
                             f"Bs {anticipo:,.2f}", _F_BOLD, _LEFT)
    else:
        _set(ws, f"A{fila}", "Anticipo solicitado: NO", _F_BOLD, _LEFT)
    fila += 2

    _fila_headers(ws, fila, ["Período", "Avance valorado (Bs)",
                             "Amortización anticipo (Bs)", "Desembolso neto (Bs)",
                             "Acumulado (Bs)"],
                  [22, 20, 22, 20, 20])
    fila += 1

    # Fila de anticipo (al inicio, si aplica)
    acumulado = 0.0
    if anticipo:
        acumulado += anticipo
        _set(ws, f"A{fila}", "Anticipo (inicio)", _F_BOLD, _LEFT)
        _set(ws, f"B{fila}", 0.0, _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"C{fila}", 0.0, _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"D{fila}", anticipo, _F_BOLD, _RIGHT, fmt="#,##0.00")
        _set(ws, f"E{fila}", acumulado, _F_NORM, _RIGHT, fmt="#,##0.00")
        for c in "ABCDE":
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1

    # Desembolsos por mes: avance del mes menos amortización proporcional del anticipo
    for m in range(1, n_periodos + 1):
        avance = montos[m]
        # amortización proporcional al avance del período
        amort = (anticipo * (avance / total_obra)) if total_obra else 0.0
        desembolso = avance - amort
        acumulado += desembolso
        _set(ws, f"A{fila}", f"Mes {m}", _F_NORM, _LEFT)
        _set(ws, f"B{fila}", round(avance, 2), _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"C{fila}", round(amort, 2), _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"D{fila}", round(desembolso, 2), _F_NORM, _RIGHT, fmt="#,##0.00")
        _set(ws, f"E{fila}", round(acumulado, 2), _F_NORM, _RIGHT, fmt="#,##0.00")
        for c in "ABCDE":
            ws[f"{c}{fila}"].border = _BORDE
        fila += 1

    # Totales
    _set(ws, f"A{fila}", "TOTAL", _F_BOLD, _RIGHT, _FILL_GRIS)
    _set(ws, f"B{fila}", round(total_obra, 2), _F_BOLD, _RIGHT, _FILL_GRIS, "#,##0.00")
    _set(ws, f"C{fila}", round(anticipo, 2), _F_BOLD, _RIGHT, _FILL_GRIS, "#,##0.00")
    _set(ws, f"D{fila}", round(total_obra - anticipo, 2), _F_BOLD, _RIGHT,
         _FILL_GRIS, "#,##0.00")
    _set(ws, f"E{fila}", round(acumulado, 2), _F_BOLD, _RIGHT, _FILL_GRIS, "#,##0.00")
    for c in "ABCDE":
        ws[f"{c}{fila}"].border = _BORDE
    fila += 2
    _pie_firma(ws, fila, proyecto, 5)


# ---------------------------------------------------------------- pie de firma
def _pie_firma(ws, fila, proyecto, ncols):
    """Bloque de firma del representante legal al pie del formulario."""
    fila += 2
    centro = max(2, ncols // 2)
    col = get_column_letter(centro)
    _set(ws, f"{col}{fila}", "_______________________________", _F_NORM, _CENTER)
    fila += 1
    nombre = proyecto.representante_legal or "(Representante Legal)"
    _set(ws, f"{col}{fila}", nombre, _F_BOLD, _CENTER)
    fila += 1
    if proyecto.ci_representante:
        _set(ws, f"{col}{fila}", f"C.I. {proyecto.ci_representante}", _F_NORM,
             _CENTER)
        fila += 1
    _set(ws, f"{col}{fila}", "REPRESENTANTE LEGAL", _F_NORM, _CENTER)
    fila += 1
    empresa = proyecto.proponente or proyecto.nombre
    _set(ws, f"{col}{fila}", empresa, _F_NORM, _CENTER)


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
    """Genera el libro Excel con los Formularios oficiales NB-SABS (DS 0181):

      B-1 Presupuesto · B-2 APU · B-3 Elementales · B-4 Equipo Mínimo
      A-8 Cronograma de Obra · A-9 Movilización de Equipo · B-5 Desembolsos
    """
    proyecto = repositories.obtener_proyecto(proyecto_id)
    if not proyecto:
        raise ValueError(f"Proyecto {proyecto_id} no encontrado")
    if ruta is None:
        ruta = settings.EXPORT_DIR / f"formularios_proyecto_{proyecto_id}.xlsx"
    ruta = Path(ruta)

    items = repositories.listar_items(proyecto_id)

    wb = Workbook()
    wb.remove(wb.active)
    _b1_presupuesto(wb.create_sheet("B-1 Presupuesto"), proyecto, items)
    _b2_apus(wb.create_sheet("B-2 APU"), proyecto, items)
    _b3_elementales(wb.create_sheet("B-3 Elementales"), proyecto, items)
    _b4_equipo(wb.create_sheet("B-4 Equipo"), proyecto, items)
    _a8_cronograma_obra(wb.create_sheet("A-8 Cronograma Obra"), proyecto, items)
    _a9_movilizacion(wb.create_sheet("A-9 Movilizacion"), proyecto, items)
    _b5_desembolsos(wb.create_sheet("B-5 Desembolsos"), proyecto, items)
    wb.save(ruta)
    return ruta
