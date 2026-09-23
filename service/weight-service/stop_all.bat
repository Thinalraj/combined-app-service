@echo off

echo Stopping Scale Backend...
taskkill /FI "WINDOWTITLE eq ScaleBackend*" /T

echo Stopping Scale Frontend...
taskkill /FI "WINDOWTITLE eq ScaleFrontend*" /T

echo Servers stopped.
