@echo off
REM Rosetta Frontend - Quick Start Script for Windows

echo ================================
echo   Rosetta Frontend Setup
echo ================================
echo.

REM Check Node.js version
node -v >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

echo OK Node.js version: 
node -v
echo.

REM Check if pnpm is installed
pnpm -v >nul 2>&1
if errorlevel 1 (
    echo WARNING: pnpm not found. Installing pnpm...
    npm install -g pnpm
)

echo OK pnpm version:
pnpm -v
echo.

REM Navigate to frontend directory
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Install dependencies
echo Installing dependencies...
call pnpm install

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo OK Dependencies installed successfully!
echo.

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file...
    (
        echo # API Configuration
        echo API_BASE_URL=http://localhost:8000/api
        echo.
        echo # Nuxt Configuration
        echo NUXT_PUBLIC_API_BASE=http://localhost:8000/api
    ) > .env
    echo OK .env file created
) else (
    echo OK .env file already exists
)

echo.
echo ================================
echo   Setup Complete!
echo ================================
echo.
echo Next steps:
echo   1. Make sure backend is running: http://localhost:8000
echo   2. Start dev server: pnpm dev
echo   3. Visit OOBE: http://localhost:3000/oobe
echo   4. Complete installation wizard
echo.
echo Starting development server...
echo.

call pnpm dev

pause
