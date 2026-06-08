@echo off
REM ===========================================================================
REM  Arranque LOCAL de APU Bolivia con Ollama (IA gratis, sin limites).
REM  Doble clic sobre este archivo o ejecutalo desde la carpeta del proyecto.
REM ===========================================================================
cd /d "%~dp0"

REM Modelo de Ollama (debe coincidir con OLLAMA_MODEL de tu .env).
set "MODELO=qwen2.5:7b"

echo.
echo [1/4] Verificando Ollama...
where ollama >nul 2>nul
if errorlevel 1 (
    echo  ERROR: Ollama no esta instalado. Descargalo de https://ollama.com
    pause
    exit /b 1
)

echo [2/4] Iniciando el servidor de Ollama (si no esta corriendo)...
start "" /b ollama serve >nul 2>nul
timeout /t 3 >nul

echo [3/4] Descargando el modelo %MODELO% (solo la primera vez)...
ollama pull %MODELO%

echo [4/4] Iniciando la aplicacion (se abrira en el navegador)...
python -m streamlit run app.py

pause
