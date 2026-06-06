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
# Carpetas de trabajo configurables (en la nube conviene apuntarlas al disco
# persistente, p.ej. /data/exports, para no depender de permisos en /app).
EXPORT_DIR = Path(os.getenv("APU_EXPORT_DIR", BASE_DIR / "exports"))
UPLOAD_DIR = Path(os.getenv("APU_UPLOAD_DIR", BASE_DIR / "uploads"))
LOG_DIR = Path(os.getenv("APU_LOG_DIR", BASE_DIR / "logs"))

for _d in (DATA_DIR, EXPORT_DIR, UPLOAD_DIR, LOG_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # en entornos read-only la carpeta ya debe existir (volumen)

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
# Modelo Gemini del nivel GRATUITO (Flash). Pro es de pago desde 2026.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Limites de tiempo para que una llamada lenta NO estanque la vinculacion:
#   timeout por intento (s) y numero maximo de reintentos ante 429.
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "30"))
GEMINI_MAX_REINTENTOS = int(os.getenv("GEMINI_MAX_REINTENTOS", "2"))
# Vinculacion por lotes: ítems procesados por tanda (cada tanda se guarda y la
# UI se refresca, evitando un bucle gigante que se corte y reinicie todo).
VINCULACION_LOTE = int(os.getenv("VINCULACION_LOTE", "8"))
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

# --------------------------------------------------------------------------- #
# Google Analytics (GA4). Opcional: configura tu ID de medicion (G-XXXXXXXXXX)
# en el panel de Render como variable de entorno GA_MEASUREMENT_ID.
# Si esta vacio, no se carga nada.
# --------------------------------------------------------------------------- #
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "").strip()

# --------------------------------------------------------------------------- #
# Autenticación / login de empresas y entidades
# --------------------------------------------------------------------------- #
# Sal global para el hash de contraseñas (cámbiala en producción).
AUTH_SALT = os.getenv("AUTH_SALT", "apu-bolivia-salt-cambiar-en-produccion")
# Verificación de NIT (Bolivia) vía API externa. Si no hay token, se omite.
VERIFIK_TOKEN = os.getenv("VERIFIK_TOKEN", "")
VERIFIK_URL = os.getenv("VERIFIK_URL", "https://api.verifik.co/v2/bo/nit/{nit}")
# Verificación de SEPREC (Registro de Comercio).
# API oficial de consulta de estado de habilitación (descubierta del portal).
SEPREC_API_BASE = os.getenv(
    "SEPREC_API_BASE",
    "https://servicios.seprec.gob.bo/api/empresas/consultarEstadoHabilitacion")
# Alternativa: URL con plantilla {seprec} si la API cambia de forma.
SEPREC_API_URL = os.getenv("SEPREC_API_URL", "")
SEPREC_API_TOKEN = os.getenv("SEPREC_API_TOKEN", "")
# Respaldo: consultar el portal con navegador (Playwright) si la API falla.
SEPREC_USAR_NAVEGADOR = os.getenv("SEPREC_USAR_NAVEGADOR", "false").lower() in {
    "1", "true", "yes"}
# Verificación de correo: por defecto ENVÍA correos reales por SMTP (Google).
# Para que funcione hay que configurar SMTP_USER/SMTP_PASSWORD (Gmail con
# contraseña de aplicación). Si se pone en true, se simula (solo para desarrollo).
AUTH_EMAIL_DRY_RUN = os.getenv("AUTH_EMAIL_DRY_RUN", "false").lower() in {
    "1", "true", "yes"}
