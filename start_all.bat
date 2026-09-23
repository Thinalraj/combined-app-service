@echo off
setlocal

cd /d "%~dp0"
set "TARGET_IP=%~1"
if "%TARGET_IP%"=="" set "TARGET_IP=127.0.0.1"
set "VIEW_URL=http://%TARGET_IP%:8080"

where wt.exe >nul 2>&1
if errorlevel 1 (
    echo Windows Terminal (wt.exe) is required for the single-window tabbed launcher.
    echo Install it from the Microsoft Store, then run this file again.
    pause
    exit /b 1
)

echo Starting all services in one Windows Terminal window...
wt.exe -w 0 new-tab --title "Signal 8001" cmd /k "cd /d "%~dp0service\signal-service" && python rest_service.py --simulate" ; ^
    new-tab --title "Weight 8002" cmd /k "cd /d "%~dp0service\weight-service" && python fast-api-mettler.py" ; ^
    new-tab --title "Image 8003" cmd /k "cd /d "%~dp0service\image-service" && python -m uvicorn api:app --host 0.0.0.0 --port 8003" ; ^
    new-tab --title "View 8080" cmd /k "cd /d "%~dp0service\view-service" && python app.py"

timeout /t 5 /nobreak >nul

echo Opening Chrome kiosk at %VIEW_URL%...
start "" chrome --kiosk --start-fullscreen "%VIEW_URL%"

echo Application launched at %VIEW_URL%.
exit /b 0
