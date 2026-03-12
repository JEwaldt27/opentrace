@echo off
title OpenTrace - Build
echo =======================================
echo   OpenTrace - PyInstaller Build
echo =======================================
echo.

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Make sure Python 3.10+ is installed and on PATH.
    pause
    exit /b 1
)

REM Install/upgrade PyInstaller
echo Installing PyInstaller...
pip install --upgrade pyinstaller
echo.

REM Clean previous build
if exist dist\OpenTrace rmdir /s /q dist\OpenTrace
if exist build rmdir /s /q build

echo Building OpenTrace...
echo.

pyinstaller ^
  --onedir ^
  --name OpenTrace ^
  --add-data "static;static" ^
  --collect-all cv2 ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import fastapi ^
  --hidden-import multipart ^
  --noconfirm ^
  main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed. Check the output above.
    pause
    exit /b 1
)

REM Clean up PyInstaller intermediates
if exist build rmdir /s /q build
if exist OpenTrace.spec del /q OpenTrace.spec

echo.
echo =======================================
echo   Build complete!
echo   Output: dist\OpenTrace\OpenTrace.exe
echo =======================================
pause
