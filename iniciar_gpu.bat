@echo off
chcp 65001 >nul
title Sistema CV

:: ── Detectar ruta base (donde está este .bat) ────────────────────────────────
set "BASE=%~dp0"
:: Quitar backslash final si existe
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

echo.
echo  ============================================
echo   Sistema CV - Iniciando...
echo   Ruta: %BASE%
echo  ============================================
echo.

:: ── Verificar que backend y frontend existen ─────────────────────────────────
if not exist "%BASE%\backend\venv\Scripts\activate.bat" (
    echo  [ERROR] No se encontro el entorno virtual.
    echo  Ruta buscada: %BASE%\backend\venv\Scripts\activate.bat
    echo.
    echo  Solucion: abre una terminal en la carpeta backend y ejecuta:
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%BASE%\frontend\package.json" (
    echo  [ERROR] No se encontro package.json del frontend.
    echo  Ruta buscada: %BASE%\frontend\package.json
    pause
    exit /b 1
)

:: ── 1. Configurar variables GPU y arrancar Ollama ────────────────────────────
echo  [1/3] Configurando GPU y arrancando Ollama...

:: IMPORTANTE: estas variables deben estar ANTES de que ollama.exe arranque
set OLLAMA_NUM_GPU=999
set OLLAMA_GPU_LAYERS=999
set CUDA_VISIBLE_DEVICES=0
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_HOST=127.0.0.1:11434

:: Matar Ollama si ya estaba corriendo (para que relance con las vars GPU)
taskkill /IM ollama.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: Buscar ollama.exe
set "OLLAMA_EXE="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if "%OLLAMA_EXE%"=="" if exist "%APPDATA%\..\Local\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%APPDATA%\..\Local\Programs\Ollama\ollama.exe"
if "%OLLAMA_EXE%"=="" (
    echo  [ERROR] ollama.exe no encontrado. Instala desde https://ollama.com
    pause
    exit /b 1
)

echo  Ollama encontrado: %OLLAMA_EXE%

:: Arrancar Ollama serve con variables GPU activas en su propio entorno
start "Ollama-GPU" /min cmd /c "set OLLAMA_NUM_GPU=999 && set CUDA_VISIBLE_DEVICES=0 && set OLLAMA_FLASH_ATTENTION=1 && "%OLLAMA_EXE%" serve"
timeout /t 4 /nobreak >nul
echo  [OK] Ollama iniciado con GPU.

:: ── 2. Backend ───────────────────────────────────────────────────────────────
echo  [2/3] Iniciando Backend Python...
start "Backend-CV" cmd /k "cd /d "%BASE%\backend" && call venv\Scripts\activate.bat && uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 2 /nobreak >nul
echo  [OK] Backend en http://localhost:8000

:: ── 3. Frontend ──────────────────────────────────────────────────────────────
echo  [3/3] Iniciando Frontend...
start "Frontend-CV" cmd /k "cd /d "%BASE%\frontend" && npm run dev"
echo  [OK] Frontend en http://localhost:5173

:: ── Listo ────────────────────────────────────────────────────────────────────
echo.
echo  ============================================
echo   Todo iniciado correctamente!
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   Ollama   : http://localhost:11434
echo.
echo   Para verificar GPU de Ollama ejecuta:
echo   nvidia-smi (ollama debe mostrar VRAM usada)
echo  ============================================
echo.
timeout /t 5 /nobreak >nul
exit