"""Moderacion de aportes publicos al Banco de APU.

Los aportes recibidos en la pagina publica (?aportar=1) NO entran directo al
banco que usa la IA: quedan en una cola PENDIENTE hasta que el contratista los
aprueba desde el panel del Banco de APU. Asi un enlace abierto no degrada la
calidad de los precios.

Almacen: data/aportes_pendientes.json
  {"aportes": [
     {"id": 17, "nombre": "...", "correo": "...", "archivo": "B-2.xlsx",
      "fecha": "2026-06-06T10:00:00", "estado": "pendiente|aprobado|rechazado",
      "apus": [ {...APU...}, ... ]}
  ]}
"""
from __future__ import annotations

import json
from datetime import datetime

from config import settings

_RUTA = settings.PERSIST_DIR / "aportes_pendientes.json"


def _leer() -> dict:
    try:
        if _RUTA.exists():
            return json.loads(_RUTA.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"aportes": []}


def _guardar(datos: dict) -> None:
    _RUTA.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                     encoding="utf-8")


def agregar_pendiente(nombre: str, correo: str, archivo: str,
                      apus: list[dict]) -> int:
    """Registra un aporte en estado 'pendiente'. Devuelve su id."""
    datos = _leer()
    aportes = datos.setdefault("aportes", [])
    nuevo_id = (max((a.get("id", 0) for a in aportes), default=0) + 1)
    aportes.append({
        "id": nuevo_id, "nombre": nombre, "correo": correo, "archivo": archivo,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "estado": "pendiente", "apus": apus})
    _guardar(datos)
    return nuevo_id


def listar(estado: str | None = None) -> list[dict]:
    """Lista aportes; si se da 'estado', filtra (pendiente/aprobado/rechazado)."""
    aportes = _leer().get("aportes", [])
    if estado:
        return [a for a in aportes if a.get("estado") == estado]
    return aportes


def contar_pendientes() -> int:
    return len(listar("pendiente"))


def aprobar(aporte_id: int) -> dict:
    """Aprueba un aporte: incorpora sus APUs al banco (actualizando los que ya
    existan) y lo marca 'aprobado'. Devuelve {agregados, actualizados, omitidos}."""
    from scripts.importar_apu_banco import guardar_banco
    from core import banco_apu

    datos = _leer()
    res = {"agregados": 0, "actualizados": 0, "omitidos": 0}
    hubo = False
    for a in datos.get("aportes", []):
        if a.get("id") == aporte_id and a.get("estado") == "pendiente":
            r = guardar_banco(a.get("apus", []),
                              proyecto=f"aporte:{a.get('nombre','')}",
                              reemplazar=False, actualizar_duplicados=True)
            for k in res:
                res[k] += r.get(k, 0)
            a["estado"] = "aprobado"
            hubo = True
            break
    _guardar(datos)
    if hubo:
        banco_apu._cargar.cache_clear()
        try:
            banco_apu.guardar_markdown()
        except Exception:
            pass
    return res


def aprobar_todos() -> dict:
    """Aprueba TODOS los aportes pendientes. Devuelve {agregados, actualizados,
    omitidos} sumados."""
    from scripts.importar_apu_banco import guardar_banco
    from core import banco_apu

    datos = _leer()
    res = {"agregados": 0, "actualizados": 0, "omitidos": 0}
    hubo = False
    for a in datos.get("aportes", []):
        if a.get("estado") == "pendiente":
            r = guardar_banco(a.get("apus", []),
                              proyecto=f"aporte:{a.get('nombre','')}",
                              reemplazar=False, actualizar_duplicados=True)
            for k in res:
                res[k] += r.get(k, 0)
            a["estado"] = "aprobado"
            hubo = True
    _guardar(datos)
    if hubo:
        banco_apu._cargar.cache_clear()
        try:
            banco_apu.guardar_markdown()
        except Exception:
            pass
    return res


def rechazar(aporte_id: int) -> bool:
    """Marca un aporte como 'rechazado' (no entra al banco)."""
    datos = _leer()
    ok = False
    for a in datos.get("aportes", []):
        if a.get("id") == aporte_id and a.get("estado") == "pendiente":
            a["estado"] = "rechazado"
            ok = True
            break
    _guardar(datos)
    return ok
