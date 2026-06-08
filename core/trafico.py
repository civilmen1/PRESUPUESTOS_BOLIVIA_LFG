"""Registro de trafico propio (sin terceros) para las paginas del programa.

Guarda un conteo de visitas por pagina y por dia en data/trafico.json. Lo usa la
pagina publica de aportes (?aportar=1) para contar visitas, y el panel del Banco
de APU para mostrar el trafico al contratista. Privado: los datos viven en el
disco persistente de Render, no se envia nada a servicios externos.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from config import settings

_RUTA = settings.PERSIST_DIR / "trafico.json"


def _leer() -> dict:
    try:
        if _RUTA.exists():
            return json.loads(_RUTA.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _guardar(datos: dict) -> None:
    try:
        _RUTA.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    except Exception:
        pass


def registrar_visita(pagina: str = "aportar") -> None:
    """Suma 1 visita a la pagina para el dia de hoy."""
    datos = _leer()
    pag = datos.setdefault(pagina, {})
    hoy = date.today().isoformat()
    pag[hoy] = int(pag.get(hoy, 0)) + 1
    _guardar(datos)


def resumen(pagina: str = "aportar", dias: int = 30) -> dict:
    """Devuelve {total, hoy, ultimos_dias:[(fecha, n)...]} de una pagina."""
    pag = _leer().get(pagina, {})
    total = sum(int(v) for v in pag.values())
    hoy = date.today().isoformat()
    serie = []
    for i in range(dias - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        serie.append((d, int(pag.get(d, 0))))
    return {"total": total, "hoy": int(pag.get(hoy, 0)),
            "ultimos_dias": serie}


def listar_aportes() -> list[dict]:
    """Aportes registrados en la pagina publica (nombre, correo, archivo, fecha)."""
    ruta = settings.PERSIST_DIR / "aportes_banco.json"
    try:
        if ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8")).get("aportes", [])
    except Exception:
        pass
    return []
