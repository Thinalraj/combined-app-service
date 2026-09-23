@echo off
setlocal

set "TARGET_IP=%~1"
if "%TARGET_IP%"=="" set "TARGET_IP=127.0.0.1"
set "VIEW_URL=http://%TARGET_IP%:8080"
set "CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME_EXE%" goto chrome_found
set "CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME_EXE%" goto chrome_found
set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME_EXE%" goto chrome_found

echo Chrome executable was not found.
echo Checked the standard Google Chrome installation locations.
pause
exit /b 1

:chrome_found
set "KIOSK_PROFILE=%LOCALAPPDATA%\CombinedAppKioskProfile"

echo Opening Chrome in full-screen kiosk mode at %VIEW_URL%...
start "" "%CHROME_EXE%" --kiosk --start-fullscreen --new-window --no-first-run --disable-session-crashed-bubble --user-data-dir="%KIOSK_PROFILE%" "%VIEW_URL%"
exit /b 0
