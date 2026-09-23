@echo off
setlocal

cd /d "%~dp0"
set "ROOT_DIR=%~dp0"

where wt.exe >nul 2>&1
if not errorlevel 1 goto terminal_found
echo Windows Terminal (wt.exe) is required for the tabbed backend launcher.
echo Install it from the Microsoft Store, then run this file again.
pause
exit /b 1

:terminal_found
echo Starting backend services in one Windows Terminal window...
wt.exe -w 0 new-tab --title "Signal 8001" -d "%ROOT_DIR%service\signal-service" cmd /k python rest_service.py --simulate ; new-tab --title "Weight 8002" -d "%ROOT_DIR%service\weight-service" cmd /k python fast-api-mettler.py ; new-tab --title "Image 8003" -d "%ROOT_DIR%service\image-service" cmd /k python -m uvicorn api:app --host 0.0.0.0 --port 8003

echo Backend services started:
echo Signal: http://127.0.0.1:8001
echo Weight: http://127.0.0.1:8002
echo Image:  http://127.0.0.1:8003
exit /b 0
