@echo off
chcp 65001 >nul
title Sistema CV - Deteniendo...

echo.
echo  Deteniendo Sistema CV...
echo.

echo  [1/3] Deteniendo Backend...
taskkill /FI "WINDOWTITLE eq SistemaCV-Backend" /F >nul 2>&1
taskkill /FI "IMAGENAME eq uvicorn.exe" /F >nul 2>&1

echo  [2/3] Limpiando puerto 8000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo  [3/3] Ollama...
set /P "cerrar_ollama=   Detener Ollama tambien? (s/N): "
if /i "%cerrar_ollama%"=="s" (
    taskkill /FI "WINDOWTITLE eq SistemaCV-Ollama" /F >nul 2>&1
    taskkill /FI "IMAGENAME eq ollama.exe" /F >nul 2>&1
    echo  [OK] Ollama detenido.
) else (
    echo  [--] Ollama sigue corriendo.
)

echo.
echo  Sistema detenido.
echo.
timeout /t 2 /nobreak >nul
