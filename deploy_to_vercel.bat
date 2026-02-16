@echo off
setlocal EnableDelayedExpansion

echo ==========================================
echo      Vanna AI - Complete Deployment
echo ==========================================

REM 0. Load .env variables
echo [0/5] Loading environment variables...
if exist .env (
    for /f "usebackq tokens=1* delims==" %%a in (".env") do (
        set "key=%%a"
        set "val=%%b"
        REM Trim whitespace if needed, though batch is tricky
        if "!key!"=="GEMINI_API_KEY" set GEMINI_API_KEY=!val!
        if "!key!"=="OPENROUTER_API_KEY" set OPENROUTER_API_KEY=!val!
        if "!key!"=="SUPABASE_CONNECTION_STRING" set SUPABASE_CONNECTION_STRING=!val!
        if "!key!"=="JWT_SECRET" set JWT_SECRET=!val!
    )
    echo Loaded variables from .env
) else (
    echo Warning: .env file not found. Ensure variables are set in your environment.
)

REM 1. Git Operations
echo.
echo [1/5] Setting up Git...
if not exist .git (
    git init
    git branch -M main
)

echo Adding remote...
git remote remove origin >nul 2>&1
REM REPLACE THIS WITH YOUR REPO URL IF DIFFERENT
git remote add origin https://github.com/razemate/KR-CHAT-WITH-DATA.git

echo Committing files...
git add .
git commit -m "Deploy Vanna Monorepo App to Vercel (Production Hardened)"

echo Pushing to GitHub...
git push -u origin main
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Git push failed. Please check your credentials or repo URL.
    echo Continuing with Vercel deployment...
)

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

REM 4. Handle Database Password & JWT
echo.
echo [4/5] Database & Auth Configuration

if "%SUPABASE_CONNECTION_STRING%"=="" (
    echo Error: SUPABASE_CONNECTION_STRING environment variable is not set.
    pause
    exit /b 1
)

echo Adding SUPABASE_CONNECTION_STRING...
echo %SUPABASE_CONNECTION_STRING% | vercel env add SUPABASE_CONNECTION_STRING production >nul 2>&1
if %ERRORLEVEL% EQU 0 ( echo   - Success ) else ( echo   - Already exists or error )

if not "%JWT_SECRET%"=="" (
    echo Adding JWT_SECRET...
    echo %JWT_SECRET% | vercel env add JWT_SECRET production >nul 2>&1
)

REM 5. Deploy
echo.
echo [5/5] Deploying to Production...
call vercel deploy --prod

echo.
echo ==========================================
echo      Deployment Complete!
echo ==========================================
pause
