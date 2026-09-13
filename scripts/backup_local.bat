@echo off
REM Travel Scout — Local Database & Itinerary Backup Script
setlocal enabledelayedexpansion

echo =========================================================
echo   Travel Scout — Local Database ^& Itinerary Backup
echo =========================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo Current directory: %CD%
echo Backing up database to local folder (backups\local)...

python scout/backup.py --action backup --folder backups/local

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Backup saved to backups\local\ and backups\itineraries_backup.json
) else (
    echo.
    echo [ERROR] Backup failed. Please check Python environment and database.
)

echo.
pause
