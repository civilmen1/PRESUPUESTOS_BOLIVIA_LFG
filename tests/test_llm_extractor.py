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
    assert set(disp.keys()) == {"openai", "anthropic", "gemini"}
    assert all(v is False for v in disp.values())  # entorno de test sin keys
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
