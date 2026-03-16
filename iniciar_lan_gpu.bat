@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Sistema CV - Iniciando (LAN - GPU)...

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

echo.
echo  ============================================================
echo   SISTEMA CV  --  IA de Reclutamiento Local (GPU - LAN)
echo   Ruta: %BASE%
echo  ============================================================
echo.

:: ---- Verificar GPU NVIDIA ------------------------------------------------
echo  [*] Verificando GPU NVIDIA...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo  [AVISO] nvidia-smi no responde. La IA usara CPU como fallback.
) else (
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu=name --format=csv,noheader 2^>nul') do echo  [OK] GPU: %%g
)

:: ---- Checks basicos -------------------------------------------------------
"%PYTHON_EXE%" -c "import fastapi, uvicorn, sqlalchemy, pdfplumber" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Dependencias de Python faltantes. Ejecuta instalar.bat primero.
    pause & exit /b 1
)

if not exist "%BASE%\frontend\dist\index.html" (
    echo  [ERROR] Frontend no buildeado. Ejecuta instalar.bat primero.
    pause & exit /b 1
)

if not exist "%BASE%\backend\.env" (
    echo  [ERROR] No se encontro backend\.env. Ejecuta instalar.bat primero.
    pause & exit /b 1
)

:: ---- 1. Ollama con CUDA --------------------------------------------------
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

echo  Iniciando Ollama ^(GPU/CUDA^)...
set OLLAMA_HOST=127.0.0.1:11434
start "SistemaCV-Ollama" /MIN cmd /c "set OLLAMA_CUDA=1 && "%OLLAMA_EXE%" serve"

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
echo  [OK] Ollama listo ^(GPU^).

:: ---- 2. Backend (LAN: host 0.0.0.0) -------------------------------------
:backend
echo  [2/2] Iniciando Backend en modo LAN (GPU)...

for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

set "LOG=%BASE%\logs\backend.log"
echo [%DATE% %TIME%] Iniciando backend (LAN - GPU)... > "%LOG%"

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
echo   SISTEMA CV iniciado en modo LAN (GPU/CUDA)
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
