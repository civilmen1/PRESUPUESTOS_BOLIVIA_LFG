"""Pruebas de busqueda semantica con embeddings (con proveedor simulado)."""
from __future__ import annotations

from core import banco_apu, embeddings


def test_coseno_basico():
    assert embeddings.coseno([1, 0], [1, 0]) == 1.0
    assert embeddings.coseno([1, 0], [0, 1]) == 0.0
    assert embeddings.coseno([], [1, 2]) == 0.0


def test_buscar_apu_semantico(monkeypatch):
    """Con embeddings simulados, buscar_apu debe elegir el APU mas cercano
    por SIGNIFICADO aunque las palabras no coincidan."""
    apus = [
        {"actividad": "Vaciado de hormigon armado para columnas", "unidad": "m3"},
        {"actividad": "Pintura latex en muros interiores", "unidad": "m2"},
    ]
    monkeypatch.setattr(banco_apu, "listar_apus", lambda: apus)
    # vector ficticio: 1 dimension "hormigon", otra "pintura"
    mapa = {
        "Vaciado de hormigon armado para columnas": [1.0, 0.0],
        "Pintura latex en muros interiores": [0.0, 1.0],
        "concreto estructural reforzado": [0.9, 0.1],  # consulta (sinonimo)
    }

    def fake_embed(textos):
        return [mapa.get(t.strip(), [0.0, 0.0]) for t in textos]

    monkeypatch.setattr(embeddings, "disponible", lambda: True)
    monkeypatch.setattr(embeddings, "embed", fake_embed)
    banco_apu._emb_banco["firma"] = None  # invalidar cache

    res = banco_apu.buscar_apu("concreto estructural reforzado")
    assert res is not None
    assert "hormigon" in res["actividad"].lower()


def test_buscar_apu_fallback_sin_embeddings(monkeypatch):
    """Sin proveedor de embeddings, cae a Jaccard sin romperse."""
    apus = [{"actividad": "Excavacion manual de zanja", "unidad": "m3"}]
    monkeypatch.setattr(banco_apu, "listar_apus", lambda: apus)
    monkeypatch.setattr(embeddings, "disponible", lambda: False)
    res = banco_apu.buscar_apu("excavacion manual zanja")
    assert res is not None
