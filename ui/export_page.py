"""Página de Exportación: Excel, PDF y JSON."""
from __future__ import annotations

import streamlit as st

from exporters.export_excel import exportar_excel
from exporters.export_formularios import exportar_formularios
from exporters.export_json import exportar_json
from exporters.export_pdf import exportar_pdf
from ui.components import requiere_proyecto


def render(proyecto):
    st.title(" Exportación")
    if not requiere_proyecto(proyecto):
        return

    st.write(f"Proyecto: **{proyecto.nombre}**")

    st.subheader(" Formularios oficiales NB-SABS (DS 0181)")
    st.caption("B-1 Presupuesto · B-2 APU · B-3 Precios Elementales · "
               "B-4 Equipo Mínimo · A-8 Cronograma de Obra · "
               "A-9 Movilización de Equipo · B-5 Cronograma de Desembolsos")
    if not proyecto.representante_legal:
        st.info(" Define el representante legal y el plazo/anticipo al crear el "
                "proyecto para que los formularios salgan completos.")
    cgen, cprev = st.columns(2)
    if cgen.button("Generar Formularios oficiales (Excel)", type="primary",
                   use_container_width=True):
        ruta = exportar_formularios(proyecto.id)
        st.session_state["ruta_formularios"] = str(ruta)
        with open(ruta, "rb") as fh:
            st.download_button(
                "Descargar Formularios B-1 a B-5", fh, file_name=ruta.name,
                mime="application/vnd.openxmlformats-officedocument."
                     "spreadsheetml.sheet", use_container_width=True)

    if cprev.button("Vista previa de formularios", use_container_width=True):
        ruta = exportar_formularios(proyecto.id)
        st.session_state["ruta_formularios"] = str(ruta)
        st.session_state["mostrar_preview"] = True

    if st.session_state.get("mostrar_preview") and \
            st.session_state.get("ruta_formularios"):
        _vista_previa(st.session_state["ruta_formularios"])

    st.divider()
    st.subheader("Otras exportaciones")
    c1, c2, c3 = st.columns(3)

    if c1.button(" Generar Excel", use_container_width=True):
        ruta = exportar_excel(proyecto.id)
        with open(ruta, "rb") as fh:
            st.download_button(" Descargar Excel", fh, file_name=ruta.name,
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet", use_container_width=True)

    if c2.button("Formularios en PDF", use_container_width=True):
        ruta = exportar_pdf(proyecto.id)
        with open(ruta, "rb") as fh:
            st.download_button("Descargar PDF (formato formularios)", fh,
                               file_name=ruta.name, use_container_width=True)

    if c3.button(" Generar JSON", use_container_width=True):
        ruta = exportar_json(proyecto.id)
        with open(ruta, "rb") as fh:
            st.download_button(" Descargar JSON", fh, file_name=ruta.name,
                               mime="application/json", use_container_width=True)

    st.caption("Las exportaciones incluyen trazabilidad técnica y de cotización.")


def _vista_previa(ruta: str):
    """Muestra en pantalla cada formulario (hoja del Excel) como una tabla."""
    import pandas as pd
    st.markdown("#### Vista previa de los formularios")
    try:
        hojas = pd.read_excel(ruta, sheet_name=None, header=None, engine="openpyxl")
    except Exception as exc:
        st.error(f"No se pudo leer el archivo de formularios: {exc}")
        return
    nombres = list(hojas.keys())
    tabs = st.tabs(nombres)
    for tab, nombre in zip(tabs, nombres):
        with tab:
            df = hojas[nombre].fillna("")
            st.dataframe(df, use_container_width=True, hide_index=True,
                         height=420)
    if st.button("Cerrar vista previa"):
        st.session_state["mostrar_preview"] = False
        st.rerun()
