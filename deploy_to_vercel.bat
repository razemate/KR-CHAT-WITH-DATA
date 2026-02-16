@echo off
setlocal EnableDelayedExpansion

echo ==========================================
echo      Vanna AI - Complete Deployment
echo ==========================================

REM 1. Git Operations
echo [1/5] Setting up Git...
if not exist .git (
    git init
    git branch -M main
)

REM echo Adding remote...
REM git remote remove origin >nul 2>&1
REM git remote add origin https://github.com/razemate/KR-CHAT-WITH-DATA.git

REM echo Committing files...
REM git add .
REM git commit -m "Deploy Vanna Monorepo App to Vercel"

REM echo Pushing to GitHub...
REM git push -u origin main
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Warning: Git push failed. You might need to sign in or pull changes first.
REM     echo Continuing with Vercel deployment...
REM )

REM 2. Link Project
echo.
echo [2/5] Linking Project to Vercel...
call vercel link --yes
if %ERRORLEVEL% NEQ 0 (
    echo Error: Vercel CLI failed. Please ensure 'vercel' is installed and you are logged in.
    pause
    exit /b %ERRORLEVEL%
)

REM 3. Add API Keys
echo.
echo [3/5] Configuring Environment Variables...

REM Check for required environment variables
if "%GEMINI_API_KEY%"=="" (
    echo Error: GEMINI_API_KEY environment variable is not set.
    pause
    exit /b 1
)
if "%OPENROUTER_API_KEY%"=="" (
    echo Error: OPENROUTER_API_KEY environment variable is not set.
    pause
    exit /b 1
)

echo Adding GEMINI_API_KEY...
echo %GEMINI_API_KEY% | vercel env add GEMINI_API_KEY production >nul 2>&1
if %ERRORLEVEL% EQU 0 ( echo   - Success ) else ( echo   - Already exists or error )

echo Adding OPENROUTER_API_KEY...
echo %OPENROUTER_API_KEY% | vercel env add OPENROUTER_API_KEY production >nul 2>&1
if %ERRORLEVEL% EQU 0 ( echo   - Success ) else ( echo   - Already exists or error )

REM 4. Handle Database Password
echo.
echo [4/5] Database Configuration

if "%SUPABASE_CONNECTION_STRING%"=="" (
    echo Error: SUPABASE_CONNECTION_STRING environment variable is not set.
    pause
    exit /b 1
)

echo Adding SUPABASE_CONNECTION_STRING...
echo %SUPABASE_CONNECTION_STRING% | vercel env add SUPABASE_CONNECTION_STRING production >nul 2>&1
if %ERRORLEVEL% EQU 0 ( echo   - Success ) else ( echo   - Already exists or error )

REM 5. Deploy
echo.
echo [5/5] Deploying to Production...
call vercel deploy --prod

echo.
echo ==========================================
echo      Deployment Complete!
echo ==========================================
pause
