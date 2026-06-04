"""Módulo de email automático para solicitudes de cotización (Nivel 3).

- Genera correos HTML con plantilla.
- Envía por SMTP (o registra en modo EMAIL_DRY_RUN).
- Invita al proveedor a la base nacional de precios de Bolivia.
- Registra cada contacto en la tabla contactos_email.
- Soporta recordatorio automático a los N días.
"""
from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from config import settings
from config.logging_config import get_logger
from core.database import db_session
from models.supplier import Proveedor

logger = get_logger(__name__)


@dataclass
class RecursoCotizar:
    descripcion: str
    unidad: str
    cantidad: float = 0.0


@dataclass
class ResultadoEnvio:
    proveedor_id: Optional[int]
    email: str
    enviado: bool
    dry_run: bool
    asunto: str
    error: str = ""
    contacto_id: Optional[int] = None
    alertas: List[str] = field(default_factory=list)


def construir_html(proveedor: Proveedor, proyecto: str,
                   recursos: List[RecursoCotizar]) -> str:
    filas = "".join(
        f"<tr><td>{r.descripcion}</td><td style='text-align:center'>{r.unidad}</td>"
        f"<td style='text-align:right'>{r.cantidad:g}</td></tr>"
        for r in recursos
    )
    return f"""\
<html><body style="font-family:Arial,sans-serif;color:#222;font-size:14px">
  <p>Estimados <strong>{proveedor.nombre or 'proveedor'}</strong>:</p>
  <p>Desde <strong>{settings.SMTP_FROM_NAME}</strong> estamos elaborando el
     presupuesto del proyecto <strong>{proyecto}</strong> en Bolivia y deseamos
     solicitar su cotización para los siguientes recursos:</p>
  <table border="1" cellpadding="6" cellspacing="0"
         style="border-collapse:collapse;width:100%">
    <thead style="background:#f0f0f0">
      <tr><th align="left">Descripción</th><th>Unidad</th><th>Cantidad ref.</th></tr>
    </thead>
    <tbody>{filas}</tbody>
  </table>
  <p>Le agradeceremos indicar <strong>precio unitario, plazo de entrega y
     disponibilidad</strong>, así como la vigencia de la oferta.</p>
  <hr>
  <p>🇧🇴 <strong>Invitación:</strong> lo invitamos a formar parte de la
     <strong>base de precios de materiales más grande de Bolivia</strong>.
     Regístrese gratis aquí:
     <a href="{settings.REGISTRO_PROVEEDOR_URL}">{settings.REGISTRO_PROVEEDOR_URL}</a>.</p>
  <p>Atentamente,<br>{settings.SMTP_FROM_NAME}<br>{settings.SMTP_FROM}</p>
</body></html>"""


def _registrar_contacto(proveedor_id: Optional[int], asunto: str, cuerpo: str,
                        estado: str, observaciones: str = "") -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO contactos_email
               (proveedor_id, asunto, cuerpo, estado, observaciones)
               VALUES (?,?,?,?,?)""",
            (proveedor_id, asunto, cuerpo, estado, observaciones),
        )
        return cur.lastrowid


def enviar_solicitud(proveedor: Proveedor, proyecto: str,
                     recursos: List[RecursoCotizar]) -> ResultadoEnvio:
    """Envía (o simula) una solicitud de cotización a un proveedor."""
    asunto = f"Solicitud de cotización - {proyecto}"
    html = construir_html(proveedor, proyecto, recursos)

    if not proveedor.email:
        cid = _registrar_contacto(proveedor.id, asunto, html, "sin_email",
                                  "Proveedor sin email; usar WhatsApp/formulario")
        return ResultadoEnvio(proveedor.id, "", False, settings.EMAIL_DRY_RUN, asunto,
                              "Proveedor sin email", cid,
                              ["Proveedor sin email registrado"])

    if settings.EMAIL_DRY_RUN:
        cid = _registrar_contacto(proveedor.id, asunto, html, "simulado",
                                  "EMAIL_DRY_RUN activo: no se envió correo real")
        logger.info("[DRY-RUN] Email simulado a %s (%s)", proveedor.email, asunto)
        return ResultadoEnvio(proveedor.id, proveedor.email, True, True, asunto,
                              "", cid, ["Modo simulación (EMAIL_DRY_RUN)"])

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        msg["To"] = proveedor.email
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [proveedor.email], msg.as_string())

        cid = _registrar_contacto(proveedor.id, asunto, html, "enviado")
        logger.info("Email enviado a %s", proveedor.email)
        return ResultadoEnvio(proveedor.id, proveedor.email, True, False, asunto,
                              "", cid)
    except Exception as exc:  # pragma: no cover - depende de red/SMTP
        logger.exception("Error enviando email a %s", proveedor.email)
        cid = _registrar_contacto(proveedor.id, asunto, html, "error", str(exc))
        return ResultadoEnvio(proveedor.id, proveedor.email, False, False, asunto,
                              str(exc), cid)


def enviar_masivo(proveedores: List[Proveedor], proyecto: str,
                  recursos: List[RecursoCotizar]) -> List[ResultadoEnvio]:
    return [enviar_solicitud(p, proyecto, recursos) for p in proveedores]


def registrar_respuesta(contacto_id: int, interesado_registro: bool = False,
                        observaciones: str = "") -> None:
    """Marca que un proveedor respondió un contacto previo."""
    with db_session() as conn:
        conn.execute(
            """UPDATE contactos_email SET respondio=1,
               fecha_respuesta=datetime('now'), interesado_registro=?,
               estado='respondido', observaciones=? WHERE id=?""",
            (int(interesado_registro), observaciones, contacto_id),
        )


def pendientes_recordatorio(dias: int = settings.EMAIL_RECORDATORIO_DIAS) -> List[dict]:
    """Contactos sin respuesta con más de `dias` días y sin recordatorio."""
    with db_session() as conn:
        filas = conn.execute(
            """SELECT * FROM contactos_email
               WHERE respondio=0 AND recordatorio_enviado=0
               AND julianday('now') - julianday(fecha_envio) >= ?""",
            (dias,),
        ).fetchall()
        return [dict(f) for f in filas]


# --------------------------------------------------------------------------- #
# Portal del PROVEEDOR: ver solicitudes y responder cotizaciones
# --------------------------------------------------------------------------- #
def solicitudes_de_proveedor(proveedor_id: int) -> List[dict]:
    """Lista las solicitudes de cotización recibidas por un proveedor."""
    with db_session() as conn:
        filas = conn.execute(
            """SELECT * FROM contactos_email
               WHERE proveedor_id=? ORDER BY fecha_envio DESC""",
            (proveedor_id,)).fetchall()
        return [dict(f) for f in filas]


def guardar_respuesta_cotizacion(contacto_id: int, proveedor_id: int,
                                 descripcion: str, unidad: str, precio: float,
                                 moneda: str = "BOB", plazo_entrega: str = "",
                                 disponibilidad: str = "",
                                 vigencia_dias: int = 30,
                                 observaciones: str = "") -> int:
    """Registra el precio cotizado por un proveedor para un material."""
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO respuestas_cotizacion
               (contacto_id, proveedor_id, descripcion, unidad, precio, moneda,
                plazo_entrega, disponibilidad, vigencia_dias, observaciones)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (contacto_id, proveedor_id, descripcion, unidad, precio, moneda,
             plazo_entrega, disponibilidad, vigencia_dias, observaciones))
        # marca el contacto como respondido
        conn.execute(
            """UPDATE contactos_email SET respondio=1,
               fecha_respuesta=datetime('now'), estado='respondido' WHERE id=?""",
            (contacto_id,))
        return cur.lastrowid


def respuestas_de_proveedor(proveedor_id: int) -> List[dict]:
    """Historial de cotizaciones enviadas por un proveedor."""
    with db_session() as conn:
        filas = conn.execute(
            """SELECT * FROM respuestas_cotizacion
               WHERE proveedor_id=? ORDER BY fecha_respuesta DESC""",
            (proveedor_id,)).fetchall()
        return [dict(f) for f in filas]


def buscar_respuestas_cotizacion(descripcion: str) -> List[dict]:
    """Busca respuestas de proveedores que coincidan con una descripción.

    Estas cotizaciones (precio confirmado por el proveedor) alimentan el
    cotizador como fuente de Nivel 3 (email confirmado), con prioridad sobre
    la búsqueda web.
    """
    from core.text_cleaner import normalizar
    palabras = [w for w in normalizar(descripcion).split() if len(w) >= 3]
    with db_session() as conn:
        filas = conn.execute(
            """SELECT rc.*, p.nombre AS proveedor_nombre, p.region AS region
               FROM respuestas_cotizacion rc
               LEFT JOIN proveedores p ON rc.proveedor_id = p.id""").fetchall()
    out = []
    for f in filas:
        desc = normalizar(f["descripcion"] or "")
        if palabras and any(w in desc for w in palabras):
            out.append(dict(f))
    return out
