"""Pruebas del matcher semántico ítem ↔ sección técnica."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.semantic_matcher import SemanticMatcher  # noqa: E402
from models.item import Item  # noqa: E402
from models.technical_source import SeccionTecnica  # noqa: E402


def _secciones():
    return [
        SeccionTecnica(id=1, titulo="Hormigón armado",
                       contenido="El hormigón armado para columnas y vigas será "
                                 "H21 con acero corrugado fy=4200.",
                       keywords="hormigon, armado, columna, acero"),
        SeccionTecnica(id=2, titulo="Pintura",
                       contenido="La pintura látex se aplicará en dos manos sobre "
                                 "muros interiores.",
                       keywords="pintura, latex, muros"),
        SeccionTecnica(id=3, titulo="Excavación",
                       contenido="La excavación manual de zanjas para cimientos.",
                       keywords="excavacion, zanja, cimientos"),
    ]


def test_match_relevante():
    matcher = SemanticMatcher(_secciones())
    item = Item(id=10, descripcion="Hormigón armado para columnas H21",
                palabras_clave="hormigon, columnas")
    resultados = matcher.buscar(item, top_k=2)
    assert resultados
    assert resultados[0].seccion_id == 1
    assert resultados[0].score_confianza > 0


def test_match_pintura():
    matcher = SemanticMatcher(_secciones())
    item = Item(id=11, descripcion="Pintura látex en muros interiores")
    resultados = matcher.buscar(item, top_k=1)
    assert resultados and resultados[0].seccion_id == 2


def test_sin_coincidencia_devuelve_vacio_o_bajo():
    matcher = SemanticMatcher(_secciones())
    item = Item(id=12, descripcion="Instalación de paneles solares fotovoltaicos")
    resultados = matcher.buscar(item, top_k=3, umbral=0.3)
    assert all(r.score_confianza >= 0.3 for r in resultados)
