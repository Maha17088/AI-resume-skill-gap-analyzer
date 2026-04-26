@echo off
echo ========================================
echo    SkillSync AI - Setup and Run
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b
)

echo [1/3] Installing Python dependencies...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b
)

echo.
echo [2/3] Dependencies installed successfully!
echo.
echo [3/3] Starting SkillSync AI server...
echo.
echo ========================================
echo   App is running at: http://localhost:5000
echo   Open your browser and go to that URL
echo   Press CTRL+C to stop the server
echo ========================================
echo.
python app.py
pause
