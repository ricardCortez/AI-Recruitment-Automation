@echo off
chcp 65001 >nul
title Compilando instalador Sistema CV...

set "ISS=%~dp0SistemaCV.iss"
set "ISCC_DEFAULT=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "ISCC_ALT=C:\Program Files\Inno Setup 6\ISCC.exe"

echo.
echo  ============================================================
echo   Compilador de instalador - Sistema CV RRHH
echo  ============================================================
echo.

:: ---- Buscar Inno Setup ISCC.exe -----------------------------------------
set "ISCC="
if exist "%ISCC_DEFAULT%" set "ISCC=%ISCC_DEFAULT%"
if "%ISCC%"=="" if exist "%ISCC_ALT%" set "ISCC=%ISCC_ALT%"
if "%ISCC%"=="" where ISCC >nul 2>&1 && set "ISCC=ISCC"

if "%ISCC%"=="" (
    echo  [ERROR] Inno Setup 6 no encontrado.
    echo.
    echo  Descargalo desde https://jrsoftware.org/isdl.php
    echo  e instala en la ruta por defecto:
    echo    %ISCC_DEFAULT%
    echo.
    pause
    exit /b 1
)

echo  [OK] Inno Setup encontrado: %ISCC%
echo  [*]  Compilando %ISS%...
echo.

:: ---- Crear carpeta de salida si no existe --------------------------------
if not exist "%~dp0..\dist_instalador" mkdir "%~dp0..\dist_instalador"

:: ---- Compilar ------------------------------------------------------------
"%ISCC%" "%ISS%"

if errorlevel 1 (
    echo.
    echo  [ERROR] La compilacion fallo. Revisa los errores de arriba.
    echo.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   Compilacion exitosa!
echo   Archivo generado: ..\dist_instalador\SistemaCV_Instalador.exe
echo  ============================================================
echo.

:: Abrir la carpeta con el .exe generado
start "" "%~dp0..\dist_instalador"

pause
