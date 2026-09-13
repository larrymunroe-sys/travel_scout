@echo off
REM Travel Scout — Reimport Itineraries from Local Backup Folder
setlocal enabledelayedexpansion

echo =========================================================
echo   Travel Scout — Reimport from Local Backup Folder
echo =========================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."

echo Current directory: %CD%
echo Restoring itineraries from newest local backup in backups\local...

python scout/backup.py --action restore --folder backups/local

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Reimport complete! Trips, stops, and deletion memory restored.
) else (
    echo.
    echo [ERROR] Reimport failed.
)

echo.
pause
