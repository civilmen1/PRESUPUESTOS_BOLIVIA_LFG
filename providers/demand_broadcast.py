"""Difusión de demanda de materiales a empresas proveedoras.

Cuando un comprador (empresa/entidad logueada) genera su proyecto y sus APUs,
los materiales a cotizar se registran en `solicitudes_materiales` y se envían
por correo a las empresas proveedoras que ofrecen ese tipo de material. El
correo incluye: descripción, tipo, unidad, cantidad y los datos del encargado
de adquisiciones del comprador, para que la empresa patrocinadora reciba la
información del posible comprador.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from config.logging_config import get_logger
from core.database import db_session
from core.text_cleaner import normalizar
from models.apu_resource import TIPO_MATERIAL
from providers import supplier_repository

logger = get_logger(__name__)


@dataclass
class Comprador:
    usuario_id: int = 0
    empresa: str = ""
    encargado_nombre: str = ""
    encargado_email: str = ""
    encargado_whatsapp: str = ""
    region: str = ""


def comprador_desde_usuario(usuario) -> Comprador:
    return Comprador(
        usuario_id=getattr(usuario, "id", 0) or 0,
        empresa=getattr(usuario, "nombre_empresa", "") or "",
        encargado_nombre=getattr(usuario, "encargado_nombre", "") or "",
        encargado_email=getattr(usuario, "email", "") or "",
        encargado_whatsapp=getattr(usuario, "encargado_whatsapp", "") or "",
        region=getattr(usuario, "nit_estado", "") or "")


def _registrar_solicitud(proyecto_id, comp: Comprador, descripcion, tipo,
                         unidad, cantidad) -> int:
    with db_session() as conn:
        cur = conn.execute(
            """INSERT INTO solicitudes_materiales
               (proyecto_id, usuario_id, empresa_compradora, encargado_nombre,
                encargado_email, encargado_whatsapp, descripcion, tipo_material,
                unidad, cantidad, region)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (proyecto_id, comp.usuario_id, comp.empresa, comp.encargado_nombre,
             comp.encargado_email, comp.encargado_whatsapp, descripcion, tipo,
             unidad, cantidad, comp.region))
        return cur.lastrowid


def consolidar_materiales(proyecto_id: int) -> List[dict]:
    """Suma las cantidades de cada material del proyecto (cantidad_apu × cantidad
    del ítem) para obtener la demanda total por material."""
    from core import repositories
    items = repositories.listar_items(proyecto_id)
    acum: dict[tuple, dict] = {}
    for it in items:
        if it.es_modulo:
            continue
        for r in repositories.listar_recursos(it.id):
            if r.tipo != TIPO_MATERIAL:
                continue
            clave = (normalizar(r.descripcion), normalizar(r.unidad))
            registro = acum.setdefault(clave, {
                "descripcion": r.descripcion, "tipo": r.tipo,
                "unidad": r.unidad, "cantidad": 0.0,
                "categoria": getattr(r, "_categoria", "")})
            registro["cantidad"] += (r.cantidad_apu or 0) * (it.cantidad or 0)
    return list(acum.values())


def _proveedores_para(categoria: str, descripcion: str, region: str = ""):
    """Empresas proveedoras que ofrecen ese material (por categoría o keywords)."""
    candidatos = []
    palabras = [w for w in normalizar(descripcion).split() if len(w) >= 3]
    for p in supplier_repository.listar_proveedores():
        if not p.email:
            continue
        texto = normalizar(f"{p.categoria} {p.materiales_servicios}")
        if (categoria and normalizar(categoria) in texto) or \
           any(w in texto for w in palabras):
            candidatos.append(p)
    return candidatos


def difundir_demanda(proyecto_id: int, comp: Comprador,
                     enviar_email: bool = True) -> dict:
    """Registra los materiales del proyecto y los envía a empresas proveedoras.

    Devuelve un resumen {materiales, solicitudes, correos_enviados}.
    """
    from providers.email_service import enviar_solicitud, RecursoCotizar

    materiales = consolidar_materiales(proyecto_id)
    solicitudes = 0
    correos = 0
    proveedores_contactados = set()

    for m in materiales:
        _registrar_solicitud(proyecto_id, comp, m["descripcion"], m["tipo"],
                             m["unidad"], round(m["cantidad"], 2))
        solicitudes += 1
        if not enviar_email:
            continue
        provs = _proveedores_para(m.get("categoria", ""), m["descripcion"],
                                  comp.region)
        for p in provs:
            # incluye datos del comprador (posible cliente) en el correo
            recurso = RecursoCotizar(descripcion=m["descripcion"],
                                     unidad=m["unidad"],
                                     cantidad=round(m["cantidad"], 2))
            proyecto_txt = (f"{comp.empresa} — Encargado de adquisiciones: "
                            f"{comp.encargado_nombre} ({comp.encargado_email}"
                            f"{', WhatsApp ' + comp.encargado_whatsapp if comp.encargado_whatsapp else ''})")
            try:
                r = enviar_solicitud(p, proyecto_txt, [recurso])
                if r.enviado:
                    correos += 1
                    proveedores_contactados.add(p.id)
            except Exception:
                logger.exception("Error enviando demanda a proveedor %s", p.id)

    logger.info("Demanda difundida: %d materiales, %d correos a %d proveedores",
                solicitudes, correos, len(proveedores_contactados))
    return {"materiales": len(materiales), "solicitudes": solicitudes,
            "correos_enviados": correos,
            "proveedores": len(proveedores_contactados)}


def solicitudes_de_proyecto(proyecto_id: int) -> List[dict]:
    with db_session() as conn:
        filas = conn.execute(
            "SELECT * FROM solicitudes_materiales WHERE proyecto_id=? "
            "ORDER BY id", (proyecto_id,)).fetchall()
        return [dict(f) for f in filas]
