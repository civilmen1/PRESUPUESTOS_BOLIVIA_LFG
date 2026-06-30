"""Pruebas de la regla 'cemento siempre en kg' (conserva el costo)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from core.reglas_unidades import es_cemento, forzar_cemento_kg  # noqa: E402
from models.apu_resource import RecursoAPU  # noqa: E402


def _r(desc, unidad, cant, precio=0.0):
    r = RecursoAPU(tipo="material", descripcion=desc, unidad=unidad,
                   cantidad_apu=cant, rendimiento=cant, precio_unitario=precio)
    r.calcular_subtotal()
    return r


def test_es_cemento():
    assert es_cemento("Cemento Portland IP-30")
    assert es_cemento("CEMENTO")
    assert not es_cemento("Arena fina")


def test_cemento_bolsa_a_kg_conserva_costo(monkeypatch):
    monkeypatch.setattr(settings, "FORZAR_CEMENTO_KG", True, raising=False)
    monkeypatch.setattr(settings, "KG_POR_BOLSA_CEMENTO", 50.0, raising=False)
    r = _r("Cemento Portland IP-30", "bolsa", 7.0, 55.0)
    sub_antes = r.subtotal
    forzar_cemento_kg([r])
    assert r.unidad == "kg"
    assert r.cantidad_apu == 350.0
    assert round(r.precio_unitario, 4) == round(55.0 / 50, 4)
    # El costo (subtotal) NO debe cambiar: 7×55 == 350×1.10
    assert round(r.subtotal, 2) == round(sub_antes, 2)


def test_cemento_ya_en_kg_es_idempotente(monkeypatch):
    monkeypatch.setattr(settings, "FORZAR_CEMENTO_KG", True, raising=False)
    r = _r("Cemento Portland", "kg", 350.0, 1.1)
    forzar_cemento_kg([r])
    assert r.unidad == "kg" and r.cantidad_apu == 350.0


def test_material_no_cemento_no_se_toca(monkeypatch):
    monkeypatch.setattr(settings, "FORZAR_CEMENTO_KG", True, raising=False)
    r = _r("Cal hidratada", "bolsa", 2.0, 30.0)
    forzar_cemento_kg([r])
    assert r.unidad == "bolsa" and r.cantidad_apu == 2.0


def test_cemento_sin_precio_solo_convierte_cantidad(monkeypatch):
    monkeypatch.setattr(settings, "FORZAR_CEMENTO_KG", True, raising=False)
    monkeypatch.setattr(settings, "KG_POR_BOLSA_CEMENTO", 50.0, raising=False)
    r = _r("Cemento Portland IP-40", "bolsa", 7.0, 0.0)
    forzar_cemento_kg([r])
    assert r.unidad == "kg" and r.cantidad_apu == 350.0 and r.precio_unitario == 0.0


def test_regla_desactivada_no_cambia(monkeypatch):
    monkeypatch.setattr(settings, "FORZAR_CEMENTO_KG", False, raising=False)
    r = _r("Cemento Portland", "bolsa", 7.0, 55.0)
    forzar_cemento_kg([r])
    assert r.unidad == "bolsa" and r.cantidad_apu == 7.0
