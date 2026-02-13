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

echo Adding remote...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/razemate/KR-CHAT-WITH-DATA.git

echo Committing files...
git add .
git commit -m "Deploy Vanna Monorepo App to Vercel"

echo Pushing to GitHub...
git push -u origin main
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Git push failed. You might need to sign in or pull changes first.
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

echo Adding GEMINI_API_KEY...
echo AIzaSyDkivE8O1DcigTKTghI6iWbu2E0bMJF7Og | vercel env add GEMINI_API_KEY production >nul 2>&1
if %ERRORLEVEL% EQU 0 ( echo   - Success ) else ( echo   - Already exists or error )

echo Adding OPENROUTER_API_KEY...
echo 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 | vercel env add OPENROUTER_API_KEY production >nul 2>&1
if %ERRORLEVEL% EQU 0 ( echo   - Success ) else ( echo   - Already exists or error )

REM 4. Handle Database Password
echo.
echo [4/5] Database Configuration
echo The Supabase connection string requires your database password.
echo (I cannot access this securely, so please enter it below)
echo.
set /p DB_PASSWORD="Enter your Supabase Database Password: "

if "!DB_PASSWORD!"=="" (
    echo Error: Password cannot be empty.
    pause
    exit /b 1
)

set "CONN_STRING=postgresql://postgres.invhetvtoqibaogwodrx:!DB_PASSWORD!@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

echo Adding SUPABASE_CONNECTION_STRING...
echo !CONN_STRING! | vercel env add SUPABASE_CONNECTION_STRING production >nul 2>&1
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
