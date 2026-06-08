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

    # Estado del extractor (siempre visible para evitar confusiones).
    try:
        from core.llm_extractor import proveedores_disponibles
        disp = proveedores_disponibles() if settings.USAR_LLM else {}
        activos = [k for k, v in disp.items() if v]
        if settings.USAR_LLM and activos:
            st.success("Generacion de recursos con IA activa (" +
                       ", ".join(activos) + "). Los recursos se generan segun el "
                       "contexto de cada item; mano de obra y equipo en horas.")
        else:
            st.warning("IA NO activa: se usan plantillas por reglas (resultados "
                       "genericos). Para activar la IA configura GEMINI_API_KEY y "
                       "USAR_LLM=true. Estado actual: USAR_LLM=" +
                       str(settings.USAR_LLM) + ", proveedores=" +
                       (", ".join(activos) if activos else "ninguno") + ".")
    except Exception as exc:
        st.warning(f"No se pudo determinar el estado de la IA: {exc}")

    # Prueba directa de la IA: confirma que el motor ACTIVO responde (Ollama,
    # Gemini u OpenAI) y, si falla, explica el motivo exacto.
    with st.expander("Probar la IA (diagnostico)"):
        if st.button("Ejecutar prueba de IA"):
            from core.llm_extractor import diagnosticar_ia
            with st.spinner("Diagnosticando el motor de IA..."):
                d = diagnosticar_ia()
            prov = d.get("proveedor", "")
            if d["ok"]:
                st.success(f"[{prov}] {d['mensaje']}")
            else:
                st.error(f"[{prov}] {d['mensaje']}")
                if d.get("modelos"):
                    st.info("Modelos disponibles para tu clave (usa uno en "
                            "GEMINI_MODEL):")
                    st.code("\n".join(d["modelos"]))

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

    # Purga: borra los recursos/precios viejos para regenerar desde cero.
    with st.expander("Purgar y regenerar desde cero (si hay generaciones malas)"):
        st.caption("Borra todos los recursos, precios, cotizaciones y "
                   "validaciones del proyecto (NO borra los ítems ni los "
                   "documentos). Útil para descartar resultados genéricos viejos "
                   "y regenerar todo con la versión actual (IA).")
        confirmar = st.checkbox("Confirmo que deseo purgar este proyecto")
        c_p1, c_p2 = st.columns(2)
        if c_p1.button("Purgar y regenerar (recomendado)", type="primary",
                       disabled=not confirmar):
            resumen = repositories.purgar_apu_proyecto(proyecto.id)
            st.success(f"Purgado: {resumen['recursos']} recursos y "
                       f"{resumen['resultados']} resultados de "
                       f"{resumen['items']} ítems. Regenerando todo desde cero...")
            # Arranca la vinculacion/armado resumible automaticamente.
            st.session_state["vinc_activa"] = True
            st.session_state["vinc_intentados"] = []
            st.rerun()
        if c_p2.button("Solo purgar", disabled=not confirmar):
            resumen = repositories.purgar_apu_proyecto(proyecto.id)
            st.success(f"Purgado: {resumen['recursos']} recursos y "
                       f"{resumen['resultados']} resultados de "
                       f"{resumen['items']} ítems.")
            st.rerun()

    col1, col2 = st.columns([1, 1])
    top_k = col1.slider("Coincidencias por ítem", 1, 5, 3)
    st.session_state["vinc_top_k"] = top_k
    if col2.button("Ejecutar vinculación inteligente", type="primary"):
        # Arranca el proceso resumible por lotes (no un bucle gigante).
        st.session_state["vinc_activa"] = True
        st.session_state["vinc_intentados"] = []
        st.rerun()

    if st.session_state.get("vinc_activa"):
        _ejecutar_vinculacion_por_lotes(items_reales, secciones, modulos)

    # Resumen de validación del proyecto
    total = len(items_reales)
    validados_tot = sum(1 for it in items_reales if it.validado_tecnico)
    st.progress(validados_tot / total if total else 0.0,
                text=f"Ítems validados técnicamente: {validados_tot} / {total}")
    if validados_tot < total:
        st.warning("Hay ítems sin validar. Revisa sus tablas (materiales, mano "
                   "de obra y equipo) y valida los pendientes para poder cotizar.")
    else:
        st.success("Todos los ítems están validados. Ya puedes pasar a "
                   "Cotización y generación de precios unitarios.")
    st.divider()

    modulo_actual = None
    for it in items_reales:
        mod = modulos.get(it.id, "")
        if mod and mod != modulo_actual:
            modulo_actual = mod
            st.markdown(f"###  {mod}")
        _render_item(it)


def _ejecutar_vinculacion_por_lotes(items_reales, secciones, modulos):
    """Procesa la vinculación en tandas pequeñas y RESUMIBLES.

    Cada tanda procesa pocos ítems, los guarda y refresca la UI. Si la sesión se
    corta o el servidor se reinicia, los ítems ya armados quedan guardados y al
    volver a ejecutar continúa con los pendientes (no reinicia todo).
    """
    from core import apu_engine

    top_k = st.session_state.get("vinc_top_k", 3)
    intentados = set(st.session_state.get("vinc_intentados", []))
    # Pendientes: ítems sin validar que no se hayan intentado en esta corrida.
    pendientes = [it for it in items_reales
                  if not it.validado_tecnico and it.id not in intentados]
    total = len(items_reales) or 1
    hechos = sum(1 for it in items_reales if it.validado_tecnico)

    if not pendientes:
        st.session_state["vinc_activa"] = False
        st.success("Vinculación completada. Los ítems quedaron armados y "
                   "validados. Revisa y modifica los que desees.")
        st.rerun()
        return

    c1, c2 = st.columns([4, 1])
    c1.progress(hechos / total,
                text=f"Vinculando con IA: {hechos}/{total} ítems. No cierres "
                     "esta página; si se corta, continúa al volver a ejecutar.")
    if c2.button("Detener"):
        st.session_state["vinc_activa"] = False
        st.info("Vinculación detenida. Puedes reanudarla cuando quieras; "
                "continuará con los ítems pendientes.")
        st.rerun()
        return

    matcher = SemanticMatcher(secciones)
    lote = pendientes[:max(1, settings.VINCULACION_LOTE)]
    for it in lote:
        try:
            repositories.borrar_vinculos_item(it.id)
            for v in matcher.buscar(it, top_k=top_k,
                                    modulo_nombre=modulos.get(it.id, "")):
                repositories.guardar_vinculo(v)
            apu_engine.armar_recursos_desde_analisis(it)
            repositories.set_validacion_tecnica(it.id, True)
        except Exception:
            # No frenar toda la corrida por un ítem; se marca intentado para no
            # reprocesarlo en bucle y se sigue con el resto.
            pass
        intentados.add(it.id)
    st.session_state["vinc_intentados"] = list(intentados)
    st.rerun()


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
        # Si el ítem no tiene recursos aún, armarlos desde el análisis (IA).
        recursos = repositories.listar_recursos(it.id)
        if not recursos:
            st.caption("Aún no se armaron los recursos de este ítem.")
            if st.button("Armar recursos con IA", key=f"armar_{it.id}",
                         type="primary"):
                from core import apu_engine
                with st.spinner("Generando recursos con IA segun el contexto..."):
                    apu_engine.armar_recursos_desde_analisis(it)
                st.session_state[abierto_key] = True
                st.rerun()
            st.caption("Genera el armado para revisar materiales, mano de obra "
                       "y equipo según las especificaciones.")
            return

        # Indicador de origen de los recursos (IA o plantilla).
        es_ia = any("hora" in (r.unidad or "").lower()
                    for r in recursos if r.tipo in ("mano_obra", "equipo"))
        if es_ia:
            st.caption("Recursos generados con IA (mano de obra y equipo en horas).")
        else:
            st.warning("Estos recursos parecen genericos (plantilla, no IA). Si "
                       "la IA esta activa, pulsa 'Rearmar con IA' abajo para "
                       "regenerarlos segun el contexto del item.")
            if st.button("Rearmar con IA", key=f"rearmar_{it.id}"):
                from core import apu_engine
                with st.spinner("Regenerando con IA..."):
                    apu_engine.armar_recursos_desde_analisis(it)
                st.session_state[abierto_key] = True
                st.rerun()

        st.markdown("**Resultado del análisis (editable). Verifica que cumpla "
                    "las especificaciones técnicas:**")
        _tabla_recursos(it, recursos, "material", "Materiales",
                        "Unidad (kg, m3, pza, glb...)")
        _tabla_recursos(it, recursos, "mano_obra", "Mano de obra",
                        "Unidad (hora, día, mes)")
        _tabla_recursos(it, recursos, "equipo", "Equipo / herramienta",
                        "Unidad (hora, día, mes)")

        spec = repositories.texto_tecnico_item(it.id)
        if spec:
            with st.popover("Ver texto técnico vinculado"):
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
