@echo off
chcp 65001 >nul
title Sistema CV - Iniciando (GPU)...

:: ── Detectar ruta base ───────────────────────────────────────────────────────
set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

echo.
echo  ============================================================
echo   SISTEMA CV  —  IA de Reclutamiento Local
echo   Modo: GPU (NVIDIA CUDA)
echo   Ruta: %BASE%
echo  ============================================================
echo.

:: ── Verificar backend\venv ───────────────────────────────────────────────────
if not exist "%BASE%\backend\venv\Scripts\activate.bat" (
    echo  [ERROR] Entorno virtual no encontrado.
    echo.
    echo  Solución: abre una terminal en la carpeta del proyecto y ejecuta:
    echo    cd backend
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: ── Verificar .env ───────────────────────────────────────────────────────────
if not exist "%BASE%\backend\.env" (
    echo  [ERROR] No se encontró backend\.env
    echo.
    if exist "%BASE%\backend\.env.example" (
        echo  Copiando .env.example -> .env ...
        copy "%BASE%\backend\.env.example" "%BASE%\backend\.env" >nul
        echo  [!] Edita backend\.env y agrega una SECRET_KEY antes de continuar.
    )
    echo.
    pause
    exit /b 1
)

:: ── Verificar Node.js ────────────────────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js no está instalado o no está en el PATH.
    echo  Descargalo desde https://nodejs.org
    echo.
    pause
    exit /b 1
)

:: ── Instalar dependencias frontend si faltan ─────────────────────────────────
if not exist "%BASE%\frontend\node_modules" (
    echo  [+] Instalando dependencias del frontend (primera vez)...
    cd /d "%BASE%\frontend"
    npm install --silent
    cd /d "%BASE%"
    echo  [OK] Dependencias del frontend instaladas.
)

:: ── 1. Ollama con GPU ────────────────────────────────────────────────────────
echo  [1/3] Configurando GPU y arrancando Ollama...

:: Matar Ollama si ya corría (para relanzarlo con las variables GPU)
taskkill /IM ollama.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: Buscar ollama.exe
set "OLLAMA_EXE="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if "%OLLAMA_EXE%"=="" if exist "C:\Program Files\Ollama\ollama.exe"       set "OLLAMA_EXE=C:\Program Files\Ollama\ollama.exe"
if "%OLLAMA_EXE%"=="" where ollama >nul 2>&1 && set "OLLAMA_EXE=ollama"

if "%OLLAMA_EXE%"=="" (
    echo  [ERROR] Ollama no encontrado.
    echo  Descargalo desde https://ollama.com y vuelve a intentar.
    echo.
    pause
    exit /b 1
)

echo  Ollama: %OLLAMA_EXE%
echo  Iniciando con soporte CUDA...

:: Variables de entorno GPU — deben existir en el proceso de Ollama
start "SistemaCV-Ollama" /min cmd /c "set OLLAMA_NUM_GPU=999 && set OLLAMA_GPU_LAYERS=999 && set CUDA_VISIBLE_DEVICES=0 && set OLLAMA_FLASH_ATTENTION=1 && set OLLAMA_HOST=127.0.0.1:11434 && "%OLLAMA_EXE%" serve"

:: Esperar hasta 20 s a que Ollama responda
echo  Esperando que Ollama arranque...
set /a TRIES=0
:wait_ollama
timeout /t 2 /nobreak >nul
set /a TRIES+=1
curl -s --max-time 2 http://localhost:11434 >nul 2>&1
if not errorlevel 1 goto :ollama_ok
if %TRIES% GEQ 10 (
    echo  [!] Ollama tardó demasiado. Continúa de todas formas...
    goto :backend
)
goto :wait_ollama
:ollama_ok
echo  [OK] Ollama listo en http://localhost:11434 (GPU activa)

:: ── 2. Backend ───────────────────────────────────────────────────────────────
:backend
echo  [2/3] Iniciando Backend...
start "SistemaCV-Backend" /min cmd /k "cd /d "%BASE%\backend" && call venv\Scripts\activate.bat && uvicorn main:app --host 127.0.0.1 --port 8000"

:: Esperar al health endpoint
echo  Esperando que el Backend responda...
set /a TRIES=0
:wait_backend
timeout /t 2 /nobreak >nul
set /a TRIES+=1
curl -s --max-time 2 http://localhost:8000/health >nul 2>&1
if not errorlevel 1 goto :backend_ok
if %TRIES% GEQ 10 (
    echo  [!] Backend tardó demasiado. Continúa de todas formas...
    goto :frontend
)
goto :wait_backend
:backend_ok
echo  [OK] Backend listo en http://localhost:8000

:: ── 3. Frontend ──────────────────────────────────────────────────────────────
:frontend
echo  [3/3] Iniciando Frontend...
start "SistemaCV-Frontend" /min cmd /k "cd /d "%BASE%\frontend" && npm run dev"

:: Esperar al frontend
echo  Esperando que el Frontend responda...
set /a TRIES=0
:wait_frontend
timeout /t 2 /nobreak >nul
set /a TRIES+=1
curl -s --max-time 2 http://localhost:5173 >nul 2>&1
if not errorlevel 1 goto :frontend_ok
if %TRIES% GEQ 8 (
    echo  [!] Frontend tardó demasiado. Abriendo navegador igual...
    goto :open_browser
)
goto :wait_frontend
:frontend_ok
echo  [OK] Frontend listo en http://localhost:5173

:: ── Abrir navegador ──────────────────────────────────────────────────────────
:open_browser
timeout /t 1 /nobreak >nul
echo  Abriendo navegador...
start http://localhost:5173

:: ── Resumen ──────────────────────────────────────────────────────────────────
echo.
echo  ============================================================
echo   Sistema iniciado correctamente  (Modo GPU)
echo.
echo   Frontend  ->  http://localhost:5173
echo   Backend   ->  http://localhost:8000
echo   Ollama    ->  http://localhost:11434
echo.
echo   Para verificar GPU:  nvidia-smi
echo   Para detener todos los servicios: ejecuta  detener.bat
echo  ============================================================
echo.
echo  Esta ventana puede cerrarse de forma segura.
pause
