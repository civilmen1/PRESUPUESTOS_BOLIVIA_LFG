@echo off
REM ===========================================================================
REM  Arranque LOCAL de APU Bolivia con Ollama (IA gratis, sin limites).
REM  Doble clic sobre este archivo o ejecutalo desde la carpeta del proyecto.
REM ===========================================================================
cd /d "%~dp0"

REM Modelo de Ollama (debe coincidir con OLLAMA_MODEL de tu .env).
REM  qwen3-coder:30b  -> potente (PC con >=24 GB RAM o GPU >=18 GB)
REM  qwen2.5:7b / qwen2.5:3b  -> alternativas mas livianas
set "MODELO=qwen3-coder:30b"
REM Modelo de embeddings para la busqueda semantica.
set "EMBED=nomic-embed-text"
REM Puerto de la app. Si Windows (Hyper-V/WSL/Docker) reserva el 8501, usamos
REM otro libre. Puedes cambiarlo si este tambien estuviera ocupado.
set "PUERTO=8600"

echo.
echo [1/5] Verificando Ollama...
where ollama >nul 2>nul
if errorlevel 1 (
    echo  ERROR: Ollama no esta instalado. Descargalo de https://ollama.com
    pause
    exit /b 1
)

echo [2/5] Iniciando el servidor de Ollama (si no esta corriendo)...
start "" /b ollama serve >nul 2>nul
timeout /t 3 >nul

echo [3/5] Descargando modelos (solo la primera vez)...
ollama pull %MODELO%
ollama pull %EMBED%

echo [4/5] Liberando el puerto %PUERTO% (cierra instancias anteriores)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PUERTO% ^| findstr LISTENING') do (
    echo   Cerrando proceso previo en el puerto %PUERTO% (PID %%a)...
    taskkill /PID %%a /F >nul 2>nul
)

echo [5/5] Iniciando la aplicacion (se abrira en el navegador)...
python -m streamlit run app.py --server.port %PUERTO%

pause
