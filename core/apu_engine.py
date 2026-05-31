"""Motor de generación de APU.

1. Infiere recursos (materiales, mano de obra, equipos) por ítem usando
   plantillas de rendimientos y palabras clave / texto técnico vinculado.
2. Cotiza cada recurso con el cotizador jerárquico (pricing_engine).
3. Calcula el resultado del APU (costos, indirectos, utilidad, impuestos).
"""
from __future__ import annotations

from typing import List, Optional

from config.logging_config import get_logger
from core import data_loader, repositories
from core.pricing_engine import cotizar_recurso
from core.sabs import calcular_desglose
from core.text_cleaner import normalizar
from models.apu_resource import (RecursoAPU, TIPO_EQUIPO, TIPO_MANO_OBRA,
                                 TIPO_MATERIAL)
from models.apu_result import ResultadoAPU
from models.item import Item
from models.project import Proyecto
from models.quotation import Cotizacion

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Inferencia de recursos
# --------------------------------------------------------------------------- #
def _seleccionar_plantilla(item: Item, texto_extra: str = "") -> dict:
    """Selecciona la plantilla de rendimientos más adecuada para el ítem."""
    data = data_loader.rendimientos()
    plantillas = data.get("plantillas", [])
    texto = normalizar(f"{item.descripcion} {item.palabras_clave} {texto_extra}")

    mejor, mejor_score = None, 0
    for plantilla in plantillas:
        score = sum(1 for kw in plantilla.get("keywords", [])
                    if normalizar(kw) in texto)
        if score > mejor_score:
            mejor, mejor_score = plantilla, score
    if mejor:
        logger.info("Ítem '%s' -> plantilla '%s' (score %d)",
                    item.descripcion[:40], mejor["nombre"], mejor_score)
        return mejor
    logger.info("Ítem '%s' -> plantilla genérica", item.descripcion[:40])
    return data.get("plantilla_generica", {"recursos": []})


def inferir_recursos(item: Item, texto_extra: str = "") -> List[RecursoAPU]:
    """Devuelve la lista de recursos sugeridos para un ítem (sin precio)."""
    plantilla = _seleccionar_plantilla(item, texto_extra)
    recursos: List[RecursoAPU] = []
    for r in plantilla.get("recursos", []):
        recursos.append(RecursoAPU(
            item_id=item.id,
            tipo=r.get("tipo", TIPO_MATERIAL),
            descripcion=r.get("descripcion", ""),
            unidad=r.get("unidad", ""),
            rendimiento=float(r.get("cantidad_apu", 1.0)),
            cantidad_apu=float(r.get("cantidad_apu", 1.0)),
            fuente_precio="sin_precio",
        ))
        # adjuntamos la categoría sugerida para la cotización
        recursos[-1]._categoria = r.get("categoria", "")
    return recursos


# --------------------------------------------------------------------------- #
# Cotización + cálculo del APU
# --------------------------------------------------------------------------- #
def cotizar_recursos(recursos: List[RecursoAPU], proyecto: Proyecto,
                     permitir_web: bool = True, permitir_email: bool = False,
                     persistir_cotizacion: bool = True) -> List[RecursoAPU]:
    """Cotiza cada recurso (respetando los bloqueados) y fija precio/subtotal."""
    for r in recursos:
        if r.bloqueado and r.precio_unitario:
            r.calcular_subtotal()
            continue
        categoria = getattr(r, "_categoria", "")
        res = cotizar_recurso(
            descripcion=r.descripcion, unidad=r.unidad, tipo=r.tipo,
            categoria=categoria, region=proyecto.region,
            proyecto_nombre=proyecto.nombre, permitir_web=permitir_web,
            permitir_email=permitir_email,
        )
        r.precio_unitario = res.precio_adoptado
        r.fuente_precio = res.fuente or "sin_precio"
        r.calcular_subtotal()

        if persistir_cotizacion and r.id:
            cot = Cotizacion(
                recurso_id=r.id, proveedor_id=res.proveedor_id,
                descripcion=r.descripcion, nivel_busqueda=res.nivel_usado,
                precio_bruto=res.precio_adoptado, unidad_origen=r.unidad,
                precio_adoptado=res.precio_adoptado, moneda=res.moneda,
                vigencia_dias=res.vigencia_dias, url_fuente=res.url,
                estado="pendiente" if res.nivel_usado == 3 else
                       ("sin_resultado" if res.nivel_usado == -1 else "obtenida"),
                nivel_confianza=1.0 if res.n_fuentes else 0.0,
                observaciones="; ".join(res.alertas))
            cot_id = repositories.guardar_cotizacion(cot)
            r.cotizacion_id = cot_id
            repositories.actualizar_recurso(r)
    return recursos


def calcular_resultado(item: Item, recursos: List[RecursoAPU],
                       proyecto: Proyecto) -> ResultadoAPU:
    """Consolida costos con la estructura NB-SABS (DS 0181) — Formulario B-2.

    En el ResultadoAPU se guardan las cifras consolidadas; el detalle completo
    (beneficios sociales, IVA, herramientas, GG, utilidad, IT) se recalcula al
    exportar los formularios con ``core.sabs.calcular_desglose``.
      - costo_mano_obra  = mano de obra TOTAL (con beneficios + IVA)
      - costo_equipos    = equipo TOTAL (con herramientas + IVA equipo)
      - indirectos       = gastos generales
      - impuestos        = IT (3.09%)
    """
    d = calcular_desglose(recursos, proyecto)

    alertas: List[str] = []
    if any(r.fuente_precio in ("sin_precio", "ninguna", "") for r in recursos):
        alertas.append("Hay recursos sin precio asignado")
    if any(r.fuente_precio == "email" for r in recursos):
        alertas.append("Hay recursos con cotización por email pendiente")
    if d.costo_directo == 0:
        alertas.append("Costo directo en cero: revisar recursos y precios")

    return ResultadoAPU(
        item_id=item.id, costo_materiales=d.materiales,
        costo_mano_obra=d.mano_obra_total, costo_equipos=d.equipo_total,
        costo_directo=d.costo_directo, indirectos=d.gastos_generales,
        utilidad=d.utilidad, impuestos=d.impuestos_it,
        precio_unitario_total=d.precio_unitario_total, alertas=alertas)


def generar_apu_item(item: Item, proyecto: Proyecto, texto_extra: str = "",
                     permitir_web: bool = True, permitir_email: bool = False,
                     persistir: bool = True) -> ResultadoAPU:
    """Flujo completo de APU para un ítem: inferir, cotizar, calcular y persistir."""
    if persistir:
        repositories.borrar_recursos_item(item.id)

    recursos = inferir_recursos(item, texto_extra)

    if persistir:
        for r in recursos:
            cat = getattr(r, "_categoria", "")
            r.id = repositories.guardar_recurso(r)
            r._categoria = cat  # re-adjuntar tras persistir

    recursos = cotizar_recursos(recursos, proyecto, permitir_web, permitir_email,
                                persistir_cotizacion=persistir)

    resultado = calcular_resultado(item, recursos, proyecto)
    if persistir:
        repositories.guardar_resultado(resultado)
        item.estado = "apu_generado"
        repositories.actualizar_item(item)
    return resultado


def generar_apu_proyecto(proyecto: Proyecto, items: Optional[List[Item]] = None,
                         permitir_web: bool = True,
                         permitir_email: bool = False) -> dict[int, ResultadoAPU]:
    """Genera el APU para todos los ítems de un proyecto."""
    items = items if items is not None else repositories.listar_items(proyecto.id)
    resultados: dict[int, ResultadoAPU] = {}
    for item in items:
        resultados[item.id] = generar_apu_item(
            item, proyecto, permitir_web=permitir_web, permitir_email=permitir_email)
    logger.info("APU generado para %d ítems del proyecto %s", len(items),
                proyecto.nombre)
    return resultados
