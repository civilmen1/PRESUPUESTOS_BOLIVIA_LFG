"""Página de Vinculación técnica: ítem ↔ sección, con score y validación."""
from __future__ import annotations

import streamlit as st

from core import repositories
from core.info_extractor import extraer_info
from core.semantic_matcher import SemanticMatcher
from ui.components import requiere_proyecto


def render(proyecto):
    st.title("🔗 Vinculación técnica (ítem ↔ especificación)")
    if not requiere_proyecto(proyecto):
        return

    items = repositories.listar_items(proyecto.id)
    secciones = repositories.listar_secciones(proyecto.id)
    modulos = repositories.nombres_modulos_de_items(proyecto.id)
    if not items:
        st.info("Carga ítems primero.")
        return
    if not secciones:
        st.info("Carga documentos técnicos primero para poder vincular.")
        return

    # Los módulos solo agrupan: no se vinculan ni se analizan.
    items_reales = [it for it in items if not it.es_modulo]

    st.caption("🔎 Búsqueda jerárquica tipo IA: 1) localiza el **módulo** del "
               "ítem en el documento, 2) busca la **especificación del ítem** "
               "dentro de ese módulo. Los módulos solo agrupan y no se vinculan.")
    col1, col2 = st.columns([1, 1])
    top_k = col1.slider("Coincidencias por ítem", 1, 5, 3)
    if col2.button("⚙️ Ejecutar vinculación inteligente", type="primary"):
        matcher = SemanticMatcher(secciones)
        with st.spinner("Buscando módulo y especificación de cada ítem..."):
            for it in items_reales:
                repositories.borrar_vinculos_item(it.id)
                for v in matcher.buscar(it, top_k=top_k,
                                        modulo_nombre=modulos.get(it.id, "")):
                    repositories.guardar_vinculo(v)
        st.success("Vinculación completada.")
        st.rerun()

    st.divider()
    modulo_actual = None
    for it in items_reales:
        mod = modulos.get(it.id, "")
        if mod and mod != modulo_actual:
            modulo_actual = mod
            st.markdown(f"### 📁 {mod}")
        vinculos = repositories.listar_vinculos(it.id)
        encabezado = f"{it.numero or ''} {it.descripcion[:60]}"
        validados = sum(1 for v in vinculos if v.validado_manual)
        with st.expander(f"📌 {encabezado}  ·  {len(vinculos)} vínculos "
                         f"({validados} validados)"):
            if not vinculos:
                st.caption("Sin vínculos. Ejecuta la vinculación inteligente.")
                continue

            # --- Información técnica EXTRAÍDA del documento para este ítem ---
            spec = repositories.texto_tecnico_item(it.id)
            info = extraer_info(it.descripcion, spec, it.id)
            st.markdown("**🧠 Información cargada de la especificación:**")
            ca, cb, cc = st.columns(3)
            ca.markdown("**Materiales**")
            ca.write(", ".join(info.materiales) or "—")
            cb.markdown("**Mano de obra**")
            cb.write(", ".join(info.mano_obra) or "—")
            cc.markdown("**Equipo**")
            cc.write(", ".join(info.equipo) or "—")
            if info.normas:
                st.caption("📐 Normas: " + ", ".join(info.normas))
            if info.medicion:
                st.caption("📏 Medición/pago: " + info.medicion[:200])
            if info.alcance:
                with st.popover("📄 Ver alcance / texto técnico"):
                    st.write(info.alcance)
            st.divider()

            st.markdown("**Secciones del documento vinculadas** "
                        "(valida las correctas):")
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
