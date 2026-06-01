"""Pruebas del extractor con IA/LLM (modo opcional con fallback offline)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.info_extractor import InfoTecnica  # noqa: E402
from core.llm_extractor import (extraer_info_inteligente, hay_llm,  # noqa: E402
                                proveedores_disponibles)

SPEC = ("2.1 HORMIGON ARMADO. MATERIALES: cemento, arena, grava, acero. "
        "EJECUCION: albañil, fierrista, mezcladora, vibradora. MEDICION: m3.")


def test_proveedores_sin_keys():
    disp = proveedores_disponibles()
    # incluye el proveedor local Ollama además de los de pago
    assert "openai" in disp and "anthropic" in disp and "gemini" in disp
    assert any("ollama" in k for k in disp)
    # entorno de test: sin keys y sin servicio Ollama corriendo
    assert all(v is False for v in disp.values())
    assert hay_llm() is False


def test_fallback_offline_sin_keys():
    """Sin API keys, debe usar el extractor offline y aún así extraer datos."""
    info = extraer_info_inteligente("Hormigón armado", SPEC, 1)
    assert isinstance(info, InfoTecnica)
    assert "cemento" in info.materiales
    assert "albañil" in info.mano_obra
    assert "mezcladora" in info.equipo


def test_fallback_no_rompe_sin_spec():
    info = extraer_info_inteligente("Item sin spec", "", 1)
    assert isinstance(info, InfoTecnica)
    assert info.materiales == []


def test_ollama_no_disponible_sin_servicio():
    """Sin Ollama corriendo, la detección no debe lanzar excepción."""
    from core.llm_extractor import ollama_disponible
    assert ollama_disponible() is False


def test_limpiar_json_quita_cercos():
    from core.llm_extractor import _limpiar_json
    assert _limpiar_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _limpiar_json('texto {"b": 2} fin') == '{"b": 2}'
