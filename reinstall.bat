@echo off
REM Auto-Clipper — Clean Reinstall (Windows)
REM
REM Wipes the old repo, re-clones fresh, preserves your user data:
REM   downloads\   library\   sessions\   uploads\
REM   static\clips\   static\thumbnails\
REM
REM Usage: reinstall.bat

setlocal enabledelayedexpansion

set REPO_URL=https://github.com/bendawg2010/Auto-clipper.git
set REPO_NAME=Auto-clipper
if "%AUTOCLIPPER_BRANCH%"=="" (set BRANCH=claude/twitch-clip-analyzer-MPT08) else (set BRANCH=%AUTOCLIPPER_BRANCH%)

echo.
echo   ================================================
echo     Auto-Clipper - Clean Reinstall
echo     (preserves VODs, clips, sessions, library)
echo   ================================================
echo.

REM If we're inside the repo, step up to the parent.
if exist .git if exist app.py (
    cd ..
)

set PARENT=%CD%
set TARGET=%PARENT%\%REPO_NAME%
for /f %%i in ('powershell -NoProfile -Command "[int][double]::Parse((Get-Date -UFormat %%s))"') do set TS=%%i
set BACKUP=%PARENT%\.autoclipper-preserve-%TS%

REM ==============================================
REM Step 1: Back up user data
REM ==============================================
if exist "%TARGET%" (
    echo [1/5] Backing up your VOD library + clips to
    echo       %BACKUP%
    mkdir "%BACKUP%"

    for %%D in (downloads library sessions uploads) do (
        if exist "%TARGET%\%%D" (
            echo       - %%D\
            move "%TARGET%\%%D" "%BACKUP%\%%D" >NUL
        )
    )

    if exist "%TARGET%\static\clips" (
        echo       - static\clips\
        mkdir "%BACKUP%\static" 2>NUL
        move "%TARGET%\static\clips" "%BACKUP%\static\clips" >NUL
    )
    if exist "%TARGET%\static\thumbnails" (
        echo       - static\thumbnails\
        mkdir "%BACKUP%\static" 2>NUL
        move "%TARGET%\static\thumbnails" "%BACKUP%\static\thumbnails" >NUL
    )

    for %%F in (.env config.json user-profiles.json best.pt arc_raiders_best.pt) do (
        if exist "%TARGET%\%%F" (
            echo       - %%F
            move "%TARGET%\%%F" "%BACKUP%\%%F" >NUL
        )
    )
) else (
    echo [1/5] No existing install found - nothing to back up.
)

REM ==============================================
REM Step 2: Delete the old repo
REM ==============================================
if exist "%TARGET%" (
    echo [2/5] Removing old install at %TARGET%
    rmdir /S /Q "%TARGET%"
) else (
    echo [2/5] Nothing to remove.
)

REM ==============================================
REM Step 3: Fresh clone
REM ==============================================
echo [3/5] Cloning fresh copy from %REPO_URL% (branch: %BRANCH%)
git clone --branch %BRANCH% %REPO_URL% "%TARGET%"
if errorlevel 1 goto :fail

REM ==============================================
REM Step 4: Restore user data
REM ==============================================
if exist "%BACKUP%" (
    echo [4/5] Restoring your VOD library + clips

    for %%D in (downloads library sessions uploads) do (
        if exist "%BACKUP%\%%D" (
            echo       - %%D\
            if exist "%TARGET%\%%D" rmdir /S /Q "%TARGET%\%%D"
            move "%BACKUP%\%%D" "%TARGET%\%%D" >NUL
        )
    )

    if exist "%BACKUP%\static\clips" (
        echo       - static\clips\
        if exist "%TARGET%\static\clips" rmdir /S /Q "%TARGET%\static\clips"
        mkdir "%TARGET%\static" 2>NUL
        move "%BACKUP%\static\clips" "%TARGET%\static\clips" >NUL
    )
    if exist "%BACKUP%\static\thumbnails" (
        echo       - static\thumbnails\
        if exist "%TARGET%\static\thumbnails" rmdir /S /Q "%TARGET%\static\thumbnails"
        mkdir "%TARGET%\static" 2>NUL
        move "%BACKUP%\static\thumbnails" "%TARGET%\static\thumbnails" >NUL
    )

    for %%F in (.env config.json user-profiles.json best.pt arc_raiders_best.pt) do (
        if exist "%BACKUP%\%%F" (
            echo       - %%F
            move "%BACKUP%\%%F" "%TARGET%\%%F" >NUL
        )
    )

    REM Clean up empty backup dir
    rmdir "%BACKUP%\static" 2>NUL
    rmdir "%BACKUP%" 2>NUL
) else (
    echo [4/5] No backup to restore - fresh install.
)

REM ==============================================
REM Step 5: Install + launch
REM ==============================================
echo [5/5] Running installer...
cd "%TARGET%"
call install.bat
if errorlevel 1 goto :fail

echo.
echo   ================================================
echo     [OK] Reinstall complete
echo     Launching Auto-Clipper...
echo   ================================================
echo.

call run.bat
goto :eof

:fail
echo.
echo   [ERROR] Reinstall failed. Your data is safe in:
echo     %BACKUP%
exit /b 1
