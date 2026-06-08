"""Asistente de estimacion con TOOL-CALLING sobre TUS datos reales.

El modelo (qwen3-coder local via Ollama, o Groq en linea) no adivina: cuando
necesita un dato llama a una HERRAMIENTA que consulta el banco de APU, los
precios o el proyecto, y razona con el resultado real. Reescrito desde cero
(sin codigo de terceros con licencia restrictiva).

Proveedor por prioridad:  Ollama local (gratis)  ->  Groq (online gratis).
"""
from __future__ import annotations

import json
from typing import Callable, Optional

from config import settings
from config.logging_config import get_logger

logger = get_logger(__name__)

_SISTEMA = (
    "Eres un asistente experto en Analisis de Precios Unitarios (APU) de la "
    "construccion en Bolivia (norma NB-SABS). Ayudas a estimar recursos y "
    "precios. SIEMPRE que necesites un dato del banco, un precio o info del "
    "proyecto, usa las herramientas disponibles en lugar de inventar. Mano de "
    "obra y equipo SIEMPRE en horas; no uses el termino 'peon' (di 'ayudante'). "
    "Responde en espanol, claro y conciso."
)


# --------------------------------------------------------------------------- #
# Implementacion de las herramientas (operan sobre datos reales)
# --------------------------------------------------------------------------- #
def _t_estado_banco(ctx: dict) -> dict:
    from core import banco_apu
    return {"total_apus": len(banco_apu.listar_apus())}


def _t_buscar_banco_apu(ctx: dict, consulta: str) -> dict:
    from core import banco_apu
    apu = banco_apu.buscar_apu(consulta)
    if not apu:
        return {"encontrado": False}
    def _res(grupo):
        return [{"descripcion": r.get("descripcion", ""),
                 "unidad": r.get("unidad", ""), "cantidad": r.get("cantidad", 0),
                 "precio": r.get("precio", 0)} for r in apu.get(grupo, []) or []]
    return {"encontrado": True, "actividad": apu.get("actividad", ""),
            "unidad": apu.get("unidad", ""),
            "materiales": _res("materiales"), "mano_obra": _res("mano_obra"),
            "equipo": _res("equipo")}


def _t_buscar_precio_insumo(ctx: dict, descripcion: str) -> dict:
    from core import banco_apu
    p = banco_apu.buscar_precio(descripcion)
    return p or {"encontrado": False}


def _t_generar_apu(ctx: dict, item: str, unidad: str = "",
                   especificacion: str = "") -> dict:
    from core.llm_extractor import extraer_estructurado
    info = extraer_estructurado(item, especificacion or item, unidad=unidad)
    if not info:
        return {"ok": False, "motivo": "la IA no pudo generar el APU"}
    return {"ok": True, "recursos": getattr(info, "recursos_detalle", [])}


def _t_listar_items(ctx: dict) -> dict:
    proyecto_id = ctx.get("proyecto_id")
    if not proyecto_id:
        return {"items": [], "nota": "no hay proyecto activo"}
    from core import repositories
    items = repositories.listar_items(proyecto_id)
    return {"items": [{"numero": it.numero, "descripcion": it.descripcion,
                       "unidad": it.unidad} for it in items if not it.es_modulo]}


# Registro: nombre -> (funcion, descripcion, parametros JSON Schema)
_TOOLS: dict[str, tuple[Callable, str, dict]] = {
    "estado_banco": (
        _t_estado_banco, "Cuantos APU hay en el banco de referencia.",
        {"type": "object", "properties": {}}),
    "buscar_banco_apu": (
        _t_buscar_banco_apu,
        "Busca en el banco el APU mas parecido a una actividad y devuelve sus "
        "materiales, mano de obra y equipo con precios.",
        {"type": "object", "properties": {
            "consulta": {"type": "string",
                         "description": "actividad a buscar, ej. 'hormigon armado columnas'"}},
         "required": ["consulta"]}),
    "buscar_precio_insumo": (
        _t_buscar_precio_insumo,
        "Busca el precio de referencia de un insumo (material/mano de obra/equipo).",
        {"type": "object", "properties": {
            "descripcion": {"type": "string"}}, "required": ["descripcion"]}),
    "generar_apu": (
        _t_generar_apu,
        "Genera con IA la lista de recursos (materiales, mano de obra, equipo) "
        "para una actividad y su unidad.",
        {"type": "object", "properties": {
            "item": {"type": "string"},
            "unidad": {"type": "string"},
            "especificacion": {"type": "string"}}, "required": ["item"]}),
    "listar_items": (
        _t_listar_items, "Lista los items del proyecto activo.",
        {"type": "object", "properties": {}}),
}


def _spec_tools() -> list:
    return [{"type": "function", "function": {
        "name": n, "description": d, "parameters": p}}
        for n, (_, d, p) in _TOOLS.items()]


def _ejecutar(nombre: str, args: dict, ctx: dict) -> str:
    fn = _TOOLS.get(nombre, (None,))[0]
    if not fn:
        return json.dumps({"error": f"herramienta desconocida: {nombre}"})
    try:
        return json.dumps(fn(ctx, **(args or {})), ensure_ascii=False)
    except Exception as exc:
        logger.exception("Error en herramienta %s", nombre)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Backends de chat (normalizan tool_calls a {id, name, args})
# --------------------------------------------------------------------------- #
def _proveedor() -> Optional[str]:
    try:
        from core.llm_extractor import ollama_disponible
        if settings.USAR_OLLAMA and ollama_disponible():
            return "ollama"
    except Exception:
        pass
    if settings.GROQ_API_KEY:
        return "groq"
    return None


def disponible() -> bool:
    return _proveedor() is not None


def _llamar_ollama(mensajes: list) -> dict:
    import requests
    r = requests.post(f"{settings.OLLAMA_HOST}/api/chat",
                      json={"model": settings.OLLAMA_MODEL, "messages": mensajes,
                            "tools": _spec_tools(), "stream": False,
                            "options": {"temperature": 0.2}},
                      timeout=settings.OLLAMA_TIMEOUT)
    r.raise_for_status()
    msg = r.json().get("message", {})
    llamadas = []
    for tc in msg.get("tool_calls", []) or []:
        f = tc.get("function", {})
        args = f.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        llamadas.append({"id": "", "name": f.get("name", ""), "args": args})
    return {"raw": msg, "content": msg.get("content", ""), "tool_calls": llamadas}


def _llamar_groq(mensajes: list) -> dict:
    import requests
    r = requests.post(f"{settings.GROQ_BASE_URL}/chat/completions",
                      headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                      json={"model": settings.GROQ_MODEL, "messages": mensajes,
                            "tools": _spec_tools(), "tool_choice": "auto",
                            "temperature": 0.2},
                      timeout=60)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    llamadas = []
    for tc in msg.get("tool_calls", []) or []:
        f = tc.get("function", {})
        try:
            args = json.loads(f.get("arguments", "{}"))
        except Exception:
            args = {}
        llamadas.append({"id": tc.get("id", ""), "name": f.get("name", ""),
                         "args": args})
    return {"raw": msg, "content": msg.get("content") or "",
            "tool_calls": llamadas}


# --------------------------------------------------------------------------- #
# Bucle de conversacion con herramientas
# --------------------------------------------------------------------------- #
def chat(historial: list, proyecto=None, max_pasos: int = 5) -> dict:
    """Procesa la conversacion. `historial` = [{role, content}, ...].

    Devuelve {"respuesta": str, "herramientas": [nombres usados]}.
    """
    prov = _proveedor()
    if not prov:
        return {"respuesta": "No hay IA disponible para el asistente. Activa "
                "Ollama local (USAR_OLLAMA=true) o configura GROQ_API_KEY.",
                "herramientas": []}

    ctx = {"proyecto_id": getattr(proyecto, "id", None)}
    mensajes = [{"role": "system", "content": _SISTEMA}] + list(historial)
    usadas: list[str] = []
    llamar = _llamar_ollama if prov == "ollama" else _llamar_groq

    for _ in range(max_pasos):
        try:
            resp = llamar(mensajes)
        except Exception as exc:
            logger.exception("Fallo el asistente (%s)", prov)
            return {"respuesta": f"Error al consultar la IA ({prov}): {exc}",
                    "herramientas": usadas}

        if not resp["tool_calls"]:
            return {"respuesta": resp["content"] or "(sin respuesta)",
                    "herramientas": usadas}

        # Anexa el turno del asistente (con las tool_calls) y ejecuta cada una.
        mensajes.append(resp["raw"])
        for tc in resp["tool_calls"]:
            usadas.append(tc["name"])
            resultado = _ejecutar(tc["name"], tc["args"], ctx)
            msg_tool = {"role": "tool", "name": tc["name"], "content": resultado}
            if tc["id"]:
                msg_tool["tool_call_id"] = tc["id"]
            mensajes.append(msg_tool)

    return {"respuesta": "No pude completar la consulta en los pasos permitidos. "
            "Reformula la pregunta, por favor.", "herramientas": usadas}
