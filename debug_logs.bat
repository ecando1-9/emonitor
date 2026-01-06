@echo off
set "LOG_DIR=%APPDATA%\eMonitor\app_data"
set "LOG_FILE=%LOG_DIR%\emoniter.log"

echo ==================================================
echo       eMonitor Log File Debugger
echo ==================================================
echo.
echo EXPECTED LOCATION: %LOG_FILE%
echo.

if exist "%LOG_FILE%" (
    echo [OK] Log file FOUND!
    echo.
    echo --- LAST 20 LINES OF LOG ---
    powershell -Command "Get-Content '%LOG_FILE%' -Tail 20"
    echo ---------------------------
    echo.
    echo Please look at the lines above for any "ERROR" or "CRITICAL".
) else (
    echo [ERROR] Log file NOT FOUND at expected location.
    echo.
    echo This means either:
    echo 1. You are running an OLD version of eMonitor.exe (before the fix).
    echo 2. The app hasn't started correctly yet.
    echo.
    echo Checking old location (next to exe)...
    if exist "app_data\emoniter.log" (
        echo [WARNING] Found log in OLD location: app_data\emoniter.log
        echo This confirms you are running an OLD build. Please rebuild.
    ) else (
        echo [ERROR] No logs found anywhere.
    )
)

pause
