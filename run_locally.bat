@echo off
setlocal

echo ==========================================
echo      Vanna AI - Local Development
echo ==========================================

REM 1. Check Prerequisites
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js/npm is not installed or not in PATH.
    pause
    exit /b 1
)

REM 2. Install Backend Dependencies
echo.
echo [1/4] Installing Backend Dependencies...
pip install -r api\requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Pip install failed. Continuing...
)

REM 3. Install Frontend Dependencies
echo.
echo [2/4] Installing Frontend Dependencies...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Npm install failed. Continuing...
)

REM 4. Start Servers
echo.
echo [3/4] Starting Backend Server (Port 8000)...
start "Vanna Backend" cmd /k "uvicorn api.app:app --reload --port 8000"

echo.
echo [4/4] Starting Frontend Server...
echo The app will open in your browser shortly...
start "Vanna Frontend" cmd /c "npm run dev & pause"

REM 5. Open Browser
timeout /t 5 >nul
start http://localhost:5173

echo.
echo ==========================================
echo      App is Running!
echo      Backend: http://localhost:8000
echo      Frontend: http://localhost:5173
echo ==========================================
pause
