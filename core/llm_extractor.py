"""Extractor de información con IA / LLM (multi-modelo, opcional).

Arquitectura recomendada (cada modelo en el rol donde rinde mejor):

  1. Extracción estructurada  → GPT-4o
     (partidas, cantidades, unidades, materiales, mano de obra, equipo)
  2. Interpretación normativa  → Claude Sonnet
     (NB-DS 2023, NB 1225001, ACI, ASTM: requisitos mínimos y ensayos)
  3. Análisis de planos/PDF    → Gemini (multimodal + contexto largo)

DISEÑO SEGURO:
  - Todo es OPCIONAL. Si no hay API key configurada, estas funciones devuelven
    None y el sistema usa el extractor offline (core.info_extractor).
  - Las llamadas y los SDKs se importan de forma perezosa: el programa arranca
    sin instalar openai / anthropic / google-generativeai.
  - El modelo elegido se enruta según la tarea; si el proveedor de esa tarea no
    está configurado, cae al proveedor disponible o al modo offline.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

from config import settings
from config.logging_config import get_logger
from core.info_extractor import InfoTecnica, extraer_info

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Disponibilidad de proveedores
# --------------------------------------------------------------------------- #
def proveedores_disponibles() -> dict:
    """Indica qué proveedores LLM tienen API key configurada."""
    return {
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "gemini": bool(settings.GEMINI_API_KEY),
    }


def hay_llm() -> bool:
    return any(proveedores_disponibles().values())


# --------------------------------------------------------------------------- #
# 1) Extracción estructurada de partidas (rol: GPT-4o)
# --------------------------------------------------------------------------- #
_PROMPT_EXTRACCION = """\
Eres un ingeniero de costos en Bolivia. A partir de la ESPECIFICACIÓN TÉCNICA de
un ítem de obra, extrae su Análisis de Precios Unitarios preliminar.

Ítem: {item}

ESPECIFICACIÓN:
\"\"\"
{spec}
\"\"\"

Devuelve SOLO un JSON válido con esta forma exacta (sin texto adicional):
{{
  "alcance": "resumen del alcance en 1-2 frases",
  "materiales": ["material 1", "material 2"],
  "mano_obra": ["albañil", "ayudante"],
  "equipo": ["mezcladora", "herramienta menor"],
  "normas": ["NB 1225001"],
  "medicion": "unidad y forma de pago"
}}
Incluye los recursos MÍNIMOS razonables aunque la especificación no los detalle.
"""


def extraer_estructurado(item_descripcion: str, spec: str,
                         item_id: int = 0) -> Optional[InfoTecnica]:
    """Extracción estructurada con GPT-4o (rol 1). None si no hay OpenAI."""
    if not settings.OPENAI_API_KEY:
        return None
    contenido = _openai_json(
        _PROMPT_EXTRACCION.format(item=item_descripcion, spec=spec[:8000]),
        modelo=settings.OPENAI_MODEL)
    if not contenido:
        return None
    return _json_a_info(contenido, item_id, item_descripcion, spec)


# --------------------------------------------------------------------------- #
# 2) Interpretación normativa (rol: Claude Sonnet)
# --------------------------------------------------------------------------- #
_PROMPT_NORMATIVO = """\
Eres especialista en normativa de construcción boliviana (NB-DS 2023, NB 1225001)
y normas ACI/ASTM. Para el ítem y su especificación, indica los requisitos
técnicos MÍNIMOS obligatorios (resistencias, ensayos, tolerancias) y los recursos
que la norma exige aunque no estén en la especificación.

Ítem: {item}
ESPECIFICACIÓN:
\"\"\"
{spec}
\"\"\"

Devuelve SOLO un JSON: {{"requisitos_normativos": ["..."], "ensayos": ["..."],
"recursos_obligatorios": ["..."], "normas": ["NB 1225001"]}}
"""


def interpretar_normativa(item_descripcion: str, spec: str) -> Optional[dict]:
    """Interpretación normativa con Claude Sonnet (rol 2). None si no hay key."""
    if not settings.ANTHROPIC_API_KEY:
        return None
    contenido = _anthropic_json(
        _PROMPT_NORMATIVO.format(item=item_descripcion, spec=spec[:8000]),
        modelo=settings.ANTHROPIC_MODEL)
    if not contenido:
        return None
    try:
        return json.loads(contenido)
    except json.JSONDecodeError:
        logger.warning("Respuesta normativa no es JSON válido")
        return None


# --------------------------------------------------------------------------- #
# 3) Análisis de planos / PDF (rol: Gemini, multimodal)
# --------------------------------------------------------------------------- #
def analizar_planos(ruta_pdf: str, prompt: str = "") -> Optional[str]:
    """Análisis multimodal de un plano/PDF con Gemini (rol 3). None si no hay key."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai no instalado; no se analizan planos")
        return None
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        archivo = genai.upload_file(ruta_pdf)
        instr = prompt or ("Analiza este plano/documento de construcción y lista "
                           "las partidas, materiales y cantidades que identifiques.")
        resp = model.generate_content([archivo, instr])
        return resp.text
    except Exception:
        logger.exception("Error analizando planos con Gemini")
        return None


# --------------------------------------------------------------------------- #
# Orquestador: combina IA (si hay) + extractor offline (siempre)
# --------------------------------------------------------------------------- #
def extraer_info_inteligente(item_descripcion: str, spec: str,
                             item_id: int = 0) -> InfoTecnica:
    """Extrae info usando el mejor recurso disponible.

    Estrategia: si hay GPT-4o, usa extracción estructurada; enriquece con la
    interpretación normativa de Claude si está disponible. Si no hay ningún
    LLM, usa el extractor offline por reglas (siempre funciona).
    """
    info = None
    try:
        info = extraer_estructurado(item_descripcion, spec, item_id)
    except Exception:
        logger.exception("Fallo extracción LLM; se usa extractor offline")

    if info is None:
        info = extraer_info(item_descripcion, spec, item_id)  # offline

    # Enriquecer con normativa (Claude) si está configurado
    try:
        norm = interpretar_normativa(item_descripcion, spec)
        if norm:
            for n in norm.get("normas", []):
                if n not in info.normas:
                    info.normas.append(n)
            obligatorios = norm.get("recursos_obligatorios", [])
            if obligatorios:
                info.resumen += " · Normativa: " + ", ".join(obligatorios[:5])
    except Exception:
        logger.exception("Fallo interpretación normativa (Claude)")

    return info


# --------------------------------------------------------------------------- #
# Clientes LLM (perezosos, con manejo de errores)
# --------------------------------------------------------------------------- #
def _openai_json(prompt: str, modelo: str) -> Optional[str]:
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai no instalado; omitiendo GPT-4o")
        return None
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1)
        return resp.choices[0].message.content
    except Exception:
        logger.exception("Error llamando a OpenAI")
        return None


def _anthropic_json(prompt: str, modelo: str) -> Optional[str]:
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic no instalado; omitiendo Claude")
        return None
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=modelo, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}])
        return resp.content[0].text
    except Exception:
        logger.exception("Error llamando a Anthropic")
        return None


def _json_a_info(contenido: str, item_id: int, item_desc: str,
                 spec: str) -> InfoTecnica:
    """Convierte la respuesta JSON del LLM en InfoTecnica; cae a offline si falla."""
    try:
        # algunos modelos envuelven el JSON en ```json ... ```
        limpio = contenido.strip().lstrip("`").replace("json", "", 1) \
            if contenido.strip().startswith("`") else contenido
        data = json.loads(limpio)
        return InfoTecnica(
            item_id=item_id,
            alcance=data.get("alcance", "")[:500],
            materiales=[str(x) for x in data.get("materiales", [])],
            mano_obra=[str(x) for x in data.get("mano_obra", [])],
            equipo=[str(x) for x in data.get("equipo", [])],
            normas=[str(x) for x in data.get("normas", [])],
            medicion=str(data.get("medicion", "")),
            tiene_especificacion=bool(spec.strip()),
            resumen="Extraído con IA (GPT-4o)")
    except (json.JSONDecodeError, AttributeError):
        logger.warning("JSON inválido del LLM; usando extractor offline")
        return extraer_info(item_desc, spec, item_id)
