"""APU Bolivia Generator — aplicación Streamlit principal.

Dos perfiles de acceso:
  1) Contratistas (constructoras, consultoras, empresas y entidades públicas):
     módulo completo de generación de APUs con IA.
  2) Proveedores de materiales: portal de solicitudes y respuesta de cotizaciones.

Ejecutar con:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from config import settings
from config.logging_config import setup_logging
from core.database import init_db
from ui import (apu_page, auth_page, dashboard, documents_page, export_page,
                items_page, linking_page, provider_portal, quotations_page,
                suppliers_page)
from ui.components import selector_proyecto


@st.cache_resource
def _inicializar() -> bool:
    """Inicializa logging y base de datos una sola vez por sesión."""
    setup_logging()
    init_db()
    return True


# Perfil 1: Contratistas / Entidades → generación de APUs con IA
PAGINAS_CONTRATISTA = {
    "📊 Dashboard": dashboard.render,
    "📋 Ítems": items_page.render,
    "📄 Documentos técnicos": documents_page.render,
    "🔗 Vinculación técnica": linking_page.render,
    "🧮 APUs": apu_page.render,
    "💲 Cotizaciones": quotations_page.render,
    "🏭 Proveedores": suppliers_page.render,
    "📤 Exportación": export_page.render,
}


def _pantalla_perfil() -> None:
    """Pantalla inicial de selección de perfil de acceso."""
    st.markdown("<h1 style='text-align:center'>🏗️ APU Bolivia Generator</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Selecciona tu perfil de acceso</p>",
                unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏢 Contratistas y Entidades")
        st.caption("Constructoras, consultoras, empresas privadas y entidades "
                   "públicas. Genera Análisis de Precios Unitarios con IA, "
                   "vinculación de especificaciones y formularios oficiales.")
        if st.button("Ingresar como Contratista / Entidad", type="primary",
                     use_container_width=True):
            st.session_state["perfil"] = "contratista"
            st.rerun()
    with c2:
        st.subheader("🏭 Proveedores de Materiales")
        st.caption("Ferreterías, distribuidores y proveedores. Recibe "
                   "solicitudes de cotización, registra tus precios y únete a la "
                   "base de precios de materiales más grande de Bolivia.")
        if st.button("Ingresar como Proveedor", use_container_width=True):
            st.session_state["perfil"] = "proveedor"
            st.rerun()


def main() -> None:
    st.set_page_config(page_title=settings.APP_NAME, page_icon="🏗️",
                       layout="wide")
    _inicializar()

    perfil = st.session_state.get("perfil")
    if not perfil:
        _pantalla_perfil()
        return

    st.sidebar.title("🏗️ APU Bolivia Generator")
    st.sidebar.caption(f"v{settings.APP_VERSION}")
    if st.sidebar.button("🔄 Cambiar de perfil", use_container_width=True):
        st.session_state.pop("perfil", None)
        st.rerun()
    st.sidebar.divider()

    if perfil == "proveedor":
        st.sidebar.info("Perfil: 🏭 Proveedor")
        provider_portal.render()
        return

    # Perfil contratista / entidad: requiere login con cuenta verificada.
    usuario = st.session_state.get("usuario")
    if not usuario:
        auth_page.render_login()
        return

    st.sidebar.success(f"🏢 {usuario.nombre_empresa}")
    st.sidebar.caption(f"{usuario.email}")
    if usuario.nit_verificado:
        st.sidebar.caption(f"✅ NIT verificado: {usuario.nit_razon_social or usuario.nit}")
    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state.pop("usuario", None)
        st.rerun()
    st.sidebar.divider()

    proyecto = selector_proyecto()
    st.sidebar.divider()
    seleccion = st.sidebar.radio("Navegación", list(PAGINAS_CONTRATISTA.keys()))

    st.sidebar.divider()
    modo_email = "🟢 real" if not settings.EMAIL_DRY_RUN else "🟡 simulado"
    modo_web = "🟢 real" if not settings.SCRAPER_DRY_RUN else "🟡 simulado"
    st.sidebar.caption(f"Email: {modo_email}  ·  Web: {modo_web}")

    PAGINAS_CONTRATISTA[seleccion](proyecto)


if __name__ == "__main__":
    main()
