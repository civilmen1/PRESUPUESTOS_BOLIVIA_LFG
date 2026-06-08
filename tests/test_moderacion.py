"""Pruebas de la moderacion de aportes publicos al Banco de APU."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _apu(nombre="Hormigon"):
    return {"actividad": nombre, "unidad": "m3", "cantidad": 1.0,
            "materiales": [{"descripcion": "Cemento", "unidad": "kg",
                            "cantidad": 300, "precio": 1.2}],
            "mano_obra": [], "equipo": []}


def _aislar(tmp_path, monkeypatch):
    from config import settings as s
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)
    monkeypatch.setattr(s, "PERSIST_DIR", tmp_path)
    from core import moderacion, banco_apu
    monkeypatch.setattr(moderacion, "_RUTA", tmp_path / "aportes_pendientes.json")
    monkeypatch.setattr(banco_apu, "_RUTA", tmp_path / "banco_apu.json")
    # Sin semilla del repo: el banco arranca vacio para aislar la prueba.
    monkeypatch.setattr(banco_apu, "_RUTA_SEED", tmp_path / "seed_inexistente.json")
    banco_apu._cargar.cache_clear()
    return moderacion, banco_apu


def test_aporte_queda_pendiente_no_entra_al_banco(tmp_path, monkeypatch):
    moderacion, banco_apu = _aislar(tmp_path, monkeypatch)
    moderacion.agregar_pendiente("Juan", "j@x.bo", "B-2.xlsx", [_apu()])
    assert moderacion.contar_pendientes() == 1
    # No debe estar en el banco aun.
    assert banco_apu.listar_apus() == []


def test_aprobar_incorpora_al_banco(tmp_path, monkeypatch):
    moderacion, banco_apu = _aislar(tmp_path, monkeypatch)
    aid = moderacion.agregar_pendiente("Ana", "a@x.bo", "B-2.xlsx", [_apu()])
    r = moderacion.aprobar(aid)
    assert r["agregados"] == 1
    banco_apu._cargar.cache_clear()
    assert len(banco_apu.listar_apus()) == 1
    assert moderacion.contar_pendientes() == 0
    assert moderacion.listar("aprobado")[0]["id"] == aid


def test_aprobar_duplicado_actualiza_no_suma(tmp_path, monkeypatch):
    """Aprobar una actividad que YA existe la actualiza (no aumenta el total)."""
    moderacion, banco_apu = _aislar(tmp_path, monkeypatch)
    a1 = moderacion.agregar_pendiente("Ana", "a@x.bo", "B-2.xlsx", [_apu()])
    moderacion.aprobar(a1)
    banco_apu._cargar.cache_clear()
    assert len(banco_apu.listar_apus()) == 1
    # Mismo nombre de actividad: debe actualizar, no agregar.
    a2 = moderacion.agregar_pendiente("Bob", "b@x.bo", "B-2.xlsx", [_apu()])
    r = moderacion.aprobar(a2)
    banco_apu._cargar.cache_clear()
    assert r["agregados"] == 0 and r["actualizados"] == 1
    assert len(banco_apu.listar_apus()) == 1


def test_rechazar_no_incorpora(tmp_path, monkeypatch):
    moderacion, banco_apu = _aislar(tmp_path, monkeypatch)
    aid = moderacion.agregar_pendiente("Eva", "e@x.bo", "B-2.xlsx", [_apu()])
    assert moderacion.rechazar(aid) is True
    assert moderacion.contar_pendientes() == 0
    banco_apu._cargar.cache_clear()
    assert banco_apu.listar_apus() == []


def test_aprobar_id_inexistente_no_falla(tmp_path, monkeypatch):
    moderacion, _ = _aislar(tmp_path, monkeypatch)
    assert moderacion.aprobar(999) == {"agregados": 0, "actualizados": 0,
                                       "omitidos": 0}
