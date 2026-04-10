@echo off
chcp 65001 >nul
cls

REM ============================================================
REM  START_ALL_v8.bat - EA AUTO MASTER V8.0
REM  Universal optimizer: any EA, any number of parameters
REM  Sequence: MT4 -> SOLO nc2.3 -> EA_AUTO_MASTER_v8.0.py
REM ============================================================

set "RUNTIME=%~dp0"
if "%RUNTIME:~-1%"=="\" set "RUNTIME=%RUNTIME:~0,-1%"
set "SCRIPTS=%RUNTIME%\scripts"

REM --- AHK detect ---
set "AHK=C:\Program Files\AutoHotkey\AutoHotkey.exe"
set "AHK_X86=C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
if not exist "%AHK%" set "AHK=%AHK_X86%"
if not exist "%AHK%" (
    echo [ERROR] AutoHotkey not found
    pause
    exit /b 1
)

REM --- MT4 detect ---
set "MT4=C:\AG TO DO\MT4"
if not exist "%MT4%\terminal.exe" set "MT4=C:\MT4"
if not exist "%MT4%\terminal.exe" set "MT4=D:\MT4"
if not exist "%MT4%\terminal.exe" (
    echo [ERROR] MT4 not found
    pause
    exit /b 1
)

REM --- SOLO file check ---
set "SOLO=%RUNTIME%\SOLO_nc2.3.ahk"
if not exist "%SOLO%" (
    echo [ERROR] SOLO_nc2.3.ahk not found
    pause
    exit /b 1
)

echo ============================================================
echo  EA AUTO MASTER V8.0 - Universal Optimizer
echo  Runtime: %RUNTIME%
echo  MT4:     %MT4%
echo ============================================================
echo.

echo [0] Flag reset...
if exist "%RUNTIME%\configs" (
    echo. > "%RUNTIME%\configs\runner_stop.signal"
    del /Q "%RUNTIME%\configs\test_completed*.flag" >nul 2>&1
    del /Q "%RUNTIME%\configs\runner_stop.signal" >nul 2>&1
)

echo [1] MT4 start...
if exist "%MT4%\Start_Portable.bat" (
    start "" /d "%MT4%" "%MT4%\Start_Portable.bat"
) else (
    start "" /d "%MT4%" "%MT4%\terminal.exe" /portable
)
timeout /t 10 /nobreak >nul

echo [2] SOLO start...
start "" "%AHK%" "%SOLO%"
timeout /t 5 /nobreak >nul

echo [3] EA Master v8.0 GUI start...
if exist "%RUNTIME%\EA_AUTO_MASTER_v8.0.py" (
    start "" python "%RUNTIME%\EA_AUTO_MASTER_v8.0.py"
)

echo [4] Watcher start...
if exist "%RUNTIME%\SOLO_WATCHER.py" (
    start /min "" python "%RUNTIME%\SOLO_WATCHER.py"
)

echo.
echo [RUNNING] EA Master v8.0 is active.
echo.
pause