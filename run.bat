@echo off
title Auto-Clipper
color 0A
echo.
echo  Starting Auto-Clipper...
echo.

:: Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo  Not installed yet! Run install.bat first.
    pause
    exit /b 1
)

:: Activate and run
call venv\Scripts\activate.bat

:: Preflight: ffmpeg check (silent pass if present)
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] ffmpeg not found on PATH. VOD download + clip extraction will fail.
    echo       Run install.bat again to auto-install it.
    echo.
)

:: Keep yt-dlp fresh - Twitch breaks its parsing monthly
python -m pip install --upgrade yt-dlp --quiet >nul 2>&1

:: Start server in background
start /B python app.py

:: Wait for server to bind the port
echo  Waiting for server...
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://localhost:8080/ >nul 2>&1
if errorlevel 1 goto wait_loop
echo  Server ready!
start http://localhost:8080

:: Keep window open while server runs
:keep_alive
timeout /t 5 /nobreak >nul
goto keep_alive
