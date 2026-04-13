@echo off
echo.
echo  FRAME Cinema Blog - Starting...
echo.

cd /d "%~dp0backend"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo Installing dependencies...
pip install flask flask-cors werkzeug -q

echo.
echo  Backend starting at http://localhost:5000
echo  Admin login: admin / frame2025
echo  Open http://localhost:5000 in your browser
echo.

python app.py
pause
