# 🏗️ APU Bolivia Generator

Sistema profesional para **generar Análisis de Precios Unitarios (APU)** en
ingeniería civil de **Bolivia**, a partir de una **tabla de cantidades** y de
**documentos técnicos** (DBC, especificaciones técnicas, TDR, pliegos), con un
**cotizador jerárquico** que prioriza proveedores bolivianos.

> **Prioridad de cotización (estricta):**
> **1) Base de Datos Bolivia → 2) Búsqueda Web → 3) Solicitud por Email**,
> invitando además a cada proveedor a integrar *la base de precios de materiales
> más grande de Bolivia*.

---

## 1. Visión general

El sistema permite:

1. Leer una tabla de cantidades (CSV/XLSX/XLS o ingreso manual).
2. Cargar documentos técnicos (PDF/DOCX/DOC/TXT), extraer, limpiar y segmentar.
3. Vincular cada ítem con sus exigencias técnicas (matcher semántico con score).
4. Construir un APU preliminar por ítem (materiales, mano de obra, equipos).
5. Cotizar cada recurso con la **jerarquía BD → Web → Email**.
6. Calcular precio unitario final con indirectos, utilidad e impuestos.
7. Generar trazabilidad técnica y de cotización.
8. Permitir revisión/edición manual del ingeniero.
9. Exportar a **Excel, PDF y JSON**.

## 2. Arquitectura

Aplicación **Python + Streamlit** con separación por capas y persistencia en
**SQLite** (preparada para PostgreSQL):

```
config/      → settings, logging
core/        → parsers, limpieza, segmentación, matcher, motor APU,
               cotizador jerárquico, reglas, conversión de unidades, DB, repos
providers/   → repositorio/serv. de proveedores, scraping web, búsqueda online,
               clasificador, email
models/      → entidades (dataclasses)
exporters/   → Excel, PDF, JSON
ui/          → páginas Streamlit
scripts/     → init_db, seed_data
tests/       → pruebas (pytest)
data/        → JSON base (rendimientos, salarios, equipos, categorías) + BD
```

## 3. Árbol de carpetas

```
.
├── app.py                      # App Streamlit principal
├── requirements.txt
├── .env.example
├── config/
│   ├── settings.py
│   └── logging_config.py
├── data/
│   ├── rendimientos.json       # plantillas de APU por tipo de ítem
│   ├── salarios_bolivia.json   # mano de obra (BD local Nivel 1)
│   ├── equipos_costos.json     # equipos (BD local Nivel 1)
│   ├── categorias_materiales.json
│   └── ejemplo_tabla_cantidades.csv
├── core/
│   ├── database.py  repositories.py  data_loader.py
│   ├── parser_tabla.py  parser_documento.py  text_cleaner.py  segmentador.py
│   ├── semantic_matcher.py  apu_engine.py  pricing_engine.py
│   ├── unit_converter.py  validation_engine.py  rules_engine.py
├── providers/
│   ├── supplier_repository.py  supplier_service.py  supplier_classifier.py
│   ├── web_scraper.py  search_online.py  email_service.py
├── models/
│   ├── project.py item.py supplier.py technical_source.py
│   ├── quotation.py apu_resource.py apu_result.py
├── exporters/
│   ├── export_excel.py  export_pdf.py  export_json.py
├── ui/
│   ├── dashboard.py items_page.py documents_page.py linking_page.py
│   ├── apu_page.py quotations_page.py suppliers_page.py export_page.py
│   └── components.py
├── scripts/
│   ├── init_db.py  seed_data.py
└── tests/
    ├── test_parser_tabla.py  test_parser_documento.py
    ├── test_pricing_engine.py  test_semantic_matcher.py
```

## 4. Modelo de datos

Entidades principales (tablas SQLite): `proyectos`, `modulos`, `items`,
`fuentes_tecnicas`, `secciones_tecnicas`, `vinculos_tecnicos`, `proveedores`,
`precios_referencia`, `cotizaciones`, `recursos_apu`, `resultados_apu`,
`contactos_email`. El esquema completo está en `core/database.py`.

## 5. Flujo del cotizador Bolivia

Para **cada recurso** de cada APU (`core/pricing_engine.py`):

| Nivel | Fuente | Acción |
|------|--------|--------|
| **0** | Manual validado | Prioridad máxima si el ingeniero lo marca. |
| **1** | **BD Bolivia** | Busca en `precios_referencia` (materiales) o en `salarios/equipos JSON` (MO/equipos). Si está vigente, se usa. |
| **2** | **Web** | Solo si no hay BD. Homologa unidades y guarda como referencia provisional. |
| **3** | **Email** | Solo si no hay BD ni web. Detecta proveedores por categoría/región y envía solicitud + invitación a la base nacional. |

**Reglas de precio adoptado** (`core/rules_engine.py`): 1 fuente → con
advertencia; 2-3 → mediana; 4+ → mediana depurada (IQR); email > web; manual
validado = máxima; precios > 30 días → alerta de vigencia.

> **Modo seguro por defecto:** `SCRAPER_DRY_RUN=true` y `EMAIL_DRY_RUN=true`
> permiten ejecutar todo localmente **sin internet ni envío real de correos**
> (datos simulados deterministas). Desactívalos en `.env` para usar red/SMTP.

## 6. Instalación y ejecución (Windows / Linux / macOS)

```bash
# 1) Crear y activar entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2) Instalar dependencias
pip install -r requirements.txt

# 3) Configurar variables de entorno
copy .env.example .env        # Windows  (Linux/macOS: cp .env.example .env)

# 4) Inicializar la base de datos
python -m scripts.init_db

# 5) (Opcional) Cargar datos demo (proveedores, precios, proyecto y APUs)
python -m scripts.seed_data

# 6) Ejecutar la aplicación
streamlit run app.py
```

Abre el navegador en `http://localhost:8501`.

### Pruebas

```bash
pytest -q
```

## 7. Uso paso a paso

1. **Sidebar →** crea o selecciona un proyecto.
2. **Ítems →** importa `data/ejemplo_tabla_cantidades.csv` o ingresa ítems.
3. **Documentos técnicos →** sube DBC/especificaciones/TDR.
4. **Vinculación técnica →** ejecuta la vinculación y valida los vínculos.
5. **APUs →** genera APUs (elige si habilitar Web/Email) y edita recursos.
6. **Cotizaciones / Proveedores →** revisa fuentes y gestiona proveedores.
7. **Exportación →** descarga Excel, PDF o JSON.

## 8. Despliegue (futuro)

- **Local productivo:** `streamlit run app.py` tras configurar `.env`.
- **Servidor:** contenedor Docker + Streamlit; migrar `DATABASE_URL` a
  PostgreSQL (el SQL del esquema es estándar).
- **Backend desacoplado:** la lógica de `core/` y `providers/` es independiente
  de la UI y puede exponerse con **FastAPI**.

## 8.b Lectura de documentos con OCR e IA (opcional)

**OCR para DBCs escaneados** (`core/parser_documento.py`): si un PDF es una
imagen (escaneo) o subes un PNG/JPG/TIFF, el sistema aplica **OCR con
Tesseract** automáticamente. Requiere instalar los binarios del sistema:

- Windows: Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) + Poppler.
- Paquete de idioma español (`spa`) recomendado.
- Sin Tesseract instalado, el OCR se omite sin romper la app.

**Extracción con IA / LLM** (`core/llm_extractor.py`, opcional): se activa con
`USAR_LLM=true`; si no hay proveedor, usa el extractor offline por reglas.

### 🆓 LLM LOCAL GRATIS con Ollama (recomendado — sin tokens ni internet)

1. Instala **Ollama**: https://ollama.com
2. Descarga un modelo (una vez):
   ```bash
   ollama pull llama3.1        # o qwen2.5, mistral, gemma2, etc.
   ```
3. En `.env`:
   ```env
   USAR_LLM=true
   USAR_OLLAMA=true
   OLLAMA_MODEL=llama3.1
   ```
El modelo corre **en tu PC**, gratis y offline. No requiere instalar SDKs
adicionales (usa la API HTTP de Ollama con `requests`).

### LLMs de pago (opcionales) — arquitectura multi-modelo

| Rol | Modelo | Tarea |
|-----|--------|-------|
| 1. Extracción estructurada | **GPT-4o** / Ollama | partidas, cantidades, recursos |
| 2. Interpretación normativa | **Claude Sonnet** / Ollama | NB-DS 2023, NB 1225001 |
| 3. Análisis de planos/PDF | **Gemini** | multimodal + contexto largo |

Configura en `.env`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
e instala los SDKs (descomenta en `requirements.txt`). El orden de preferencia
para extracción es: **Ollama local → GPT-4o**; para normativa: **Claude →
Ollama local**. Si nada está disponible, cae al extractor offline.

## 9. Notas sobre componentes mock / sustituibles

- `providers/web_scraper.py` → genera precios **simulados** en `SCRAPER_DRY_RUN`.
  Reemplaza `_simular` / añade parsers por sitio para scraping real.
- `providers/email_service.py` → en `EMAIL_DRY_RUN` registra contactos sin
  enviar. Configura SMTP/SendGrid en `.env` para envío real.
- `core/semantic_matcher.py` → TF-IDF + coseno (offline). El extractor de
  información (`core/info_extractor.py`) usa reglas; con `USAR_LLM=true` se
  sustituye por la extracción multi-LLM sin cambiar la interfaz.
- `data/*.json` → rendimientos, salarios y equipos son **referenciales**;
  ajústalos a tus bases reales.

## 10. Mejoras futuras

- Embeddings semánticos y OCR para PDF escaneados.
- Scrapers reales por proveedor + caché de precios.
- Bandeja de respuestas de email e ingreso de cotizaciones recibidas.
- Multi-usuario, roles y autenticación.
- Migración a PostgreSQL + API FastAPI + despliegue Docker.
- Versionado de APUs y comparación de presupuestos.

---

*Hecho para ingeniería civil en Bolivia 🇧🇴 — prioriza proveedores nacionales y
construye la base de precios de materiales más grande del país.*
