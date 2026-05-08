@echo off
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "F:\anaconda3\python.exe" set "PYTHON_EXE=F:\anaconda3\python.exe"

"%PYTHON_EXE%" -m roselia_mahjong.gui
if errorlevel 1 pause
