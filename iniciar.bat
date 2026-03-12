@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Sistema CV - Iniciando...

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

if not exist "%BASE%\logs" mkdir "%BASE%\logs"

:: Detectar Python por ruta absoluta
set "PYTHON_EXE="
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

:: Detectar npm por ruta absoluta
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
echo   SISTEMA CV  --  IA de Reclutamiento Local (CPU)
echo   Ruta: %BASE%
echo  ============================================================
echo.

:: =========================================================================
:: Validacion automatica de requisitos (auto-repara lo que puede)
:: =========================================================================
echo  ============================================
echo   Validando requisitos del sistema...
echo  ============================================

set ERRORES=0

:: ---- Python --------------------------------------------------------------
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo  [X] Python NO encontrado
    set ERRORES=1
) else (
    for /f "tokens=2" %%V in ('"%PYTHON_EXE%" --version 2^>^&1') do echo  [OK] Python %%V
)

:: ---- Paquetes Python criticos --------------------------------------------
"%PYTHON_EXE%" -c "import fastapi, uvicorn, sqlalchemy, pdfplumber" >nul 2>&1
if errorlevel 1 (
    echo  [!] Dependencias Python incompletas - reinstalando...
    "%PYTHON_EXE%" -m pip install -r "%BASE%\backend\requirements.txt" --quiet --no-warn-script-location
) else (
    echo  [OK] Dependencias Python instaladas
)

:: ---- Frontend (construir si falta) ---------------------------------------
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

:: ---- Ollama instalado ----------------------------------------------------
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

:: ---- Modelo IA -----------------------------------------------------------
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

:: ---- Archivo .env --------------------------------------------------------
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

:: ---- Base de datos -------------------------------------------------------
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

:: ---- Errores criticos -> abortar -----------------------------------------
if %ERRORES%==1 (
    echo.
    echo  [ERROR] El sistema no puede iniciarse.
    echo  Ejecuta verificar.bat para diagnostico detallado.
    echo  O ejecuta instalar.bat para reinstalar las dependencias.
    echo.
    pause
    exit /b 1
)

echo   Todo listo. Iniciando sistema...
echo  ============================================
echo.

:: ---- 1. Ollama ----------------------------------------------------------
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

:: ---- 2. Backend ---------------------------------------------------------
:backend
echo  [2/2] Iniciando Backend...

:: Limpiar puerto 8000 si esta ocupado
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

set "LOG=%BASE%\logs\backend.log"
echo [%DATE% %TIME%] Iniciando backend... > "%LOG%"

:: Escribir el comando de arranque en un .bat temporal
set "BAKCMD=%TEMP%\sistemaCV_backend.bat"
echo @echo off > "%BAKCMD%"
echo cd /d "%BASE%\backend" >> "%BAKCMD%"
echo "%PYTHON_EXE%" -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log 1^>^> "%LOG%" 2^>^&1 >> "%BAKCMD%"

:: Lanzar el .bat completamente oculto via WScript (0 = sin ventana)
set "VBSCMD=%TEMP%\sistemaCV_launch.vbs"
echo Set sh = WScript.CreateObject("WScript.Shell") > "%VBSCMD%"
echo sh.Run "cmd.exe /c ""%BAKCMD%""", 0, False >> "%VBSCMD%"
wscript //nologo "%VBSCMD%"
del "%VBSCMD%" >nul 2>&1

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
del "%BAKCMD%" >nul 2>&1
echo  [OK] Backend listo en http://127.0.0.1:8000
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8000
echo.
echo  Sistema CV iniciado. La aplicacion se abrio en el navegador.
echo  Para detener el sistema ejecuta detener.bat
echo.
timeout /t 3 /nobreak >nul
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
