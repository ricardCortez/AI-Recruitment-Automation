@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Sistema CV - Verificacion

set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

set "LOG=%BASE%\verificacion.log"

echo.
echo  ============================================================
echo   SISTEMA CV  --  Diagnostico del sistema
echo   Fecha: %DATE%  %TIME%
echo  ============================================================
echo.

echo ============================================================ > "%LOG%"
echo  SISTEMA CV  -- Diagnostico del sistema >> "%LOG%"
echo  Fecha: %DATE%  %TIME% >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo. >> "%LOG%"

:: ===========================================================================
:: Python
:: ===========================================================================
echo  === Python === >> "%LOG%"
echo  === Python ===
python --version >nul 2>&1
if errorlevel 1 (
    echo  [XX] Python NO encontrado en PATH
    echo  [XX] Python NO encontrado en PATH >> "%LOG%"
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do (
        echo  [OK] %%v
        echo  [OK] %%v >> "%LOG%"
    )
)

:: ===========================================================================
:: Paquetes Python
:: ===========================================================================
echo.
echo  === Paquetes Python ===
echo. >> "%LOG%"
echo  === Paquetes Python === >> "%LOG%"
for %%p in (fastapi uvicorn sqlalchemy pydantic python-jose passlib aiofiles python-multipart httpx) do (
    python -c "import %%p" >nul 2>&1
    if errorlevel 1 (
        echo  [XX] %%p  NO instalado
        echo  [XX] %%p  NO instalado >> "%LOG%"
    ) else (
        echo  [OK] %%p
        echo  [OK] %%p >> "%LOG%"
    )
)
python -c "import pdfminer" >nul 2>&1
if errorlevel 1 (
    echo  [XX] pdfminer.six  NO instalado
    echo  [XX] pdfminer.six  NO instalado >> "%LOG%"
) else (
    echo  [OK] pdfminer.six
    echo  [OK] pdfminer.six >> "%LOG%"
)

:: ===========================================================================
:: Node.js
:: ===========================================================================
echo.
echo  === Node.js ===
echo. >> "%LOG%"
echo  === Node.js === >> "%LOG%"
node --version >nul 2>&1
if errorlevel 1 (
    echo  [!!] Node.js no encontrado (solo necesario para rebuild del frontend)
    echo  [!!] Node.js no encontrado >> "%LOG%"
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do (
        echo  [OK] Node.js %%v
        echo  [OK] Node.js %%v >> "%LOG%"
    )
)

:: ===========================================================================
:: Ollama
:: ===========================================================================
echo.
echo  === Ollama ===
echo. >> "%LOG%"
echo  === Ollama === >> "%LOG%"
curl -s --max-time 3 http://localhost:11434 >nul 2>&1
if errorlevel 1 (
    echo  [!!] Ollama no responde en localhost:11434
    echo  [!!] Ollama no responde en localhost:11434 >> "%LOG%"
) else (
    echo  [OK] Ollama corriendo en localhost:11434
    echo  [OK] Ollama corriendo en localhost:11434 >> "%LOG%"
    for /f "tokens=*" %%m in ('curl -s http://localhost:11434/api/tags 2^>nul ^| python -c "import sys,json; d=json.load(sys.stdin); [print(m[chr(110)+chr(97)+chr(109)+chr(101)]) for m in d.get(chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(115),[])]" 2^>nul') do (
        echo     Modelo disponible: %%m
        echo     Modelo disponible: %%m >> "%LOG%"
    )
)

:: ===========================================================================
:: Archivos del proyecto
:: ===========================================================================
echo.
echo  === Archivos del proyecto ===
echo. >> "%LOG%"
echo  === Archivos del proyecto === >> "%LOG%"
for %%f in ("backend\.env" "backend\main.py" "backend\requirements.txt" "frontend\dist\index.html" "frontend\package.json") do (
    if exist "%BASE%\%%~f" (
        echo  [OK] %%~f
        echo  [OK] %%~f >> "%LOG%"
    ) else (
        echo  [XX] %%~f  NO encontrado
        echo  [XX] %%~f  NO encontrado >> "%LOG%"
    )
)

:: ===========================================================================
:: Variables .env
:: ===========================================================================
echo.
echo  === Variables .env ===
echo. >> "%LOG%"
echo  === Variables .env === >> "%LOG%"
if exist "%BASE%\backend\.env" (
    for %%v in (SECRET_KEY DATABASE_URL IA_PROVIDER OLLAMA_BASE_URL OLLAMA_MODEL) do (
        findstr /i "^%%v=" "%BASE%\backend\.env" >nul 2>&1
        if errorlevel 1 (
            echo  [!!] %%v  no definida en .env
            echo  [!!] %%v  no definida en .env >> "%LOG%"
        ) else (
            echo  [OK] %%v  definida
            echo  [OK] %%v  definida >> "%LOG%"
        )
    )
    findstr /i "^SECRET_KEY=cambia_esta" "%BASE%\backend\.env" >nul 2>&1
    if not errorlevel 1 (
        echo  [!!] SECRET_KEY tiene el valor por defecto -- cambiarla es recomendado
        echo  [!!] SECRET_KEY tiene el valor por defecto >> "%LOG%"
    )
) else (
    echo  [XX] backend\.env no existe
    echo  [XX] backend\.env no existe >> "%LOG%"
)

:: ===========================================================================
:: Backend health
:: ===========================================================================
echo.
echo  === Backend ===
echo. >> "%LOG%"
echo  === Backend === >> "%LOG%"
curl -s --max-time 5 http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 (
    echo  [!!] Backend no responde en puerto 8000 (puede que no este iniciado)
    echo  [!!] Backend no responde en puerto 8000 >> "%LOG%"
) else (
    echo  [OK] Backend respondiendo en http://127.0.0.1:8000
    echo  [OK] Backend respondiendo en http://127.0.0.1:8000 >> "%LOG%"
)

:: ===========================================================================
:: Puertos
:: ===========================================================================
echo.
echo  === Puertos ===
echo. >> "%LOG%"
echo  === Puertos === >> "%LOG%"
netstat -aon 2>nul | findstr ":8000 " >nul 2>&1
if errorlevel 1 (
    echo  Puerto 8000: libre
    echo  Puerto 8000: libre >> "%LOG%"
) else (
    echo  Puerto 8000: en uso
    echo  Puerto 8000: en uso >> "%LOG%"
)
netstat -aon 2>nul | findstr ":11434 " >nul 2>&1
if errorlevel 1 (
    echo  Puerto 11434: libre
    echo  Puerto 11434: libre >> "%LOG%"
) else (
    echo  Puerto 11434: en uso (Ollama activo)
    echo  Puerto 11434: en uso (Ollama activo) >> "%LOG%"
)

:: ===========================================================================
:: Resumen
:: ===========================================================================
echo.
echo  ============================================================
echo   Diagnostico completo guardado en: verificacion.log
echo  ============================================================
echo.
pause
