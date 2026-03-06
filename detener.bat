@echo off
title Sistema CV - Deteniendo...

echo.
echo [+] Deteniendo Sistema CV...

taskkill /FI "WINDOWTITLE eq Backend-SistemaCV*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend-SistemaCV*" /F >nul 2>&1

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do taskkill /PID %%a /F >nul 2>&1

echo [OK] Servicios detenidos.
echo.
timeout /t 2 /nobreak >nul