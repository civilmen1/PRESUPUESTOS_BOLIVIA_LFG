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

# --------------------------------------------------------------------------- #
# Estructura de APU boliviana (NB-SABS / DS 0181) — Formulario B-2
# Porcentajes editables. Aplicación estándar en licitaciones de obra:
#   MANO DE OBRA:  + beneficios sociales (% sobre MO) + IVA s/MO
#   EQUIPO/HERR.:  herramientas menores (% sobre MO)
#   COSTO DIRECTO = Materiales + Mano de obra + Equipo/Herramientas
#   GASTOS GENERALES (% sobre costo directo)
#   UTILIDAD (% sobre costo directo + GG)
#   IMPUESTOS IT (% sobre subtotal anterior)
# --------------------------------------------------------------------------- #
# Beneficios sociales sobre la mano de obra (rango usual 55%–71.18%).
FACTOR_BENEFICIOS_SOCIALES = float(os.getenv("APU_BENEFICIOS_SOCIALES", "0.55"))
# IVA aplicado a la mano de obra (alícuota efectiva 14.94%).
FACTOR_IVA_MANO_OBRA = float(os.getenv("APU_IVA_MANO_OBRA", "0.1494"))
# Herramientas menores como % de la mano de obra (usual 5%).
FACTOR_HERRAMIENTAS = float(os.getenv("APU_HERRAMIENTAS", "0.05"))
# Cargas sociales/IVA sobre el equipo (normalmente 0; configurable).
FACTOR_IVA_EQUIPO = float(os.getenv("APU_IVA_EQUIPO", "0.0"))
# Gastos generales (% sobre costo directo; usual 8%–12%).
FACTOR_GASTOS_GENERALES = float(os.getenv("APU_GASTOS_GENERALES", "0.10"))
# Utilidad (% sobre costo directo + gastos generales; usual 7%–10%).
FACTOR_UTILIDAD_SABS = float(os.getenv("APU_UTILIDAD_SABS", "0.10"))
# Impuesto a las Transacciones IT (3.09% efectivo según DS 0181).
FACTOR_IT = float(os.getenv("APU_IT", "0.0309"))

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

# --------------------------------------------------------------------------- #
# Extracción con IA / LLM (opcional, multi-modelo). Si no hay key, modo offline.
#   1. Extracción estructurada → GPT-4o (OpenAI)
#   2. Interpretación normativa → Claude Sonnet (Anthropic)
#   3. Análisis de planos/PDF   → Gemini (Google, multimodal)
# --------------------------------------------------------------------------- #
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-pro-exp")
# LLM LOCAL GRATIS (Ollama): corre modelos en tu PC, sin tokens ni internet.
# Instala Ollama (https://ollama.com) y un modelo: `ollama pull llama3.1`
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# Modelo liviano por defecto, apto para PCs con 8 GB de RAM.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
USAR_OLLAMA = os.getenv("USAR_OLLAMA", "false").lower() in {"1", "true", "yes"}
# Activa el uso de LLM en la extracción (requiere al menos una API key).
USAR_LLM = os.getenv("USAR_LLM", "false").lower() in {"1", "true", "yes"}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
APP_NAME = "APU Bolivia Generator"
APP_VERSION = "0.1.0"
