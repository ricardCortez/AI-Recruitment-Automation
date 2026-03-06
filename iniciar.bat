@echo off
title Sistema CV

echo.
echo  =========================================
echo   SISTEMA CV - RR.HH
echo   Iniciando servicios...
echo  =========================================
echo.

:: Verificar que existe el .env
if not exist "backend\.env" (
    echo [!] No se encontro backend\.env
    echo [!] Copiando desde .env.example...
    copy ".env.example" "backend\.env" >nul
    echo [!] Edita backend\.env antes de continuar.
    pause
    exit /b 1
)

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Descargalo desde https://python.org
    pause
    exit /b 1
)

:: Crear entorno virtual si no existe
if not exist "backend\venv\Scripts\activate.bat" (
    echo [+] Creando entorno virtual Python...
    python -m venv backend\venv
)

:: Activar entorno e instalar dependencias
echo [+] Activando entorno virtual...
call backend\venv\Scripts\activate.bat

echo [+] Verificando dependencias Python...
pip install -r backend\requirements.txt -q --disable-pip-version-check

:: Verificar Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js no esta instalado.
    echo Descargalo desde https://nodejs.org
    pause
    exit /b 1
)

:: Instalar dependencias frontend
if not exist "frontend\node_modules" (
    echo [+] Instalando dependencias del frontend...
    cd frontend
    npm install --silent
    cd ..
)

:: Inicializar base de datos
echo [+] Inicializando base de datos...
cd backend
python app\db\seed.py
cd ..

:: Levantar backend
echo [+] Iniciando Backend en http://localhost:8000 ...
start "Backend-SistemaCV" /min cmd /c "call backend\venv\Scripts\activate.bat && cd backend && uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

:: Esperar
timeout /t 3 /nobreak >nul

:: Levantar frontend
echo [+] Iniciando Frontend en http://localhost:5173 ...
start "Frontend-SistemaCV" /min cmd /c "cd frontend && npm run dev"

:: Esperar y abrir navegador
timeout /t 4 /nobreak >nul
echo [+] Abriendo navegador...
start http://localhost:5173

echo.
echo  =========================================
echo   Sistema iniciado correctamente
echo.
echo   Frontend -> http://localhost:5173
echo   Backend  -> http://localhost:8000
echo   API Docs -> http://localhost:8000/docs
echo.
echo   Para detener: ejecuta detener.bat
echo  =========================================
echo.
echo  Esta ventana puede cerrarse de forma segura.
pause