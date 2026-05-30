"""Exportación de APUs a Excel (.xlsx) con hojas de resumen y detalle."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import settings
from core import repositories


def exportar_excel(proyecto_id: int, ruta: str | Path | None = None) -> Path:
    proyecto = repositories.obtener_proyecto(proyecto_id)
    if not proyecto:
        raise ValueError(f"Proyecto {proyecto_id} no encontrado")
    if ruta is None:
        ruta = settings.EXPORT_DIR / f"apu_proyecto_{proyecto_id}.xlsx"
    ruta = Path(ruta)

    items = repositories.listar_items(proyecto_id)

    resumen_rows, detalle_rows = [], []
    for item in items:
        res = repositories.obtener_resultado(item.id)
        resumen_rows.append({
            "N°": item.numero, "Código": item.codigo,
            "Descripción": item.descripcion, "Unidad": item.unidad,
            "Cantidad": item.cantidad,
            "Costo Materiales": res.costo_materiales if res else 0,
            "Costo Mano Obra": res.costo_mano_obra if res else 0,
            "Costo Equipos": res.costo_equipos if res else 0,
            "Costo Directo": res.costo_directo if res else 0,
            "Indirectos": res.indirectos if res else 0,
            "Utilidad": res.utilidad if res else 0,
            "Impuestos": res.impuestos if res else 0,
            "Precio Unitario": res.precio_unitario_total if res else 0,
            "Precio Total": round((res.precio_unitario_total if res else 0)
                                  * item.cantidad, 2),
            "Alertas": "; ".join(res.alertas) if res else "",
        })
        for r in repositories.listar_recursos(item.id):
            detalle_rows.append({
                "Ítem N°": item.numero, "Ítem": item.descripcion,
                "Tipo": r.tipo, "Recurso": r.descripcion, "Unidad": r.unidad,
                "Rendimiento": r.rendimiento, "Cantidad APU": r.cantidad_apu,
                "Precio Unitario": r.precio_unitario, "Subtotal": r.subtotal,
                "Fuente Precio": r.fuente_precio,
            })

    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        meta = pd.DataFrame([{
            "Proyecto": proyecto.nombre, "Región": proyecto.region,
            "Moneda": proyecto.moneda,
            "Factor Indirectos": proyecto.factor_indirectos,
            "Factor Utilidad": proyecto.factor_utilidad,
            "Factor Impuestos": proyecto.factor_impuestos,
        }])
        meta.to_excel(writer, sheet_name="Proyecto", index=False)
        pd.DataFrame(resumen_rows).to_excel(writer, sheet_name="Resumen APU",
                                            index=False)
        pd.DataFrame(detalle_rows).to_excel(writer, sheet_name="Detalle Recursos",
                                            index=False)
        cot = repositories.listar_cotizaciones(proyecto_id)
        if cot:
            pd.DataFrame(cot).to_excel(writer, sheet_name="Cotizaciones",
                                       index=False)
    return ruta
