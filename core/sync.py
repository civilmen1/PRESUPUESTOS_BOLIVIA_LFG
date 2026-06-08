"""Sincronizacion del banco de APU entre la NUBE (Render) y el LOCAL.

Modelo elegido: la NUBE manda.
  - La nube publica el banco en  ./static/banco_<token>.json , servido por
    Streamlit (enableStaticServing) en  /app/static/banco_<token>.json .
  - El local lo descarga al abrir (y con un boton) y lo FUSIONA con el suyo,
    de modo que ve todo lo aportado en la nube sin perder lo local.

El token (APU_SYNC_TOKEN) hace el enlace dificil de adivinar. Todo es opcional
y a prueba de fallos: si no hay red o configuracion, la app local sigue con su
banco actual sin romperse.
"""
from __future__ import annotations

from typing import Optional

from config import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


def _archivo_publicado():
    return settings.STATIC_DIR / f"banco_{settings.SYNC_TOKEN}.json"


def publicar() -> bool:
    """En la NUBE: copia el banco persistente a ./static para que el local lo
    descargue. No hace nada si no esta configurado para publicar."""
    if not settings.SYNC_PUBLISH or not settings.SYNC_TOKEN:
        return False
    try:
        from core import banco_apu
        ruta = banco_apu.ruta_persistente()
        if not ruta.exists():
            return False
        settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
        _archivo_publicado().write_text(ruta.read_text(encoding="utf-8"),
                                        encoding="utf-8")
        return True
    except Exception:
        logger.exception("No se pudo publicar el banco para sincronizacion")
        return False


def sincronizar_desde_nube(fusionar: bool = True) -> Optional[dict]:
    """En el LOCAL: descarga el banco de la nube y lo incorpora.

    Devuelve {antes, despues, nuevos} o None si no hay URL / fallo de red.
    """
    if not settings.SYNC_URL:
        return None
    try:
        import requests
        from core import banco_apu
        antes = len(banco_apu.listar_apus())
        r = requests.get(settings.SYNC_URL, timeout=20)
        r.raise_for_status()
        despues = banco_apu.cargar_desde_json(r.text, fusionar=fusionar)
        return {"antes": antes, "despues": despues,
                "nuevos": max(0, despues - antes)}
    except Exception as exc:
        logger.warning("Sincronizacion desde la nube fallida: %s", exc)
        return None


def estado() -> dict:
    """Resumen de la configuracion de sincronizacion (para la UI)."""
    return {
        "publica": bool(settings.SYNC_PUBLISH and settings.SYNC_TOKEN),
        "url_local": settings.SYNC_URL,
        "auto": settings.SYNC_AL_ABRIR,
    }
