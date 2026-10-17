@echo off
setlocal
rem FINISH-01: explicit mode in system_assets\runtime.json; no hidden simulator flag.
cd /d "%~dp0"
python "%~dp0launch_stack.py"
set "LAUNCH_RESULT=%ERRORLEVEL%"
if not "%LAUNCH_RESULT%"=="0" pause
exit /b %LAUNCH_RESULT%
