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
    """Indica qué proveedores LLM están disponibles.

    Ollama es LOCAL y GRATIS: disponible si el servicio responde en OLLAMA_HOST.
    Los demás dependen de su API key (de pago).
    """
    return {
        "ollama (local gratis)": settings.USAR_OLLAMA and ollama_disponible(),
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "gemini": bool(settings.GEMINI_API_KEY),
    }


def hay_llm() -> bool:
    return any(proveedores_disponibles().values())


def ollama_disponible() -> bool:
    """True si el servicio Ollama responde en el host configurado."""
    try:
        import requests
        r = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# 1) Extracción estructurada de partidas (rol: GPT-4o)
# --------------------------------------------------------------------------- #
_PROMPT_EXTRACCION = """\
Eres un INGENIERO CIVIL ESPECIALISTA EN COSTOS de Bolivia con 20 anios de
experiencia elaborando Analisis de Precios Unitarios (APU) bajo la norma
NB-SABS (DS 0181). Conoces los rendimientos reales de la construccion boliviana.

TAREA: Para el ITEM dado y su ESPECIFICACION, genera la lista COMPLETA y
REALISTA de recursos (materiales, mano de obra y equipo) necesarios para
ejecutar UNA UNIDAD del item. Razona por el TIPO de actividad aunque la
especificacion no detalle todo.

REGLAS DE CALIDAD (obligatorias):
1. COHERENCIA: los recursos deben corresponder al tipo de obra. Ej.: un letrero
   metalico NO lleva tuberia PVC; una excavacion NO lleva cemento salvo que se
   indique. Piensa: que se usa REALMENTE para esta actividad.
2. MATERIALES: unidad real (kg, m3, m2, ml, bolsa, pza, lt, glb, p2) y cantidad
   por unidad del item, con desperdicio razonable.
3. MANO DE OBRA: SIEMPRE unidad "hora". Indica las cuadrillas que correspondan
   (ej. soldador para estructura metalica, plomero para sanitario, pintor para
   pintura, fierrista para armaduras). Cantidad = horas-hombre por unidad.
4. EQUIPO/HERRAMIENTA: SIEMPRE unidad "hora". Incluye el equipo especifico de la
   actividad (ej. soldadora para soldadura, mezcladora+vibradora para hormigon).
5. Incluye "Herramientas menores" como equipo cuando aplique.
6. Cantidades realistas (rendimientos bolivianos), no genericas.

EJEMPLO 1 - Item: "Hormigon armado para zapatas H21", unidad m3:
{{"alcance":"Provision y vaciado de hormigon armado H21 para zapatas",
"normas":["NB 1225001"],"medicion":"metro cubico (m3)",
"recursos":[
{{"tipo":"material","descripcion":"Cemento Portland IP-30","unidad":"bolsa","cantidad":7.0}},
{{"tipo":"material","descripcion":"Arena","unidad":"m3","cantidad":0.5}},
{{"tipo":"material","descripcion":"Grava","unidad":"m3","cantidad":0.8}},
{{"tipo":"material","descripcion":"Acero corrugado fy=4200","unidad":"kg","cantidad":80.0}},
{{"tipo":"material","descripcion":"Madera para encofrado","unidad":"p2","cantidad":6.0}},
{{"tipo":"mano_obra","descripcion":"Albanil","unidad":"hora","cantidad":8.0}},
{{"tipo":"mano_obra","descripcion":"Fierrista","unidad":"hora","cantidad":6.0}},
{{"tipo":"mano_obra","descripcion":"Ayudante","unidad":"hora","cantidad":16.0}},
{{"tipo":"equipo","descripcion":"Mezcladora de hormigon","unidad":"hora","cantidad":2.0}},
{{"tipo":"equipo","descripcion":"Vibradora de inmersion","unidad":"hora","cantidad":1.5}},
{{"tipo":"equipo","descripcion":"Herramientas menores","unidad":"hora","cantidad":1.0}}]}}

EJEMPLO 2 - Item: "Letrero de obra de estructura metalica 7.00x4.8 m", unidad pza:
{{"alcance":"Provision y montaje de letrero de obra con estructura metalica",
"normas":[],"medicion":"pieza (pza)",
"recursos":[
{{"tipo":"material","descripcion":"Poste metalico perfil costanera 80x40x15x2mm","unidad":"ml","cantidad":10.0}},
{{"tipo":"material","descripcion":"Letrero banner con bastidor metalico","unidad":"glb","cantidad":1.0}},
{{"tipo":"material","descripcion":"Electrodos para soldadura","unidad":"kg","cantidad":1.0}},
{{"tipo":"material","descripcion":"Cemento Portland IP-40","unidad":"kg","cantidad":50.0}},
{{"tipo":"material","descripcion":"Arena","unidad":"m3","cantidad":0.25}},
{{"tipo":"material","descripcion":"Grava","unidad":"m3","cantidad":0.5}},
{{"tipo":"mano_obra","descripcion":"Soldador","unidad":"hora","cantidad":15.0}},
{{"tipo":"mano_obra","descripcion":"Albanil","unidad":"hora","cantidad":4.0}},
{{"tipo":"mano_obra","descripcion":"Ayudante","unidad":"hora","cantidad":12.0}},
{{"tipo":"equipo","descripcion":"Equipo de soldadura","unidad":"hora","cantidad":15.0}},
{{"tipo":"equipo","descripcion":"Herramientas menores","unidad":"hora","cantidad":1.0}}]}}

AHORA GENERA EL APU PARA:
Item: {item}
Unidad del item: {unidad}
ESPECIFICACION:
\"\"\"
{spec}
\"\"\"

Devuelve SOLO un JSON valido con la misma forma de los ejemplos (sin texto extra).
"""


def extraer_estructurado(item_descripcion: str, spec: str, item_id: int = 0,
                         unidad: str = "") -> Optional[InfoTecnica]:
    """Extracción estructurada de partidas (rol 1).

    Prioriza el LLM LOCAL GRATIS (Ollama); si no, usa GPT-4o (de pago).
    Devuelve None si no hay ningún proveedor disponible.
    """
    prompt = _PROMPT_EXTRACCION.format(item=item_descripcion, unidad=unidad or "und",
                                       spec=spec[:8000])

    contenido = None
    # 1) Ollama local (gratis, sin tokens)
    if settings.USAR_OLLAMA and ollama_disponible():
        contenido = _ollama_json(prompt, modelo=settings.OLLAMA_MODEL)
    # 2) Gemini (nivel gratuito) — ideal para la nube
    if not contenido and settings.GEMINI_API_KEY:
        contenido = _gemini_json(prompt, modelo=settings.GEMINI_MODEL)
    # 3) GPT-4o (de pago) como alternativa
    if not contenido and settings.OPENAI_API_KEY:
        contenido = _openai_json(prompt, modelo=settings.OPENAI_MODEL)

    if not contenido:
        return None
    info = _json_a_info(contenido, item_id, item_descripcion, spec)
    # Control de calidad: la IA debe entregar al menos mano de obra (toda
    # actividad la necesita). Si la salida es vacia o absurda, se descarta.
    detalle = getattr(info, "recursos_detalle", []) or []
    tiene_mo = any(d.get("tipo") == "mano_obra" for d in detalle)
    if not detalle or not tiene_mo:
        logger.warning("Salida de IA pobre para '%s' (%d recursos); se descarta",
                       item_descripcion[:40], len(detalle))
        return None
    return info


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
    """Interpretación normativa (rol 2): Claude si hay key, si no Ollama local."""
    prompt = _PROMPT_NORMATIVO.format(item=item_descripcion, spec=spec[:8000])
    contenido = None
    if settings.ANTHROPIC_API_KEY:
        contenido = _anthropic_json(prompt, modelo=settings.ANTHROPIC_MODEL)
    if not contenido and settings.USAR_OLLAMA and ollama_disponible():
        contenido = _ollama_json(prompt, modelo=settings.OLLAMA_MODEL)
    if not contenido:
        return None
    try:
        return json.loads(_limpiar_json(contenido))
    except json.JSONDecodeError:
        logger.warning("Respuesta normativa no es JSON válido")
        return None


# --------------------------------------------------------------------------- #
# 3) Análisis de planos / PDF (rol: Gemini, multimodal)
# --------------------------------------------------------------------------- #
def analizar_planos(ruta_pdf: str, prompt: str = "") -> Optional[str]:
    """Análisis de un plano/PDF con Gemini (rol 3). None si no hay key.

    Usa la API REST (sin SDK): sube el texto del documento como contexto.
    """
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from core.parser_documento import extraer_texto
        texto = extraer_texto(ruta_pdf)[:12000]
    except Exception:
        texto = ""
    instr = (prompt or "Analiza este documento de construcción y lista las "
             "partidas, materiales y cantidades que identifiques.") + \
        "\n\nDOCUMENTO:\n" + texto
    return _gemini_json(instr, settings.GEMINI_MODEL)


# --------------------------------------------------------------------------- #
# Orquestador: combina IA (si hay) + extractor offline (siempre)
# --------------------------------------------------------------------------- #
def extraer_info_inteligente(item_descripcion: str, spec: str, item_id: int = 0,
                             unidad: str = "") -> InfoTecnica:
    """Extrae info usando el mejor recurso disponible.

    Estrategia: si hay GPT-4o, usa extracción estructurada; enriquece con la
    interpretación normativa de Claude si está disponible. Si no hay ningún
    LLM, usa el extractor offline por reglas (siempre funciona).
    """
    info = None
    try:
        info = extraer_estructurado(item_descripcion, spec, item_id, unidad)
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
def _ollama_json(prompt: str, modelo: str) -> Optional[str]:
    """Llama a un modelo LOCAL vía Ollama (gratis, sin tokens). Pide JSON."""
    try:
        import requests
    except ImportError:
        return None
    try:
        resp = requests.post(
            f"{settings.OLLAMA_HOST}/api/generate",
            json={"model": modelo, "prompt": prompt, "stream": False,
                  "format": "json", "options": {"temperature": 0.1}},
            timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception:
        logger.exception("Error llamando a Ollama (%s)", settings.OLLAMA_HOST)
        return None


def _gemini_json(prompt: str, modelo: str) -> Optional[str]:
    """Llama a Gemini por su API REST (sin SDK) pidiendo respuesta en JSON.

    Usa requests (ya disponible), por lo que no requiere instalar paquetes
    pesados ni arriesgar el arranque de la app.
    """
    try:
        import requests
    except ImportError:
        return None
    import time
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{modelo}:generateContent")
    cuerpo = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1,
                             "responseMimeType": "application/json"},
    }
    # Reintenta ante limite de tasa (429) del nivel gratuito, con tiempo acotado.
    intentos = max(1, settings.GEMINI_MAX_REINTENTOS + 1)
    for intento in range(intentos):
        try:
            resp = requests.post(url, params={"key": settings.GEMINI_API_KEY},
                                 json=cuerpo, timeout=settings.GEMINI_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            if resp.status_code == 429:
                if intento == intentos - 1:
                    logger.warning("Gemini 429 persistente; se omite este item.")
                    return None
                espera = 5 * (intento + 1)
                logger.warning("Gemini 429 (limite de tasa); reintentando en %ss",
                               espera)
                time.sleep(espera)
                continue
            logger.error("Gemini API HTTP %s: %s", resp.status_code,
                         resp.text[:300])
            return None
        except Exception as exc:
            logger.error("Error llamando a Gemini REST: %s", exc)
            return None
    return None


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


def _limpiar_json(contenido: str) -> str:
    """Quita cercos ```json ... ``` y recorta al primer objeto { ... }."""
    if not contenido:
        return ""
    txt = contenido.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lstrip().lower().startswith("json"):
            txt = txt.lstrip()[4:]
    ini, fin = txt.find("{"), txt.rfind("}")
    return txt[ini:fin + 1] if ini != -1 and fin != -1 else txt


def _json_a_info(contenido: str, item_id: int, item_desc: str,
                 spec: str) -> InfoTecnica:
    """Convierte la respuesta JSON del LLM en InfoTecnica; cae a offline si falla."""
    try:
        data = json.loads(_limpiar_json(contenido))
        recursos = []
        mats, mo, eq = [], [], []
        for r in data.get("recursos", []):
            tipo = str(r.get("tipo", "material")).lower()
            if tipo not in ("material", "mano_obra", "equipo"):
                tipo = "material"
            unidad = str(r.get("unidad", ""))
            # mano de obra y equipo: forzar unidad horas
            if tipo in ("mano_obra", "equipo"):
                unidad = "hora"
            desc = str(r.get("descripcion", "")).strip()
            if not desc:
                continue
            try:
                cant = float(r.get("cantidad", 0) or 0)
            except (TypeError, ValueError):
                cant = 0.0
            recursos.append({"tipo": tipo, "descripcion": desc, "unidad": unidad,
                             "cantidad": cant, "categoria": ""})
            (mats if tipo == "material" else mo if tipo == "mano_obra" else eq
             ).append(desc)
        return InfoTecnica(
            item_id=item_id,
            alcance=str(data.get("alcance", ""))[:500],
            materiales=mats or [str(x) for x in data.get("materiales", [])],
            mano_obra=mo or [str(x) for x in data.get("mano_obra", [])],
            equipo=eq or [str(x) for x in data.get("equipo", [])],
            normas=[str(x) for x in data.get("normas", [])],
            medicion=str(data.get("medicion", "")),
            recursos_detalle=recursos,
            tiene_especificacion=bool(spec.strip()),
            resumen="Generado con IA según contexto del ítem")
    except (json.JSONDecodeError, AttributeError, TypeError):
        logger.warning("JSON inválido del LLM; usando extractor offline")
        return extraer_info(item_desc, spec, item_id)
