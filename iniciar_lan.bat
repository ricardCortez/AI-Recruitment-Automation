@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Sistema CV - Iniciando (LAN - CPU)...

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

if not exist "%BASE%\logs" mkdir "%BASE%\logs"

:: ── Detectar IP LAN ───────────────────────────────────────────────────────────
set "LAN_IP="
for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /C:"IPv4"') do (
    set "TMP=%%I"
    set "TMP=!TMP: =!"
    if not "!TMP:~0,3!"=="127" if not defined LAN_IP set "LAN_IP=!TMP!"
)
if not defined LAN_IP set "LAN_IP=<no-detectada>"

:: ── Detectar Python (venv primero) ───────────────────────────────────────────
set "VENV_PYTHON=%BASE%\backend\venv\Scripts\python.exe"
set "PYTHON_EXE="

if exist "%VENV_PYTHON%" (
    set "PYTHON_EXE=%VENV_PYTHON%"
    echo  [OK] Usando Python del entorno virtual del proyecto
    goto :python_ok
)

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if exist %%P if not defined PYTHON_EXE set "PYTHON_EXE=%%~P"
)
if not defined PYTHON_EXE where python >nul 2>&1 && set "PYTHON_EXE=python"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

:python_ok

:: Detectar npm
set "NPM_EXE="
for %%P in (
    "C:\Program Files\nodejs\npm.cmd"
    "C:\Program Files (x86)\nodejs\npm.cmd"
) do (
    if exist %%P if not defined NPM_EXE set "NPM_EXE=%%~P"
)
if not defined NPM_EXE where npm >nul 2>&1 && set "NPM_EXE=npm"
if not defined NPM_EXE set "NPM_EXE=npm"

echo.
echo  ============================================================
echo   SISTEMA CV  --  IA de Reclutamiento Local (CPU - LAN)
echo   Ruta: %BASE%
echo  ============================================================
echo.

:: =========================================================================
:: Validacion
:: =========================================================================
echo  ============================================
echo   Validando requisitos del sistema...
echo  ============================================

set ERRORES=0

:: ---- Python ---------------------------------------------------------------
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo  [X] Python NO encontrado
    set ERRORES=1
) else (
    for /f "tokens=2" %%V in ('"%PYTHON_EXE%" --version 2^>^&1') do echo  [OK] Python %%V
)

:: ---- Paquetes Python ------------------------------------------------------
"%PYTHON_EXE%" -c "import fastapi, uvicorn, sqlalchemy, pdfplumber" >nul 2>&1
if errorlevel 1 (
    echo  [!] Dependencias Python incompletas - reinstalando...
    "%PYTHON_EXE%" -m pip install -r "%BASE%\backend\requirements.txt" --quiet --no-warn-script-location
) else (
    echo  [OK] Dependencias Python instaladas
)

:: ---- Frontend -------------------------------------------------------------
if not exist "%BASE%\frontend\dist\index.html" (
    node --version >nul 2>&1
    if errorlevel 1 (
        echo  [X] Node.js NO encontrado y frontend no buildeado
        set ERRORES=1
    ) else (
        echo  [!] Frontend no buildeado - construyendo...
        cd /d "%BASE%\frontend"
        "%NPM_EXE%" install --quiet
        "%NPM_EXE%" run build
        cd /d "%BASE%"
        if not exist "%BASE%\frontend\dist\index.html" (
            echo  [X] Fallo la construccion del frontend
            set ERRORES=1
        ) else (
            echo  [OK] Frontend construido correctamente
        )
    )
) else (
    echo  [OK] Frontend listo
)

:: ---- Ollama ---------------------------------------------------------------
where ollama >nul 2>&1
if errorlevel 1 (
    if not exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        echo  [X] Ollama NO encontrado
        set ERRORES=1
    ) else (
        echo  [OK] Ollama instalado
    )
) else (
    echo  [OK] Ollama instalado
)

:: ---- Modelo IA ------------------------------------------------------------
set "OLLAMA_BIN="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_BIN=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not defined OLLAMA_BIN where ollama >nul 2>&1 && set "OLLAMA_BIN=ollama"
if defined OLLAMA_BIN (
    "%OLLAMA_BIN%" list 2>nul | findstr "qwen2.5:7b" >nul 2>&1
    if errorlevel 1 (
        echo  [!] Modelo qwen2.5:7b no descargado
        echo      Iniciando descarga ^(~4.5 GB^). Esto puede tardar varios minutos...
        start /B "" "%OLLAMA_BIN%" serve >nul 2>&1
        timeout /t 3 /nobreak >nul
        "%OLLAMA_BIN%" pull qwen2.5:7b
        if errorlevel 1 (
            echo  [X] No se pudo descargar el modelo. Verifica tu conexion.
            set ERRORES=1
        ) else (
            echo  [OK] Modelo descargado correctamente
        )
    ) else (
        echo  [OK] Modelo qwen2.5:7b disponible
    )
)

:: ---- .env -----------------------------------------------------------------
if not exist "%BASE%\backend\.env" (
    echo  [!] Archivo .env no encontrado - creando desde plantilla...
    if exist "%BASE%\backend\.env.example" (
        copy "%BASE%\backend\.env.example" "%BASE%\backend\.env" >nul
        echo  [OK] .env creado
    ) else (
        echo  [X] No se encontro .env.example
        set ERRORES=1
    )
) else (
    echo  [OK] Configuracion .env presente
)

:: ---- Base de datos --------------------------------------------------------
if not exist "%BASE%\backend\database\sistema_cv.db" (
    echo  [!] Base de datos no encontrada - inicializando...
    cd /d "%BASE%\backend"
    "%PYTHON_EXE%" migrate_v5.py >nul 2>&1
    "%PYTHON_EXE%" -m app.db.seed >nul 2>&1
    cd /d "%BASE%"
    echo  [OK] Base de datos inicializada
) else (
    echo  [OK] Base de datos presente
)

echo  ============================================

if %ERRORES%==1 (
    echo.
    echo  [ERROR] El sistema no puede iniciarse.
    echo  Ejecuta verificar.bat para diagnostico detallado.
    echo.
    pause
    exit /b 1
)

echo   Todo listo. Iniciando sistema en modo LAN...
echo  ============================================
echo.

:: ---- 1. Ollama ------------------------------------------------------------
echo  [1/2] Verificando Ollama...
curl -s --max-time 2 http://localhost:11434 >nul 2>&1
if not errorlevel 1 (
    echo  [OK] Ollama ya esta corriendo.
    goto :backend
)

set "OLLAMA_EXE="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if "%OLLAMA_EXE%"=="" if exist "C:\Program Files\Ollama\ollama.exe" set "OLLAMA_EXE=C:\Program Files\Ollama\ollama.exe"
if "%OLLAMA_EXE%"=="" where ollama >nul 2>&1 && set "OLLAMA_EXE=ollama"

if "%OLLAMA_EXE%"=="" (
    echo  [AVISO] Ollama no encontrado. Continuando sin IA...
    goto :backend
)

echo  Iniciando Ollama ^(CPU^)...
set OLLAMA_HOST=127.0.0.1:11434
start "" /B "%OLLAMA_EXE%" serve >nul 2>&1

set /a TRIES=0
:wait_ollama
timeout /t 2 /nobreak >nul
set /a TRIES+=1
curl -s --max-time 2 http://localhost:11434 >nul 2>&1
if not errorlevel 1 goto :ollama_ok
if %TRIES% GEQ 7 (
    echo  [!] Ollama tardo demasiado. Continuando...
    goto :backend
)
goto :wait_ollama
:ollama_ok
echo  [OK] Ollama listo.

:: ---- 2. Backend (LAN: host 0.0.0.0) -------------------------------------
:backend
echo  [2/2] Iniciando Backend en modo LAN...

for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

set "LOG=%BASE%\logs\backend.log"
echo [%DATE% %TIME%] Iniciando backend (LAN)... > "%LOG%"

:: ── HOST 0.0.0.0 para aceptar conexiones de la red local ──────────────────
start "SistemaCV-Backend" /MIN cmd /c "cd /d "%BASE%\backend" && "%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8000 --no-access-log 1>> "%LOG%" 2>&1"

echo  Esperando que el Backend responda...
set /a TRIES=0
:wait_backend
timeout /t 3 /nobreak >nul
set /a TRIES+=1
curl -s --max-time 3 http://127.0.0.1:8000/health >nul 2>&1
if not errorlevel 1 goto :backend_ok
if %TRIES% GEQ 10 goto :backend_error
goto :wait_backend

:backend_ok
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8000
echo.
echo  ============================================================
echo   SISTEMA CV iniciado en modo LAN (CPU)
echo.
echo   Esta maquina  ^(localhost^):  http://127.0.0.1:8000
echo   Red local     ^(LAN^):        http://%LAN_IP%:8000
echo.
echo   Comparte la URL de red con el resto de tu equipo.
echo   IMPORTANTE: el Firewall de Windows debe permitir el
echo   puerto 8000 para que otros equipos puedan conectarse.
echo.
echo   Para detener el sistema: ejecuta detener.bat
echo   Log del backend: %LOG%
echo  ============================================================
echo.
pause
exit /b 0

:backend_error
echo.
echo  [ERROR] El backend no respondio en el tiempo esperado.
echo  Revisa el log de errores a continuacion:
echo.
type "%LOG%"
echo.
pause
exit /b 1
