@echo off
cd /d "%~dp0"

echo Starting Mettler FastAPI backend...
start "ScaleBackend" cmd /k python fast-api-mettler.py

timeout /t 2 /nobreak >nul

echo Starting Weight UI frontend...
start "ScaleFrontend" cmd /k python test-ui-weight.py

echo Both servers started.
exit /b
