@echo off
chcp 65001 >nul
title Sistema CV - Deteniendo...
echo  Deteniendo Sistema CV...
taskkill /FI "WINDOWTITLE eq Backend CV*"   /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend CV*"  /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Ollama Server*" /F >nul 2>&1
echo  Sistema detenido.
timeout /t 2 /nobreak >nul
exit
