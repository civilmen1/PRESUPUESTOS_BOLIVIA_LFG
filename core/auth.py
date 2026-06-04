"""Autenticación de empresas y entidades (login, registro, verificación).

Funciones:
  - registrar_usuario: alta de empresa/entidad con datos requeridos.
  - hash de contraseñas con PBKDF2 (sin dependencias externas).
  - verificación de correo por código (token enviado por email; en modo
    AUTH_EMAIL_DRY_RUN el código se muestra para pruebas).
  - verificación de NIT vía API externa (Verifik); para entidades públicas se
    valida por email.
  - login: solo permite acceder si el correo está verificado.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional

from config import settings
from config.logging_config import get_logger
from core.database import db_session

logger = get_logger(__name__)


@dataclass
class Usuario:
    id: Optional[int] = None
    perfil: str = "contratista"        # contratista | entidad | proveedor
    nombre_empresa: str = ""
    nit: str = ""
    seprec: str = ""
    direccion: str = ""
    email: str = ""
    encargado_nombre: str = ""
    encargado_whatsapp: str = ""
    email_verificado: bool = False
    nit_verificado: bool = False
    nit_razon_social: str = ""
    nit_estado: str = ""
    estado: str = "activo"
    proveedor_id: Optional[int] = None


# --------------------------------------------------------------------------- #
# Hash de contraseñas (PBKDF2-HMAC-SHA256)
# --------------------------------------------------------------------------- #
def _hash_password(password: str) -> str:
    sal = settings.AUTH_SALT.encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, 120_000)
    return dk.hex()


def _verificar_password(password: str, hash_guardado: str) -> bool:
    return secrets.compare_digest(_hash_password(password), hash_guardado or "")


def validar_password(password: str) -> tuple[bool, str]:
    """Valida que la contraseña cumpla los estándares mínimos de seguridad.

    Reglas: mínimo 8 caracteres y al menos una letra y un número.
    Devuelve (es_valida, mensaje).
    """
    if len(password or "") < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not any(c.isalpha() for c in password):
        return False, "La contraseña debe incluir al menos una letra."
    if not any(c.isdigit() for c in password):
        return False, "La contraseña debe incluir al menos un número."
    return True, "Contraseña válida."


# --------------------------------------------------------------------------- #
# Registro
# --------------------------------------------------------------------------- #
def email_existe(email: str) -> bool:
    with db_session() as conn:
        r = conn.execute("SELECT 1 FROM usuarios WHERE lower(email)=lower(?)",
                         (email.strip(),)).fetchone()
        return r is not None


def registrar_usuario(u: Usuario, password: str) -> tuple[Optional[int], str]:
    """Registra una empresa/entidad. Devuelve (id, token_verificacion).

    Genera un token de verificación de correo. El usuario NO podrá entrar hasta
    verificar el correo con ese token.
    """
    if email_existe(u.email):
        raise ValueError("Ya existe una cuenta con ese correo electrónico.")
    ok, msg = validar_password(password)
    if not ok:
        raise ValueError(msg)
    token = f"{secrets.randbelow(1000000):06d}"  # código de 6 dígitos
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO usuarios
               (perfil, nombre_empresa, nit, seprec, direccion, email,
                encargado_nombre, encargado_whatsapp, password_hash,
                token_verificacion, nit_verificado, nit_razon_social, nit_estado,
                proveedor_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (u.perfil, u.nombre_empresa, u.nit, u.seprec, u.direccion,
             u.email.strip(), u.encargado_nombre, u.encargado_whatsapp,
             _hash_password(password), token, int(u.nit_verificado),
             u.nit_razon_social, u.nit_estado, u.proveedor_id))
        return cur.lastrowid, token


def registrar_proveedor_con_cuenta(u: Usuario, password: str,
                                   categoria: str = "otros",
                                   materiales: str = "", ciudad: str = "",
                                   telefono: str = "") -> tuple[int, str]:
    """Registra un proveedor: crea su ficha en 'proveedores' y su cuenta de login.

    Devuelve (usuario_id, token). El usuario queda vinculado a su proveedor_id.
    """
    from models.supplier import Proveedor
    from providers import supplier_service
    pid = supplier_service.alta_manual(Proveedor(
        nombre=u.nombre_empresa, nit=u.nit, email=u.email, telefono=telefono,
        whatsapp=u.encargado_whatsapp or telefono, region=u.nit_estado or "",
        ciudad=ciudad, direccion=u.direccion, categoria=categoria,
        materiales_servicios=materiales))
    u.perfil = "proveedor"
    u.proveedor_id = pid
    uid, token = registrar_usuario(u, password)
    return uid, token


# --------------------------------------------------------------------------- #
# Verificación de correo
# --------------------------------------------------------------------------- #
def enviar_codigo_verificacion(email: str, token: str) -> bool:
    """Envía el código de verificación por correo real (Gmail/SMTP)."""
    if settings.AUTH_EMAIL_DRY_RUN:
        logger.info("[DRY-RUN] Código de verificación para %s: %s", email, token)
        return True
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP no configurado: no se puede enviar el código a %s",
                       email)
        return False
    try:
        import smtplib
        from email.mime.text import MIMEText
        cuerpo = (f"Su código de verificación para {settings.APP_NAME} es: "
                  f"{token}\n\nIngréselo en la aplicación para activar su cuenta.")
        msg = MIMEText(cuerpo, "plain", "utf-8")
        msg["Subject"] = f"Código de verificación - {settings.APP_NAME}"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.sendmail(settings.SMTP_FROM, [email], msg.as_string())
        logger.info("Código de verificación enviado correctamente a %s", email)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP AUTENTICACION fallida para %s: revisa SMTP_USER y la "
                     "CONTRASEÑA DE APLICACION de Gmail (sin espacios). %s",
                     settings.SMTP_USER, exc)
        return False
    except Exception as exc:
        logger.error("Error enviando código de verificación a %s: %s (%s)",
                     email, exc, type(exc).__name__)
        return False


def verificar_email(email: str, token: str) -> bool:
    """Marca el correo como verificado si el token coincide."""
    with db_session() as conn:
        r = conn.execute(
            "SELECT token_verificacion FROM usuarios WHERE lower(email)=lower(?)",
            (email.strip(),)).fetchone()
        if not r or not r["token_verificacion"]:
            return False
        if secrets.compare_digest(str(r["token_verificacion"]), str(token).strip()):
            conn.execute(
                """UPDATE usuarios SET email_verificado=1, token_verificacion=NULL
                   WHERE lower(email)=lower(?)""", (email.strip(),))
            return True
    return False


def reenviar_token(email: str) -> Optional[str]:
    """Genera y devuelve un nuevo token de verificación para el correo."""
    token = f"{secrets.randbelow(1000000):06d}"
    with db_session() as conn:
        cur = conn.execute(
            """UPDATE usuarios SET token_verificacion=?
               WHERE lower(email)=lower(?) AND email_verificado=0""",
            (token, email.strip()))
        return token if cur.rowcount else None


# --------------------------------------------------------------------------- #
# Verificación de SEPREC (Registro de Comercio de Bolivia)
# --------------------------------------------------------------------------- #
def verificar_seprec(seprec: str) -> dict:
    """Verifica un numero de matricula SEPREC.

    Orden de verificacion:
      1. API oficial del SEPREC (consulta de estado de habilitacion).
      2. Portal oficial con navegador (si SEPREC_USAR_NAVEGADOR), como respaldo.
      3. Validacion de formato (numerico de 6 a 12 digitos).
    Devuelve {ok, razon_social, estado, mensaje, fuente}.
    """
    seprec = (seprec or "").strip().replace("-", "").replace(" ", "")
    if not seprec:
        return {"ok": False, "mensaje": "Numero de SEPREC vacio."}

    # 1) API oficial del SEPREC (lo mas rapido y estable)
    res_api = _consultar_seprec_api(seprec)
    if res_api is not None:
        return res_api

    # 2) Portal oficial con navegador (respaldo si la API no respondio)
    if settings.SEPREC_USAR_NAVEGADOR:
        try:
            from core.seprec_verifier import verificar_seprec_navegador
            res = verificar_seprec_navegador(seprec)
            if res.get("fuente") in ("seprec_portal",):
                return res
            logger.info("SEPREC navegador no concluyente (%s); se usa respaldo",
                        res.get("fuente"))
        except Exception as exc:
            logger.error("Fallo verificacion SEPREC por navegador: %s", exc)

    # 3) Validacion de formato
    if seprec.isdigit() and 6 <= len(seprec) <= 12:
        return {"ok": True, "razon_social": "", "estado": "FORMATO VALIDO",
                "mensaje": "Formato de SEPREC valido (verificacion de formato).",
                "fuente": "formato"}
    return {"ok": False, "mensaje": "El numero de SEPREC no tiene un formato "
            "valido (debe ser numerico, de 6 a 12 digitos)."}


def _consultar_seprec_api(seprec: str):
    """Consulta la API oficial del SEPREC de estado de habilitacion.

    Devuelve un dict con el resultado, o None si la API no esta disponible o no
    responde (para que el flujo caiga al respaldo).
    """
    base = settings.SEPREC_API_URL or settings.SEPREC_API_BASE
    if not base:
        return None
    try:
        import requests
    except ImportError:
        return None

    headers = {"Accept": "application/json",
               "User-Agent": "APUBolivia/1.0"}
    if settings.SEPREC_API_TOKEN:
        headers["Authorization"] = f"Bearer {settings.SEPREC_API_TOKEN}"

    # Si la URL trae {seprec}, se usa tal cual; si no, se prueban variantes
    # comunes: matricula al final de la ruta o como parametro de consulta.
    if "{seprec}" in base:
        intentos = [(base.format(seprec=seprec), None)]
    else:
        b = base.rstrip("/")
        intentos = [
            (f"{b}/{seprec}", None),
            (b, {"matricula": seprec}),
            (b, {"nroMatricula": seprec}),
        ]

    for url, params in intentos:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            return _interpretar_seprec(data, seprec)
        except Exception as exc:
            logger.warning("SEPREC API intento fallido (%s): %s", url, exc)
            continue
    logger.error("No se pudo consultar la API del SEPREC para %s", seprec)
    return None


def _interpretar_seprec(data, seprec: str) -> dict:
    """Interpreta la respuesta JSON de la API del SEPREC de forma flexible."""
    d = data.get("data", data) if isinstance(data, dict) else {}
    if isinstance(d, list):
        d = d[0] if d else {}
    texto = str(data).lower()

    # Razon social y estado (nombres flexibles segun la respuesta real).
    razon = (d.get("razonSocial") or d.get("razon_social") or d.get("nombre") or
             d.get("nombreComercial") or "")
    estado = str(d.get("estado") or d.get("estadoHabilitacion") or
                 d.get("habilitado") or d.get("status") or "").upper()

    # Determinar si esta habilitada.
    no_encontrado = ("no se encontr" in texto or "not found" in texto or
                     d.get("encontrado") is False)
    habilitada = (not no_encontrado and (
        bool(razon) or estado in ("HABILITADA", "VIGENTE", "ACTIVA", "ACTIVO",
                                  "TRUE", "1") or d.get("habilitado") in (True, 1)))

    if no_encontrado or (not habilitada and not razon):
        return {"ok": False, "estado": estado or "NO ENCONTRADO",
                "mensaje": "La matricula no se encontro o no esta habilitada en "
                "el SEPREC.", "fuente": "seprec_api"}
    return {"ok": True, "razon_social": razon, "estado": estado or "HABILITADA",
            "mensaje": "Matricula verificada en el SEPREC.", "fuente": "seprec_api"}


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #
def login(email: str, password: str) -> tuple[Optional[Usuario], str]:
    """Autentica un usuario. Devuelve (Usuario, mensaje).

    Falla si el correo no está verificado.
    """
    with db_session() as conn:
        r = conn.execute("SELECT * FROM usuarios WHERE lower(email)=lower(?)",
                         (email.strip(),)).fetchone()
    if not r:
        return None, "No existe una cuenta con ese correo."
    if not _verificar_password(password, r["password_hash"]):
        return None, "Contraseña incorrecta."
    if not r["email_verificado"]:
        return None, "Debes verificar tu correo electrónico antes de ingresar."
    if r["estado"] != "activo":
        return None, "La cuenta no está activa."
    with db_session() as conn:
        conn.execute("UPDATE usuarios SET ultimo_acceso=datetime('now') WHERE id=?",
                     (r["id"],))
    u = Usuario(
        id=r["id"], perfil=r["perfil"], nombre_empresa=r["nombre_empresa"],
        nit=r["nit"] or "", seprec=r["seprec"] or "", direccion=r["direccion"] or "",
        email=r["email"], encargado_nombre=r["encargado_nombre"] or "",
        encargado_whatsapp=r["encargado_whatsapp"] or "",
        email_verificado=True, nit_verificado=bool(r["nit_verificado"]),
        nit_razon_social=r["nit_razon_social"] or "", nit_estado=r["nit_estado"] or "",
        estado=r["estado"], proveedor_id=r["proveedor_id"])
    return u, "Bienvenido."
