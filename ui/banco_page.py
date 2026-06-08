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
    if reemplazar:
        st.warning(f"PELIGRO: vas a BORRAR los {n} APU actuales y dejar solo "
                   "los del archivo que subas. Se guarda un respaldo "
                   "automatico, pero asegurate de que es lo que quieres. "
                   "Si solo quieres sumar precios, DESMARCA esta casilla.")
        confirmar = st.checkbox(f"Si, entiendo que se borraran los {n} APU "
                                "actuales y quiero reemplazarlos.", value=False)
        reemplazar = reemplazar and confirmar

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
                r = guardar_banco(apus, proyecto=seguro,
                                  reemplazar=reemplazar and primero,
                                  actualizar_duplicados=not reemplazar)
                primero = False
                total_nuevos += len(apus)
                st.success(f"{seguro}: {len(apus)} APUs leidos "
                           f"({r['agregados']} nuevos, {r['actualizados']} "
                           f"actualizados, {r['omitidos']} ya existian).")
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

    # Descargar el banco COMPLETO en JSON (respaldo / migracion entre equipos).
    # Lee el archivo persistente tal cual (incluye TODOS los APU del servidor).
    # Para usarlo en otra PC, reemplaza data/banco_apu.json con este archivo.
    ruta_json = banco_apu.ruta_persistente()
    if ruta_json.exists():
        st.download_button(
            f"Descargar banco completo en JSON ({len(apus)} APU)",
            ruta_json.read_text(encoding="utf-8"),
            file_name="banco_apu.json", mime="application/json",
            help="Respaldo total del banco. Para llevarlo a otra PC, reemplaza "
                 "el archivo data/banco_apu.json con este.")

    _panel_sync()

    _panel_cargar_json()

    _panel_cwicr()


def _panel_sync():
    """Sincronizacion con la nube (la nube manda; el local baja)."""
    from core import sync
    est = sync.estado()
    with st.expander("Sincronizacion con la nube"):
        if est["publica"]:
            st.success("Esta es la NUBE: publica el banco para que tus equipos "
                       "locales lo descarguen automaticamente.")
            st.caption("En cada PC local, configura APU_SYNC_URL con el enlace "
                       "/app/static/banco_<token>.json de este servidor.")
        elif est["url_local"]:
            st.info("Esta app baja el banco de la nube al abrir"
                    + (" (automatico activado)." if est["auto"] else "."))
            st.caption(f"Origen: {est['url_local']}")
            if st.button("Sincronizar ahora (bajar de la nube)", type="primary"):
                with st.spinner("Descargando el banco de la nube..."):
                    res = sync.sincronizar_desde_nube(fusionar=True)
                if res:
                    st.success(f"Sincronizado: {res['nuevos']} APU nuevos. "
                               f"Total ahora: {res['despues']}.")
                    st.rerun()
                else:
                    st.error("No se pudo sincronizar (revisa APU_SYNC_URL y tu "
                             "conexion a internet).")
        else:
            st.caption("Sincronizacion no configurada. En la nube pon "
                       "APU_SYNC_PUBLISH=true y APU_SYNC_TOKEN; en tu PC pon "
                       "APU_SYNC_URL con el enlace del servidor.")

    _panel_respaldos()

    st.divider()
    _panel_moderacion()


def _panel_cargar_json():
    """Carga el banco completo desde un archivo JSON (p.ej. el descargado del
    servidor) sin tener que copiar archivos a mano."""
    with st.expander("Cargar banco completo desde un archivo JSON "
                     "(p.ej. el descargado del servidor)"):
        st.caption("Sube el archivo banco_apu.json (el que descargaste con el "
                   "boton de arriba en el servidor). Se guarda un respaldo del "
                   "banco actual antes de reemplazarlo.")
        archivo = st.file_uploader("Archivo banco_apu.json", type=["json"],
                                   key="banco_json_file")
        fusionar = st.checkbox("Fusionar con el banco actual (en vez de "
                               "reemplazar)", value=False)
        if archivo and st.button("Cargar este banco", type="primary"):
            try:
                texto = archivo.getvalue().decode("utf-8")
                total = banco_apu.cargar_desde_json(texto, fusionar=fusionar)
                st.success(f"Banco cargado: ahora tiene {total} APU.")
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo cargar: {exc}")


def _panel_cwicr():
    """Importa rendimientos del catalogo CWICR (CC BY 4.0) SIN sus precios."""
    with st.expander("Importar rendimientos CWICR (catalogo internacional, sin precios)"):
        st.caption("Toma de un archivo CWICR (CSV/Excel) los RENDIMIENTOS "
                   "(cantidades y horas por unidad) y los agrega al banco como "
                   "referencia. Los precios del CWICR estan en EUR y se DESCARTAN "
                   "(entran en 0): debes repreciarlos con tus tarifas bolivianas. "
                   "Fuente: DataDrivenConstruction CWICR (CC BY 4.0).")
        archivo = st.file_uploader("Archivo CWICR (.csv, .xlsx)",
                                   type=["csv", "xlsx"], key="cwicr_file")
        contiene = st.text_input(
            "Filtrar solo partidas que contengan (separa por comas; vacio = todas)",
            placeholder="hormigon, acero, pintura, excavacion")
        if archivo and st.button("Importar rendimientos CWICR", type="primary"):
            from scripts.importar_cwicr import importar_cwicr
            from scripts.importar_apu_banco import guardar_banco
            from core.text_cleaner import nombre_archivo_seguro
            ruta = settings.UPLOAD_DIR / nombre_archivo_seguro(archivo.name)
            ruta.write_bytes(archivo.getbuffer())
            palabras = [p for p in contiene.split(",") if p.strip()]
            try:
                with st.spinner("Leyendo CWICR (rendimientos, sin precios)..."):
                    apus = importar_cwicr(str(ruta), contiene=palabras)
                if not apus:
                    st.warning("No se obtuvieron partidas (revisa el filtro o el "
                               "formato del archivo).")
                    return
                guardar_banco(apus, proyecto="CWICR", reemplazar=False)
                banco_apu._cargar.cache_clear()
                st.success(f"{len(apus)} partidas CWICR agregadas (precios en 0). "
                           "Reprecia los insumos con tus tarifas bolivianas.")
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo importar: {exc}")


def _panel_respaldos():
    """Lista de respaldos automaticos del banco, con descarga y restauracion."""
    respaldos = banco_apu.listar_respaldos()
    with st.expander(f"Respaldos automaticos del banco ({len(respaldos)})"):
        st.caption("Cada vez que el banco se reescribe (saneo, reemplazo o "
                   "aprobacion de aportes) se guarda una copia. Si algo borro "
                   "datos por error, restaura aqui la version con mas APU.")
        if not respaldos:
            st.info("Aun no hay respaldos. Se crearan automaticamente con el "
                    "proximo cambio del banco.")
            return
        for bak in respaldos:
            n_bak = banco_apu.contar_apus_archivo(bak)
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"`{bak.name}` - **{n_bak}** APU")
            c2.download_button("Descargar", bak.read_text(encoding="utf-8"),
                               file_name=bak.name, mime="application/json",
                               key=f"dl_{bak.name}")
            if c3.button("Restaurar", key=f"rs_{bak.name}"):
                total = banco_apu.restaurar(bak)
                st.success(f"Banco restaurado: ahora tiene {total} APU.")
                st.rerun()

    st.divider()
    _panel_trafico()


def _resumen_aporte(r: dict) -> str:
    """Mensaje honesto de lo que realmente paso al incorporar APUs al banco."""
    msg = (f"Listo: {r.get('agregados', 0)} APU nuevos agregados, "
           f"{r.get('actualizados', 0)} actualizados (la actividad ya existia y "
           f"se refrescaron sus precios), {r.get('omitidos', 0)} omitidos. "
           f"Total en el banco: {r.get('total', '?')}.")
    if not r.get("agregados") and not r.get("actualizados"):
        msg += (" El contador no sube porque esas actividades ya estaban en el "
                "banco.")
    return msg


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

    n_apus = sum(len(a.get("apus", [])) for a in pendientes)
    c1, c2 = st.columns([3, 1])
    c1.caption(f"Hay {len(pendientes)} aportes pendientes con {n_apus} APUs en "
               "total. Revisalos abajo o incorporalos todos de una vez.")
    if c2.button("Aprobar todos", type="primary", use_container_width=True):
        r = moderacion.aprobar_todos()
        banco_apu._cargar.cache_clear()
        st.success(_resumen_aporte(r))
        st.rerun()

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
                r = moderacion.aprobar(a["id"])
                banco_apu._cargar.cache_clear()
                st.success(_resumen_aporte(r))
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
