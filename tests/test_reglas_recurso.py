"""Garantiza que NINGUN recurso se guarde/lea con 'peón' o 'jornal'.

Estas pruebas protegen el PORTON unico de reglas de mano de obra: si alguien
rompe la normalizacion, fallan."""
from __future__ import annotations

from core import mano_obra


def test_limpiar_quita_peon_y_jornal():
    assert mano_obra.limpiar_descripcion("Peón") .lower().startswith("ayudante")
    # 'jornal' desaparece de la descripcion
    out = mano_obra.limpiar_descripcion("Jornal de albañil").lower()
    assert "jornal" not in out and "albañil" in out
    assert "jornal" not in mano_obra.limpiar_descripcion("Jornales peones").lower()


def test_unidad_mano_obra_siempre_horas():
    assert mano_obra.unidad_mano_obra("mano_obra", "jornal") == "HR"
    assert mano_obra.unidad_mano_obra("mano_obra", "dia") == "HR"
    assert mano_obra.unidad_mano_obra("mano_obra", "") == "HR"
    # el equipo con unidad prohibida tambien pasa a horas
    assert mano_obra.unidad_mano_obra("equipo", "jornal") == "HR"
    # el material conserva su unidad
    assert mano_obra.unidad_mano_obra("material", "m3") == "m3"


def test_aplicar_reglas_portico():
    desc, unidad = mano_obra.aplicar_reglas("mano_obra", "Peón", "jornal")
    assert unidad == "HR"
    assert "peon" not in desc.lower() and "peón" not in desc.lower()


def test_round_trip_db_normaliza(tmp_path, monkeypatch):
    """Al guardar y leer por la base, mano de obra queda en HR sin peón/jornal."""
    from config import settings
    from core import database, repositories
    from models.item import Item
    from models.project import Proyecto
    from models.apu_resource import RecursoAPU

    monkeypatch.setattr(settings, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    proyecto_id = repositories.crear_proyecto(Proyecto(nombre="Prueba"))
    item_id = repositories.crear_item(
        Item(proyecto_id=proyecto_id, descripcion="Muro de ladrillo",
             unidad="m2", cantidad=1))
    repositories.guardar_recurso(RecursoAPU(
        item_id=item_id, tipo="mano_obra", descripcion="Peón",
        unidad="jornal", rendimiento=8, cantidad_apu=8))

    leidos = repositories.listar_recursos(item_id)
    mo = [r for r in leidos if r.tipo == "mano_obra"]
    assert mo, "deberia haber mano de obra"
    r = mo[0]
    assert r.unidad == "HR"
    assert "jornal" not in r.unidad.lower()
    assert "peon" not in r.descripcion.lower() and "peón" not in r.descripcion.lower()
