@echo off
echo ==========================================
echo      Vanna AI - Dependency Fix & Deploy
echo ==========================================

REM 1. Git Operations
echo [1/2] Updating GitHub with optimized dependencies...
git add .
git commit -m "Fix: Optimize requirements.txt for Vercel 250MB limit"
git push origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Warning: Git push might have failed.
    echo Continuing with Vercel deployment...
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
