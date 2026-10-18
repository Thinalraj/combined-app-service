@echo off
setlocal
cd /d "%~dp0"
set "TARGET_IP=%~1"
if "%TARGET_IP%"=="" set "TARGET_IP=127.0.0.1"
py "%~dp0launch_kiosk.py" --target "%TARGET_IP%"
if errorlevel 1 pause
