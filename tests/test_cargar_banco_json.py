"""Prueba de cargar el banco completo desde un archivo JSON (descarga del server)."""
from __future__ import annotations

import json

import pytest


def _aislar(tmp_path, monkeypatch):
    from config import settings as s
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)
    monkeypatch.setattr(s, "PERSIST_DIR", tmp_path)
    from core import banco_apu
    monkeypatch.setattr(banco_apu, "_RUTA", tmp_path / "banco_apu.json")
    monkeypatch.setattr(banco_apu, "_RUTA_SEED", tmp_path / "seed_inexistente.json")
    banco_apu._cargar.cache_clear()
    return banco_apu


def test_cargar_desde_json_reemplaza(tmp_path, monkeypatch):
    banco_apu = _aislar(tmp_path, monkeypatch)
    data = {"apus": [{"actividad": "Muro", "unidad": "m2",
                      "materiales": [], "mano_obra": [], "equipo": []}]}
    total = banco_apu.cargar_desde_json(json.dumps(data))
    assert total == 1
    assert banco_apu.listar_apus()[0]["actividad"] == "Muro"


def test_cargar_desde_json_invalido(tmp_path, monkeypatch):
    banco_apu = _aislar(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        banco_apu.cargar_desde_json('{"otra_cosa": 1}')
