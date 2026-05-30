"""Página de Vinculación técnica: ítem ↔ sección, con score y validación."""
from __future__ import annotations

import streamlit as st

from core import repositories
from core.semantic_matcher import SemanticMatcher
from ui.components import requiere_proyecto


def render(proyecto):
    st.title("🔗 Vinculación técnica (ítem ↔ especificación)")
    if not requiere_proyecto(proyecto):
        return

    items = repositories.listar_items(proyecto.id)
    secciones = repositories.listar_secciones(proyecto.id)
    if not items:
        st.info("Carga ítems primero.")
        return
    if not secciones:
        st.info("Carga documentos técnicos primero para poder vincular.")
        return

    col1, col2 = st.columns([1, 1])
    top_k = col1.slider("Coincidencias por ítem", 1, 5, 3)
    if col2.button("⚙️ Ejecutar vinculación semántica", type="primary"):
        matcher = SemanticMatcher(secciones)
        with st.spinner("Calculando similitud..."):
            for it in items:
                repositories.borrar_vinculos_item(it.id)
                for v in matcher.buscar(it, top_k=top_k):
                    repositories.guardar_vinculo(v)
        st.success("Vinculación completada.")
        st.rerun()

    st.divider()
    for it in items:
        vinculos = repositories.listar_vinculos(it.id)
        encabezado = f"{it.numero or ''} {it.descripcion[:60]}"
        validados = sum(1 for v in vinculos if v.validado_manual)
        with st.expander(f"📌 {encabezado}  ·  {len(vinculos)} vínculos "
                         f"({validados} validados)"):
            if not vinculos:
                st.caption("Sin vínculos. Ejecuta la vinculación semántica.")
                continue
            for v in vinculos:
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{v.titulo_seccion}** — score "
                            f"`{v.score_confianza:.3f}`")
                c1.caption(v.extracto)
                marcado = c2.checkbox("Validar", value=v.validado_manual,
                                      key=f"val_{v.id}")
                if marcado != v.validado_manual:
                    v.validado_manual = marcado
                    repositories.borrar_vinculos_item(it.id)
                    for vv in vinculos:
                        repositories.guardar_vinculo(vv)
                    st.rerun()
