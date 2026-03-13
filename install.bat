@echo off
title Auto-Clipper Installer
color 0A
echo.
echo  ============================================
echo    Auto-Clipper - One-Click Installer
echo  ============================================
echo.

:: Check for Python
echo [1/4] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  Python is NOT installed.
    echo  Opening the Python download page...
    echo.
    echo  IMPORTANT: When installing, CHECK THE BOX that says
    echo  "Add python.exe to PATH" at the bottom of the installer!
    echo.
    start https://www.python.org/downloads/
    echo  After installing Python, close this window and run install.bat again.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo  Found Python %%v

:: Check for FFmpeg
echo.
echo [2/4] Checking for FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  FFmpeg is NOT installed.
    echo.
    echo  Downloading FFmpeg automatically...

    :: Try to download FFmpeg using PowerShell
    echo  This may take a minute...
    powershell -Command "& { $ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile '%TEMP%\ffmpeg.zip' -UseBasicParsing } catch { Write-Host 'Download failed'; exit 1 } }"

    if %errorlevel% neq 0 (
        echo.
        echo  Automatic download failed. Please install FFmpeg manually:
        echo  1. Go to: https://github.com/BtbN/FFmpeg-Builds/releases
        echo  2. Download: ffmpeg-master-latest-win64-gpl.zip
        echo  3. Extract it and add the bin folder to your PATH
        echo.
        start https://github.com/BtbN/FFmpeg-Builds/releases
        pause
        exit /b 1
    )

    echo  Extracting FFmpeg...
    powershell -Command "Expand-Archive -Path '%TEMP%\ffmpeg.zip' -DestinationPath '%LOCALAPPDATA%\ffmpeg' -Force"

    :: Find the bin folder
    for /d %%d in ("%LOCALAPPDATA%\ffmpeg\ffmpeg-*") do set FFMPEG_BIN=%%d\bin

    if not defined FFMPEG_BIN (
        echo  Could not find FFmpeg bin folder after extraction.
        pause
        exit /b 1
    )

    :: Add to user PATH
    echo  Adding FFmpeg to PATH...
    powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%FFMPEG_BIN%', 'User')"
    set "PATH=%PATH%;%FFMPEG_BIN%"

    echo  FFmpeg installed!
    del "%TEMP%\ffmpeg.zip" 2>nul
) else (
    echo  Found FFmpeg
)

:: Create virtual environment and install dependencies
echo.
echo [3/4] Setting up Python environment...
if not exist "venv" (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  Created virtual environment
) else (
    echo  Virtual environment already exists
)

echo.
echo [4/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo    Installation Complete!
echo  ============================================
echo.
echo  To run Auto-Clipper, double-click:  run.bat
echo.
echo  Or open Command Prompt and type:
echo    cd %cd%
echo    venv\Scripts\activate
echo    python app.py
echo.
pause
