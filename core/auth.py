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
    """Verifica un número de matrícula SEPREC.

    Devuelve {ok, razon_social, estado, mensaje, fuente}.

    Si se configura una API (SEPREC_API_URL, opcional con SEPREC_API_TOKEN), se
    consulta en línea. Si no, valida el formato de la matrícula (debe ser
    numérica de 6 a 12 dígitos) como verificación básica.
    """
    seprec = (seprec or "").strip().replace("-", "").replace(" ", "")
    if not seprec:
        return {"ok": False, "mensaje": "Número de SEPREC vacío."}

    api_url = settings.SEPREC_API_URL
    if api_url:
        try:
            import requests
            headers = {}
            if settings.SEPREC_API_TOKEN:
                headers["Authorization"] = f"Bearer {settings.SEPREC_API_TOKEN}"
            resp = requests.get(api_url.format(seprec=seprec), headers=headers,
                                timeout=15)
            resp.raise_for_status()
            data = resp.json()
            d = data.get("data", data)
            return {
                "ok": True,
                "razon_social": d.get("razonSocial") or d.get("nombre") or
                                d.get("razon_social", ""),
                "estado": d.get("estado") or d.get("status", "VIGENTE"),
                "mensaje": "SEPREC verificado en línea.",
                "fuente": "seprec_api",
            }
        except Exception as exc:
            logger.error("Error verificando SEPREC %s en línea: %s", seprec, exc)
            return {"ok": False, "mensaje": f"No se pudo verificar el SEPREC en "
                    f"línea: {exc}"}

    # Sin API configurada: validación de formato.
    if seprec.isdigit() and 6 <= len(seprec) <= 12:
        return {"ok": True, "razon_social": "", "estado": "FORMATO VÁLIDO",
                "mensaje": "Formato de SEPREC válido (verificación de formato).",
                "fuente": "formato"}
    return {"ok": False, "mensaje": "El número de SEPREC no tiene un formato "
            "válido (debe ser numérico, de 6 a 12 dígitos)."}


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
