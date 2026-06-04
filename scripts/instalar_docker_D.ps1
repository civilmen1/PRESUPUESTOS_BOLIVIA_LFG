# =============================================================================
#  Instalar Docker Desktop en Windows (datos en disco D:)
#
#  Que hace:
#   1. Descarga el instalador oficial de Docker Desktop.
#   2. Lo instala.
#   3. Te indica como mover los datos de Docker (imagenes) al disco D:.
#
#  Uso (PowerShell COMO ADMINISTRADOR, desde la carpeta del proyecto):
#     powershell -ExecutionPolicy Bypass -File scripts\instalar_docker_D.ps1
#
#  NOTA: Docker Desktop requiere WSL2 (lo instala solo si falta) y reiniciar
#  el equipo la primera vez. Necesita Windows 10/11 64-bit.
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host " Instalacion de Docker Desktop (datos en D:)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# --- 0) Verificar si ya esta instalado ---
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Docker ya esta instalado. Version:" -ForegroundColor Green
    docker --version
    Write-Host "Si quieres mover los datos a D:, sigue el PASO D mas abajo." -ForegroundColor Yellow
}

# --- 1) Asegurar WSL2 ---
Write-Host "`n[1/3] Verificando WSL2 (motor de Docker)..." -ForegroundColor Green
try {
    wsl --status *> $null
    Write-Host "WSL disponible." -ForegroundColor Green
} catch {
    Write-Host "Instalando WSL2 (puede pedir reiniciar el equipo)..." -ForegroundColor Yellow
    wsl --install
    Write-Host "Si te pide reiniciar, REINICIA y vuelve a ejecutar este script." -ForegroundColor Yellow
}

# --- 2) Descargar el instalador de Docker Desktop ---
Write-Host "`n[2/3] Descargando Docker Desktop..." -ForegroundColor Green
$installer = "$env:TEMP\DockerDesktopInstaller.exe"
if (-not (Test-Path $installer)) {
    Invoke-WebRequest -UseBasicParsing `
        -Uri "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" `
        -OutFile $installer
}

# --- 3) Instalar ---
Write-Host "`n[3/3] Instalando Docker Desktop (acepta los permisos de admin)..." -ForegroundColor Green
Start-Process -FilePath $installer -ArgumentList "install","--quiet","--accept-license" -Wait
Remove-Item $installer -ErrorAction SilentlyContinue

Write-Host "`n==============================================" -ForegroundColor Cyan
Write-Host " Docker Desktop instalado." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PASOS SIGUIENTES (importante):" -ForegroundColor Yellow
Write-Host "  1. REINICIA el equipo si te lo pide." -ForegroundColor Yellow
Write-Host "  2. Abre 'Docker Desktop' y espera a que diga 'Engine running'." -ForegroundColor Yellow
Write-Host ""
Write-Host "PASO D - Mover los datos de Docker al disco D: (para no llenar C:):" -ForegroundColor Cyan
Write-Host "  a. Abre Docker Desktop -> Settings (engranaje)." -ForegroundColor White
Write-Host "  b. Resources -> Advanced -> 'Disk image location'." -ForegroundColor White
Write-Host "  c. Cambia la ruta a:  D:\APU_Bolivia\docker_disk" -ForegroundColor White
Write-Host "  d. Apply & Restart." -ForegroundColor White
Write-Host ""
Write-Host "Cuando Docker diga 'Engine running', ejecuta:" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\docker_build_run.ps1" -ForegroundColor White
