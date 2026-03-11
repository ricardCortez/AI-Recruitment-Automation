@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Sistema CV RRHH - Instalador

set "BASE=%~dp0"
set "LOG=%BASE%instalacion.log"
set "ERRORES=0"
set "INSTALADOS="
set "YA_EXISTIAN="
set "PYTHON_EXE="
set "NPM_EXE="

echo.
echo  ============================================================
echo   SISTEMA CV RRHH  --  Instalador
echo   Ruta: %BASE%
echo  ============================================================
echo.

:: ---- Inicializar log -------------------------------------------------------
echo [%DATE% %TIME%] === INICIO DE INSTALACION === > "%LOG%"
echo [%DATE% %TIME%] Ruta base: %BASE% >> "%LOG%"
echo. >> "%LOG%"

:: ---- Verificar permisos de administrador -----------------------------------
net session >nul 2>&1
if errorlevel 1 (
    call :log "  [AVISO] Sin privilegios de administrador."
    call :log "          Instalaciones de sistema pueden fallar."
    call :log "          Recomendado: clic derecho -> Ejecutar como administrador"
    echo.
) else (
    call :log "  [OK] Privilegios de administrador confirmados."
)
echo.

:: ===========================================================================
:: PASO 1 -- Python 3.11+
:: ===========================================================================
call :log "--- PASO 1: Python ---"
echo  [1/10] Verificando Python 3.11+...

:: Si el instalador .exe indico INSTALL_PYTHON=0, omitir este paso
if "%INSTALL_PYTHON%"=="0" (
    call :log "  [--] Instalacion de Python omitida (INSTALL_PYTHON=0)."
    goto :paso2
)

python -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('python --version 2^>nul') do call :log "  [OK] %%v ya instalado."
    set "YA_EXISTIAN=!YA_EXISTIAN! Python"
    goto :paso2
)

call :log "  [+] Python no encontrado o version anterior a 3.11. Descargando..."
echo  Descargando Python 3.12...
curl -L --progress-bar "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" -o "%TEMP%\python-installer.exe"
if errorlevel 1 (
    call :log "  [ERROR] No se pudo descargar Python. Verificar conexion a internet."
    set /a ERRORES+=1
    goto :paso2
)

call :log "  Instalando Python silenciosamente..."
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
del "%TEMP%\python-installer.exe" >nul 2>&1

:: Refrescar PATH desde el Registro (sin reiniciar consola)
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEM_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%B"
if defined USER_PATH (set "PATH=!SYSTEM_PATH!;!USER_PATH!") else (set "PATH=!SYSTEM_PATH!")

:: Agregar rutas conocidas de Python como fallback
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;C:\Python312;C:\Python312\Scripts;C:\Program Files\Python312;C:\Program Files\Python312\Scripts;!PATH!"

python --version >nul 2>&1
if errorlevel 1 (
    call :log "  [AVISO] Python instalado pero requiere reiniciar la consola."
    call :log "          Cierra y vuelve a ejecutar instalar.bat"
    echo.
    echo  Python fue instalado pero requiere reiniciar.
    echo  Cierra esta ventana y vuelve a ejecutar instalar.bat
    pause
    exit /b 0
)
call :log "  [OK] Python 3.12 instalado correctamente."
set "INSTALADOS=!INSTALADOS! Python"

:paso2
:: ===========================================================================
:: PASO 2 -- Node.js 18+
:: ===========================================================================
call :log "--- PASO 2: Node.js ---"
echo  [2/10] Verificando Node.js 18+...

:: Si el instalador .exe indico INSTALL_NODE=0, omitir este paso
if "%INSTALL_NODE%"=="0" (
    call :log "  [--] Instalacion de Node.js omitida (INSTALL_NODE=0)."
    goto :paso3
)

node -e "process.exit(parseInt(process.version.slice(1))>=18?0:1)" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('node --version 2^>nul') do call :log "  [OK] Node.js %%v ya instalado."
    set "YA_EXISTIAN=!YA_EXISTIAN! Node.js"
    goto :paso3
)

call :log "  [+] Node.js no encontrado o version anterior a 18. Descargando..."
echo  Descargando Node.js 20 LTS...
curl -L --progress-bar "https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi" -o "%TEMP%\node-installer.msi"
if errorlevel 1 (
    call :log "  [ERROR] No se pudo descargar Node.js."
    set /a ERRORES+=1
    goto :paso3
)

call :log "  Instalando Node.js silenciosamente..."
msiexec /i "%TEMP%\node-installer.msi" /quiet /norestart
del "%TEMP%\node-installer.msi" >nul 2>&1

:: Refrescar PATH desde el Registro (sin reiniciar consola)
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEM_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%B"
if defined USER_PATH (set "PATH=!SYSTEM_PATH!;!USER_PATH!") else (set "PATH=!SYSTEM_PATH!")

:: Agregar rutas conocidas de Node como fallback
set "PATH=C:\Program Files\nodejs;%APPDATA%\npm;!PATH!"

node --version >nul 2>&1
if errorlevel 1 (
    call :log "  [AVISO] Node.js instalado pero requiere reiniciar la consola."
    call :log "          Cierra y vuelve a ejecutar instalar.bat"
    echo.
    echo  Node.js fue instalado pero requiere reiniciar.
    echo  Cierra esta ventana y vuelve a ejecutar instalar.bat
    pause
    exit /b 0
)
call :log "  [OK] Node.js 20 instalado correctamente."
set "INSTALADOS=!INSTALADOS! Node.js"

:paso3
:: ===========================================================================
:: PASO 3 -- Ollama
:: ===========================================================================
call :log "--- PASO 3: Ollama ---"
echo  [3/10] Verificando Ollama...

:: Si el instalador .exe indico INSTALL_OLLAMA=0, omitir este paso
if "%INSTALL_OLLAMA%"=="0" (
    call :log "  [--] Instalacion de Ollama omitida (INSTALL_OLLAMA=0)."
    goto :buscar_exes
)

where ollama >nul 2>&1
if not errorlevel 1 (
    call :log "  [OK] Ollama ya instalado."
    set "YA_EXISTIAN=!YA_EXISTIAN! Ollama"
    goto :buscar_exes
)
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    call :log "  [OK] Ollama encontrado en AppData."
    set "YA_EXISTIAN=!YA_EXISTIAN! Ollama"
    goto :buscar_exes
)

call :log "  [+] Ollama no encontrado. Descargando..."
echo  Descargando Ollama...
curl -L --progress-bar "https://ollama.com/download/OllamaSetup.exe" -o "%TEMP%\OllamaSetup.exe"
if errorlevel 1 (
    call :log "  [ERROR] No se pudo descargar Ollama."
    set /a ERRORES+=1
    goto :buscar_exes
)

call :log "  Instalando Ollama..."
"%TEMP%\OllamaSetup.exe" /S
del "%TEMP%\OllamaSetup.exe" >nul 2>&1
timeout /t 3 /nobreak >nul
call :log "  [OK] Ollama instalado correctamente."
set "INSTALADOS=!INSTALADOS! Ollama"

:buscar_exes
:: ===========================================================================
:: Localizar ejecutables Python y Node por ruta absoluta
:: (no depender del PATH del proceso actual, que puede estar desactualizado)
:: ===========================================================================
call :log "--- Localizando ejecutables ---"

:: ---- Python ----------------------------------------------------------------
set "PYTHON_EXE="
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
) do (
    if exist %%P if not defined PYTHON_EXE set "PYTHON_EXE=%%~P"
)
if not defined PYTHON_EXE (
    where python >nul 2>&1 && set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
    call :log "  [ERROR] Python no encontrado despues de instalar."
    call :log "          Por favor reinicia el instalador."
    exit /b 1
)
call :log "  Python: !PYTHON_EXE!"

:: ---- Node / npm ------------------------------------------------------------
set "NPM_EXE="
for %%N in (
    "C:\Program Files\nodejs\npm.cmd"
    "C:\Program Files (x86)\nodejs\npm.cmd"
    "%APPDATA%\npm\npm.cmd"
) do (
    if exist %%N if not defined NPM_EXE set "NPM_EXE=%%~N"
)
if not defined NPM_EXE (
    where npm >nul 2>&1 && set "NPM_EXE=npm"
)
if not defined NPM_EXE (
    call :log "  [ERROR] Node.js (npm) no encontrado despues de instalar."
    exit /b 1
)
call :log "  npm: !NPM_EXE!"

:paso4
:: ===========================================================================
:: PASO 4 -- Dependencias Python (global, sin venv)
:: ===========================================================================
call :log "--- PASO 4: Dependencias Python ---"
echo  [4/10] Instalando dependencias Python...
echo  (esto puede tardar un momento)

"%PYTHON_EXE%" -m pip install -r "%BASE%backend\requirements.txt" --no-warn-script-location --quiet
if errorlevel 1 (
    call :log "  [ERROR] Fallo la instalacion de dependencias Python."
    call :log "          Intentando con --user..."
    "%PYTHON_EXE%" -m pip install -r "%BASE%backend\requirements.txt" --user --no-warn-script-location
    if errorlevel 1 (
        call :log "  [ERROR] No se pudieron instalar las dependencias Python."
        set /a ERRORES+=1
    ) else (
        call :log "  [OK] Dependencias Python instaladas (modo usuario)."
    )
) else (
    call :log "  [OK] Dependencias Python instaladas correctamente."
)

:: ===========================================================================
:: PASO 5 -- Build del frontend
:: ===========================================================================
call :log "--- PASO 5: Build Frontend ---"
echo  [5/10] Construyendo interfaz web...
echo  (esto puede tardar varios minutos la primera vez)

cd /d "%BASE%frontend"

call :log "  Instalando node_modules..."
"%NPM_EXE%" install --prefer-offline --no-audit --no-fund
if errorlevel 1 (
    call :log "  [WARN] npm install tuvo advertencias, intentando continuar..."
)

call :log "  Ejecutando npm run build..."
"%NPM_EXE%" run build
if errorlevel 1 (
    call :log "  [ERROR] npm run build fallo. Intentando con npx vite build..."
    "%NPM_EXE%" exec vite build
)

cd /d "%BASE%"

if not exist "%BASE%frontend\dist\index.html" (
    call :log "  [ERROR CRITICO] El frontend no se construyo correctamente."
    call :log "  Revisa instalacion.log para mas detalles."
    set /a ERRORES+=1
    goto :paso6
)
call :log "  [OK] Frontend construido correctamente."

:paso6
:: ===========================================================================
:: PASO 6 -- Crear .env
:: ===========================================================================
call :log "--- PASO 6: Archivo .env ---"
echo  [6/10] Configurando .env...

if exist "%BASE%backend\.env" (
    call :log "  [OK] backend\.env ya existe, no se sobreescribe."
    set "YA_EXISTIAN=!YA_EXISTIAN! .env"
    goto :paso7
)

:: Generar SECRET_KEY con Python (evitar for /f para rutas con espacios)
"%PYTHON_EXE%" -c "import secrets; print(secrets.token_hex(32))" > "%TEMP%\sk_tmp.txt"
set /p SK= < "%TEMP%\sk_tmp.txt"
del "%TEMP%\sk_tmp.txt" >nul 2>&1

if exist "%BASE%.env.example" (
    call :log "  Copiando desde .env.example y configurando..."
    copy "%BASE%.env.example" "%BASE%backend\.env" >nul
    powershell -Command "$f='%BASE%backend\.env'; $c=(Get-Content $f); $c=$c -replace 'SECRET_KEY=.*','SECRET_KEY=!SK!'; $c=$c -replace 'OLLAMA_MODEL=.*','OLLAMA_MODEL=qwen2.5:7b'; $c=$c -replace 'ADMIN_PASSWORD=','ADMIN_PASSWORD=Admin@2025!'; [IO.File]::WriteAllLines($f,$c)"
) else (
    call :log "  Creando .env desde cero..."
    "%PYTHON_EXE%" -c "
import sys
key = sys.argv[1]
content = '\n'.join([
    'APP_NAME=Sistema CV',
    'APP_VERSION=1.0.0',
    'ENVIRONMENT=production',
    'BACKEND_HOST=127.0.0.1',
    'BACKEND_PORT=8000',
    'FRONTEND_PORT=5173',
    'SECRET_KEY=' + key,
    'ALGORITHM=HS256',
    'ACCESS_TOKEN_EXPIRE_MINUTES=480',
    'DATABASE_URL=sqlite:///./database/sistema_cv.db',
    'IA_PROVIDER=ollama',
    'OLLAMA_BASE_URL=http://localhost:11434',
    'OLLAMA_MODEL=qwen2.5:7b',
    'OPENAI_API_KEY=',
    'OPENAI_MODEL=gpt-4o-mini',
    'STORAGE_CVS_PATH=storage/cvs',
    'STORAGE_EXPORTS_PATH=storage/exports',
    'MAX_FILE_SIZE_MB=10',
    'ALLOWED_EXTENSIONS=pdf',
    'ADMIN_USERNAME=admin',
    'ADMIN_PASSWORD=Admin@2025!',
]) + '\n'
open(sys.argv[2], 'w', encoding='utf-8').write(content)
print('ok')
" "!SK!" "%BASE%backend\.env"
)

if exist "%BASE%backend\.env" (
    call :log "  [OK] backend\.env creado correctamente."
    set "INSTALADOS=!INSTALADOS! .env"
) else (
    call :log "  [ERROR] No se pudo crear backend\.env"
    set /a ERRORES+=1
)

:paso7
:: ===========================================================================
:: PASO 7 -- Crear carpetas necesarias
:: ===========================================================================
call :log "--- PASO 7: Carpetas ---"
echo  [7/10] Creando carpetas necesarias...

for %%d in (
    "%BASE%backend\database"
    "%BASE%backend\storage\cvs"
    "%BASE%backend\storage\exports"
    "%BASE%logs"
) do (
    if not exist %%d (
        mkdir %%d >nul 2>&1
        call :log "  [+] Creada: %%~d"
    ) else (
        call :log "  [OK] Ya existe: %%~d"
    )
)

:paso8
:: ===========================================================================
:: PASO 8 -- Migraciones
:: ===========================================================================
call :log "--- PASO 8: Migraciones ---"
echo  [8/10] Ejecutando migraciones de base de datos...

cd /d "%BASE%backend"
"%PYTHON_EXE%" migrate_v5.py >> "%LOG%" 2>&1
if errorlevel 1 (
    call :log "  [AVISO] migrate_v5.py fallo (puede ser normal si la BD ya existe)."
) else (
    call :log "  [OK] Migraciones completadas."
)
cd /d "%BASE%"

:paso9
:: ===========================================================================
:: PASO 9 -- Seed (usuario admin inicial)
:: ===========================================================================
call :log "--- PASO 9: Usuario admin ---"
echo  [9/10] Creando usuario admin inicial...

cd /d "%BASE%backend"
"%PYTHON_EXE%" -m app.db.seed >> "%LOG%" 2>&1
if errorlevel 1 (
    call :log "  [AVISO] Seed fallo (posiblemente el admin ya existe -- normal)."
) else (
    call :log "  [OK] Usuario admin creado/verificado."
)
cd /d "%BASE%"

:paso10
:: ===========================================================================
:: PASO 10 -- Descargar modelo IA
:: ===========================================================================
call :log "--- PASO 10: Modelo IA ---"
echo  [10/10] Descargando modelo IA qwen2.5:7b...
echo.
echo  *** AVISO: La descarga del modelo puede tardar 10-20 minutos ***
echo  *** Requiere ~4.7 GB de espacio libre                        ***
echo.

:: Buscar ollama por ruta absoluta
set "OLLAMA_BIN="
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_BIN=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not defined OLLAMA_BIN if exist "C:\Program Files\Ollama\ollama.exe" set "OLLAMA_BIN=C:\Program Files\Ollama\ollama.exe"
if not defined OLLAMA_BIN (
    where ollama >nul 2>&1 && set "OLLAMA_BIN=ollama"
)

if not defined OLLAMA_BIN (
    call :log "  [AVISO] ollama no encontrado. Saltar descarga del modelo."
    call :log "          Ejecuta manualmente: ollama pull qwen2.5:7b"
    goto :resumen
)

:: Iniciar Ollama en background para la descarga
call :log "  Iniciando Ollama en background..."
start /B "" "%OLLAMA_BIN%" serve >nul 2>&1
timeout /t 5 /nobreak >nul

call :log "  Descargando qwen2.5:7b (puede tardar varios minutos)..."
"%OLLAMA_BIN%" pull qwen2.5:7b
if errorlevel 1 (
    call :log "  [ERROR] No se pudo descargar qwen2.5:7b"
    call :log "          Intenta manualmente: ollama pull qwen2.5:7b"
    set /a ERRORES+=1
) else (
    call :log "  [OK] Modelo qwen2.5:7b descargado correctamente."
    set "INSTALADOS=!INSTALADOS! ModeloIA"
)

:resumen
:: ===========================================================================
:: RESUMEN FINAL
:: ===========================================================================
echo.
echo  ============================================================
echo   RESUMEN DE INSTALACION
echo  ============================================================
echo.
echo   Instalados ahora:  !INSTALADOS!
echo   Ya existian:       !YA_EXISTIAN!
echo   Errores:           !ERRORES!
echo.

echo. >> "%LOG%"
echo [%DATE% %TIME%] === FIN DE INSTALACION === >> "%LOG%"
echo Instalados: !INSTALADOS! >> "%LOG%"
echo Ya existian: !YA_EXISTIAN! >> "%LOG%"
echo Errores: !ERRORES! >> "%LOG%"

if !ERRORES! GTR 0 (
    echo   [!] Se encontraron !ERRORES! error(es).
    echo       Revisa %LOG% para mas detalles.
    echo       Puedes volver a ejecutar instalar.bat de forma segura.
    echo.
) else (
    echo   Instalacion completada sin errores.
    echo.
)

echo   Instalacion completa. Ejecuta iniciar.bat para usar el sistema.
echo.
echo   Log guardado en: %LOG%
echo.

:: Centinela para deteccion automatica por el instalador .exe
echo [INSTALACION_COMPLETA] >> "%LOG%"

pause
exit /b 0

:: ===========================================================================
:: Subrutina: escribir en consola Y en log
:: ===========================================================================
:log
echo %~1
echo %~1 >> "%LOG%"
goto :eof
