@echo off
echo ===================================================
echo          eMonitor Build Script (PyInstaller)
echo ===================================================
echo.

REM Activate Virtual Environment (Parent Directory)
if exist "..\.venv\Scripts\activate.bat" (
    echo Activating virtual environment from parent folder...
    call "..\.venv\Scripts\activate.bat"
) else (
    if exist ".venv\Scripts\activate.bat" (
        echo Activating virtual environment from current folder...
        call ".venv\Scripts\activate.bat"
    ) else (
        echo WARNING: .venv not found in parent or current dir.
        echo Please ensure Python is installed and valid.
    )
)

REM Install PyInstaller if not present
echo Checking dependencies...
pip install pyinstaller --upgrade
pip install -r requirements.txt

REM Convert icon.png to icon.ico for PyInstaller
echo Converting icon.png to icon.ico...
python -c "from PIL import Image; img = Image.open('icon.png'); img.save('icon.ico', format='ICO', sizes=[(256, 256)])"

echo.
echo Cleaning previous builds...
rmdir /s /q build
rmdir /s /q dist
del /q *.spec

echo.
echo Building eMonitor executable...
echo This process may take a few minutes.
echo.

REM Build Command
REM --noconsole: Hides the terminal window (GUI mode)
REM --onefile: Bundles everything into a single .exe
REM --icon: Sets the application icon (must be .ico)
REM --name: Name of the output file
REM --add-data: Include necessary assets (icon.png for tray)
REM --hidden-import: Ensure dynamic imports are caught

pyinstaller --noconsole --onefile ^
    --name="eMonitor" ^
    --icon="icon.ico" ^
    --add-data "icon.png;." ^
    --hidden-import="pystray" ^
    --hidden-import="PIL" ^
    --hidden-import="cv2" ^
    --hidden-import="supabase" ^
    --hidden-import="postgrest" ^
    --hidden-import="realtime" ^
    --hidden-import="gotrue" ^
    --hidden-import="storage3" ^
    --hidden-import="win32timezone" ^
    --clean ^
    main.py

echo.
REM Clean up generated ico
del icon.ico

if exist "dist\eMonitor.exe" (
    echo ===================================================
    echo BUILD SUCCESSFUL!
    echo ===================================================
    echo.
    echo Your executable is located at:
    echo    %CD%\dist\eMonitor.exe
    echo.
    echo You can move this file anywhere.
) else (
    echo ===================================================
    echo BUILD FAILED. Check the error messages above.
    echo ===================================================
)

pause
