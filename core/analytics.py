"""Integracion de Google Analytics 4 (GA4) en Streamlit.

Streamlit ejecuta los componentes HTML dentro de un iframe y filtra los <script>
del cuerpo principal, por lo que el tag estandar de GA no funciona directamente.
La tecnica usada aqui inyecta gtag.js en el documento PADRE (la pagina real)
desde el iframe del componente, una sola vez.

Se activa solo si settings.GA_MEASUREMENT_ID esta configurado (variable de
entorno GA_MEASUREMENT_ID, ej. "G-XXXXXXXXXX").
"""
from __future__ import annotations

from config import settings


def inyectar_ga() -> None:
    """Carga GA4 en la pagina si hay ID configurado (una vez por sesion)."""
    mid = settings.GA_MEASUREMENT_ID
    if not mid:
        return
    import streamlit as st

    if st.session_state.get("_ga_cargado"):
        return
    st.session_state["_ga_cargado"] = True

    import streamlit.components.v1 as components

    codigo = """
    <script>
    (function() {
      try {
        var id = "%s";
        var doc = window.parent.document;
        if (doc.getElementById('ga-gtag-src')) return;
        var s = doc.createElement('script');
        s.id = 'ga-gtag-src';
        s.async = true;
        s.src = 'https://www.googletagmanager.com/gtag/js?id=' + id;
        doc.head.appendChild(s);
        var s2 = doc.createElement('script');
        s2.id = 'ga-gtag-init';
        s2.text = "window.dataLayer=window.dataLayer||[];"
          + "function gtag(){dataLayer.push(arguments);}"
          + "gtag('js', new Date());"
          + "gtag('config', '" + id + "');";
        doc.head.appendChild(s2);
      } catch (e) { /* sin analitica si el navegador bloquea el acceso */ }
    })();
    </script>
    """ % mid
    components.html(codigo, height=0, width=0)
