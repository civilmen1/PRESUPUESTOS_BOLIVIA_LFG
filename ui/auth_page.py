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
        _panel_verificacion(pend)

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
                            "email": email, "enviado": False}
                        st.rerun()

    with tab_registro:
        if es_proveedor:
            _form_registro_proveedor()
        else:
            _form_registro()


def _panel_verificacion(datos: dict):
    """Panel destacado de verificacion de correo (estable, sin dialogos fragiles)."""
    email = datos.get("email", "")
    enviado = datos.get("enviado", True)
    with st.container(border=True):
        st.subheader("Confirma tu correo electronico")
        if enviado:
            st.write(f"Enviamos un codigo de 6 digitos a **{email}**. "
                     "Revisa tu bandeja de entrada (y la carpeta de spam) e "
                     "ingresalo aqui para activar tu cuenta.")
        else:
            st.warning(f"Tu cuenta ({email}) existe pero el correo no esta "
                       "verificado. Pulsa 'Reenviar codigo' y revisa tu correo.")
        with st.form("form_verif"):
            codigo = st.text_input("Codigo de verificacion", max_chars=6)
            c1, c2, c3 = st.columns(3)
            verificar = c1.form_submit_button("Verificar", type="primary",
                                              use_container_width=True)
            reenviar = c2.form_submit_button("Reenviar codigo",
                                             use_container_width=True)
            cancelar = c3.form_submit_button("Cancelar", use_container_width=True)
        if verificar:
            if auth.verificar_email(email, codigo.strip()):
                # Empresa verificada: limpiar TODO y volver al menu principal.
                st.session_state.clear()
                st.session_state["empresa_verificada"] = True
                st.rerun()
            else:
                st.error("Codigo incorrecto. Revisa tu correo e intenta de nuevo.")
        if reenviar:
            token = auth.reenviar_token(email)
            if token is None:
                st.error("No hay una cuenta pendiente con ese correo.")
            elif auth.enviar_codigo_verificacion(email, token):
                st.session_state["verificacion_pendiente"]["enviado"] = True
                st.success("Codigo reenviado. Revisa tu correo (y spam).")
            else:
                st.error("No se pudo enviar el correo. La configuracion de correo "
                         "(SMTP) tiene un problema. Avisa al administrador.")
        if cancelar:
            st.session_state.pop("verificacion_pendiente", None)
            st.rerun()


def _abrir_verificacion(email: str, enviado: bool = True):
    st.session_state["verificacion_pendiente"] = {"email": email,
                                                  "enviado": enviado}
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
        seprec = c3.text_input("SEPREC (registro de comercio) *")
        direccion = c4.text_input("Direccion")
        st.markdown("**Encargado de compras / adquisiciones**")
        c5, c6 = st.columns(2)
        enc_nombre = c5.text_input("Nombre del encargado")
        enc_wsp = c6.text_input("WhatsApp del encargado")
        st.markdown("**Acceso**")
        c7, c8 = st.columns(2)
        email = c7.text_input("Correo electronico *")
        c9, c10 = st.columns(2)
        password = c9.text_input("Contrasena * (min. 8, con letra y numero)",
                                 type="password")
        password2 = c10.text_input("Repetir contrasena *", type="password")
        verificar = st.checkbox("Verificar SEPREC", value=True)
        enviado = st.form_submit_button("Registrar empresa", type="primary")

    if not enviado:
        return
    if not (nombre and email and password and seprec):
        st.error("Completa los campos obligatorios (*).")
        return
    if password != password2:
        st.error("Las contrasenas no coinciden. Vuelve a escribirlas igual.")
        return
    ok, msg = auth.validar_password(password)
    if not ok:
        st.error(msg)
        return
    if auth.email_existe(email):
        st.error("Ya existe una cuenta con ese correo.")
        return

    sep_info = {"ok": False}
    if verificar and seprec:
        sep_info = auth.verificar_seprec(seprec)
        if sep_info.get("ok"):
            extra = (f": {sep_info.get('razon_social')}"
                     if sep_info.get("razon_social") else "")
            st.success(f"SEPREC verificado{extra} - {sep_info.get('estado')}")
        else:
            st.error(sep_info.get("mensaje", "No se pudo verificar el SEPREC."))
            return

    u = auth.Usuario(
        perfil=perfil, nombre_empresa=nombre, nit=nit, seprec=seprec,
        direccion=direccion, email=email, encargado_nombre=enc_nombre,
        encargado_whatsapp=enc_wsp, nit_verificado=sep_info.get("ok", False),
        nit_razon_social=sep_info.get("razon_social", ""),
        nit_estado=sep_info.get("estado", ""))
    try:
        _uid, token = auth.registrar_usuario(u, password)
    except ValueError as e:
        st.error(str(e))
        return
    enviado = auth.enviar_codigo_verificacion(email, token)
    _abrir_verificacion(email, enviado)


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
        email = st.text_input("Correo electronico *")
        c7, c8 = st.columns(2)
        password = c7.text_input("Contrasena * (min. 8, con letra y numero)",
                                 type="password")
        password2 = c8.text_input("Repetir contrasena *", type="password")
        enviado = st.form_submit_button("Registrar proveedor", type="primary")

    if not enviado:
        return
    if not (nombre and email and password):
        st.error("Completa los campos obligatorios (*).")
        return
    if password != password2:
        st.error("Las contrasenas no coinciden. Vuelve a escribirlas igual.")
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
    enviado = auth.enviar_codigo_verificacion(email, token)
    _abrir_verificacion(email, enviado)
