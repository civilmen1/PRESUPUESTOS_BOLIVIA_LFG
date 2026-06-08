"""Pruebas del extractor de información técnica por ítem."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.info_extractor import extraer_info  # noqa: E402

SPEC = """2.1 HORMIGON ARMADO
DEFINICION: Provision y colocado de hormigon armado H21 para zapatas.
MATERIALES: cemento portland, arena, grava, agua y acero corrugado fy=4200.
Encofrado de madera.
EJECUCION: mezclado con hormigonera y vibrado con vibradora. Personal: maestro
albañil, fierrista y ayudantes.
MEDICION Y FORMA DE PAGO: se medira en metros cubicos (m3).
NORMAS: NB 1225001, ASTM C150."""


def test_extrae_materiales():
    info = extraer_info("Hormigón armado", SPEC, 1)
    assert "cemento" in info.materiales
    assert "acero" in info.materiales
    assert "madera" in info.materiales


def test_extrae_mano_obra_y_equipo():
    info = extraer_info("Hormigón armado", SPEC, 1)
    assert "albañil" in info.mano_obra
    assert "fierrista" in info.mano_obra
    assert "mezcladora" in info.equipo
    assert "vibradora" in info.equipo


def test_extrae_normas_y_medicion():
    info = extraer_info("Hormigón armado", SPEC, 1)
    assert "NB 1225001" in info.normas
    assert "ASTM C150" in info.normas
    assert "m3" in info.medicion.lower() or "metros cubicos" in info.medicion.lower()


def test_sin_especificacion():
    info = extraer_info("Item cualquiera", "", 1)
    assert not info.tiene_especificacion
    assert info.materiales == []
    assert "mínimos por contexto" in info.resumen


def test_como_texto_alimenta_apu():
    info = extraer_info("Hormigón armado", SPEC, 1)
    texto = info.como_texto()
    assert "cemento" in texto and "albañil" in texto
