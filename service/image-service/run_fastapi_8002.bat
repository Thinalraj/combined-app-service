@echo off
setlocal
cd /d "%~dp0"
echo Starting Vision Service FastAPI backend on port 8003...
python -m uvicorn api:app --host 0.0.0.0 --port 8003
pause
