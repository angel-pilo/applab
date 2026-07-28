@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Publicar-AppLab-Temporal.ps1"
echo.
pause
