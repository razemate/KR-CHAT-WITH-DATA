@echo off
echo ==========================================
echo      Vanna AI - Update & Deploy
echo ==========================================

REM 1. Git Operations
echo [1/2] Updating GitHub...
git add .
git commit -m "Update Vanna App Code and Configuration"
git push origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Warning: Git push might have failed (or nothing to push).
    echo Checking Vercel deployment...
)

REM 2. Vercel Deployment
echo.
echo [2/2] Deploying to Vercel Production...
call vercel deploy --prod

echo.
echo ==========================================
echo      Update Complete!
echo ==========================================
pause
