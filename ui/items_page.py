"""Página de Ítems: carga, importación y edición de la tabla de cantidades."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from core import repositories
from core.parser_tabla import dataframe_a_items, leer_dataframe
from core.validation_engine import validar_items
from models.item import Item
from ui.components import requiere_proyecto


def render(proyecto):
    st.title("📋 Ítems — Tabla de cantidades")
    if not requiere_proyecto(proyecto):
        return

    tab_import, tab_manual, tab_tabla = st.tabs(
        ["⬆️ Importar archivo", "✍️ Ingreso manual", "📑 Tabla actual"])

    # ---------------------------------------------------------------- importar
    with tab_import:
        archivo = st.file_uploader("CSV / XLSX / XLS", type=["csv", "xlsx", "xls"])
        if archivo:
            ruta = settings.UPLOAD_DIR / archivo.name
            ruta.write_bytes(archivo.getbuffer())
            try:
                df = leer_dataframe(ruta)
                st.write("Vista previa:")
                st.dataframe(df.head(20), use_container_width=True)
                items = dataframe_a_items(df, proyecto.id)
                val = validar_items(items)
                for e in val.errores:
                    st.error(e)
                for a in val.advertencias[:10]:
                    st.warning(a)
                st.info(f"Se detectaron {len(items)} ítems.")
                if st.button("💾 Guardar ítems importados", type="primary"):
                    n = 0
                    for it in items:
                        mod = getattr(it, "_modulo_nombre", "")
                        it.modulo_id = repositories.obtener_o_crear_modulo(
                            proyecto.id, mod) if mod else None
                        repositories.crear_item(it)
                        n += 1
                    st.success(f"{n} ítems guardados.")
                    st.rerun()
            except Exception as exc:
                st.error(f"Error al leer el archivo: {exc}")

    # ------------------------------------------------------------------ manual
    with tab_manual:
        with st.form("item_manual", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            numero = col1.text_input("N° ítem")
            codigo = col2.text_input("Código")
            unidad = col3.text_input("Unidad", "m3")
            descripcion = st.text_area("Descripción", height=80)
            col4, col5 = st.columns(2)
            cantidad = col4.number_input("Cantidad", 0.0, step=1.0)
            modulo = col5.text_input("Módulo")
            obs = st.text_input("Observaciones")
            if st.form_submit_button("➕ Agregar ítem") and descripcion:
                from core.text_cleaner import extraer_keywords
                mod_id = repositories.obtener_o_crear_modulo(
                    proyecto.id, modulo) if modulo else None
                repositories.crear_item(Item(
                    proyecto_id=proyecto.id, modulo_id=mod_id, numero=numero,
                    codigo=codigo, descripcion=descripcion, unidad=unidad,
                    cantidad=cantidad, observaciones=obs,
                    palabras_clave=", ".join(extraer_keywords(descripcion, 8))))
                st.success("Ítem agregado.")
                st.rerun()

    # ---------------------------------------------------------------- tabla
    with tab_tabla:
        items = repositories.listar_items(proyecto.id)
        if not items:
            st.info("Aún no hay ítems. Importa un archivo o ingrésalos manualmente.")
            return
        df = pd.DataFrame([{
            "id": it.id, "N°": it.numero, "Código": it.codigo,
            "Descripción": it.descripcion, "Unidad": it.unidad,
            "Cantidad": it.cantidad, "Estado": it.estado,
            "Observaciones": it.observaciones} for it in items])
        edit = st.data_editor(df, use_container_width=True, num_rows="fixed",
                              disabled=["id", "Estado"], key="editor_items")
        if st.button("💾 Guardar cambios"):
            for _, fila in edit.iterrows():
                it = repositories.obtener_item(int(fila["id"]))
                if it:
                    it.numero = str(fila["N°"])
                    it.codigo = str(fila["Código"])
                    it.descripcion = str(fila["Descripción"])
                    it.unidad = str(fila["Unidad"])
                    it.cantidad = float(fila["Cantidad"] or 0)
                    it.observaciones = str(fila["Observaciones"])
                    repositories.actualizar_item(it)
            st.success("Cambios guardados.")
            st.rerun()
