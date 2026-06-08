"""Pruebas del desglose de costos NB-SABS (DS 0181) — Formulario B-2."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.sabs import calcular_desglose  # noqa: E402
from models.apu_resource import (RecursoAPU, TIPO_EQUIPO, TIPO_MANO_OBRA,  # noqa: E402
                                 TIPO_MATERIAL)
from models.project import Proyecto  # noqa: E402


def _proyecto():
    return Proyecto(
        nombre="Test", factor_beneficios_sociales=0.55, factor_iva_mano_obra=0.1494,
        factor_herramientas=0.05, factor_iva_equipo=0.0,
        factor_gastos_generales=0.10, factor_utilidad_sabs=0.10, factor_it=0.0309)


def _recursos():
    return [
        RecursoAPU(tipo=TIPO_MATERIAL, descripcion="Cemento", subtotal=1000.0),
        RecursoAPU(tipo=TIPO_MANO_OBRA, descripcion="Albañil", subtotal=400.0),
        RecursoAPU(tipo=TIPO_EQUIPO, descripcion="Mezcladora", subtotal=100.0),
    ]


def test_beneficios_e_iva_mano_obra():
    d = calcular_desglose(_recursos(), _proyecto())
    assert d.mano_obra_neta == 400.0
    assert d.beneficios_sociales == 220.0          # 55% de 400
    assert round(d.iva_mano_obra, 2) == 92.63      # 14.94% de (400+220)
    assert round(d.mano_obra_total, 2) == 712.63


def test_herramientas_sobre_mano_obra():
    d = calcular_desglose(_recursos(), _proyecto())
    # herramientas = 5% de la mano de obra total
    assert round(d.herramientas, 2) == round(d.mano_obra_total * 0.05, 2)
    assert round(d.equipo_total, 2) == round(100.0 + d.herramientas, 2)


def test_cascada_gg_utilidad_it():
    p = _proyecto()
    d = calcular_desglose(_recursos(), p)
    assert round(d.gastos_generales, 2) == round(d.costo_directo * 0.10, 2)
    base_ut = d.costo_directo + d.gastos_generales
    assert round(d.utilidad, 2) == round(base_ut * 0.10, 2)
    base_it = base_ut + d.utilidad
    assert round(d.impuestos_it, 2) == round(base_it * 0.0309, 2)
    assert round(d.precio_unitario_total, 2) == round(base_it + d.impuestos_it, 2)


def test_costo_directo_suma_componentes():
    d = calcular_desglose(_recursos(), _proyecto())
    assert round(d.costo_directo, 2) == round(
        d.materiales + d.mano_obra_total + d.equipo_total, 2)


def test_sin_recursos_da_cero():
    d = calcular_desglose([], _proyecto())
    assert d.precio_unitario_total == 0.0
    assert d.costo_directo == 0.0


def test_recalcular_con_incidencias(tmp_path, monkeypatch):
    import os
    db = tmp_path / "recalc.db"
    monkeypatch.setenv("APU_DB_PATH", str(db))
    from config import settings as s
    monkeypatch.setattr(s, "DB_PATH", db)
    from core.database import init_db
    from core import repositories, apu_engine
    from models.project import Proyecto
    from models.item import Item
    from models.apu_resource import RecursoAPU, TIPO_MATERIAL, TIPO_MANO_OBRA
    init_db()
    pid = repositories.crear_proyecto(Proyecto(nombre="R", factor_utilidad_sabs=0.10))
    iid = repositories.crear_item(Item(proyecto_id=pid, numero="1",
                                       descripcion="X", unidad="m3", cantidad=2))
    repositories.guardar_recurso(RecursoAPU(item_id=iid, tipo=TIPO_MATERIAL,
                                            descripcion="Cemento", unidad="kg",
                                            cantidad_apu=1, precio_unitario=100,
                                            subtotal=100))
    repositories.guardar_recurso(RecursoAPU(item_id=iid, tipo=TIPO_MANO_OBRA,
                                            descripcion="Albanil", unidad="hora",
                                            cantidad_apu=1, precio_unitario=20,
                                            subtotal=20))
    p = repositories.obtener_proyecto(pid)
    t1 = apu_engine.recalcular_proyecto(p)
    # subir utilidad -> total mayor
    repositories.actualizar_incidencias(pid, factor_utilidad_sabs=0.30)
    p2 = repositories.obtener_proyecto(pid)
    t2 = apu_engine.recalcular_proyecto(p2)
    assert t2 > t1
