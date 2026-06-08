"""Página de Documentos técnicos: carga, extracción y segmentación."""
from __future__ import annotations

import streamlit as st

from config import settings
from core import repositories
from core.parser_documento import detectar_tipo, extraer_texto
from core.segmentador import segmentar
from models.technical_source import FuenteTecnica
from ui.components import requiere_proyecto


def render(proyecto):
    st.title(" Documentos técnicos (DBC / Especificaciones / TDR)")
    if not requiere_proyecto(proyecto):
        return

    archivos = st.file_uploader(
        "PDF / DOCX / DOC / TXT / Imagen (PNG, JPG, TIFF)",
        type=["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg", "tiff", "tif", "bmp"],
        accept_multiple_files=True)
    st.caption(" Los PDFs escaneados y las imágenes se leen con OCR "
               "automáticamente (requiere Tesseract instalado).")
    if archivos and st.button(" Procesar documentos", type="primary"):
        for archivo in archivos:
            ruta = settings.UPLOAD_DIR / archivo.name
            ruta.write_bytes(archivo.getbuffer())
            with st.spinner(f"Extrayendo {archivo.name}..."):
                texto = extraer_texto(ruta)
                fuente = FuenteTecnica(
                    proyecto_id=proyecto.id,
                    tipo_documento=detectar_tipo(archivo.name),
                    nombre_archivo=archivo.name, ruta=str(ruta),
                    texto_extraido=texto)
                fuente_id = repositories.crear_fuente(fuente)
                secciones = segmentar(texto, fuente_id=fuente_id)
                for s in secciones:
                    repositories.crear_seccion(s)
            st.success(f"{archivo.name}: {len(secciones)} secciones extraídas "
                       f"({len(texto)} caracteres).")
        st.rerun()

    st.divider()
    fuentes = repositories.listar_fuentes(proyecto.id)
    if not fuentes:
        st.info("No hay documentos cargados todavía.")
        return

    secciones = repositories.listar_secciones(proyecto.id)
    col_a, col_b = st.columns([3, 1])
    col_a.subheader(f"Documentos cargados ({len(fuentes)}) · "
                    f"Secciones: {len(secciones)}")
    if col_b.button(" Eliminar TODOS", use_container_width=True):
        n = repositories.borrar_todas_fuentes(proyecto.id)
        st.success(f"{n} documento(s) eliminado(s).")
        st.rerun()

    for f in fuentes:
        with st.expander(f" {f.nombre_archivo}  ·  {f.tipo_documento}"):
            secs = [s for s in secciones if s.fuente_id == f.id]
            cc1, cc2 = st.columns([3, 1])
            cc1.caption(f"{len(secs)} secciones · "
                        f"{len(f.texto_extraido or '')} caracteres")
            if cc2.button(" Eliminar documento", key=f"del_{f.id}",
                          use_container_width=True):
                repositories.borrar_fuente(f.id)
                st.success(f"Documento '{f.nombre_archivo}' eliminado.")
                st.rerun()
            busqueda = st.text_input(" Buscar en el documento", key=f"buscar_{f.id}")
            for s in secs:
                if busqueda and busqueda.lower() not in (s.contenido or "").lower():
                    continue
                st.markdown(f"**{s.titulo}** _(pág. {s.pagina_inicio}-{s.pagina_fin})_")
                st.write((s.contenido or "")[:600] + ("…" if len(s.contenido or "") > 600 else ""))
