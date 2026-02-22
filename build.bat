@echo off
echo ===============================
echo Building xPatch EXE
echo ===============================
echo.

REM Ensure pyinstaller is available
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
)

echo.
echo Cleaning previous builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del xpatch.spec 2>nul

echo.
echo Building EXE...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "xPatch" ^
    --icon "%~dp0ico.ico" ^
    --add-data "%~dp0tool\xdelta3.exe;tool" ^
    --add-data "%~dp0theme.qss;." ^
    "%~dp0gui.py"

echo.
echo Build complete.
echo Output EXE is in the dist folder.
pause