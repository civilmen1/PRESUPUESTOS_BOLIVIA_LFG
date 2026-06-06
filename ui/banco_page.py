"""Pagina para cargar Formularios B-2 al BANCO DE APU (base de conocimiento).

El ingeniero sube uno o varios archivos B-2 (Excel) y se agregan al banco para
mejorar la generacion de precios unitarios. La importacion NO consume tokens
(lee el Excel directamente). El banco se usa como plantilla prioritaria y como
fuente de precios reales.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from core import banco_apu


def render(proyecto=None):
    st.title("Banco de APU (base de conocimiento)")
    st.caption("Sube tus Formularios B-2 (mismo formato del archivo de ejemplo) "
               "para mejorar el conocimiento del sistema. La importacion lee el "
               "Excel directamente, NO consume tokens de IA.")

    n = len(banco_apu.listar_apus())
    st.metric("APUs en el banco", n)

    st.caption("Formatos aceptados: Formulario B-2 (.xlsx) y presupuestos "
               "BC3 / FIEBDC-3 (.bc3) exportados de CYPE, Arquimedes o Presto.")
    archivos = st.file_uploader(
        "Archivos B-2 (.xlsx) o BC3/FIEBDC-3 (.bc3)",
        type=["xlsx", "bc3"], accept_multiple_files=True)
    reemplazar = st.checkbox("Reemplazar el banco (en vez de agregar)",
                             value=False)

    if archivos and st.button("Cargar al banco", type="primary"):
        from scripts.importar_apu_banco import importar, guardar_banco
        from core import importador_bc3
        from core.text_cleaner import nombre_archivo_seguro
        total_nuevos = 0
        primero = True
        for archivo in archivos:
            seguro = nombre_archivo_seguro(archivo.name)
            ruta = settings.UPLOAD_DIR / seguro
            ruta.write_bytes(archivo.getbuffer())
            try:
                if seguro.lower().endswith(".bc3"):
                    apus = importador_bc3.extraer_apus(archivo.getbuffer())
                else:
                    apus = importar(str(ruta))
                guardar_banco(apus, proyecto=seguro,
                              reemplazar=reemplazar and primero)
                primero = False
                total_nuevos += len(apus)
                st.success(f"{seguro}: {len(apus)} APUs procesados.")
            except Exception as exc:
                st.error(f"{seguro}: error al leer - {exc}")
        # refrescar cache del banco
        banco_apu._cargar.cache_clear()
        banco_apu.guardar_markdown()
        st.success(f"Banco actualizado. Total de APUs ahora: "
                   f"{len(banco_apu.listar_apus())}.")
        st.rerun()

    st.divider()
    st.subheader("Contenido actual del banco")
    apus = banco_apu.listar_apus()
    if not apus:
        st.info("El banco esta vacio. Sube tus Formularios B-2 para empezar.")
        return
    df = pd.DataFrame([{
        "Actividad": a.get("actividad", ""), "Unidad": a.get("unidad", ""),
        "Materiales": len(a.get("materiales", [])),
        "Mano de obra": len(a.get("mano_obra", [])),
        "Equipo": len(a.get("equipo", []))} for a in apus])
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    # Descargar el banco en Markdown (version compacta para IA / respaldo)
    md = banco_apu.a_markdown()
    st.download_button("Descargar banco en Markdown (compacto)", md,
                       file_name="banco_apu.md", mime="text/markdown")

    st.divider()
    _panel_moderacion()

    st.divider()
    _panel_trafico()


def _panel_moderacion():
    """Aprobacion de los aportes publicos antes de que entren al banco."""
    from core import moderacion

    pendientes = moderacion.listar("pendiente")
    st.subheader(f"Aportes publicos por revisar ({len(pendientes)})")
    st.caption("Los aportes recibidos por el enlace publico NO entran al banco "
               "hasta que los apruebes aqui. Asi proteges la calidad de tus "
               "precios.")
    if not pendientes:
        st.info("No hay aportes pendientes de revision.")
        return

    for a in pendientes:
        apus = a.get("apus", [])
        with st.expander(f"#{a['id']}  ·  {a.get('archivo','')}  ·  "
                         f"{len(apus)} APUs  ·  {a.get('nombre','')} "
                         f"({a.get('correo','')})"):
            df = pd.DataFrame([{
                "Actividad": x.get("actividad", ""),
                "Unidad": x.get("unidad", ""),
                "Materiales": len(x.get("materiales", [])),
                "Mano de obra": len(x.get("mano_obra", [])),
                "Equipo": len(x.get("equipo", []))} for x in apus])
            st.dataframe(df, use_container_width=True, hide_index=True,
                         height=220)
            c1, c2 = st.columns(2)
            if c1.button("Aprobar e incorporar al banco", key=f"ap_{a['id']}",
                         type="primary", use_container_width=True):
                n = moderacion.aprobar(a["id"])
                banco_apu._cargar.cache_clear()
                st.success(f"Aprobado: {n} APUs incorporados al banco.")
                st.rerun()
            if c2.button("Rechazar", key=f"rc_{a['id']}",
                         use_container_width=True):
                moderacion.rechazar(a["id"])
                st.warning("Aporte rechazado (no entro al banco).")
                st.rerun()


def _panel_trafico():
    """Trafico de la pagina publica de aportes (?aportar=1) y lista de aportes."""
    from core import trafico

    st.subheader("Trafico de la pagina publica de aportes")
    st.caption("Enlace para compartir:  tu-app.onrender.com/?aportar=1")
    r = trafico.resumen("aportar", dias=30)
    aportes = trafico.listar_aportes()
    c1, c2, c3 = st.columns(3)
    c1.metric("Visitas totales", f"{r['total']:,}")
    c2.metric("Visitas hoy", r["hoy"])
    c3.metric("Aportes recibidos", len(aportes))

    serie = r["ultimos_dias"]
    if any(n for _, n in serie):
        df = pd.DataFrame(serie, columns=["fecha", "visitas"]).set_index("fecha")
        st.caption("Visitas por dia (ultimos 30 dias)")
        st.bar_chart(df, height=200)
    else:
        st.info("Aun no hay visitas registradas en la pagina de aportes.")

    if aportes:
        st.caption("Quienes han aportado")
        dfa = pd.DataFrame([{
            "Fecha": a.get("fecha", ""), "Nombre": a.get("nombre", ""),
            "Correo": a.get("correo", ""), "Archivo": a.get("archivo", ""),
            "APUs": a.get("apus", 0)} for a in reversed(aportes)])
        st.dataframe(dfa, use_container_width=True, hide_index=True, height=260)
