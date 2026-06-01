# =============================================================================
#  APU Bolivia Generator — Instalacion en la unidad D: (PCs con 8 GB de RAM)
#
#  Que hace este script:
#   1. Crea las carpetas de trabajo en D:\APU_Bolivia (codigo, venv, datos).
#   2. Crea un entorno virtual de Python en D: (no usa el disco C).
#   3. Instala las dependencias del proyecto.
#   4. Configura Ollama para guardar los modelos en D: (variable OLLAMA_MODELS).
#   5. Descarga un modelo LLM liviano (qwen2.5:3b) apto para 8 GB de RAM.
#   6. Crea el archivo .env con el LLM local activado.
#
#  Como ejecutar (PowerShell, desde la carpeta del proyecto):
#     powershell -ExecutionPolicy Bypass -File scripts\setup_windows_D.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# --- Parametros (puedes cambiar la unidad/carpeta) ---
$Unidad      = "D:"
$BaseDir     = "$Unidad\APU_Bolivia"
$VenvDir     = "$BaseDir\venv"
$ModelosDir  = "$BaseDir\ollama_models"
$ModeloLLM   = "qwen2.5:3b"     # liviano para 8 GB RAM
$ProyectoDir = (Get-Location).Path   # carpeta actual del proyecto

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " APU Bolivia Generator - Instalacion en $Unidad" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# --- 0) Verificar que la unidad D: existe ---
if (-not (Test-Path $Unidad)) {
    Write-Host "ERROR: La unidad $Unidad no existe en este equipo." -ForegroundColor Red
    Write-Host "Edita la variable \$Unidad al inicio del script." -ForegroundColor Yellow
    exit 1
}

# --- 1) Crear carpetas en D: ---
Write-Host "`n[1/6] Creando carpetas en $BaseDir ..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $BaseDir, $ModelosDir | Out-Null

# --- 2) Verificar Python e instalar venv en D: ---
Write-Host "`n[2/6] Creando entorno virtual de Python en $VenvDir ..." -ForegroundColor Green
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python no esta instalado o no esta en el PATH." -ForegroundColor Red
    Write-Host "Instala Python 3.11+ desde https://www.python.org (marca 'Add to PATH')." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
}
$pip = "$VenvDir\Scripts\pip.exe"

# --- 3) Instalar dependencias ---
Write-Host "`n[3/6] Instalando dependencias (puede tardar varios minutos) ..." -ForegroundColor Green
& $pip install --upgrade pip --quiet
& $pip install -r "$ProyectoDir\requirements.txt"

# --- 4) Configurar Ollama para guardar modelos en D: ---
Write-Host "`n[4/6] Configurando Ollama para usar $ModelosDir ..." -ForegroundColor Green
# Variable de entorno PERSISTENTE para el usuario (los modelos iran a D:)
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ModelosDir, "User")
$env:OLLAMA_MODELS = $ModelosDir   # tambien en la sesion actual

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "  AVISO: Ollama no esta instalado todavia." -ForegroundColor Yellow
    Write-Host "  Instalalo desde https://ollama.com y vuelve a ejecutar este script" -ForegroundColor Yellow
    Write-Host "  (o solo el paso de descarga del modelo)." -ForegroundColor Yellow
} else {
    # --- 5) Descargar el modelo liviano ---
    Write-Host "`n[5/6] Descargando modelo LLM liviano '$ModeloLLM' en D: ..." -ForegroundColor Green
    Write-Host "  (esto descarga ~2 GB la primera vez)" -ForegroundColor DarkGray
    ollama pull $ModeloLLM
}

# --- 6) Crear archivo .env con el LLM local activado ---
Write-Host "`n[6/6] Creando archivo .env ..." -ForegroundColor Green
$envPath = "$ProyectoDir\.env"
if (Test-Path $envPath) {
    Write-Host "  Ya existe .env; no se sobrescribe. Revisa que tenga USAR_OLLAMA=true." -ForegroundColor Yellow
} else {
    $envContent = @"
# Configuracion generada por setup_windows_D.ps1
# Base de datos y archivos en la unidad $Unidad
APU_DB_PATH=$BaseDir\data\proveedores.db

# LLM LOCAL GRATIS (Ollama) activado
USAR_LLM=true
USAR_OLLAMA=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=$ModeloLLM

# Modo seguro (sin internet ni correos reales)
SCRAPER_DRY_RUN=true
EMAIL_DRY_RUN=true
LOG_LEVEL=INFO
"@
    Set-Content -Path $envPath -Value $envContent -Encoding UTF8
    Write-Host "  .env creado con la BD y los modelos en $Unidad" -ForegroundColor Green
}

# --- Resumen final ---
Write-Host "`n==============================================" -ForegroundColor Cyan
Write-Host " Instalacion completada." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Entorno virtual : $VenvDir"
Write-Host "Modelos Ollama  : $ModelosDir  (variable OLLAMA_MODELS)"
Write-Host "Modelo LLM      : $ModeloLLM"
Write-Host "Datos / BD      : $BaseDir\data"
Write-Host ""
Write-Host "Para ejecutar la aplicacion:" -ForegroundColor Yellow
Write-Host "   $VenvDir\Scripts\activate"
Write-Host "   python -m scripts.init_db"
Write-Host "   streamlit run app.py"
Write-Host ""
Write-Host "IMPORTANTE: si acabas de instalar Ollama, cierra y reabre PowerShell" -ForegroundColor Yellow
Write-Host "para que tome la variable OLLAMA_MODELS antes de 'ollama pull'." -ForegroundColor Yellow
