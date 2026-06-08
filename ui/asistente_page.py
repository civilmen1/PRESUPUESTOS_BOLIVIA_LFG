"""Asistente IA con tool-calling: conversa y consulta TUS datos reales.

El asistente puede buscar en el banco, generar APUs, consultar precios y los
items del proyecto activo llamando herramientas (no inventa)."""
from __future__ import annotations

import streamlit as st

from core import asistente


def render(proyecto):
    st.title("Asistente de estimacion (IA)")

    if not asistente.disponible():
        st.warning("El asistente necesita IA activa: Ollama local "
                   "(USAR_OLLAMA=true) o una GROQ_API_KEY configurada.")
        return

    st.caption("Pregunta en lenguaje natural. El asistente consulta tu banco, "
               "precios y proyecto con herramientas reales. Ej.: \"busca un APU "
               "de hormigon armado y dime su mano de obra\", \"genera el APU de "
               "pintura latex en muros, unidad m2\", \"cuantos APU hay en el "
               "banco\".")

    historial = st.session_state.setdefault("asist_hist", [])

    c1, c2 = st.columns([4, 1])
    if c2.button("Limpiar conversacion", use_container_width=True):
        st.session_state["asist_hist"] = []
        st.rerun()

    # Historial visible
    for msg in historial:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg["content"])

    pregunta = st.chat_input("Escribe tu consulta...")
    if not pregunta:
        return

    historial.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando tus datos con IA..."):
            res = asistente.chat(historial, proyecto=proyecto)
        st.markdown(res["respuesta"])
        if res.get("herramientas"):
            st.caption("Herramientas usadas: " + ", ".join(res["herramientas"]))

    historial.append({"role": "assistant", "content": res["respuesta"]})
    st.session_state["asist_hist"] = historial
