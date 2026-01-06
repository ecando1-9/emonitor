@echo off
REM Run eMonitor with the correct Python environment
cd /d "C:\Users\yuvak\Downloads\ecantech_esolutions\projects"
call .venv\Scripts\activate.bat
cd emoniter
python main.py
pause
