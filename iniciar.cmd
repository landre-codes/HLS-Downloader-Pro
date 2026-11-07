@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    start "" py -3 main.py
    exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
    start "" python main.py
    exit /b 0
)

echo Python 3 nao encontrado. Instale Python 3.10+ e tente novamente.
pause
exit /b 1
