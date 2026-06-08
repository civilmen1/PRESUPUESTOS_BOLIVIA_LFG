"""Pruebas del asistente con tool-calling (proveedor simulado)."""
from __future__ import annotations

import json

from core import asistente


def test_ejecutar_tool_estado_banco(monkeypatch):
    from core import banco_apu
    monkeypatch.setattr(banco_apu, "listar_apus", lambda: [{}, {}, {}])
    out = json.loads(asistente._ejecutar("estado_banco", {}, {}))
    assert out["total_apus"] == 3


def test_ejecutar_tool_desconocida():
    out = json.loads(asistente._ejecutar("no_existe", {}, {}))
    assert "error" in out


def test_chat_bucle_con_herramienta(monkeypatch):
    """El asistente llama una herramienta y luego responde con el resultado."""
    monkeypatch.setattr(asistente, "_proveedor", lambda: "groq")

    pasos = {"n": 0}

    def fake_llamar(mensajes):
        pasos["n"] += 1
        if pasos["n"] == 1:
            # Primer turno: pide ejecutar la herramienta estado_banco
            return {"raw": {"role": "assistant", "content": "",
                            "tool_calls": [{"id": "1", "function": {
                                "name": "estado_banco", "arguments": "{}"}}]},
                    "content": "",
                    "tool_calls": [{"id": "1", "name": "estado_banco", "args": {}}]}
        # Segundo turno: responde usando el resultado (ya en mensajes)
        assert any(m.get("role") == "tool" for m in mensajes)
        return {"raw": {"role": "assistant", "content": "Hay APU en el banco."},
                "content": "Hay APU en el banco.", "tool_calls": []}

    monkeypatch.setattr(asistente, "_llamar_groq", fake_llamar)
    from core import banco_apu
    monkeypatch.setattr(banco_apu, "listar_apus", lambda: [{}, {}])

    res = asistente.chat([{"role": "user", "content": "cuantos APU hay?"}])
    assert "estado_banco" in res["herramientas"]
    assert "banco" in res["respuesta"].lower()


def test_chat_sin_proveedor(monkeypatch):
    monkeypatch.setattr(asistente, "_proveedor", lambda: None)
    res = asistente.chat([{"role": "user", "content": "hola"}])
    assert "No hay IA" in res["respuesta"]
