"""Componentes y utilidades compartidas de la interfaz Streamlit."""
from __future__ import annotations

import streamlit as st

from core import repositories
from models.project import Proyecto


def selector_proyecto() -> Proyecto | None:
    """Muestra en el sidebar el selector/creador de proyecto activo."""
    st.sidebar.header("📁 Proyecto")
    proyectos = repositories.listar_proyectos()
    opciones = {f"{p.id} · {p.nombre}": p.id for p in proyectos}

    seleccion = None
    if opciones:
        clave = st.sidebar.selectbox("Proyecto activo", list(opciones.keys()))
        seleccion = opciones[clave]
        st.session_state["proyecto_id"] = seleccion

    with st.sidebar.expander("➕ Nuevo proyecto"):
        with st.form("nuevo_proyecto", clear_on_submit=True):
            nombre = st.text_input("Nombre")
            region = st.selectbox("Región (departamento)", [
                "La Paz", "Santa Cruz", "Cochabamba", "Oruro", "Potosí",
                "Tarija", "Chuquisaca", "Beni", "Pando"])
            moneda = st.selectbox("Moneda", ["BOB", "USD"])
            col1, col2, col3 = st.columns(3)
            fi = col1.number_input("Indirectos", 0.0, 1.0, 0.10, 0.01)
            fu = col2.number_input("Utilidad", 0.0, 1.0, 0.10, 0.01)
            fim = col3.number_input("Impuestos", 0.0, 1.0, 0.0, 0.01)
            if st.form_submit_button("Crear proyecto") and nombre:
                pid = repositories.crear_proyecto(Proyecto(
                    nombre=nombre, region=region, moneda=moneda,
                    factor_indirectos=fi, factor_utilidad=fu, factor_impuestos=fim))
                st.session_state["proyecto_id"] = pid
                st.success(f"Proyecto '{nombre}' creado (id {pid}).")
                st.rerun()

    pid = st.session_state.get("proyecto_id")
    return repositories.obtener_proyecto(pid) if pid else None


def requiere_proyecto(proyecto) -> bool:
    if not proyecto:
        st.info("👉 Crea o selecciona un proyecto en la barra lateral para comenzar.")
        return False
    return True


def badge_nivel(nivel: int) -> str:
    return {0: "✍️ Manual", 1: "🗃️ BD Bolivia", 2: "🌐 Web",
            3: "✉️ Email", -1: "⛔ Sin precio"}.get(nivel, str(nivel))
