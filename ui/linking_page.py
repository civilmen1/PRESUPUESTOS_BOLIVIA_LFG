"""Página de Vinculación técnica: ítem  sección, con score y validación."""
from __future__ import annotations

import streamlit as st

from config import settings
from core import repositories
from core.info_extractor import extraer_info
from core.semantic_matcher import SemanticMatcher
from ui.components import requiere_proyecto


def _extraer(descripcion, spec, item_id):
    """Usa el extractor con IA si está habilitado y hay key; si no, el offline."""
    if settings.USAR_LLM:
        try:
            from core.llm_extractor import extraer_info_inteligente, hay_llm
            if hay_llm():
                return extraer_info_inteligente(descripcion, spec, item_id)
        except Exception:
            pass
    return extraer_info(descripcion, spec, item_id)


def render(proyecto):
    st.title(" Vinculación técnica (ítem  especificación)")
    if not requiere_proyecto(proyecto):
        return

    # Estado del extractor (offline vs IA)
    if settings.USAR_LLM:
        try:
            from core.llm_extractor import proveedores_disponibles
            disp = proveedores_disponibles()
            activos = [k for k, v in disp.items() if v]
            if activos:
                st.success(" Extracción con IA activa: " + ", ".join(activos))
            else:
                st.warning("USAR_LLM activo pero sin proveedor disponible. Para "
                           "LLM **local gratis**: instala Ollama, ejecuta "
                           "`ollama pull llama3.1` y pon USAR_OLLAMA=true en .env. "
                           "Mientras tanto se usa el extractor offline.")
        except Exception:
            pass

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

    st.caption(" Búsqueda jerárquica tipo IA: 1) localiza el **módulo** del "
               "ítem en el documento, 2) busca la **especificación del ítem** "
               "dentro de ese módulo. Los módulos solo agrupan y no se vinculan.")
    col1, col2 = st.columns([1, 1])
    top_k = col1.slider("Coincidencias por ítem", 1, 5, 3)
    if col2.button(" Ejecutar vinculación inteligente", type="primary"):
        matcher = SemanticMatcher(secciones)
        with st.spinner("Buscando módulo y especificación de cada ítem..."):
            for it in items_reales:
                repositories.borrar_vinculos_item(it.id)
                for v in matcher.buscar(it, top_k=top_k,
                                        modulo_nombre=modulos.get(it.id, "")):
                    repositories.guardar_vinculo(v)
        st.success("Vinculación completada.")
        st.rerun()

    # Resumen de validación del proyecto
    total = len(items_reales)
    validados_tot = sum(1 for it in items_reales if it.validado_tecnico)
    st.progress(validados_tot / total if total else 0.0,
                text=f"Ítems validados técnicamente: {validados_tot} / {total}")
    if validados_tot < total:
        st.warning(" La cotización y los precios unitarios **no podrán "
                   "generarse** hasta validar técnicamente todos los ítems.")
    else:
        st.success(" Todos los ítems están validados. Ya puedes pasar a "
                   "**APUs / Cotización**.")
    st.divider()

    modulo_actual = None
    for it in items_reales:
        mod = modulos.get(it.id, "")
        if mod and mod != modulo_actual:
            modulo_actual = mod
            st.markdown(f"###  {mod}")
        _render_item(it)


def _render_item(it):
    """Muestra un ítem con sus tablas editables (material/MO/equipo) y validación.

    Para que el ítem NO se contraiga al validar, se mantiene abierto vía
    session_state y se evita st.rerun() en las ediciones.
    """
    estado = "" if it.validado_tecnico else "⏳"
    abierto_key = f"open_{it.id}"
    expandido = st.session_state.get(abierto_key, not it.validado_tecnico)
    with st.expander(f"{estado} {it.numero or ''} {it.descripcion[:60]}",
                     expanded=expandido):
        spec = repositories.texto_tecnico_item(it.id)
        info = _extraer(it.descripcion, spec, it.id)

        if info.medicion:
            st.caption(" Medición/pago: " + info.medicion[:200])
        if info.normas:
            st.caption(" Normas: " + ", ".join(info.normas))

        # Si el ítem no tiene recursos aún, armarlos desde el análisis
        recursos = repositories.listar_recursos(it.id)
        if not recursos:
            if st.button(" Armar recursos desde la especificación",
                         key=f"armar_{it.id}", type="primary"):
                from core import apu_engine
                apu_engine.armar_recursos_desde_analisis(it)
                st.session_state[abierto_key] = True
                st.rerun()
            st.caption("Genera el armado para revisar materiales, mano de obra "
                       "y equipo según las especificaciones.")
            return

        st.markdown("**Resultado del análisis (editable). Verifica que cumpla "
                    "las especificaciones técnicas:**")
        _tabla_recursos(it, recursos, "material", " Materiales",
                        "Unidad (kg, m3, pza, glb...)")
        _tabla_recursos(it, recursos, "mano_obra", " Mano de obra",
                        "Unidad (hora, día, mes)")
        _tabla_recursos(it, recursos, "equipo", " Equipo / herramienta",
                        "Unidad (hora, día, mes)")

        with st.popover(" Ver texto técnico / alcance"):
            st.write(info.alcance or "—")
            if spec:
                st.divider()
                st.caption(spec[:1500])

        # Validación armada final (no contrae el ítem)
        st.divider()
        val = st.checkbox(
            " Validar técnicamente este ítem (cumple las especificaciones)",
            value=bool(it.validado_tecnico), key=f"valtec_{it.id}")
        if val != bool(it.validado_tecnico):
            repositories.set_validacion_tecnica(it.id, val)
            st.session_state[abierto_key] = True  # mantener abierto
            st.rerun()


def _tabla_recursos(it, recursos, tipo, titulo, ayuda_unidad):
    """Tabla editable de recursos de un tipo (material / mano_obra / equipo)."""
    import pandas as pd
    from models.apu_resource import RecursoAPU

    st.markdown(f"**{titulo}**")
    filas = [{"id": r.id, "Descripción": r.descripcion, "Unidad": r.unidad,
              "Cantidad": r.cantidad_apu} for r in recursos if r.tipo == tipo]
    df = pd.DataFrame(filas) if filas else pd.DataFrame(
        columns=["id", "Descripción", "Unidad", "Cantidad"])
    edit = st.data_editor(
        df, key=f"ed_{tipo}_{it.id}", num_rows="dynamic",
        use_container_width=True, hide_index=True,
        column_config={
            "id": None,
            "Unidad": st.column_config.TextColumn(help=ayuda_unidad),
            "Cantidad": st.column_config.NumberColumn(format="%.4f"),
        })
    if st.button(f" Guardar {titulo}", key=f"save_{tipo}_{it.id}"):
        ids_previos = {r.id for r in recursos if r.tipo == tipo}
        ids_vistos = set()
        for _, fila in edit.iterrows():
            desc = str(fila.get("Descripción") or "").strip()
            if not desc:
                continue
            rid = fila.get("id")
            cant = float(fila.get("Cantidad") or 0)
            unidad = str(fila.get("Unidad") or "")
            if pd.notna(rid) and int(rid) in ids_previos:
                r = next(x for x in recursos if x.id == int(rid))
                r.descripcion, r.unidad, r.cantidad_apu = desc, unidad, cant
                r.rendimiento = cant
                repositories.actualizar_recurso(r)
                ids_vistos.add(int(rid))
            else:
                repositories.guardar_recurso(RecursoAPU(
                    item_id=it.id, tipo=tipo, descripcion=desc, unidad=unidad,
                    cantidad_apu=cant, rendimiento=cant,
                    fuente_precio="sin_precio"))
        for rid in ids_previos - ids_vistos:
            repositories.borrar_recurso(rid)
        st.session_state[f"open_{it.id}"] = True
        st.success(f"{titulo} guardado.")
        st.rerun()
