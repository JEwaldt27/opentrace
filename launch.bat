@echo off
title OpenTrace
echo =======================================
echo   OpenTrace - Local Server
echo =======================================
echo.

REM Check if Python is installed
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

REM Show Python version for confirmation
echo Python found:
python --version
echo.

REM Install dependencies if needed
echo Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies - this may take a minute on first run...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install one or more dependencies.
        echo Check the output above for details.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo Dependencies installed successfully.
    echo.
)

echo All dependencies OK.
echo.
echo Starting OpenTrace server...
echo Open your browser to: http://localhost:8000
echo Press Ctrl+C to stop the server.
echo.

REM Open browser after a short delay
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

REM Start the server
python -m uvicorn main:app --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause
