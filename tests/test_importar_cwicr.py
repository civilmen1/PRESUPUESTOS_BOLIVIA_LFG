"""Prueba del importador CWICR (rendimientos sin precios)."""
from __future__ import annotations

import pandas as pd

from scripts import importar_cwicr


def _csv_cwicr(tmp_path):
    """CSV sintetico con forma CWICR: una fila por recurso, rate_code repetido."""
    filas = [
        # Partida 1: hormigon (material + mano de obra + equipo)
        {"rate_code": "R1", "rate_final_name": "Hormigon armado H21",
         "rate_unit": "m3", "resource_name": "Cemento Portland",
         "resource_unit": "kg", "resource_quantity": 350,
         "resource_price_per_unit_eur_current": 0.12,
         "labor_hours_construction_workers": 0},
        {"rate_code": "R1", "rate_final_name": "Hormigon armado H21",
         "rate_unit": "m3", "resource_name": "Albanil obrero",
         "resource_unit": "h", "resource_quantity": 8,
         "resource_price_per_unit_eur_current": 15.0,
         "labor_hours_construction_workers": 8},
        {"rate_code": "R1", "rate_final_name": "Hormigon armado H21",
         "rate_unit": "m3", "resource_name": "Mezcladora de hormigon",
         "resource_unit": "h", "resource_quantity": 2,
         "resource_price_per_unit_eur_current": 5.0,
         "labor_hours_construction_workers": 0},
        # Partida 2: pintura (debe filtrarse fuera si pido solo 'hormigon')
        {"rate_code": "R2", "rate_final_name": "Pintura latex muros",
         "rate_unit": "m2", "resource_name": "Pintura latex",
         "resource_unit": "lt", "resource_quantity": 0.25,
         "resource_price_per_unit_eur_current": 3.0,
         "labor_hours_construction_workers": 0},
    ]
    ruta = tmp_path / "cwicr.csv"
    pd.DataFrame(filas).to_csv(ruta, index=False)
    return str(ruta)


def test_importa_rendimientos_sin_precios(tmp_path):
    ruta = _csv_cwicr(tmp_path)
    apus = importar_cwicr.importar_cwicr(ruta)
    assert len(apus) == 2
    r1 = next(a for a in apus if a["actividad"].startswith("Hormigon"))
    assert r1["unidad"] == "m3"
    # clasificacion
    assert len(r1["materiales"]) == 1
    assert len(r1["mano_obra"]) == 1
    assert len(r1["equipo"]) == 1
    # rendimientos conservados, precios descartados (0)
    assert r1["materiales"][0]["cantidad"] == 350
    assert all(r["precio"] == 0 for grupo in ("materiales", "mano_obra", "equipo")
               for r in r1[grupo])
    # mano de obra normalizada a horas
    assert r1["mano_obra"][0]["unidad"] == "HR"


def test_filtro_contiene(tmp_path):
    ruta = _csv_cwicr(tmp_path)
    apus = importar_cwicr.importar_cwicr(ruta, contiene=["hormigon"])
    assert len(apus) == 1
    assert apus[0]["actividad"].startswith("Hormigon")
