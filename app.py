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
from ui import (apu_page, aportar_page, auth_page, banco_page, dashboard,
                documents_page, export_page, items_page, linking_page,
                provider_portal, quotations_page, suppliers_page)
from ui.components import selector_proyecto


@st.cache_resource
def _inicializar() -> bool:
    """Inicializa logging y base de datos una sola vez por sesión."""
    setup_logging()
    init_db()
    return True


# Perfil 1: Contratistas / Entidades  generación de APUs con IA
PAGINAS_CONTRATISTA = {
    "PRESUPUESTO BOLIVIA con IA": dashboard.render,
    " Ítems": items_page.render,
    " Documentos técnicos": documents_page.render,
    " Vinculación técnica": linking_page.render,
    " APUs": apu_page.render,
    " Cotizaciones": quotations_page.render,
    " Banco de APU": banco_page.render,
    " Proveedores": suppliers_page.render,
    " Exportación": export_page.render,
}


def _pantalla_perfil() -> None:
    """Pantalla inicial de selección de perfil de acceso."""
    st.markdown("<h1 style='text-align:center'>APU Bolivia Generator</h1>",
                unsafe_allow_html=True)
    if st.session_state.pop("empresa_verificada", False):
        st.success("Empresa verificada correctamente. Ya puedes iniciar sesion "
                   "seleccionando tu perfil.")
    st.markdown("<p style='text-align:center'>Selecciona tu perfil de acceso</p>",
                unsafe_allow_html=True)
    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(" Contratistas y Entidades")
        st.caption("Constructoras, consultoras, empresas privadas y entidades "
                   "públicas. Genera Análisis de Precios Unitarios con IA, "
                   "vinculación de especificaciones y formularios oficiales.")
        if st.button("Ingresar como Contratista / Entidad", type="primary",
                     use_container_width=True):
            st.session_state["perfil"] = "contratista"
            st.rerun()
    with c2:
        st.subheader(" Proveedores de Materiales")
        st.caption("Ferreterías, distribuidores y proveedores. Recibe "
                   "solicitudes de cotización, registra tus precios y únete a la "
                   "base de precios de materiales más grande de Bolivia.")
        if st.button("Ingresar como Proveedor", use_container_width=True):
            st.session_state["perfil"] = "proveedor"
            st.rerun()
    st.write("")
    st.divider()
    cc1, cc2, cc3 = st.columns([1, 2, 1])
    with cc2:
        st.markdown("<p style='text-align:center'>¿Solo quieres aportar tus "
                    "precios unitarios? Sube tus Formularios B-2 sin necesidad "
                    "de cuenta.</p>", unsafe_allow_html=True)
        if st.button("Aportar al banco de precios (sin cuenta)",
                     use_container_width=True):
            st.query_params["aportar"] = "1"
            st.rerun()


_CSS = """
<style>
  .stApp { background: #FFFFFF; }
  /* Botones mas sobrios */
  .stButton > button {
      border-radius: 6px;
      border: 1px solid #1F3B57;
      font-weight: 600;
  }
  /* Encabezados con color corporativo */
  h1, h2, h3 { color: #1F3B57; }
  /* Barra lateral con fondo suave */
  section[data-testid="stSidebar"] { background: #F1F4F8; }
  /* Tarjetas de metricas */
  div[data-testid="stMetric"] {
      background: #F7F9FC;
      border: 1px solid #E1E8F0;
      border-radius: 8px;
      padding: 12px;
  }
</style>
"""


def main() -> None:
    st.set_page_config(page_title=settings.APP_NAME, page_icon=":construction:",
                       layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    _inicializar()

    # Google Analytics 4 (si GA_MEASUREMENT_ID esta configurado en el entorno).
    from core import analytics
    analytics.inyectar_ga()

    # Ruta PUBLICA de aportes al banco (enlace propio: ?aportar=1).
    # Cualquier persona puede subir Formularios B-2 sin cuenta ni login.
    if str(st.query_params.get("aportar", "")).lower() in ("1", "true", "si"):
        aportar_page.render()
        return

    perfil = st.session_state.get("perfil")
    if not perfil:
        _pantalla_perfil()
        return

    st.sidebar.title(" APU Bolivia Generator")
    st.sidebar.caption(f"v{settings.APP_VERSION}")
    if st.sidebar.button(" Cambiar de perfil", use_container_width=True):
        st.session_state.pop("perfil", None)
        st.rerun()
    st.sidebar.divider()

    # Ambos perfiles requieren login con cuenta verificada.
    usuario = st.session_state.get("usuario")
    if not usuario:
        auth_page.render_login(perfil=perfil)
        return

    if perfil == "proveedor":
        st.sidebar.success(f" {usuario.nombre_empresa}")
        st.sidebar.caption(usuario.email)
        if st.sidebar.button(" Cerrar sesión", use_container_width=True):
            st.session_state.pop("usuario", None)
            st.rerun()
        provider_portal.render(usuario)
        return

    st.sidebar.success(f" {usuario.nombre_empresa}")
    st.sidebar.caption(f"{usuario.email}")
    if usuario.nit_verificado:
        st.sidebar.caption(f"SEPREC verificado: {usuario.seprec}")
    if st.sidebar.button(" Cerrar sesión", use_container_width=True):
        st.session_state.pop("usuario", None)
        st.rerun()
    st.sidebar.divider()

    proyecto = selector_proyecto(usuario)
    st.sidebar.divider()
    seleccion = st.sidebar.radio("Navegación", list(PAGINAS_CONTRATISTA.keys()))

    st.sidebar.divider()
    # Estado de la IA, visible siempre tras iniciar sesion.
    try:
        from core.llm_extractor import proveedores_disponibles
        disp = proveedores_disponibles() if settings.USAR_LLM else {}
        activos = [k for k, v in disp.items() if v]
        if settings.USAR_LLM and activos:
            st.sidebar.success("IA activa: " + ", ".join(activos))
        else:
            st.sidebar.error(
                "IA NO activa (USAR_LLM=" + str(settings.USAR_LLM) +
                ", proveedores=" + (", ".join(activos) if activos else "ninguno")
                + ")")
    except Exception:
        pass
    modo_email = " real" if not settings.EMAIL_DRY_RUN else " simulado"
    modo_web = " real" if not settings.SCRAPER_DRY_RUN else " simulado"
    st.sidebar.caption(f"Email: {modo_email}  ·  Web: {modo_web}")

    PAGINAS_CONTRATISTA[seleccion](proyecto)


if __name__ == "__main__":
    main()
