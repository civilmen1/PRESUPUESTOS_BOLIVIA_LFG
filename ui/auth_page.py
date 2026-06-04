"""Páginas de login y registro de empresas / entidades."""
from __future__ import annotations

import streamlit as st

from config import settings
from core import auth


def render_login(perfil: str = "contratista") -> auth.Usuario | None:
    """Pantalla de acceso. Devuelve el Usuario autenticado o None.

    `perfil` define el tipo de registro mostrado: contratista/entidad o proveedor.
    """
    es_proveedor = perfil == "proveedor"
    st.markdown("<h1 style='text-align:center'>🏗️ APU Bolivia Generator</h1>",
                unsafe_allow_html=True)
    sub = ("Acceso para proveedores de materiales" if es_proveedor
           else "Acceso para empresas y entidades")
    st.markdown(f"<p style='text-align:center'>{sub}</p>", unsafe_allow_html=True)

    etiqueta_reg = "📝 Registrar proveedor" if es_proveedor else "📝 Registrar empresa"
    tab_login, tab_registro, tab_verif = st.tabs(
        ["🔑 Iniciar sesión", etiqueta_reg, "✉️ Verificar correo"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Correo electrónico")
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", type="primary",
                                     use_container_width=True):
                u, msg = auth.login(email, password)
                if u and es_proveedor and u.perfil != "proveedor":
                    st.error("Esta cuenta no es de proveedor. Usa el perfil "
                             "correcto en la pantalla inicial.")
                elif u and not es_proveedor and u.perfil == "proveedor":
                    st.error("Esta es una cuenta de proveedor. Ingresa por el "
                             "perfil de Proveedor.")
                elif u:
                    st.session_state["usuario"] = u
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    if "verificar tu correo" in msg:
                        st.info("Ve a la pestaña «Verificar correo».")

    with tab_registro:
        if es_proveedor:
            _form_registro_proveedor()
        else:
            _form_registro()

    with tab_verif:
        _form_verificacion()

    return None


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


def _form_registro_proveedor():
    from models.supplier import TIPOS_PROVEEDOR
    st.caption("Regístrate como proveedor. Verificaremos tu correo antes de "
               "habilitar el acceso a tus solicitudes de cotización.")
    with st.form("registro_prov", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre comercial *")
        nit = c2.text_input("NIT")
        c3, c4 = st.columns(2)
        categoria = c3.selectbox("Rubro", TIPOS_PROVEEDOR)
        ciudad = c4.text_input("Ciudad / Departamento")
        direccion = st.text_input("Dirección")
        materiales = st.text_area("Materiales / servicios que ofrece")
        st.markdown("**Encargado de ventas**")
        c5, c6 = st.columns(2)
        enc = c5.text_input("Nombre del encargado")
        wsp = c6.text_input("WhatsApp")
        st.markdown("**Acceso**")
        c7, c8 = st.columns(2)
        email = c7.text_input("Correo electrónico *")
        password = c8.text_input("Contraseña *", type="password")
        enviado = st.form_submit_button("Registrar proveedor", type="primary")

    if enviado:
        if not (nombre and email and password):
            st.error("Completa los campos obligatorios (*).")
            return
        if auth.email_existe(email):
            st.error("Ya existe una cuenta con ese correo.")
            return
        u = auth.Usuario(perfil="proveedor", nombre_empresa=nombre, nit=nit,
                         direccion=direccion, email=email, encargado_nombre=enc,
                         encargado_whatsapp=wsp, nit_estado=ciudad)
        _uid, token = auth.registrar_proveedor_con_cuenta(
            u, password, categoria=categoria, materiales=materiales,
            ciudad=ciudad, telefono=wsp)
        auth.enviar_codigo_verificacion(email, token)
        st.success("✅ Proveedor registrado. Te enviamos un código a tu correo. "
                   "Ve a «Verificar correo».")
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
