"""Página de APUs: generación, desglose, edición y bloqueo de recursos."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import apu_engine, repositories
from ui.components import badge_nivel, requiere_proyecto


def render(proyecto):
    st.title("🧮 APUs — Análisis de Precios Unitarios")
    if not requiere_proyecto(proyecto):
        return

    items = repositories.listar_items(proyecto.id)
    if not items:
        st.info("Carga ítems primero.")
        return

    st.subheader("Generación automática (cotizador jerárquico Bolivia)")
    c1, c2, c3 = st.columns(3)
    permitir_web = c1.checkbox("Nivel 2: búsqueda web", value=True)
    permitir_email = c2.checkbox("Nivel 3: solicitar por email", value=False)
    st.caption("Orden de cotización: 🗃️ BD Bolivia → 🌐 Web → ✉️ Email")

    if c3.button("⚙️ Generar APUs de todos los ítems", type="primary"):
        prog = st.progress(0.0)
        for i, it in enumerate(items):
            apu_engine.generar_apu_item(it, proyecto, permitir_web=permitir_web,
                                        permitir_email=permitir_email)
            prog.progress((i + 1) / len(items))
        st.success("APUs generados.")
        st.rerun()

    st.divider()
    for it in items:
        recursos = repositories.listar_recursos(it.id)
        res = repositories.obtener_resultado(it.id)
        total = res.precio_unitario_total if res else 0
        with st.expander(f"🧱 {it.numero or ''} {it.descripcion[:55]} — "
                         f"P.U. {total:,.2f} {proyecto.moneda}"):
            cga, cgb = st.columns([1, 1])
            if cga.button("🔄 Regenerar este APU", key=f"regen_{it.id}"):
                apu_engine.generar_apu_item(it, proyecto, permitir_web=permitir_web,
                                            permitir_email=permitir_email)
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

            if st.button("💾 Guardar recursos", key=f"save_{it.id}"):
                _guardar_recursos(it, recursos, edit, proyecto)
                st.rerun()

            if res:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Materiales", f"{res.costo_materiales:,.2f}")
                m2.metric("Mano de obra", f"{res.costo_mano_obra:,.2f}")
                m3.metric("Equipos", f"{res.costo_equipos:,.2f}")
                m4.metric("Costo directo", f"{res.costo_directo:,.2f}")
                st.markdown(
                    f"Indirectos: **{res.indirectos:,.2f}** · "
                    f"Utilidad: **{res.utilidad:,.2f}** · "
                    f"Impuestos: **{res.impuestos:,.2f}** · "
                    f"**P.U. Total: {res.precio_unitario_total:,.2f} {proyecto.moneda}**")
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
