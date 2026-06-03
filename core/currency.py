"""Manejo de monedas extensible (Bolivianos, Dólares y las que se agreguen).

Cada moneda define su tipo de cambio respecto al **Dólar Americano (USD)**:
  por_usd = cuántas unidades de esa moneda equivalen a 1 USD.
  Ej.: BOB por_usd = 6.96  (6.96 Bs = 1 $us).

El catálogo se carga desde data/monedas.json y se puede ampliar desde la UI.
Todos los cálculos internos del APU se hacen en BOB; estas utilidades convierten
y formatean a la moneda del proyecto al mostrar o exportar.
"""
from __future__ import annotations

import json
from pathlib import Path

from config import settings

BOB = "BOB"
USD = "USD"

_RUTA = settings.DATA_DIR / "monedas.json"

# Catálogo por defecto (si falta el archivo)
_DEFECTO = {
    "monedas": [
        {"codigo": "BOB", "nombre": "Bolivianos", "simbolo": "Bs", "por_usd": 6.96},
        {"codigo": "USD", "nombre": "Dólares Americanos", "simbolo": "$us",
         "por_usd": 1.0},
    ]
}


def _cargar() -> dict:
    try:
        if _RUTA.exists():
            return json.loads(_RUTA.read_text(encoding="utf-8"))
    except Exception:
        pass
    return _DEFECTO


def _guardar(data: dict) -> None:
    _RUTA.parent.mkdir(parents=True, exist_ok=True)
    _RUTA.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                     encoding="utf-8")


def listar_monedas() -> list[dict]:
    """Lista de monedas disponibles: [{codigo, nombre, simbolo, por_usd}]."""
    return [m for m in _cargar().get("monedas", []) if m.get("codigo")]


def codigos() -> list[str]:
    return [m["codigo"] for m in listar_monedas()]


def info(codigo: str) -> dict:
    for m in listar_monedas():
        if m["codigo"] == codigo:
            return m
    return {"codigo": codigo, "nombre": codigo, "simbolo": codigo, "por_usd": 1.0}


def nombre(codigo: str) -> str:
    return info(codigo).get("nombre", codigo)


def simbolo(codigo: str) -> str:
    return info(codigo).get("simbolo", codigo)


def etiqueta(codigo: str) -> str:
    """Texto para selects: 'Bolivianos (Bs)'."""
    m = info(codigo)
    return f"{m.get('nombre', codigo)} ({m.get('simbolo', codigo)})"


def agregar_moneda(codigo: str, nombre_: str, simbolo_: str,
                   por_usd: float) -> None:
    """Agrega o actualiza una moneda en el catálogo (tipo de cambio vs USD)."""
    data = _cargar()
    monedas = data.setdefault("monedas", [])
    codigo = codigo.strip().upper()
    for m in monedas:
        if m["codigo"] == codigo:
            m.update(nombre=nombre_, simbolo=simbolo_, por_usd=float(por_usd))
            _guardar(data)
            return
    monedas.append({"codigo": codigo, "nombre": nombre_, "simbolo": simbolo_,
                    "por_usd": float(por_usd)})
    _guardar(data)


def eliminar_moneda(codigo: str) -> None:
    """Elimina una moneda del catálogo (no permite quitar BOB ni USD)."""
    if codigo in (BOB, USD):
        return
    data = _cargar()
    data["monedas"] = [m for m in data.get("monedas", []) if m["codigo"] != codigo]
    _guardar(data)


# --------------------------------------------------------------------------- #
# Conversión. Base interna de cálculo: BOB.
# --------------------------------------------------------------------------- #
def _por_usd(codigo: str, proyecto=None) -> float:
    """Tipo de cambio (unidades por 1 USD). Para BOB usa el del proyecto si hay."""
    if codigo == BOB and proyecto is not None and getattr(proyecto, "tipo_cambio", 0):
        return float(proyecto.tipo_cambio)
    return float(info(codigo).get("por_usd", 1.0)) or 1.0


def tipo_cambio(proyecto=None) -> float:
    """BOB por 1 USD (para mostrar). Toma el del proyecto si existe."""
    if proyecto is not None and getattr(proyecto, "tipo_cambio", 0):
        return float(proyecto.tipo_cambio)
    return float(info(BOB).get("por_usd", settings.TIPO_CAMBIO_USD))


def convertir(monto_bob: float, moneda_destino: str, proyecto=None) -> float:
    """Convierte un monto en BOB a la moneda destino."""
    try:
        monto_bob = float(monto_bob)
    except (TypeError, ValueError):
        return 0.0
    if moneda_destino == BOB:
        return round(monto_bob, 2)
    # BOB -> USD -> destino
    bob_por_usd = _por_usd(BOB, proyecto)
    usd = monto_bob / bob_por_usd if bob_por_usd else 0.0
    return round(usd * _por_usd(moneda_destino, proyecto), 2)


def a_bob(monto: float, moneda_origen: str, proyecto=None) -> float:
    """Convierte un monto de su moneda de origen a BOB (base de cálculo)."""
    try:
        monto = float(monto)
    except (TypeError, ValueError):
        return 0.0
    if moneda_origen == BOB:
        return round(monto, 2)
    usd = monto / (_por_usd(moneda_origen, proyecto) or 1.0)
    return round(usd * _por_usd(BOB, proyecto), 2)


def factor_desde_bob(moneda_destino: str, proyecto=None) -> float:
    """Factor multiplicativo para pasar un monto BOB a la moneda destino."""
    if moneda_destino == BOB:
        return 1.0
    bob_por_usd = _por_usd(BOB, proyecto) or 1.0
    return _por_usd(moneda_destino, proyecto) / bob_por_usd


def formatear(monto_bob: float, moneda: str, proyecto=None,
              con_simbolo: bool = True) -> str:
    """Formatea un monto (dado en BOB) en la moneda indicada."""
    valor = convertir(monto_bob, moneda, proyecto)
    texto = f"{valor:,.2f}"
    return f"{simbolo(moneda)} {texto}".strip() if con_simbolo else texto
