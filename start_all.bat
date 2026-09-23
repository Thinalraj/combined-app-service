@echo off
setlocal

cd /d "%~dp0"

echo Starting Signal Service on port 8001...
start "Signal Service" cmd /k "cd /d "%~dp0service\signal-service" && python rest_service.py --simulate"

echo Starting Weight Service on port 8002...
start "Weight Service" cmd /k "cd /d "%~dp0service\weight-service" && python fast-api-mettler.py"

echo Starting Image Service on port 8003...
start "Image Service" cmd /k "cd /d "%~dp0service\image-service" && python -m uvicorn api:app --host 0.0.0.0 --port 8003"

timeout /t 3 /nobreak >nul

echo Starting View Service on port 8080...
start "View Service" cmd /k "cd /d "%~dp0service\view-service" && python app.py"

echo.
echo All services started.
echo View service: http://127.0.0.1:8080
echo Signal service: http://127.0.0.1:8001
echo Weight service: http://127.0.0.1:8002
echo Image service: http://127.0.0.1:8003
pause
