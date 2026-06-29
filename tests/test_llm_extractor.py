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
    # GLM-5.2 (Z.AI) también debe aparecer en la lista de proveedores
    assert any("glm" in k for k in disp)
    # entorno de test: sin keys y sin servicio Ollama corriendo
    assert all(v is False for v in disp.values())
    assert hay_llm() is False


def test_glm_disponible_con_key(monkeypatch):
    """Con GLM_API_KEY configurada, GLM aparece como proveedor disponible."""
    from config import settings
    monkeypatch.setattr(settings, "GLM_API_KEY", "test-key", raising=False)
    disp = proveedores_disponibles()
    assert disp.get("glm-5.2 (z.ai)") is True
    assert hay_llm() is True


def test_glm_json_sin_red_devuelve_none(monkeypatch):
    """Si la llamada HTTP falla, _glm_json devuelve None (no rompe la cadena)."""
    from config import settings
    from core import llm_extractor
    monkeypatch.setattr(settings, "GLM_API_KEY", "test-key", raising=False)
    # Base URL inalcanzable → requests lanza, se captura y devuelve None.
    monkeypatch.setattr(settings, "GLM_BASE_URL", "http://127.0.0.1:9", raising=False)
    monkeypatch.setattr(settings, "GLM_TIMEOUT", 1, raising=False)
    assert llm_extractor._glm_json("hola", "glm-5.2") is None


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
