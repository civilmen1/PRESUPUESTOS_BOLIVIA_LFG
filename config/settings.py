"""Configuración central del sistema APU Bolivia Generator.

Carga variables de entorno (.env si está disponible) y expone constantes y
rutas usadas por el resto de la aplicación.
"""
from __future__ import annotations

import os
from pathlib import Path

try:  # carga opcional de .env
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv es opcional
    pass


# --------------------------------------------------------------------------- #
# Rutas base
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
UPLOAD_DIR = BASE_DIR / "uploads"
LOG_DIR = BASE_DIR / "logs"

for _d in (DATA_DIR, EXPORT_DIR, UPLOAD_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Base de datos (SQLite local por defecto; preparado para PostgreSQL futuro)
DB_PATH = Path(os.getenv("APU_DB_PATH", DATA_DIR / "proveedores.db"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Archivos de datos base
RENDIMIENTOS_JSON = DATA_DIR / "rendimientos.json"
SALARIOS_JSON = DATA_DIR / "salarios_bolivia.json"
EQUIPOS_JSON = DATA_DIR / "equipos_costos.json"
CATEGORIAS_JSON = DATA_DIR / "categorias_materiales.json"


# --------------------------------------------------------------------------- #
# Parámetros de negocio (Bolivia)
# --------------------------------------------------------------------------- #
MONEDA_DEFAULT = os.getenv("APU_MONEDA", "BOB")
TIPO_CAMBIO_USD = float(os.getenv("APU_TIPO_CAMBIO_USD", "6.96"))  # BOB por 1 USD

FACTOR_INDIRECTOS_DEFAULT = float(os.getenv("APU_FACTOR_INDIRECTOS", "0.10"))
FACTOR_UTILIDAD_DEFAULT = float(os.getenv("APU_FACTOR_UTILIDAD", "0.10"))
FACTOR_IMPUESTOS_DEFAULT = float(os.getenv("APU_FACTOR_IMPUESTOS", "0.0"))

# Vigencia de precios
VIGENCIA_DIAS_DEFAULT = int(os.getenv("APU_VIGENCIA_DIAS", "30"))

DEPARTAMENTOS_BOLIVIA = [
    "La Paz",
    "Santa Cruz",
    "Cochabamba",
    "Oruro",
    "Potosí",
    "Tarija",
    "Chuquisaca",
    "Beni",
    "Pando",
]

# --------------------------------------------------------------------------- #
# Configuración de email (módulo de cotización Nivel 3)
# --------------------------------------------------------------------------- #
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@apubolivia.local")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "APU Bolivia Generator")
# Si está activo, no se envían correos reales: se registran en log/BD (modo seguro).
EMAIL_DRY_RUN = os.getenv("EMAIL_DRY_RUN", "true").lower() in {"1", "true", "yes"}
EMAIL_RECORDATORIO_DIAS = int(os.getenv("EMAIL_RECORDATORIO_DIAS", "5"))

# --------------------------------------------------------------------------- #
# Configuración de scraping web (Nivel 2)
# --------------------------------------------------------------------------- #
# Si está activo, el scraper no sale a internet y devuelve datos simulados.
SCRAPER_DRY_RUN = os.getenv("SCRAPER_DRY_RUN", "true").lower() in {"1", "true", "yes"}
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "10"))
SCRAPER_USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "APUBoliviaBot/1.0 (+https://apubolivia.local; cotizaciones)",
)

# Enlace público de registro de proveedores (se incluye en los correos)
REGISTRO_PROVEEDOR_URL = os.getenv(
    "REGISTRO_PROVEEDOR_URL", "https://apubolivia.local/registro-proveedor"
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
APP_NAME = "APU Bolivia Generator"
APP_VERSION = "0.1.0"
