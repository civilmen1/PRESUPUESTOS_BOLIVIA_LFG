"""Pruebas del secuenciamiento lógico de obra (cronograma A-8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cronograma import clasificar_fase, construir_cronograma  # noqa: E402
from models.item import Item  # noqa: E402


def test_clasificacion_fases():
    assert clasificar_fase("Replanteo y trazado de obra")[0] == "Trabajos preliminares"
    assert clasificar_fase("Excavación de zanja")[0] == "Movimiento de tierras"
    assert clasificar_fase("Hormigón armado columnas")[0] == "Obra gruesa / estructura"
    assert clasificar_fase("Tendido de tubería de agua")[0] == "Instalaciones"
    assert clasificar_fase("Pintura látex en muros")[0] == "Acabados"


def test_secuencia_logica_respeta_orden():
    items = [
        Item(id=1, numero="1", descripcion="Pintura látex muros"),
        Item(id=2, numero="2", descripcion="Replanteo y trazado"),
        Item(id=3, numero="3", descripcion="Excavación para cimientos"),
        Item(id=4, numero="4", descripcion="Hormigón armado zapatas"),
    ]
    montos = {1: 1000, 2: 500, 3: 800, 4: 2000}
    n, prog = construir_cronograma(items, plazo_dias=120, montos_por_item=montos)
    # el orden de ejecución debe seguir las fases: replanteo < excavación <
    # estructura < pintura
    descripciones = [p.item.descripcion for p in prog]
    assert descripciones.index("Replanteo y trazado") < \
           descripciones.index("Excavación para cimientos")
    assert descripciones.index("Excavación para cimientos") < \
           descripciones.index("Hormigón armado zapatas")
    assert descripciones.index("Hormigón armado zapatas") < \
           descripciones.index("Pintura látex muros")


def test_cronograma_respeta_plazo():
    items = [Item(id=i, numero=str(i), descripcion=d) for i, d in enumerate(
        ["Replanteo", "Excavación", "Hormigón", "Pintura"], 1)]
    montos = {i: 1000 for i in range(1, 5)}
    n, prog = construir_cronograma(items, plazo_dias=90, montos_por_item=montos)
    assert n == 3  # 90 días -> 3 meses
    # ninguna actividad excede el plazo
    assert all(p.mes_fin <= n for p in prog)
    # la obra termina en el último mes
    assert max(p.mes_fin for p in prog) == n


def test_sin_items():
    n, prog = construir_cronograma([], plazo_dias=60, montos_por_item={})
    assert prog == []
    assert n == 2
