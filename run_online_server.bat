@echo off
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "F:\anaconda3\python.exe" set "PYTHON_EXE=F:\anaconda3\python.exe"

"%PYTHON_EXE%" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
pause
