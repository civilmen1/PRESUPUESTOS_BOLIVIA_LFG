"""Página de Dashboard / resumen del proyecto."""
from __future__ import annotations

import streamlit as st

from core import currency, repositories
from ui.components import requiere_proyecto


def render(proyecto):
    st.title("PRESUPUESTO BOLIVIA con IA")
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
    _editor_incidencias(proyecto)

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


def _editor_incidencias(proyecto):
    """Editor de incidencias indirectas; al guardar recalcula todo el presupuesto."""
    from core import apu_engine, repositories

    st.subheader("Incidencias indirectas del precio unitario")
    st.caption("Ajusta los porcentajes y pulsa 'Aplicar y recalcular'. Todo el "
               "presupuesto se actualiza automaticamente con los nuevos valores.")
    with st.form("incidencias"):
        c1, c2, c3 = st.columns(3)
        bs = c1.number_input("Beneficios sociales (% sobre mano de obra)",
                             0.0, 2.0, float(proyecto.factor_beneficios_sociales),
                             0.01, format="%.4f")
        iva_mo = c2.number_input("IVA mano de obra",
                                 0.0, 1.0, float(proyecto.factor_iva_mano_obra),
                                 0.0001, format="%.4f")
        herr = c3.number_input("Herramientas (% sobre mano de obra)",
                               0.0, 1.0, float(proyecto.factor_herramientas),
                               0.01, format="%.4f")
        c4, c5, c6 = st.columns(3)
        gg = c4.number_input("Gastos generales (% sobre costo directo)",
                             0.0, 1.0, float(proyecto.factor_gastos_generales),
                             0.01, format="%.4f")
        ut = c5.number_input("Utilidad", 0.0, 1.0,
                             float(proyecto.factor_utilidad_sabs), 0.01,
                             format="%.4f")
        it = c6.number_input("Impuestos IT", 0.0, 1.0, float(proyecto.factor_it),
                             0.0001, format="%.4f")
        aplicar = st.form_submit_button("Aplicar y recalcular presupuesto",
                                        type="primary")
    if aplicar:
        repositories.actualizar_incidencias(
            proyecto.id, factor_beneficios_sociales=bs, factor_iva_mano_obra=iva_mo,
            factor_herramientas=herr, factor_gastos_generales=gg,
            factor_utilidad_sabs=ut, factor_it=it)
        proyecto_actualizado = repositories.obtener_proyecto(proyecto.id)
        with st.spinner("Recalculando todos los precios unitarios..."):
            total = apu_engine.recalcular_proyecto(proyecto_actualizado)
        st.success(f"Presupuesto recalculado. Nuevo costo total: "
                   f"{currency.formatear(total, proyecto.moneda, proyecto)}")
        st.rerun()
