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
            nombre = st.text_input("Nombre del proyecto")
            entidad = st.text_input("Entidad convocante")
            proponente = st.text_input("Nombre de la empresa proponente")
            region = st.selectbox("Región (departamento)", [
                "La Paz", "Santa Cruz", "Cochabamba", "Oruro", "Potosí",
                "Tarija", "Chuquisaca", "Beni", "Pando"])
            colm1, colm2 = st.columns(2)
            moneda = colm1.selectbox("Moneda", ["BOB", "USD"],
                                     help="Bolivianos o Dólares americanos")
            tipo_cambio = colm2.number_input(
                "Tipo de cambio (Bs por 1 $us)", 1.0, 100.0, 6.96, 0.01,
                help="Cotización del dólar. Por defecto 6.96 Bs/$us.")

            st.caption("**Representante legal (pie de firma)**")
            rep_legal = st.text_input("Nombre del representante legal")
            ci_rep = st.text_input("C.I. del representante legal")

            st.caption("**Plazo y anticipo (A-8 / B-5)**")
            colp1, colp2 = st.columns(2)
            plazo = colp1.number_input("Plazo de obra (días)", 1, 3650, 180, 1)
            solicita_ant = colp2.checkbox("Solicita anticipo")
            pct_ant = st.number_input(
                "Porcentaje de anticipo (%)", 0.0, 100.0, 20.0, 1.0,
                disabled=not solicita_ant,
                help="Se aplica solo si 'Solicita anticipo' está marcado") / 100.0

            st.caption("**Estructura NB-SABS (DS 0181) — Formulario B-2**")
            col1, col2 = st.columns(2)
            bs = col1.number_input("Beneficios sociales", 0.0, 2.0, 0.55, 0.01,
                                   help="% sobre la mano de obra")
            iva_mo = col2.number_input("IVA mano de obra", 0.0, 1.0, 0.1494, 0.0001,
                                       format="%.4f")
            col3, col4 = st.columns(2)
            herr = col3.number_input("Herramientas", 0.0, 1.0, 0.05, 0.01,
                                     help="% sobre mano de obra")
            gg = col4.number_input("Gastos generales", 0.0, 1.0, 0.10, 0.01,
                                   help="% sobre costo directo")
            col5, col6 = st.columns(2)
            ut = col5.number_input("Utilidad", 0.0, 1.0, 0.10, 0.01)
            it = col6.number_input("Impuestos IT", 0.0, 1.0, 0.0309, 0.0001,
                                   format="%.4f")

            if st.form_submit_button("Crear proyecto") and nombre:
                pid = repositories.crear_proyecto(Proyecto(
                    nombre=nombre, region=region, moneda=moneda,
                    tipo_cambio=tipo_cambio,
                    entidad=entidad, proponente=proponente,
                    representante_legal=rep_legal, ci_representante=ci_rep,
                    plazo_dias=int(plazo), solicita_anticipo=solicita_ant,
                    porcentaje_anticipo=pct_ant,
                    factor_beneficios_sociales=bs, factor_iva_mano_obra=iva_mo,
                    factor_herramientas=herr, factor_gastos_generales=gg,
                    factor_utilidad_sabs=ut, factor_it=it))
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
