"""Prueba manual de la API del SEPREC para ver la respuesta real.

Uso (en tu PC o en la nube, donde haya acceso a internet):
    python -m scripts.probar_seprec 5042325017
    python -m scripts.probar_seprec <matricula_real>

Muestra la URL probada, el codigo HTTP y el JSON devuelto, para confirmar
como interpretar el resultado.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

BASE = "https://servicios.seprec.gob.bo/api/empresas/consultarEstadoHabilitacion"


def main() -> None:
    matricula = sys.argv[1] if len(sys.argv) > 1 else "5042325017"
    headers = {"Accept": "application/json", "User-Agent": "APUBolivia/1.0"}
    intentos = [
        (f"{BASE}/{matricula}", None),
        (BASE, {"matricula": matricula}),
        (BASE, {"nroMatricula": matricula}),
    ]
    for url, params in intentos:
        print("=" * 60)
        print("URL:", url, "| params:", params)
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            print("HTTP:", r.status_code)
            try:
                print("JSON:", json.dumps(r.json(), indent=2, ensure_ascii=False)[:2000])
            except Exception:
                print("TEXTO:", r.text[:1000])
        except Exception as exc:
            print("ERROR:", exc)


if __name__ == "__main__":
    main()
