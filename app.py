"""APU Bolivia Generator — aplicación Streamlit principal.

Ejecutar con:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from config import settings
from config.logging_config import setup_logging
from core.database import init_db
from ui import (apu_page, dashboard, documents_page, export_page, items_page,
                linking_page, quotations_page, suppliers_page)
from ui.components import selector_proyecto


@st.cache_resource
def _inicializar() -> bool:
    """Inicializa logging y base de datos una sola vez por sesión."""
    setup_logging()
    init_db()
    return True


PAGINAS = {
    "📊 Dashboard": dashboard.render,
    "📋 Ítems": items_page.render,
    "📄 Documentos técnicos": documents_page.render,
    "🔗 Vinculación técnica": linking_page.render,
    "🧮 APUs": apu_page.render,
    "💲 Cotizaciones": quotations_page.render,
    "🏭 Proveedores": suppliers_page.render,
    "📤 Exportación": export_page.render,
}


def main() -> None:
    st.set_page_config(page_title=settings.APP_NAME, page_icon="🏗️",
                       layout="wide")
    _inicializar()

    st.sidebar.title("🏗️ APU Bolivia Generator")
    st.sidebar.caption(f"v{settings.APP_VERSION}")

    proyecto = selector_proyecto()

    st.sidebar.divider()
    seleccion = st.sidebar.radio("Navegación", list(PAGINAS.keys()))

    st.sidebar.divider()
    modo_email = "🟢 real" if not settings.EMAIL_DRY_RUN else "🟡 simulado"
    modo_web = "🟢 real" if not settings.SCRAPER_DRY_RUN else "🟡 simulado"
    st.sidebar.caption(f"Email: {modo_email}  ·  Web: {modo_web}")

    PAGINAS[seleccion](proyecto)


if __name__ == "__main__":
    main()
