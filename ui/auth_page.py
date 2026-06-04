"""Páginas de login y registro de empresas / entidades."""
from __future__ import annotations

import streamlit as st

from config import settings
from core import auth


def render_login() -> auth.Usuario | None:
    """Pantalla de acceso. Devuelve el Usuario autenticado o None."""
    st.markdown("<h1 style='text-align:center'>🏗️ APU Bolivia Generator</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Acceso para empresas y "
                "entidades</p>", unsafe_allow_html=True)

    tab_login, tab_registro, tab_verif = st.tabs(
        ["🔑 Iniciar sesión", "📝 Registrar empresa", "✉️ Verificar correo"])

    usuario = None

    # -------------------------------------------------------------- login
    with tab_login:
        with st.form("login"):
            email = st.text_input("Correo electrónico")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", type="primary",
                                     use_container_width=True):
                u, msg = auth.login(email, password)
                if u:
                    st.session_state["usuario"] = u
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    if "verificar tu correo" in msg:
                        st.info("Ve a la pestaña «Verificar correo».")

    # ----------------------------------------------------------- registro
    with tab_registro:
        _form_registro()

    # -------------------------------------------------------- verificación
    with tab_verif:
        _form_verificacion()

    return usuario


def _form_registro():
    st.caption("Completa los datos de tu empresa o entidad. Verificaremos tu "
               "correo antes de habilitar el acceso.")
    perfil = st.radio("Tipo de organización", ["contratista", "entidad"],
                      format_func=lambda x: ("🏢 Empresa (constructora / "
                                             "consultora / privada)" if x ==
                                             "contratista" else
                                             "🏛️ Entidad pública"),
                      horizontal=True)

    with st.form("registro", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre de la empresa / entidad *")
        nit = c2.text_input("NIT")
        c3, c4 = st.columns(2)
        seprec = c3.text_input("SEPREC (registro de comercio)")
        direccion = c4.text_input("Dirección")
        st.markdown("**Encargado de compras / adquisiciones**")
        c5, c6 = st.columns(2)
        enc_nombre = c5.text_input("Nombre del encargado")
        enc_wsp = c6.text_input("WhatsApp del encargado")
        st.markdown("**Acceso**")
        c7, c8 = st.columns(2)
        email = c7.text_input("Correo electrónico *")
        password = c8.text_input("Contraseña *", type="password")

        verificar_nit = st.checkbox("Verificar NIT automáticamente", value=True)
        enviado = st.form_submit_button("Registrar empresa", type="primary")

    if enviado:
        if not (nombre and email and password):
            st.error("Completa los campos obligatorios (*).")
            return
        if auth.email_existe(email):
            st.error("Ya existe una cuenta con ese correo.")
            return

        # Verificación de NIT (empresas). Entidades públicas: solo por email.
        nit_info = {"ok": False}
        if verificar_nit and nit and perfil == "contratista":
            nit_info = auth.verificar_nit(nit)
            if nit_info.get("ok"):
                st.success(f"NIT verificado: {nit_info.get('razon_social')} "
                           f"· {nit_info.get('estado')}")
            else:
                st.warning(nit_info.get("mensaje", "No se pudo verificar el NIT; "
                           "podrás verificarlo luego."))

        u = auth.Usuario(
            perfil=perfil, nombre_empresa=nombre, nit=nit, seprec=seprec,
            direccion=direccion, email=email, encargado_nombre=enc_nombre,
            encargado_whatsapp=enc_wsp, nit_verificado=nit_info.get("ok", False),
            nit_razon_social=nit_info.get("razon_social", ""),
            nit_estado=nit_info.get("estado", ""))
        try:
            _uid, token = auth.registrar_usuario(u, password)
        except ValueError as e:
            st.error(str(e))
            return
        auth.enviar_codigo_verificacion(email, token)
        st.success("✅ Empresa registrada. Te enviamos un código de verificación "
                   "a tu correo. Ve a la pestaña «Verificar correo».")
        if settings.AUTH_EMAIL_DRY_RUN:
            st.info(f"🔧 Modo prueba — tu código de verificación es: **{token}**")


def _form_verificacion():
    st.caption("Ingresa el código de 6 dígitos que enviamos a tu correo para "
               "habilitar tu cuenta.")
    with st.form("verificar"):
        email = st.text_input("Correo electrónico")
        codigo = st.text_input("Código de verificación")
        col1, col2 = st.columns(2)
        verificar = col1.form_submit_button("Verificar", type="primary",
                                            use_container_width=True)
        reenviar = col2.form_submit_button("Reenviar código",
                                           use_container_width=True)
    if verificar:
        if auth.verificar_email(email, codigo):
            st.success("✅ Correo verificado. Ya puedes iniciar sesión.")
        else:
            st.error("Código incorrecto o correo ya verificado.")
    if reenviar:
        token = auth.reenviar_token(email)
        if token:
            auth.enviar_codigo_verificacion(email, token)
            st.success("Código reenviado.")
            if settings.AUTH_EMAIL_DRY_RUN:
                st.info(f"🔧 Modo prueba — nuevo código: **{token}**")
        else:
            st.error("No se encontró una cuenta pendiente con ese correo.")
