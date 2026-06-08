# =============================================================================
#  APU Bolivia Generator — construir y arrancar la imagen Docker (Windows)
#
#  Requisito: tener Docker Desktop instalado y CORRIENDO.
#  (Si no lo tienes, primero ejecuta scripts\instalar_docker_D.ps1)
#
#  Uso (PowerShell, desde la carpeta del proyecto):
#     powershell -ExecutionPolicy Bypass -File scripts\docker_build_run.ps1
#
#  Resultado: la app queda en  http://localhost:8501
#  Los datos se guardan en  D:\APU_Bolivia\docker_data  (persistente).
# =============================================================================

$ErrorActionPreference = "Stop"

$Imagen   = "apu-bolivia:latest"
$Contenedor = "apu_bolivia"
$DatosDir = "D:\APU_Bolivia\docker_data"
$ProyectoDir = (Get-Location).Path

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " APU Bolivia - Construir imagen Docker" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# --- 0) Verificar que Docker esta instalado y corriendo ---
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "ERROR: Docker no esta instalado o no esta en el PATH." -ForegroundColor Red
    Write-Host "Ejecuta primero: scripts\instalar_docker_D.ps1" -ForegroundColor Yellow
    exit 1
}
try {
    docker info *> $null
} catch {
    Write-Host "ERROR: Docker esta instalado pero el motor no esta corriendo." -ForegroundColor Red
    Write-Host "Abre 'Docker Desktop' y espera a que diga 'Engine running', luego reintenta." -ForegroundColor Yellow
    exit 1
}
Write-Host "Docker detectado y corriendo. OK" -ForegroundColor Green

# --- 1) Verificar que estamos en la carpeta del proyecto ---
if (-not (Test-Path "$ProyectoDir\Dockerfile")) {
    Write-Host "ERROR: no se encuentra el Dockerfile aqui ($ProyectoDir)." -ForegroundColor Red
    Write-Host "Ejecuta este script DESDE la carpeta del proyecto (donde esta app.py)." -ForegroundColor Yellow
    exit 1
}

# --- 2) Crear carpeta de datos persistente en D: ---
New-Item -ItemType Directory -Force -Path $DatosDir | Out-Null
Write-Host "Datos persistentes en: $DatosDir" -ForegroundColor Green

# --- 3) Construir la imagen ---
Write-Host "`n[1/3] Construyendo la imagen '$Imagen' (5-10 min la primera vez)..." -ForegroundColor Green
docker build -t $Imagen $ProyectoDir

# --- 4) Detener/eliminar un contenedor anterior si existe ---
Write-Host "`n[2/3] Limpiando contenedor anterior (si existe)..." -ForegroundColor Green
docker rm -f $Contenedor 2>$null | Out-Null

# --- 5) Arrancar el contenedor ---
Write-Host "`n[3/3] Arrancando la aplicacion..." -ForegroundColor Green
docker run -d `
    --name $Contenedor `
    --restart unless-stopped `
    -p 8501:8501 `
    -v "${DatosDir}:/data" `
    -e APU_DB_PATH=/data/proveedores.db `
    -e APU_EXPORT_DIR=/data/exports `
    -e APU_UPLOAD_DIR=/data/uploads `
    -e APU_LOG_DIR=/data/logs `
    -e AUTH_SALT=cambia-esto-por-un-secreto `
    $Imagen | Out-Null

Start-Sleep -Seconds 5
Write-Host "`n==============================================" -ForegroundColor Cyan
Write-Host " Listo. La aplicacion esta corriendo." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Abre en tu navegador:  http://localhost:8501" -ForegroundColor Yellow
Write-Host ""
Write-Host "Comandos utiles:" -ForegroundColor DarkGray
Write-Host "  docker logs -f $Contenedor      # ver registros en vivo"
Write-Host "  docker stop $Contenedor         # detener"
Write-Host "  docker start $Contenedor        # volver a arrancar"
Write-Host "  docker rm -f $Contenedor        # eliminar el contenedor"
