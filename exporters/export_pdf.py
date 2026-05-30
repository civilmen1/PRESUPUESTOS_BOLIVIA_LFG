"""Exportación de APUs a PDF (reportlab).

Si reportlab no está instalado, genera un .txt con el mismo contenido para no
bloquear el flujo.
"""
from __future__ import annotations

from pathlib import Path

from config import settings
from config.logging_config import get_logger
from core import repositories

logger = get_logger(__name__)


def exportar_pdf(proyecto_id: int, ruta: str | Path | None = None) -> Path:
    proyecto = repositories.obtener_proyecto(proyecto_id)
    if not proyecto:
        raise ValueError(f"Proyecto {proyecto_id} no encontrado")
    if ruta is None:
        ruta = settings.EXPORT_DIR / f"apu_proyecto_{proyecto_id}.pdf"
    ruta = Path(ruta)

    try:
        return _exportar_reportlab(proyecto, proyecto_id, ruta)
    except ImportError:
        logger.warning("reportlab no instalado; exportando a texto plano")
        return _exportar_txt(proyecto, proyecto_id, ruta.with_suffix(".txt"))


def _exportar_reportlab(proyecto, proyecto_id, ruta: Path) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(ruta), pagesize=A4, topMargin=1.5 * cm,
                            bottomMargin=1.5 * cm)
    story = [
        Paragraph(f"Análisis de Precios Unitarios — {proyecto.nombre}",
                  styles["Title"]),
        Paragraph(f"Región: {proyecto.region or '-'} | Moneda: {proyecto.moneda}",
                  styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    for item in repositories.listar_items(proyecto_id):
        res = repositories.obtener_resultado(item.id)
        story.append(Paragraph(
            f"<b>{item.numero or ''} {item.descripcion}</b> "
            f"({item.unidad}, cant. {item.cantidad:g})", styles["Heading4"]))

        data = [["Tipo", "Recurso", "Und", "Cant. APU", "P. Unit.", "Subtotal"]]
        for r in repositories.listar_recursos(item.id):
            data.append([r.tipo, r.descripcion[:32], r.unidad,
                         f"{r.cantidad_apu:g}", f"{r.precio_unitario:,.2f}",
                         f"{r.subtotal:,.2f}"])
        tabla = Table(data, colWidths=[2.2 * cm, 6 * cm, 1.5 * cm, 2 * cm,
                                       2.3 * cm, 2.3 * cm])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f2f2f2")]),
        ]))
        story.append(tabla)
        if res:
            story.append(Paragraph(
                f"Directo: {res.costo_directo:,.2f} | Indirectos: "
                f"{res.indirectos:,.2f} | Utilidad: {res.utilidad:,.2f} | "
                f"<b>P.U. Total: {res.precio_unitario_total:,.2f} "
                f"{proyecto.moneda}</b>", styles["Normal"]))
        story.append(Spacer(1, 0.4 * cm))

    doc.build(story)
    return ruta


def _exportar_txt(proyecto, proyecto_id, ruta: Path) -> Path:
    lineas = [f"APU - {proyecto.nombre} ({proyecto.moneda})", "=" * 60]
    for item in repositories.listar_items(proyecto_id):
        res = repositories.obtener_resultado(item.id)
        lineas.append(f"\n{item.numero or ''} {item.descripcion} [{item.unidad}]")
        for r in repositories.listar_recursos(item.id):
            lineas.append(f"  - {r.tipo}: {r.descripcion} {r.cantidad_apu:g} "
                          f"{r.unidad} x {r.precio_unitario:,.2f} = {r.subtotal:,.2f}")
        if res:
            lineas.append(f"  P.U. Total: {res.precio_unitario_total:,.2f}")
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    return ruta
