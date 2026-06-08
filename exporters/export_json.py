"""Exportación de un proyecto completo a JSON (con trazabilidad)."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from config import settings
from core import repositories


def construir_payload(proyecto_id: int) -> dict:
    """Arma el diccionario completo del proyecto: ítems, recursos, resultados."""
    proyecto = repositories.obtener_proyecto(proyecto_id)
    if not proyecto:
        raise ValueError(f"Proyecto {proyecto_id} no encontrado")

    items_payload = []
    for item in repositories.listar_items(proyecto_id):
        recursos = repositories.listar_recursos(item.id)
        resultado = repositories.obtener_resultado(item.id)
        vinculos = repositories.listar_vinculos(item.id)
        items_payload.append({
            "item": asdict(item),
            "recursos": [asdict(r) for r in recursos],
            "resultado": asdict(resultado) if resultado else None,
            "trazabilidad_tecnica": [
                {"seccion_id": v.seccion_id, "titulo": v.titulo_seccion,
                 "score": v.score_confianza, "validado": v.validado_manual,
                 "extracto": v.extracto} for v in vinculos],
        })

    return {
        "generado": datetime.now().isoformat(),
        "app": f"{settings.APP_NAME} {settings.APP_VERSION}",
        "proyecto": asdict(proyecto),
        "items": items_payload,
        "cotizaciones": repositories.listar_cotizaciones(proyecto_id),
    }


def exportar_json(proyecto_id: int, ruta: str | Path | None = None) -> Path:
    payload = construir_payload(proyecto_id)
    if ruta is None:
        ruta = settings.EXPORT_DIR / f"apu_proyecto_{proyecto_id}.json"
    ruta = Path(ruta)
    ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8")
    return ruta
