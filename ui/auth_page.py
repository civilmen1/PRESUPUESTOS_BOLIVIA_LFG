"""Paginas de inicio de sesion y registro de empresas, entidades y proveedores.

Diseno sobrio (sin emojis), en espanol. La verificacion de correo aparece como
ventana emergente (dialog) inmediatamente despues del registro.
"""
from __future__ import annotations

import streamlit as st

from core import auth


def render_login(perfil: str = "contratista"):
    """Pantalla de acceso. Guarda el usuario en sesion al autenticar."""
    es_proveedor = perfil == "proveedor"
    sub = ("Acceso para proveedores de materiales" if es_proveedor
           else "Acceso para empresas y entidades")
    st.markdown(
        "<h2 style='text-align:center;color:#1F3B57'>APU Bolivia Generator</h2>"
        f"<p style='text-align:center;color:#5A6B7B'>{sub}</p>",
        unsafe_allow_html=True)

    pend = st.session_state.get("verificacion_pendiente")
    if pend:
        _dialogo_verificacion(pend)

    etiqueta_reg = "Registrar proveedor" if es_proveedor else "Registrar empresa"
    tab_login, tab_registro = st.tabs(["Iniciar sesion", etiqueta_reg])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Correo electronico")
            password = st.text_input("Contrasena", type="password")
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
                    st.rerun()
                else:
                    st.error(msg)
                    if "verificar tu correo" in msg:
                        st.session_state["verificacion_pendiente"] = {
                            "email": email}
                        st.rerun()

    with tab_registro:
        if es_proveedor:
            _form_registro_proveedor()
        else:
            _form_registro()


@st.dialog("Confirma tu correo electronico")
def _dialogo_verificacion(datos: dict):
    email = datos.get("email", "")
    st.write(f"Enviamos un codigo de 6 digitos a {email}. Ingresalo para "
             "activar tu cuenta.")
    codigo = st.text_input("Codigo de verificacion", max_chars=6)
    col1, col2 = st.columns(2)
    if col1.button("Verificar", type="primary", use_container_width=True):
        if auth.verificar_email(email, codigo):
            st.session_state.pop("verificacion_pendiente", None)
            st.success("Correo verificado. Ya puedes iniciar sesion.")
            st.rerun()
        else:
            st.error("Codigo incorrecto. Revisa tu correo e intenta de nuevo.")
    if col2.button("Reenviar codigo", use_container_width=True):
        token = auth.reenviar_token(email)
        if token:
            auth.enviar_codigo_verificacion(email, token)
            st.info("Codigo reenviado a tu correo.")
        else:
            st.error("No hay una cuenta pendiente con ese correo.")
    if st.button("Cerrar"):
        st.session_state.pop("verificacion_pendiente", None)
        st.rerun()


def _abrir_verificacion(email: str):
    st.session_state["verificacion_pendiente"] = {"email": email}
    st.rerun()


def _form_registro():
    st.caption("Completa los datos de tu empresa o entidad. Confirmaremos tu "
               "correo electronico para habilitar el acceso.")
    perfil = st.radio(
        "Tipo de organizacion", ["contratista", "entidad"],
        format_func=lambda x: ("Empresa (constructora / consultora / privada)"
                               if x == "contratista" else "Entidad publica"),
        horizontal=True)

    with st.form("registro", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre de la empresa / entidad *")
        nit = c2.text_input("NIT")
        c3, c4 = st.columns(2)
        seprec = c3.text_input("SEPREC (registro de comercio)")
        direccion = c4.text_input("Direccion")
        st.markdown("**Encargado de compras / adquisiciones**")
        c5, c6 = st.columns(2)
        enc_nombre = c5.text_input("Nombre del encargado")
        enc_wsp = c6.text_input("WhatsApp del encargado")
        st.markdown("**Acceso**")
        c7, c8 = st.columns(2)
        email = c7.text_input("Correo electronico *")
        password = c8.text_input("Contrasena * (min. 8, con letra y numero)",
                                 type="password")
        verificar_nit = st.checkbox("Verificar NIT automaticamente", value=True)
        enviado = st.form_submit_button("Registrar empresa", type="primary")

    if not enviado:
        return
    if not (nombre and email and password):
        st.error("Completa los campos obligatorios (*).")
        return
    ok, msg = auth.validar_password(password)
    if not ok:
        st.error(msg)
        return
    if auth.email_existe(email):
        st.error("Ya existe una cuenta con ese correo.")
        return

    nit_info = {"ok": False}
    if verificar_nit and nit and perfil == "contratista":
        nit_info = auth.verificar_nit(nit)
        if nit_info.get("ok"):
            st.success(f"NIT verificado: {nit_info.get('razon_social')} "
                       f"- {nit_info.get('estado')}")
        else:
            st.warning(nit_info.get("mensaje", "No se pudo verificar el NIT; "
                       "podras verificarlo luego."))

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
    if not auth.enviar_codigo_verificacion(email, token):
        st.warning("No se pudo enviar el correo de verificacion. Verifica la "
                   "configuracion de correo (SMTP) o reenvia el codigo.")
    _abrir_verificacion(email)


def _form_registro_proveedor():
    from models.supplier import TIPOS_PROVEEDOR
    st.caption("Registrate como proveedor. Confirmaremos tu correo para "
               "habilitar el acceso a tus solicitudes de cotizacion.")
    with st.form("registro_prov", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre comercial *")
        nit = c2.text_input("NIT")
        c3, c4 = st.columns(2)
        categoria = c3.selectbox("Rubro", TIPOS_PROVEEDOR)
        ciudad = c4.text_input("Ciudad / Departamento")
        direccion = st.text_input("Direccion")
        materiales = st.text_area("Materiales / servicios que ofrece")
        st.markdown("**Encargado de ventas**")
        c5, c6 = st.columns(2)
        enc = c5.text_input("Nombre del encargado")
        wsp = c6.text_input("WhatsApp")
        st.markdown("**Acceso**")
        c7, c8 = st.columns(2)
        email = c7.text_input("Correo electronico *")
        password = c8.text_input("Contrasena * (min. 8, con letra y numero)",
                                 type="password")
        enviado = st.form_submit_button("Registrar proveedor", type="primary")

    if not enviado:
        return
    if not (nombre and email and password):
        st.error("Completa los campos obligatorios (*).")
        return
    ok, msg = auth.validar_password(password)
    if not ok:
        st.error(msg)
        return
    if auth.email_existe(email):
        st.error("Ya existe una cuenta con ese correo.")
        return
    u = auth.Usuario(perfil="proveedor", nombre_empresa=nombre, nit=nit,
                     direccion=direccion, email=email, encargado_nombre=enc,
                     encargado_whatsapp=wsp, nit_estado=ciudad)
    try:
        _uid, token = auth.registrar_proveedor_con_cuenta(
            u, password, categoria=categoria, materiales=materiales,
            ciudad=ciudad, telefono=wsp)
    except ValueError as e:
        st.error(str(e))
        return
    if not auth.enviar_codigo_verificacion(email, token):
        st.warning("No se pudo enviar el correo de verificacion. Verifica la "
                   "configuracion de correo (SMTP) o reenvia el codigo.")
    _abrir_verificacion(email)
