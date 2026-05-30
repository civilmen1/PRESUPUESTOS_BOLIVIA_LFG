"""Página de Exportación: Excel, PDF y JSON."""
from __future__ import annotations

import streamlit as st

from exporters.export_excel import exportar_excel
from exporters.export_json import exportar_json
from exporters.export_pdf import exportar_pdf
from ui.components import requiere_proyecto


def render(proyecto):
    st.title("📤 Exportación")
    if not requiere_proyecto(proyecto):
        return

    st.write(f"Proyecto: **{proyecto.nombre}**")
    c1, c2, c3 = st.columns(3)

    if c1.button("📊 Generar Excel", use_container_width=True):
        ruta = exportar_excel(proyecto.id)
        with open(ruta, "rb") as fh:
            st.download_button("⬇️ Descargar Excel", fh, file_name=ruta.name,
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet", use_container_width=True)

    if c2.button("📄 Generar PDF", use_container_width=True):
        ruta = exportar_pdf(proyecto.id)
        with open(ruta, "rb") as fh:
            st.download_button("⬇️ Descargar PDF", fh, file_name=ruta.name,
                               use_container_width=True)

    if c3.button("🧾 Generar JSON", use_container_width=True):
        ruta = exportar_json(proyecto.id)
        with open(ruta, "rb") as fh:
            st.download_button("⬇️ Descargar JSON", fh, file_name=ruta.name,
                               mime="application/json", use_container_width=True)

    st.caption("Las exportaciones incluyen trazabilidad técnica y de cotización.")
