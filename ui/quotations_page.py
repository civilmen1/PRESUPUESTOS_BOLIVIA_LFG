"""Página de Cotizaciones: estado por recurso, fuente, vigencia, proveedor."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import repositories
from ui.components import badge_nivel, requiere_proyecto


def render(proyecto):
    st.title("💲 Cotizaciones")
    if not requiere_proyecto(proyecto):
        return

    cotizaciones = repositories.listar_cotizaciones(proyecto.id)
    if not cotizaciones:
        st.info("Aún no hay cotizaciones. Genera APUs para producir cotizaciones.")
        return

    rows = []
    for c in cotizaciones:
        rows.append({
            "Recurso": c.get("recurso_desc") or c.get("descripcion"),
            "Nivel": badge_nivel(c.get("nivel_busqueda", -1)),
            "Precio adoptado": c.get("precio_adoptado"),
            "Moneda": c.get("moneda"),
            "Proveedor": c.get("proveedor_nombre") or "-",
            "Estado": c.get("estado"),
            "Vigencia (días)": c.get("vigencia_dias"),
            "Fecha": c.get("fecha_consulta"),
            "URL": c.get("url_fuente") or "",
            "Observaciones": c.get("observaciones") or "",
        })
    df = pd.DataFrame(rows)

    c1, c2 = st.columns(2)
    niveles = ["(todos)"] + sorted(df["Nivel"].unique().tolist())
    estados = ["(todos)"] + sorted(df["Estado"].dropna().unique().tolist())
    fnivel = c1.selectbox("Filtrar por nivel", niveles)
    festado = c2.selectbox("Filtrar por estado", estados)
    if fnivel != "(todos)":
        df = df[df["Nivel"] == fnivel]
    if festado != "(todos)":
        df = df[df["Estado"] == festado]

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    c3, c4, c5 = st.columns(3)
    c3.metric("Total cotizaciones", len(cotizaciones))
    c4.metric("Obtenidas",
              sum(1 for c in cotizaciones if c.get("estado") == "obtenida"))
    c5.metric("Pendientes (email)",
              sum(1 for c in cotizaciones if c.get("estado") == "pendiente"))
