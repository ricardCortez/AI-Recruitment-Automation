@echo off
chcp 65001 >nul
title Sistema CV - Deteniendo...

echo.
echo  Deteniendo Sistema CV...
echo.

echo  [1/4] Deteniendo Frontend...
taskkill /FI "WINDOWTITLE eq SistemaCV-Frontend" /F >nul 2>&1

echo  [2/4] Deteniendo Backend...
taskkill /FI "WINDOWTITLE eq SistemaCV-Backend"  /F >nul 2>&1

echo  [3/4] Deteniendo Ollama...
taskkill /FI "WINDOWTITLE eq SistemaCV-Ollama"   /F >nul 2>&1

taskkill /FI "IMAGENAME eq uvicorn.exe" /F >nul 2>&1

echo  [4/4] Limpiando puerto 8000...
for /f "tokens=5" %%a in ('netstat -aon 2^nul ^| findstr ":8000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo  Sistema detenido correctamente.
echo.
timeout /t 2 /nobreak >nul
