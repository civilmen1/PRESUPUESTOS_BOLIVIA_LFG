"""Página de Dashboard / resumen del proyecto."""
from __future__ import annotations

import streamlit as st

from core import currency, repositories
from ui.components import requiere_proyecto


def render(proyecto):
    st.title(" Dashboard")
    if not requiere_proyecto(proyecto):
        return

    items = repositories.listar_items(proyecto.id)
    fuentes = repositories.listar_fuentes(proyecto.id)
    cotizaciones = repositories.listar_cotizaciones(proyecto.id)
    apus = [i for i in items if repositories.obtener_resultado(i.id)]

    alertas_total = 0
    costo_total = 0.0
    for it in items:
        res = repositories.obtener_resultado(it.id)
        if res:
            alertas_total += len(res.alertas)
            costo_total += res.precio_unitario_total * it.cantidad

    st.subheader(f"Proyecto: {proyecto.nombre}  ·  {proyecto.region}  ·  "
                 f"{currency.nombre(proyecto.moneda)}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ítems", len(items))
    c2.metric("Documentos técnicos", len(fuentes))
    c3.metric("APUs generados", len(apus))
    c4.metric("Cotizaciones", len(cotizaciones))

    c5, c6, c7 = st.columns(3)
    cot_vigentes = [c for c in cotizaciones if c.get("estado") == "obtenida"]
    c5.metric("Cotizaciones vigentes", len(cot_vigentes))
    c6.metric("Alertas pendientes", alertas_total)
    c7.metric(f"Costo total estimado ({currency.simbolo(proyecto.moneda)})",
              currency.formatear(costo_total, proyecto.moneda, proyecto,
                                 con_simbolo=False))

    st.divider()
    st.markdown("""
**Flujo recomendado**
1. **Ítems**  carga la tabla de cantidades (CSV/XLSX) o ingresa manualmente.
2. **Documentos**  sube DBC / especificaciones / TDR (PDF, DOCX, TXT).
3. **Vinculación**  revisa y valida los vínculos ítem  especificación.
4. **APUs**  genera los APU; el **cotizador jerárquico Bolivia** busca precios
   en **BD  Web  Email** en ese orden.
5. **Cotizaciones / Proveedores**  revisa fuentes y gestiona proveedores.
6. **Exportación**  Excel, PDF y JSON con trazabilidad completa.
    """)
