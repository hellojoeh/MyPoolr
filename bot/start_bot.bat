@echo off
echo 🤖 MyPoolr Telegram Bot Setup and Start
echo.

REM Change to bot directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+ and add it to PATH.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo 🔧 Virtual environment not found. Creating one...
    python create_env.py
    if errorlevel 1 (
        echo ❌ Environment setup failed!
        pause
        exit /b 1
    )
    echo.
)

REM Activate virtual environment and run bot
echo 🚀 Starting bot in virtual environment...
call venv\Scripts\activate.bat && venv\Scripts\python.exe simple_run.py

pause