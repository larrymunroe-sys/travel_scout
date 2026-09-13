@echo off
REM Travel Scout — Backup Database Locally and Push Code to Git
setlocal enabledelayedexpansion

echo =========================================================
echo   Travel Scout — Local Backup ^& Git Upload Helper
echo =========================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo [1/3] Backing up database to local folder (backups\local)...
python scout/backup.py --action backup --folder backups/local

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Backup failed. Aborting Git upload to safeguard data.
    pause
    exit /b %ERRORLEVEL%
)

echo [2/3] Staging backup snapshot into Git...
git add backups/itineraries_backup.json

echo [3/3] Ready to commit and push.
set /p commitMsg="Enter commit message (or press ENTER to use default): "
if "!commitMsg!"=="" (
    set commitMsg=Update code and sync latest itinerary backup
)

git commit -m "!commitMsg!"
echo Pushing to origin/main...
git push origin main

echo.
echo [DONE] Upload complete with latest itinerary backup included!
echo.
pause
