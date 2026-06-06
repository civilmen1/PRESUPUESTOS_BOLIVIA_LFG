"""Pagina PUBLICA de aportes al Banco de APU.

Cualquier persona, solo con su nombre y correo (sin cuenta ni login de empresa),
puede subir Formularios B-2 en Excel para que el programa aprenda mas. Se accede
por un enlace propio:  https://TU-APP.onrender.com/?aportar=1

Los aportes se agregan al banco (nunca reemplazan) y se registra quien aporto
(nombre, correo, archivo, cantidad de APUs, fecha) en data/aportes_banco.json.
La importacion lee el Excel directamente y NO consume tokens de IA.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

import streamlit as st

from config import settings
from core import banco_apu

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REGISTRO = settings.DATA_DIR / "aportes_banco.json"


def _registrar_aporte(nombre: str, correo: str, archivo: str, n_apus: int) -> None:
    """Anexa el aporte al registro (para trazabilidad y reconocimiento)."""
    try:
        datos = json.loads(_REGISTRO.read_text(encoding="utf-8")) \
            if _REGISTRO.exists() else {"aportes": []}
    except Exception:
        datos = {"aportes": []}
    datos.setdefault("aportes", []).append({
        "nombre": nombre, "correo": correo, "archivo": archivo,
        "apus": n_apus, "fecha": datetime.now().isoformat(timespec="seconds")})
    _REGISTRO.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                         encoding="utf-8")


def render(*_args, **_kwargs) -> None:
    # Contar la visita una sola vez por sesion (evita recontar en cada rerun).
    if not st.session_state.get("_visita_aportar"):
        from core import trafico
        trafico.registrar_visita("aportar")
        st.session_state["_visita_aportar"] = True

    st.markdown("<h1 style='text-align:center;color:#1F3B57'>PRESUPUESTO "
                "BOLIVIA con IA</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;font-size:1.1rem'>Aporta tus "
                "precios unitarios al banco de datos y ayuda a que el programa "
                "aprenda mas</p>", unsafe_allow_html=True)
    st.write("")

    total = len(banco_apu.listar_apus())
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.metric("Analisis de Precios Unitarios en el banco", f"{total:,}")
        st.caption("Sube uno o varios Formularios B-2 en Excel (.xlsx). La carga "
                   "se SUMA al banco, no borra lo existente. No se necesita cuenta "
                   "ni contrasena: basta tu nombre y correo.")

        with st.form("aporte_publico"):
            nombre = st.text_input("Tu nombre o el de tu empresa *")
            correo = st.text_input("Tu correo electronico *")
            archivos = st.file_uploader(
                "Formularios B-2 (Excel .xlsx) *", type=["xlsx", "bc3"],
                accept_multiple_files=True)
            acepta = st.checkbox(
                "Autorizo que estos precios se usen como referencia dentro del "
                "banco de datos del programa.")
            enviar = st.form_submit_button("Aportar al banco", type="primary",
                                           use_container_width=True)

        if enviar:
            if not nombre.strip():
                st.error("Escribe tu nombre o el de tu empresa.")
                return
            if not _EMAIL_RE.match(correo.strip()):
                st.error("Escribe un correo electronico valido.")
                return
            if not archivos:
                st.error("Adjunta al menos un archivo Excel del Formulario B-2.")
                return
            if not acepta:
                st.error("Debes autorizar el uso de los precios para continuar.")
                return

            from scripts.importar_apu_banco import importar, guardar_banco
            from core import importador_bc3
            total_nuevos = 0
            for archivo in archivos:
                ruta = settings.UPLOAD_DIR / archivo.name
                ruta.write_bytes(archivo.getbuffer())
                try:
                    if archivo.name.lower().endswith(".bc3"):
                        apus = importador_bc3.extraer_apus(archivo.getbuffer())
                    else:
                        apus = importar(str(ruta))
                    # Aportes publicos: SIEMPRE se agregan, nunca reemplazan.
                    guardar_banco(apus, proyecto=f"aporte:{nombre.strip()}",
                                  reemplazar=False)
                    _registrar_aporte(nombre.strip(), correo.strip(),
                                      archivo.name, len(apus))
                    total_nuevos += len(apus)
                    st.success(f"{archivo.name}: {len(apus)} APUs recibidos.")
                except Exception as exc:
                    st.error(f"{archivo.name}: no se pudo leer - {exc}")

            banco_apu._cargar.cache_clear()
            try:
                banco_apu.guardar_markdown()
            except Exception:
                pass
            if total_nuevos:
                st.success(f"Gracias, {nombre.strip()}. Aportaste "
                           f"{total_nuevos} APUs. El banco ahora tiene "
                           f"{len(banco_apu.listar_apus()):,} APUs.")
                st.balloons()

        st.divider()
        st.caption("El Formulario B-2 debe tener el formato oficial (filas "
                   "Actividad / Unidad / Cantidad y secciones 1 Materiales, "
                   "2 Mano de obra, 3 Equipo). Tambien se aceptan presupuestos "
                   "BC3 / FIEBDC-3 (.bc3) de CYPE, Arquimedes o Presto.")
