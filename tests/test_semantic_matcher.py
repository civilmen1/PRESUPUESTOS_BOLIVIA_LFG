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


def test_busqueda_jerarquica_con_modulo():
    secs = [
        SeccionTecnica(id=1, titulo="MODULO 2 OBRA GRUESA",
                       contenido="Estructura de hormigón armado y mampostería."),
        SeccionTecnica(id=2, titulo="2.1 Hormigón armado",
                       contenido="Hormigón H21 con acero corrugado para zapatas."),
        SeccionTecnica(id=3, titulo="MODULO 4 ACABADOS",
                       contenido="Pintura y revestimientos."),
    ]
    m = SemanticMatcher(secs)
    it = Item(id=10, numero="2.1", descripcion="Hormigón armado para zapatas")
    res = m.buscar(it, top_k=2, modulo_nombre="OBRA GRUESA")
    assert res and res[0].seccion_id == 2


def test_detectar_modulo():
    secs = [
        SeccionTecnica(id=1, titulo="MODULO 2 OBRA GRUESA", contenido="..."),
        SeccionTecnica(id=2, titulo="MODULO 4 ACABADOS", contenido="..."),
    ]
    m = SemanticMatcher(secs)
    assert m.detectar_modulo("ACABADOS") == 1
    assert m.detectar_modulo("OBRA GRUESA") == 0


def test_modulos_no_se_vinculan():
    from core.semantic_matcher import vincular_items
    secs = _secciones()
    items = [
        Item(id=1, descripcion="MODULO 1 OBRAS", unidad="", cantidad=0),  # módulo
        Item(id=2, descripcion="Pintura látex muros", unidad="m2", cantidad=10),
    ]
    out = vincular_items(items, secs)
    assert 1 not in out      # el módulo no se vincula
    assert 2 in out          # el ítem real sí
