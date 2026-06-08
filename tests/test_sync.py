"""Pruebas de la sincronizacion del banco nube->local (red simulada)."""
from __future__ import annotations

import json


def _aislar(tmp_path, monkeypatch):
    from config import settings as s
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)
    monkeypatch.setattr(s, "PERSIST_DIR", tmp_path)
    monkeypatch.setattr(s, "STATIC_DIR", tmp_path / "static")
    from core import banco_apu
    monkeypatch.setattr(banco_apu, "_RUTA", tmp_path / "banco_apu.json")
    monkeypatch.setattr(banco_apu, "_RUTA_SEED", tmp_path / "seed_inexistente.json")
    banco_apu._cargar.cache_clear()
    return s, banco_apu


def test_publicar_copia_a_static(tmp_path, monkeypatch):
    s, banco_apu = _aislar(tmp_path, monkeypatch)
    monkeypatch.setattr(s, "SYNC_PUBLISH", True)
    monkeypatch.setattr(s, "SYNC_TOKEN", "abc123")
    # banco actual con 1 APU
    banco_apu._RUTA.write_text(json.dumps(
        {"apus": [{"actividad": "Muro", "unidad": "m2", "materiales": [],
                   "mano_obra": [], "equipo": []}]}), encoding="utf-8")
    from core import sync
    assert sync.publicar() is True
    pub = s.STATIC_DIR / "banco_abc123.json"
    assert pub.exists()
    assert json.loads(pub.read_text())["apus"][0]["actividad"] == "Muro"


def test_sincronizar_desde_nube_fusiona(tmp_path, monkeypatch):
    s, banco_apu = _aislar(tmp_path, monkeypatch)
    monkeypatch.setattr(s, "SYNC_URL", "http://servidor/banco.json")
    # local arranca con 1 APU
    banco_apu._RUTA.write_text(json.dumps(
        {"apus": [{"actividad": "Local", "unidad": "m2", "materiales": [],
                   "mano_obra": [], "equipo": []}]}), encoding="utf-8")
    banco_apu._cargar.cache_clear()

    # la nube responde con 2 APU (uno nuevo, uno repetido)
    remoto = {"apus": [
        {"actividad": "Local", "unidad": "m2", "materiales": [],
         "mano_obra": [], "equipo": []},
        {"actividad": "Nube", "unidad": "m3", "materiales": [],
         "mano_obra": [], "equipo": []}]}

    class _Resp:
        text = json.dumps(remoto)
        def raise_for_status(self): pass

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())
    from core import sync
    res = sync.sincronizar_desde_nube(fusionar=True)
    assert res is not None
    assert res["despues"] == 2 and res["nuevos"] == 1


def test_sincronizar_sin_url_devuelve_none(tmp_path, monkeypatch):
    s, _ = _aislar(tmp_path, monkeypatch)
    monkeypatch.setattr(s, "SYNC_URL", "")
    from core import sync
    assert sync.sincronizar_desde_nube() is None
