@echo off
setlocal

set "TARGET_IP=%~1"
if "%TARGET_IP%"=="" set "TARGET_IP=127.0.0.1"
set "VIEW_URL=http://%TARGET_IP%:8080"

echo Opening Chrome in full-screen kiosk mode at %VIEW_URL%...
start "" chrome --kiosk --start-fullscreen "%VIEW_URL%"
exit /b 0
