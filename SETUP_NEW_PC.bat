@echo off
chcp 65001 >nul
echo =============================================
echo   EA AUTO MASTER v8.1 - New PC Setup
echo =============================================
echo.

set "HERE=%~dp0"
set "HERE=%HERE:~0,-1%"

echo [1/3] Detecting current folder...
echo   Path: %HERE%
echo.

echo [2/3] Patching all config paths...
python "%HERE%\scripts\patch_paths.py" "%HERE%" auto
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] patch_paths.py not found - manual config required
) else (
    echo [OK] Paths updated
)

echo.
echo [3/3] Setup complete!
echo.
echo   How to start:
echo   - Double-click EA_AUTO_MASTER_v8.0.py
echo   - Or run: python EA_AUTO_MASTER_v8.0.py
echo.
echo   MT4 path setting:
echo   - Open [Settings] tab in the app
echo   - Set terminal.exe path for this PC
echo.
pause
