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


def _recursos_desde_banco(item: Item) -> List[RecursoAPU]:
    """Si el ítem coincide con un APU del banco de referencia, devuelve sus
    recursos (rendimientos reales). Lista vacía si no hay coincidencia clara."""
    try:
        from core import banco_apu
        if not banco_apu.hay_banco():
            return []
        apu = banco_apu.buscar_apu(item.descripcion, umbral=0.45)
        if not apu:
            return []
        recursos: List[RecursoAPU] = []
        mapa = {"materiales": TIPO_MATERIAL, "mano_obra": TIPO_MANO_OBRA,
                "equipo": TIPO_EQUIPO}
        for grupo, tipo in mapa.items():
            for d in apu.get(grupo, []):
                cant = float(d.get("cantidad", 0) or 0)
                if cant <= 0:
                    continue
                r = RecursoAPU(
                    item_id=item.id, tipo=tipo,
                    descripcion=d.get("descripcion", ""),
                    unidad=d.get("unidad", ""), rendimiento=cant,
                    cantidad_apu=cant, precio_unitario=float(d.get("precio", 0) or 0),
                    fuente_precio="banco_apu" if d.get("precio") else "sin_precio")
                r.calcular_subtotal()
                recursos.append(r)
        if recursos:
            logger.info("Ítem '%s' -> APU del banco '%s' (%d recursos)",
                        item.descripcion[:40], apu.get("actividad", "")[:40],
                        len(recursos))
        return recursos
    except Exception:
        logger.exception("Fallo buscando en el banco de APU")
        return []


def _extraer_info_item(descripcion: str, spec: str, item_id: int,
                       unidad: str = ""):
    """Extrae info de la especificación: usa IA si está habilitada, si no offline."""
    from config import settings
    if settings.USAR_LLM:
        try:
            from core.llm_extractor import extraer_info_inteligente, hay_llm
            if hay_llm():
                return extraer_info_inteligente(descripcion, spec, item_id, unidad)
        except Exception:
            logger.exception("Fallo extractor IA; usando offline")
    from core.info_extractor import extraer_info
    return extraer_info(descripcion, spec, item_id)


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
    """Devuelve la lista de recursos sugeridos para un ítem (sin precio).

    Garantiza que TODA actividad tenga, como mínimo, sus tres componentes:
    material, mano de obra y equipo/herramienta. Si la plantilla o las
    especificaciones técnicas no los mencionan, se analiza el contexto del
    ítem (descripción + texto técnico) para adicionar lo que corresponde como
    mínimo, dejándolo marcado para revisión del ingeniero.
    """
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
        recursos[-1]._categoria = r.get("categoria", "")

    return _garantizar_minimos(item, recursos, texto_extra)


def _garantizar_minimos(item: Item, recursos: List[RecursoAPU],
                        texto_extra: str = "") -> List[RecursoAPU]:
    """Asegura que existan los 3 grupos clave; adiciona mínimos si faltan."""
    presentes = {r.tipo for r in recursos}
    contexto = normalizar(f"{item.descripcion} {item.palabras_clave} {texto_extra}")
    fase, _orden = _clasificar_fase_segura(item.descripcion)

    def _add(tipo, descripcion, unidad, cantidad, categoria, nota):
        nuevo = RecursoAPU(
            item_id=item.id, tipo=tipo, descripcion=descripcion, unidad=unidad,
            rendimiento=cantidad, cantidad_apu=cantidad, fuente_precio="sin_precio")
        nuevo._categoria = categoria
        nuevo._auto_minimo = nota  # marca para revisión del ingeniero
        recursos.append(nuevo)

    # --- MANO DE OBRA mínima (toda actividad requiere personal) ---
    if TIPO_MANO_OBRA not in presentes:
        if any(k in contexto for k in ("electric", "cable", "luminaria")):
            _add(TIPO_MANO_OBRA, "Electricista", "jornal", 0.1, "electricista",
                 "Personal mínimo inferido del contexto")
        elif any(k in contexto for k in ("tuberia", "sanitaria", "agua", "gas")):
            _add(TIPO_MANO_OBRA, "Plomero", "jornal", 0.1, "plomero",
                 "Personal mínimo inferido del contexto")
        else:
            _add(TIPO_MANO_OBRA, "Albañil", "jornal", 0.2, "albañil",
                 "Personal mínimo inferido del contexto")
        _add(TIPO_MANO_OBRA, "Ayudante", "jornal", 0.2, "ayudante",
             "Personal mínimo inferido del contexto")

    # --- EQUIPO / HERRAMIENTA mínima ---
    if TIPO_EQUIPO not in presentes:
        _add(TIPO_EQUIPO, "Herramientas menores", "porcentaje", 0.05,
             "herramienta_menor", "Equipo mínimo inferido (5% de mano de obra)")

    # --- MATERIAL mínimo (si la actividad lo amerita) ---
    if TIPO_MATERIAL not in presentes and fase not in ("Trabajos preliminares",
                                                       "Movimiento de tierras"):
        _add(TIPO_MATERIAL, "Material principal (definir según especificación)",
             "glb", 1.0, "otros",
             "Material mínimo a definir: la especificación no lo detalla")

    return recursos


def armar_recursos_desde_analisis(item: Item, persistir: bool = True
                                  ) -> List[RecursoAPU]:
    """Construye (y persiste) los recursos del ítem desde el análisis técnico.

    Carga la especificación vinculada, infiere los recursos (materiales, mano de
    obra en horas, equipo en horas) y los guarda. Es la base de las tablas
    editables de la página de Vinculación. No respeta recursos bloqueados aquí:
    se usa para el armado inicial.
    """
    # PRIORIDAD 1: banco de APU de referencia. Si el ítem coincide claramente
    # con un APU real del banco, se usa ese armado (rendimientos reales).
    recursos_banco = _recursos_desde_banco(item)
    if recursos_banco:
        if persistir and item.id:
            repositories.borrar_recursos_item(item.id)
            for r in recursos_banco:
                cat = getattr(r, "_categoria", "")
                r.id = repositories.guardar_recurso(r)
                r._categoria = cat
        return recursos_banco

    spec = ""
    if item.id:
        try:
            spec = repositories.texto_tecnico_item(item.id)
        except Exception:
            spec = ""

    info = _extraer_info_item(item.descripcion, spec, item.id, item.unidad)

    # Si la IA generó recursos detallados (con cantidad y unidad), se usan tal
    # cual: mano de obra y equipo en HORAS, materiales con su unidad real.
    recursos: List[RecursoAPU] = []
    detalle = getattr(info, "recursos_detalle", None) or []
    if detalle:
        for d in detalle:
            r = RecursoAPU(
                item_id=item.id, tipo=d.get("tipo", TIPO_MATERIAL),
                descripcion=d.get("descripcion", ""), unidad=d.get("unidad", ""),
                rendimiento=float(d.get("cantidad", 0) or 0),
                cantidad_apu=float(d.get("cantidad", 0) or 0),
                fuente_precio="sin_precio")
            r._categoria = d.get("categoria", "")
            recursos.append(r)
        recursos = _garantizar_minimos(item, recursos, info.como_texto())
    else:
        # Sin IA: plantillas + contexto (extractor offline por reglas)
        recursos = inferir_recursos(item, info.como_texto())

    if persistir and item.id:
        repositories.borrar_recursos_item(item.id)
        for r in recursos:
            cat = getattr(r, "_categoria", "")
            r.id = repositories.guardar_recurso(r)
            r._categoria = cat
    return recursos


def _clasificar_fase_segura(descripcion: str):
    try:
        from core.cronograma import clasificar_fase
        return clasificar_fase(descripcion)
    except Exception:
        return "Obra gruesa / estructura", 2


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
    if any(getattr(r, "_auto_minimo", "") for r in recursos):
        alertas.append("Se adicionaron recursos mínimos por contexto (revisar)")
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
                     persistir: bool = True,
                     reusar_recursos: bool = True) -> ResultadoAPU:
    """Flujo completo de APU para un ítem: inferir, cotizar, calcular y persistir.

    Los MÓDULOS (filas sin unidad ni cantidad) solo agrupan ítems y NO requieren
    análisis de precios unitarios: se omiten.

    Si ``reusar_recursos`` y el ítem ya tiene recursos (armados y validados en la
    página de Vinculación), se RESPETAN tal cual y solo se cotizan; así no se
    pierde la edición manual del ingeniero.
    """
    if item.es_modulo:
        logger.info("Ítem '%s' es un módulo; se omite el APU", item.descripcion[:40])
        if persistir:
            item.estado = "modulo"
            repositories.actualizar_item(item)
        return ResultadoAPU(item_id=item.id, alertas=["Módulo (sin APU)"])

    recursos_existentes = repositories.listar_recursos(item.id) if item.id else []
    usar_existentes = reusar_recursos and bool(recursos_existentes)

    if usar_existentes:
        recursos = recursos_existentes  # respetar el armado validado
    else:
        if persistir:
            repositories.borrar_recursos_item(item.id)
        # Carga la especificación técnica vinculada para enriquecer la inferencia.
        if not texto_extra and item.id:
            try:
                spec = repositories.texto_tecnico_item(item.id)
                if spec:
                    info = _extraer_info_item(item.descripcion, spec, item.id)
                    texto_extra = info.como_texto()
            except Exception:
                logger.exception("No se pudo cargar la especificación del ítem %s",
                                 item.id)
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
