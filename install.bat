@echo off
title Auto-Clipper Installer
color 0A
echo.
echo  ============================================
echo    Auto-Clipper - One-Click Installer
echo  ============================================
echo.

:: ──────────────────────────────────────────────
:: Step 1: Check for Python
:: ──────────────────────────────────────────────
echo [1/6] Checking for Python...
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

:: ──────────────────────────────────────────────
:: Step 2: Check for FFmpeg
:: ──────────────────────────────────────────────
echo.
echo [2/6] Checking for FFmpeg...
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

:: ──────────────────────────────────────────────
:: Step 3: Create virtual environment
:: ──────────────────────────────────────────────
echo.
echo [3/6] Setting up Python environment...
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

call venv\Scripts\activate.bat

:: ──────────────────────────────────────────────
:: Step 4: Install core dependencies
:: ──────────────────────────────────────────────
echo.
echo [4/6] Installing core dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  Failed to install core dependencies.
    pause
    exit /b 1
)
:: Always upgrade yt-dlp: Twitch ships API changes constantly and stale
:: yt-dlp is the #1 cause of "can't download VOD" reports.
pip install --upgrade yt-dlp --quiet
echo  Core dependencies installed

:: ──────────────────────────────────────────────
:: Step 5: Optional enhanced features
:: ──────────────────────────────────────────────
echo.
echo [5/6] Optional features...
echo.
echo  Auto-Clipper supports optional enhanced features.
echo  You can install them now or skip and add them later.
echo.

set OPT_INSTALLED=
set OPT_SKIPPED=

:: --- Feature: openWakeWord ---
echo  ┌──────────────────────────────────────────────┐
echo  │  [A] openWakeWord - Real-Time Voice Triggers │
echo  │      Detects 'clip that' in real-time with   │
echo  │      near-zero CPU usage. Great for live      │
echo  │      streaming and always-on monitoring.      │
echo  └──────────────────────────────────────────────┘
set /p INSTALL_WAKE="  Install openWakeWord? [y/N] "
echo.

:: --- Feature: WhisperX ---
echo  ┌──────────────────────────────────────────────┐
echo  │  [B] WhisperX - Precise Word Timestamps      │
echo  │      Adds phoneme-level alignment for more   │
echo  │      accurate clip trigger detection.         │
echo  │      Requires ~500MB additional download.     │
echo  └──────────────────────────────────────────────┘
set /p INSTALL_WHISPERX="  Install WhisperX? [y/N] "
echo.

:: --- Feature: librosa ---
echo  ┌──────────────────────────────────────────────┐
echo  │  [C] librosa - Audio Waveform Visualization  │
echo  │      Generates visual waveforms on the clip   │
echo  │      timeline. Helps identify loud moments.   │
echo  └──────────────────────────────────────────────┘
set /p INSTALL_LIBROSA="  Install librosa (waveform viz)? [y/N] "
echo.

:: Install selected optional features
if /i "%INSTALL_WAKE%"=="y" (
    echo  Installing openWakeWord...
    pip install openwakeword --quiet 2>nul
    if %errorlevel% equ 0 (
        set "OPT_INSTALLED=%OPT_INSTALLED% openWakeWord"
        echo  openWakeWord installed
    ) else (
        echo  WARNING: openWakeWord install failed
        set "OPT_SKIPPED=%OPT_SKIPPED% openWakeWord(failed)"
    )
) else (
    set "OPT_SKIPPED=%OPT_SKIPPED% openWakeWord"
)

if /i "%INSTALL_WHISPERX%"=="y" (
    echo  Installing WhisperX...
    pip install whisperx --quiet 2>nul
    if %errorlevel% equ 0 (
        set "OPT_INSTALLED=%OPT_INSTALLED% WhisperX"
        echo  WhisperX installed
    ) else (
        echo  WARNING: WhisperX install failed
        set "OPT_SKIPPED=%OPT_SKIPPED% WhisperX(failed)"
    )
) else (
    set "OPT_SKIPPED=%OPT_SKIPPED% WhisperX"
)

if /i "%INSTALL_LIBROSA%"=="y" (
    echo  Installing librosa...
    pip install librosa --quiet 2>nul
    if %errorlevel% equ 0 (
        set "OPT_INSTALLED=%OPT_INSTALLED% librosa"
        echo  librosa installed
    ) else (
        echo  WARNING: librosa install failed
        set "OPT_SKIPPED=%OPT_SKIPPED% librosa(failed)"
    )
) else (
    set "OPT_SKIPPED=%OPT_SKIPPED% librosa"
)

:: ──────────────────────────────────────────────
:: Step 6: Verify installation
:: ──────────────────────────────────────────────
echo.
echo [6/6] Verifying installation...

:: Check core features
python -c "import faster_whisper; print('  faster-whisper: OK (clip trigger detection)')" 2>nul
if %errorlevel% neq 0 (
    python -c "import whisper; print('  openai-whisper: OK (clip trigger detection, slower fallback)')" 2>nul
    if %errorlevel% neq 0 (
        echo  WARNING: No speech-to-text backend found
        echo           'Clip That' voice detection will not work
    )
)

python -c "import flask; print('  Flask: OK (web UI)')" 2>nul
python -c "import yt_dlp; print('  yt-dlp: OK (VOD downloads)')" 2>nul
python -c "import cv2; print('  OpenCV: OK (video processing)')" 2>nul
python -c "import ultralytics; print('  YOLO/ultralytics: OK (object detection)')" 2>nul

:: Check optional features
python -c "import openwakeword; print('  openWakeWord: OK (real-time voice triggers)')" 2>nul
python -c "import whisperx; print('  WhisperX: OK (precise word timestamps)')" 2>nul
python -c "import librosa; print('  librosa: OK (audio waveform visualization)')" 2>nul

:: Check FFmpeg hardware acceleration
echo.
ffmpeg -hwaccels 2>nul | findstr /i "cuda nvenc" >nul 2>&1
if %errorlevel% equ 0 (
    echo  FFmpeg HW Accel: NVENC/CUDA (NVIDIA)
) else (
    ffmpeg -hwaccels 2>nul | findstr /i "qsv" >nul 2>&1
    if %errorlevel% equ 0 (
        echo  FFmpeg HW Accel: Quick Sync (Intel)
    ) else (
        ffmpeg -hwaccels 2>nul | findstr /i "d3d11va dxva2" >nul 2>&1
        if %errorlevel% equ 0 (
            echo  FFmpeg HW Accel: DirectX Video Acceleration
        )
    )
)

:: ──────────────────────────────────────────────
:: Summary
:: ──────────────────────────────────────────────
echo.
echo  ============================================
echo    Installation Complete!
echo  ============================================
echo.
echo  Core features installed:
echo    - Video analysis (motion, scene, audio)
echo    - 'Clip That' voice trigger detection
echo    - VOD download ^& clip extraction
echo    - Web UI with timeline ^& clip manager
echo    - Keyboard shortcut clipping (Ctrl+Shift+C)
echo    - Watch folder auto-detection
echo.

if defined OPT_INSTALLED (
    echo  Optional features installed:
    echo    %OPT_INSTALLED%
    echo.
)

if defined OPT_SKIPPED (
    echo  Optional features skipped (install later with pip):
    echo    %OPT_SKIPPED%
    echo.
)

echo  To run Auto-Clipper, double-click:  run.bat
echo.
echo  Or open Command Prompt and type:
echo    cd %cd%
echo    venv\Scripts\activate
echo    python app.py
echo.
echo  To add optional features later:
echo    venv\Scripts\activate
echo    pip install openwakeword    # real-time voice triggers
echo    pip install whisperx        # precise word timestamps
echo    pip install librosa         # audio waveform timeline
echo.
pause
