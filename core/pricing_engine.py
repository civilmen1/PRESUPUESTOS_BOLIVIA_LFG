"""Cotizador jerárquico Bolivia (núcleo del sistema).

Orden estricto de búsqueda de precios:
  Nivel 1: Base de Datos de proveedores/precios registrados de Bolivia.
  Nivel 2: Búsqueda web de precios online (homologando unidades).
  Nivel 3: Solicitud automática de cotización por email.

El precio manual validado del ingeniero tiene prioridad máxima.
Aplica reglas de precio adoptado (rules_engine) y registra trazabilidad.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from config import settings
from config.logging_config import get_logger
from core import data_loader
from core.rules_engine import FuentePrecio, PrecioAdoptado, calcular_precio_adoptado
from core.unit_converter import homologar_precio
from models.apu_resource import TIPO_MATERIAL
from models.quotation import NIVEL_BD, NIVEL_EMAIL, NIVEL_WEB
from providers import search_online, supplier_repository, supplier_service
from providers.email_service import RecursoCotizar, enviar_masivo

logger = get_logger(__name__)


@dataclass
class ResultadoCotizacion:
    descripcion: str
    precio_adoptado: float
    unidad: str
    nivel_usado: int            # 0 manual, 1 BD, 2 web, 3 email, -1 sin precio
    fuente: str
    regla: str
    n_fuentes: int
    moneda: str = settings.MONEDA_DEFAULT
    proveedor_id: Optional[int] = None
    url: str = ""
    vigencia_dias: int = settings.VIGENCIA_DIAS_DEFAULT
    alertas: List[str] = field(default_factory=list)
    fuentes_detalle: List[dict] = field(default_factory=list)


def _fecha_hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cotizar_recurso(
    descripcion: str,
    unidad: str,
    tipo: str = TIPO_MATERIAL,
    categoria: str = "",
    region: str = "",
    proyecto_nombre: str = "Proyecto",
    precio_manual: Optional[float] = None,
    permitir_web: bool = True,
    permitir_email: bool = False,
    vigencia_dias: int = settings.VIGENCIA_DIAS_DEFAULT,
) -> ResultadoCotizacion:
    """Ejecuta el cotizador jerárquico para un recurso y devuelve el resultado."""
    fuentes: List[FuentePrecio] = []
    detalle: List[dict] = []

    # Prioridad máxima: precio manual validado por el ingeniero
    if precio_manual and precio_manual > 0:
        fuentes.append(FuentePrecio(precio=precio_manual, nivel=0,
                                    fecha=_fecha_hoy(), fuente="manual",
                                    validado=True))
        detalle.append({"nivel": 0, "fuente": "manual", "precio": precio_manual})

    # --------------------------------------------------------------------- #
    # NIVEL 1: Banco de APU de referencia (precios reales de Bolivia)
    # --------------------------------------------------------------------- #
    if not fuentes:
        try:
            from core import banco_apu
            pb = banco_apu.buscar_precio(descripcion)
            if pb and pb.get("precio"):
                precio_h, _ = homologar_precio(pb["precio"], pb["unidad"], unidad)
                precio_final = precio_h if precio_h is not None else pb["precio"]
                fuentes.append(FuentePrecio(
                    precio=precio_final, nivel=NIVEL_BD, fecha=_fecha_hoy(),
                    fuente="banco_apu"))
                detalle.append({"nivel": 1, "fuente": "banco_apu",
                                "precio": precio_final})
        except Exception:
            pass

    # --------------------------------------------------------------------- #
    # NIVEL 1: Base de Datos Bolivia (proveedores registrados)
    # --------------------------------------------------------------------- #
    if not fuentes:
        if tipo == TIPO_MATERIAL:
            encontrados = supplier_repository.buscar_precios(
                descripcion, categoria=categoria, region=region)
            for e in encontrados:
                precio_h, _ = homologar_precio(e["precio"], e["unidad"], unidad)
                precio_final = precio_h if precio_h is not None else e["precio"]
                fuentes.append(FuentePrecio(
                    precio=precio_final, nivel=NIVEL_BD, fecha=e["fecha"],
                    fuente=f"BD:{e.get('proveedor') or 'interna'}",
                    proveedor_id=e.get("proveedor_id"), url=e.get("url") or ""))
                detalle.append({"nivel": 1, "fuente": "BD", "precio": precio_final,
                                "proveedor": e.get("proveedor"), "fecha": e["fecha"]})
        else:
            # mano de obra / equipos: BD local de salarios/equipos
            local = data_loader.precio_local_recurso(categoria, descripcion)
            if local:
                precio_h, _ = homologar_precio(local["precio"], local["unidad"], unidad)
                precio_final = precio_h if precio_h is not None else local["precio"]
                fuentes.append(FuentePrecio(
                    precio=precio_final, nivel=NIVEL_BD, fecha=_fecha_hoy(),
                    fuente=local["fuente"]))
                detalle.append({"nivel": 1, "fuente": local["fuente"],
                                "precio": precio_final})

    # --------------------------------------------------------------------- #
    # NIVEL 3 (respuestas reales): cotizaciones que los proveedores ya
    # respondieron en su portal. Tienen prioridad sobre la web.
    # --------------------------------------------------------------------- #
    if not fuentes and tipo == TIPO_MATERIAL:
        from providers.email_service import buscar_respuestas_cotizacion
        for rc in buscar_respuestas_cotizacion(descripcion):
            precio_h, _ = homologar_precio(rc["precio"], rc.get("unidad", unidad),
                                           unidad)
            precio_final = precio_h if precio_h is not None else rc["precio"]
            fuentes.append(FuentePrecio(
                precio=precio_final, nivel=NIVEL_EMAIL, fecha=rc.get("fecha_respuesta"),
                fuente=f"email:{rc.get('proveedor_nombre') or 'proveedor'}",
                proveedor_id=rc.get("proveedor_id")))
            detalle.append({"nivel": 3, "fuente": "email_respondido",
                            "precio": precio_final,
                            "proveedor": rc.get("proveedor_nombre")})

    # --------------------------------------------------------------------- #
    # NIVEL 2: Búsqueda web (solo materiales, si no hay nada en BD)
    # --------------------------------------------------------------------- #
    if not fuentes and permitir_web and tipo == TIPO_MATERIAL:
        web = search_online.buscar_precios_online(
            descripcion, unidad_destino=unidad, categoria=categoria, region=region)
        for w in web:
            fuentes.append(FuentePrecio(
                precio=w["precio"], nivel=NIVEL_WEB, fecha=_fecha_hoy(),
                fuente=f"web:{w['proveedor']}", url=w["url"]))
            detalle.append({"nivel": 2, "fuente": "web", "precio": w["precio"],
                            "proveedor": w["proveedor"], "url": w["url"],
                            "inconsistencia_unidad": w["inconsistencia_unidad"]})

    # --------------------------------------------------------------------- #
    # NIVEL 3: Solicitud por email (sin precio inmediato; queda pendiente)
    # --------------------------------------------------------------------- #
    email_enviado = False
    if not fuentes and permitir_email and tipo == TIPO_MATERIAL:
        candidatos = supplier_service.candidatos_para_cotizar(categoria, region)
        if candidatos:
            envios = enviar_masivo(
                candidatos, proyecto_nombre,
                [RecursoCotizar(descripcion=descripcion, unidad=unidad)])
            email_enviado = any(e.enviado for e in envios)
            detalle.append({"nivel": 3, "fuente": "email",
                            "proveedores_contactados": len(candidatos),
                            "enviados": sum(1 for e in envios if e.enviado)})
            logger.info("Nivel 3: %d proveedores contactados para '%s'",
                        len(candidatos), descripcion)

    # --------------------------------------------------------------------- #
    # Aplicar reglas de precio adoptado
    # --------------------------------------------------------------------- #
    adoptado: PrecioAdoptado = calcular_precio_adoptado(fuentes, vigencia_dias)

    if not fuentes:
        nivel_usado = NIVEL_EMAIL if email_enviado else -1
        alertas = (["Cotización solicitada por email; pendiente de respuesta"]
                   if email_enviado else
                   ["Sin precio en BD ni web; sin proveedores para email"])
        return ResultadoCotizacion(
            descripcion=descripcion, precio_adoptado=0.0, unidad=unidad,
            nivel_usado=nivel_usado, fuente="email" if email_enviado else "ninguna",
            regla="pendiente" if email_enviado else "sin_precio", n_fuentes=0,
            alertas=alertas, fuentes_detalle=detalle, vigencia_dias=vigencia_dias)

    return ResultadoCotizacion(
        descripcion=descripcion, precio_adoptado=adoptado.precio, unidad=unidad,
        nivel_usado=adoptado.nivel, fuente=adoptado.fuente, regla=adoptado.regla,
        n_fuentes=adoptado.n_fuentes, proveedor_id=adoptado.proveedor_id,
        url=adoptado.url, vigencia_dias=vigencia_dias, alertas=adoptado.alertas,
        fuentes_detalle=detalle)
