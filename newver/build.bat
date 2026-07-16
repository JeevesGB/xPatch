@echo off
echo ========================================
echo     Building xPatch...
echo ========================================

pyinstaller --onefile ^
    --windowed ^
    --name "xPatch" ^
    --icon "../ico.ico" ^
    --add-data "ui;ui" ^
    --add-data "utils;utils" ^
    --add-data "services;services" ^
    --add-data "tool;tool" ^
    --clean ^
    main.py

echo.
echo Build completed!
pause