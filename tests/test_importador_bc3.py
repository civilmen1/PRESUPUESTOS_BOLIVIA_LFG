"""Pruebas del importador BC3 / FIEBDC-3 al Banco de APU."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import importador_bc3  # noqa: E402

# BC3 minimo: una partida (E01) que descompone en mano de obra, material y equipo.
# Formato: ~C concepto, ~D descomposicion (codigo | hijo\factor\rendimiento...).
_BC3 = (
    "~V|PROG|FIEBDC-3/2016|EJEMPLO|||\r\n"
    "~C|E01#|m3|Hormigon armado vaciado en obra|850.00|||\r\n"
    "~C|mo01#|h|Albanil|18.75|||\r\n"
    "~C|mt01#|kg|Cemento portland|1.20|||\r\n"
    "~C|mq01#|h|Mezcladora de hormigon|25.00|||\r\n"
    "~D|E01#|mo01#\\1\\8.5\\mt01#\\1\\320\\mq01#\\1\\1.2\\|\r\n"
)


def _datos():
    return _BC3.encode("latin-1")


def test_parsear_conceptos_y_descomposicion():
    conceptos, descomp = importador_bc3.parsear(_datos())
    assert "E01#" in conceptos
    assert conceptos["mo01#"]["precio"] == 18.75
    assert conceptos["mt01#"]["unidad"] == "kg"
    assert len(descomp["E01#"]) == 3


def test_extraer_apu_clasifica_recursos():
    apus = importador_bc3.extraer_apus(_datos())
    assert len(apus) == 1
    apu = apus[0]
    assert apu["unidad"] == "m3"
    assert "Hormigon" in apu["actividad"]
    # un recurso de cada tipo, bien clasificado
    assert len(apu["mano_obra"]) == 1
    assert len(apu["materiales"]) == 1
    assert len(apu["equipo"]) == 1
    # rendimiento (cantidad) y precio del material
    mat = apu["materiales"][0]
    assert mat["cantidad"] == 320
    assert mat["precio"] == 1.20
    # mano de obra
    assert apu["mano_obra"][0]["precio"] == 18.75
    assert apu["mano_obra"][0]["cantidad"] == 8.5


def test_capitulo_sin_elementales_no_es_apu():
    # Un capitulo que solo agrupa la partida E01 no debe contar como APU.
    bc3 = _BC3 + "~C|CAP01|cap|Capitulo Estructuras|||\r\n~D|CAP01|E01#\\1\\1\\|\r\n"
    apus = importador_bc3.extraer_apus(bc3.encode("latin-1"))
    actividades = [a["actividad"] for a in apus]
    assert any("Hormigon" in x for x in actividades)
    assert not any("Capitulo" in x for x in actividades)


def test_decodifica_utf8_y_cp1252():
    # Acentos en cp1252 no deben romper el parser.
    bc3 = "~C|mt9#|u|Ladrillo gambote ceramico|2.50|||"
    conceptos, _ = importador_bc3.parsear(bc3.encode("cp1252"))
    assert conceptos["mt9#"]["precio"] == 2.50
