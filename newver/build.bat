@echo off
echo Building xPatch v0.1.2...

pyinstaller --onefile ^
    --windowed ^
    --name "xPatch" ^
    --icon "../ico.ico" ^
    --add-data "ui/theme.qss;ui" ^
    --add-data "../tool/xdelta3.exe;tool" ^
    --clean ^
    main.py

echo.
echo Build finished! Check the "dist" folder.
pause