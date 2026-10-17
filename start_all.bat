@echo off
setlocal
rem FINISH-01: explicit mode in system_assets\runtime.json; no hidden simulator flag.
cd /d "%~dp0"
set "TARGET_IP=%~1"
if "%TARGET_IP%"=="" set "TARGET_IP=127.0.0.1"
python "%~dp0launch_stack.py" --kiosk --target "%TARGET_IP%"
set "LAUNCH_RESULT=%ERRORLEVEL%"
if not "%LAUNCH_RESULT%"=="0" pause
exit /b %LAUNCH_RESULT%
