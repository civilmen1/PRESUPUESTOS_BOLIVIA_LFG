# =============================================================================
#  APU Bolivia Generator — Instalacion COMPLETA en la unidad D: (8 GB de RAM)
#
#  Que hace este script (TODO queda en D:, el disco C no se llena):
#   1. Crea las carpetas de trabajo en D:\APU_Bolivia.
#   2. Instala PYTHON en D:\APU_Bolivia\Python y crea el entorno virtual en D:.
#   3. Instala las dependencias del proyecto.
#   4. Instala OLLAMA (el ejecutable) en D:\APU_Bolivia\Ollama.
#   5. Configura Ollama para guardar los modelos en D: (OLLAMA_MODELS).
#   6. Descarga un modelo LLM liviano (qwen2.5:3b) apto para 8 GB de RAM.
#   7. Crea el archivo .env con el LLM local activado.
#
#  Como ejecutar (PowerShell, desde la carpeta del proyecto):
#     powershell -ExecutionPolicy Bypass -File scripts\setup_windows_D.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

# --- Parametros (puedes cambiar la unidad/carpeta) ---
$Unidad      = "D:"
$BaseDir     = "$Unidad\APU_Bolivia"
$PythonDir   = "$BaseDir\Python"          # Python instalado en D:
$PyVersion   = "3.11.9"                    # version de Python a instalar en D:
$VenvDir     = "$BaseDir\venv"
$OllamaDir   = "$BaseDir\Ollama"          # ejecutable de Ollama en D:
$ModelosDir  = "$BaseDir\ollama_models"   # modelos de Ollama en D:
$ModeloLLM   = "qwen2.5:3b"               # liviano para 8 GB RAM
$ProyectoDir = (Get-Location).Path        # carpeta actual del proyecto

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
Write-Host "`n[1/7] Creando carpetas en $BaseDir ..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $BaseDir, $ModelosDir, $OllamaDir, $PythonDir | Out-Null

# --- 2) Python en D: (instala una copia en D: si no hay una ya) ---
Write-Host "`n[2/7] Preparando Python en $PythonDir ..." -ForegroundColor Green
$pyExe = "$PythonDir\python.exe"
if (-not (Test-Path $pyExe)) {
    Write-Host "  Descargando instalador de Python $PyVersion ..." -ForegroundColor DarkGray
    $pyInstaller = "$env:TEMP\python-$PyVersion-amd64.exe"
    try {
        Invoke-WebRequest -UseBasicParsing -OutFile $pyInstaller `
            -Uri "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-amd64.exe"
        # Instalacion silenciosa SOLO en D: (no toca el disco C, sin admin)
        Write-Host "  Instalando Python en $PythonDir (silencioso)..." -ForegroundColor DarkGray
        Start-Process -FilePath $pyInstaller -Wait -ArgumentList `
            "/quiet","InstallAllUsers=0","TargetDir=$PythonDir","Include_pip=1",`
            "Include_test=0","Include_launcher=0","Shortcuts=0","AssociateFiles=0"
        Remove-Item $pyInstaller -ErrorAction SilentlyContinue
    } catch {
        Write-Host "  No se pudo instalar Python en D: automaticamente: $_" -ForegroundColor Yellow
    }
}
# Si quedo Python en D:, se usa ese; si no, se intenta el del sistema (PATH).
if (Test-Path $pyExe) {
    $pythonCmd = $pyExe
} else {
    $sys = Get-Command python -ErrorAction SilentlyContinue
    if (-not $sys) {
        Write-Host "ERROR: no hay Python en D: ni en el PATH del sistema." -ForegroundColor Red
        Write-Host "Instala Python 3.11+ desde https://www.python.org y reintenta." -ForegroundColor Yellow
        exit 1
    }
    $pythonCmd = $sys.Source
    Write-Host "  Usando Python del sistema: $pythonCmd" -ForegroundColor DarkGray
}

# Crear el entorno virtual en D: con el Python elegido
Write-Host "  Creando entorno virtual en $VenvDir ..." -ForegroundColor DarkGray
if (-not (Test-Path $VenvDir)) {
    & $pythonCmd -m venv $VenvDir
}
$pip = "$VenvDir\Scripts\pip.exe"

# --- 3) Instalar dependencias ---
Write-Host "`n[3/7] Instalando dependencias (puede tardar varios minutos) ..." -ForegroundColor Green
& $pip install --upgrade pip --quiet
& $pip install -r "$ProyectoDir\requirements.txt"

# --- 4) Instalar Ollama (ejecutable) en D: ---
Write-Host "`n[4/7] Instalando Ollama en $OllamaDir ..." -ForegroundColor Green
$ollamaExe = "$OllamaDir\ollama.exe"
if (Test-Path $ollamaExe) {
    Write-Host "  Ollama ya esta instalado en D:; se omite la instalacion." -ForegroundColor DarkGray
} else {
    $installer = "$env:TEMP\OllamaSetup.exe"
    Write-Host "  Descargando instalador de Ollama (~700 MB)..." -ForegroundColor DarkGray
    try {
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" `
            -OutFile $installer -UseBasicParsing
        # Instalacion DESATENDIDA con directorio destino en D: (flag /DIR de NSIS)
        Write-Host "  Instalando en $OllamaDir (silencioso)..." -ForegroundColor DarkGray
        Start-Process -FilePath $installer -ArgumentList "/VERYSILENT","/DIR=$OllamaDir" -Wait
        Remove-Item $installer -ErrorAction SilentlyContinue
    } catch {
        Write-Host "  No se pudo instalar Ollama automaticamente: $_" -ForegroundColor Yellow
        Write-Host "  Instalalo manualmente desde https://ollama.com en $OllamaDir" -ForegroundColor Yellow
    }
}

# --- 5) Configurar Ollama para guardar modelos en D: ---
Write-Host "`n[5/7] Configurando Ollama para usar $ModelosDir ..." -ForegroundColor Green
# Variables PERSISTENTES para el usuario (modelos en D: y ejecutable en PATH)
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ModelosDir, "User")
$env:OLLAMA_MODELS = $ModelosDir   # tambien en la sesion actual
# Agregar el ejecutable de Ollama (en D:) al PATH de la sesion actual
if (Test-Path $ollamaExe) { $env:Path = "$OllamaDir;$env:Path" }

# Resolver el comando ollama (en D: o en PATH global)
$ollamaCmd = if (Test-Path $ollamaExe) { $ollamaExe }
             else { (Get-Command ollama -ErrorAction SilentlyContinue).Source }

if (-not $ollamaCmd) {
    Write-Host "  AVISO: no se encontro el ejecutable de Ollama." -ForegroundColor Yellow
    Write-Host "  Reinicia PowerShell y ejecuta: ollama pull $ModeloLLM" -ForegroundColor Yellow
} else {
    # --- 6) Descargar el modelo liviano (los modelos van a D: por OLLAMA_MODELS) ---
    Write-Host "`n[6/7] Descargando modelo LLM liviano '$ModeloLLM' en D: ..." -ForegroundColor Green
    Write-Host "  (esto descarga ~2 GB la primera vez)" -ForegroundColor DarkGray
    # Arrancar el servidor Ollama si no esta corriendo
    if (-not (Get-Process -Name "ollama" -ErrorAction SilentlyContinue)) {
        Start-Process -FilePath $ollamaCmd -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 5
    }
    & $ollamaCmd pull $ModeloLLM
}

# --- 7) Crear archivo .env con el LLM local activado ---
Write-Host "`n[7/7] Creando archivo .env ..." -ForegroundColor Green
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
Write-Host "Python          : $PythonDir"
Write-Host "Entorno virtual : $VenvDir"
Write-Host "Ollama (exe)    : $OllamaDir"
Write-Host "Modelos Ollama  : $ModelosDir  (variable OLLAMA_MODELS)"
Write-Host "Modelo LLM      : $ModeloLLM"
Write-Host "Datos / BD      : $BaseDir\data"
Write-Host "==> TODO en la unidad $Unidad (el disco C no se llena)." -ForegroundColor Green
Write-Host ""
Write-Host "Para ejecutar la aplicacion:" -ForegroundColor Yellow
Write-Host "   $VenvDir\Scripts\activate"
Write-Host "   python -m scripts.init_db"
Write-Host "   streamlit run app.py"
Write-Host ""
Write-Host "NOTA: reinicia PowerShell antes de usar 'ollama' manualmente, para" -ForegroundColor Yellow
Write-Host "que tome OLLAMA_MODELS y el PATH actualizados." -ForegroundColor Yellow
