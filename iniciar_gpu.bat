@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Sistema CV - Iniciando (GPU)...

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

if not exist "%BASE%\logs" mkdir "%BASE%\logs"

echo.
echo  ============================================================
echo   SISTEMA CV  --  IA de Reclutamiento Local (GPU/CUDA)
echo   Ruta: %BASE%
echo  ============================================================
echo.

:: ---- Verificar GPU NVIDIA -----------------------------------------------
echo  [*] Verificando GPU NVIDIA...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo  [AVISO] nvidia-smi no responde. La IA usara CPU como fallback.
) else (
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu=name --format=csv,noheader 2^>nul') do echo  [OK] GPU: %%g
)

:: ---- Verificar Python ---------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado. Ejecuta instalar.bat primero.
    pause & exit /b 1
)

:: ---- Verificar dependencias ---------------------------------------------
python -c "import fastapi, uvicorn, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Dependencias de Python faltantes. Ejecuta instalar.bat primero.
    pause & exit /b 1
)

:: ---- Verificar frontend buildeado --------------------------------------
if not exist "%BASE%\frontend\dist\index.html" (
    echo  [ERROR] Frontend no buildeado. Ejecuta instalar.bat primero.
    pause & exit /b 1
)

:: ---- Verificar .env -----------------------------------------------------
if not exist "%BASE%\backend\.env" (
    echo  [ERROR] No se encontro backend\.env. Ejecuta instalar.bat primero.
    pause & exit /b 1
)

:: ---- 1. Ollama con CUDA -------------------------------------------------
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
start "SistemaCV-Ollama" /min cmd /c "set OLLAMA_CUDA=1 && "%OLLAMA_EXE%" serve"

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

:: ---- 2. Backend ---------------------------------------------------------
:backend
echo  [2/2] Iniciando Backend...

for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

set "LOG=%BASE%\logs\backend.log"
echo [%DATE% %TIME%] Iniciando backend (GPU)... > "%LOG%"

start "SistemaCV-Backend" /min cmd /c "cd /d "%BASE%\backend" && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log >> "%LOG%" 2>&1"

echo  Esperando que el Backend responda...
set /a TRIES=0
:wait_backend
timeout /t 3 /nobreak >nul
set /a TRIES+=1
curl -s --max-time 3 http://127.0.0.1:8000/health >nul 2>&1
if not errorlevel 1 goto :backend_ok
if %TRIES% GEQ 10 (
    echo  [!] Backend tardo demasiado. Comprueba logs\backend.log
    goto :open_browser
)
goto :wait_backend
:backend_ok
echo  [OK] Backend listo en http://127.0.0.1:8000

:open_browser
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8000

echo.
echo  +--------------------------------------------+
echo  ^|   Sistema CV RRHH iniciado ^(GPU/CUDA^)     ^|
echo  ^|                                            ^|
echo  ^|   Aplicacion: http://127.0.0.1:8000       ^|
echo  ^|   Para detener: ejecuta detener.bat        ^|
echo  +--------------------------------------------+
echo.
echo  -- Log en tiempo real ^(Ctrl+C para salir^) --
echo.

powershell -Command "Get-Content '%BASE%\logs\backend.log' -Wait -Tail 20"
