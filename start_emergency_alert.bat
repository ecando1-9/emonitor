@echo off
:: This script triggers emergency alert completely silently
:: No windows, no output, completely stealthy

:: Find the directory where this script is located (the 'emoniter' folder)
SET SCRIPT_DIR=%~dp0

:: Find pythonw.exe (no console window) in the parent directory's .venv
:: (e.g., C:\...projects\.venv\Scripts\pythonw.exe)
SET PYTHONW_EXE=%SCRIPT_DIR%..\\.venv\Scripts\pythonw.exe

:: If pythonw.exe doesn't exist, try python.exe
IF NOT EXIST "%PYTHONW_EXE%" (
    SET PYTHONW_EXE=%SCRIPT_DIR%..\\.venv\Scripts\python.exe
)

:: Find the trigger_emergency.py script in THIS directory
SET TRIGGER_SCRIPT=%SCRIPT_DIR%trigger_emergency.py

:: Run the script completely silently
:: /B = No new window, /MIN = Minimized, >NUL = No output, 2>&1 = Redirect errors
START "" /B "%PYTHONW_EXE%" "%TRIGGER_SCRIPT%" >NUL 2>&1

:: Exit immediately without showing anything
EXIT /B 0