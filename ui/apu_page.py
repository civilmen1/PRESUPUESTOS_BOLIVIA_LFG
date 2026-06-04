"""Página de APUs: generación, desglose, edición y bloqueo de recursos."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import apu_engine, currency, repositories
from ui.components import badge_nivel, requiere_proyecto


def render(proyecto):
    st.title(" APUs — Análisis de Precios Unitarios")
    if not requiere_proyecto(proyecto):
        return

    items = repositories.listar_items(proyecto.id)
    if not items:
        st.info("Carga ítems primero.")
        return

    # Gate de validación técnica: no se cotiza sin validar los ítems.
    items_reales = [it for it in items if not it.es_modulo]
    sin_validar = [it for it in items_reales if not it.validado_tecnico]
    if sin_validar:
        st.error(f" Hay {len(sin_validar)} de {len(items_reales)} ítems sin "
                 "validar técnicamente. Ve a ** Vinculación técnica**, revisa "
                 "los recursos (material / mano de obra / equipo) de cada ítem y "
                 "márcalos como validados antes de cotizar y generar precios.")
        with st.expander("Ver ítems pendientes de validación"):
            for it in sin_validar:
                st.write(f"⏳ {it.numero or ''} {it.descripcion}")
        return

    st.success(" Todos los ítems están validados técnicamente.")
    st.subheader("Generación automática (cotizador jerárquico Bolivia)")
    c1, c2, c3 = st.columns(3)
    permitir_web = c1.checkbox("Nivel 2: búsqueda web", value=True)
    permitir_email = c2.checkbox("Nivel 3: solicitar por email", value=False)
    st.caption("Orden de cotización:  BD Bolivia   Web   Email")

    if c3.button(" Generar APUs de todos los ítems", type="primary"):
        prog = st.progress(0.0)
        for i, it in enumerate(items_reales):
            apu_engine.generar_apu_item(it, proyecto, permitir_web=permitir_web,
                                        permitir_email=permitir_email)
            prog.progress((i + 1) / len(items_reales))
        st.success("APUs generados.")
        st.rerun()

    _seccion_difusion(proyecto)

    st.divider()
    for it in items:
        recursos = repositories.listar_recursos(it.id)
        res = repositories.obtener_resultado(it.id)
        total = res.precio_unitario_total if res else 0
        pu_txt = currency.formatear(total, proyecto.moneda, proyecto)
        with st.expander(f" {it.numero or ''} {it.descripcion[:55]} — "
                         f"P.U. {pu_txt}"):
            cga, cgb = st.columns([1, 1])
            if cga.button(" Recotizar (mantiene recursos)", key=f"regen_{it.id}"):
                apu_engine.generar_apu_item(it, proyecto, permitir_web=permitir_web,
                                            permitir_email=permitir_email,
                                            reusar_recursos=True)
                st.rerun()

            if not recursos:
                st.caption("Sin recursos. Genera el APU.")
                continue

            df = pd.DataFrame([{
                "id": r.id, "Tipo": r.tipo, "Recurso": r.descripcion,
                "Unidad": r.unidad, "Cant. APU": r.cantidad_apu,
                "P. Unit.": r.precio_unitario, "Subtotal": r.subtotal,
                "Fuente": r.fuente_precio, "Bloqueado": r.bloqueado}
                for r in recursos])
            edit = st.data_editor(
                df, use_container_width=True, num_rows="dynamic",
                disabled=["id", "Subtotal", "Fuente"], key=f"ed_{it.id}")

            if st.button(" Guardar recursos", key=f"save_{it.id}"):
                _guardar_recursos(it, recursos, edit, proyecto)
                st.rerun()

            if res:
                def _f(v):
                    return currency.formatear(v, proyecto.moneda, proyecto,
                                              con_simbolo=False)
                sim = currency.simbolo(proyecto.moneda)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(f"Materiales ({sim})", _f(res.costo_materiales))
                m2.metric(f"Mano de obra ({sim})", _f(res.costo_mano_obra))
                m3.metric(f"Equipos ({sim})", _f(res.costo_equipos))
                m4.metric(f"Costo directo ({sim})", _f(res.costo_directo))
                st.markdown(
                    f"Indirectos: **{_f(res.indirectos)}** · "
                    f"Utilidad: **{_f(res.utilidad)}** · "
                    f"Impuestos: **{_f(res.impuestos)}** · "
                    f"**P.U. Total: {currency.formatear(res.precio_unitario_total, proyecto.moneda, proyecto)}**")
                for a in res.alertas:
                    st.warning(a)
                fuentes = {badge_nivel(_nivel(r.fuente_precio)) for r in recursos}
                st.caption("Fuentes de precio usadas: " + ", ".join(sorted(fuentes)))


def _nivel(fuente: str) -> int:
    f = (fuente or "").lower()
    if f.startswith("manual"):
        return 0
    if f.startswith("bd") or "json" in f:
        return 1
    if f.startswith("web"):
        return 2
    if f.startswith("email"):
        return 3
    return -1


def _guardar_recursos(item, recursos_actuales, edit_df, proyecto):
    existentes = {r.id: r for r in recursos_actuales}
    ids_vistos = set()
    for _, fila in edit_df.iterrows():
        rid = fila.get("id")
        if pd.notna(rid) and int(rid) in existentes:
            r = existentes[int(rid)]
            ids_vistos.add(int(rid))
            r.tipo = str(fila["Tipo"])
            r.descripcion = str(fila["Recurso"])
            r.unidad = str(fila["Unidad"])
            r.cantidad_apu = float(fila["Cant. APU"] or 0)
            r.precio_unitario = float(fila["P. Unit."] or 0)
            r.bloqueado = bool(fila["Bloqueado"])
            r.calcular_subtotal()
            repositories.actualizar_recurso(r)
        elif str(fila.get("Recurso") or "").strip():
            from models.apu_resource import RecursoAPU
            nuevo = RecursoAPU(
                item_id=item.id, tipo=str(fila["Tipo"] or "material"),
                descripcion=str(fila["Recurso"]), unidad=str(fila["Unidad"] or ""),
                cantidad_apu=float(fila["Cant. APU"] or 0),
                rendimiento=float(fila["Cant. APU"] or 0),
                precio_unitario=float(fila["P. Unit."] or 0),
                fuente_precio="manual", bloqueado=bool(fila["Bloqueado"]))
            nuevo.calcular_subtotal()
            repositories.guardar_recurso(nuevo)
    # eliminar los que se quitaron en el editor
    for rid, r in existentes.items():
        if rid not in ids_vistos:
            repositories.borrar_recurso(rid)

    recursos = repositories.listar_recursos(item.id)
    resultado = apu_engine.calcular_resultado(item, recursos, proyecto)
    repositories.guardar_resultado(resultado)


def _seccion_difusion(proyecto):
    """Envía la demanda de materiales del proyecto a empresas proveedoras."""
    import streamlit as st
    from providers import demand_broadcast

    usuario = st.session_state.get("usuario")
    if not usuario:
        return
    with st.expander(" Enviar materiales a cotizar a empresas proveedoras"):
        st.caption("Registra los materiales del proyecto en la base nacional y "
                   "los envía por correo a las empresas que ofrecen esos "
                   "materiales, con la cantidad, tipo y tus datos de contacto "
                   "como posible comprador.")
        mats = demand_broadcast.consolidar_materiales(proyecto.id)
        if not mats:
            st.info("Genera los APUs primero para tener materiales que difundir.")
            return
        import pandas as pd
        st.dataframe(pd.DataFrame([{
            "Material": m["descripcion"], "Tipo": m["tipo"],
            "Unidad": m["unidad"], "Cantidad total": round(m["cantidad"], 2)}
            for m in mats]), use_container_width=True, hide_index=True)
        st.caption(f"Encargado de adquisiciones: **{usuario.encargado_nombre or '—'}** "
                   f"· {usuario.email}")
        if st.button(" Difundir demanda a proveedores", type="primary"):
            comp = demand_broadcast.comprador_desde_usuario(usuario)
            resumen = demand_broadcast.difundir_demanda(proyecto.id, comp,
                                                        enviar_email=True)
            st.success(
                f"Demanda difundida: {resumen['materiales']} materiales, "
                f"{resumen['correos_enviados']} correos a "
                f"{resumen['proveedores']} proveedores.")
