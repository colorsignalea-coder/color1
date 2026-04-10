"""
BUILD_DEPLOY.py ??EA AUTO MASTER v8.0 諛고룷 ?⑦궎吏 鍮뚮뜑
=========================================================
?ㅽ뻾: python BUILD_DEPLOY.py
寃곌낵: EA_AUTO_MASTER_v8.0_DEPLOY\ ?대뜑 ?앹꽦
      ?????대뜑瑜??ㅻⅨ PC??蹂듭궗 ??SETUP.bat ?ㅽ뻾?섎㈃ 諛붾줈 ?ъ슜 媛??"""
import os, sys, shutil, json
from pathlib import Path

SRC  = Path(os.path.dirname(os.path.abspath(__file__)))
DEST = SRC.parent / 'EA_AUTO_MASTER_v8.0_DEPLOY'

# ?? ?ы븿???뚯씪/?대뜑 紐⑸줉 ?????????????????????????????????????????????????
INCLUDE_FILES = [
    'ea_optimizer_v7.py',
    'ea_master.py',
    'SOLO_WATCHER.py',
    'SOLO_nc2.3.ahk',
    'START_ALL_v7.bat',
    'verify_deploy.py',
]

INCLUDE_DIRS = [
    'core',
    'ui',
]

SCRIPTS_INCLUDE = [
    'patch_paths.py',
    'integrated_solo_worker_v7.1.py',
    'CLOSE_MT4_LOGIN.ahk',
    'CLOSE_SECURITY_WARNING.ahk',
    'SOLO_LAYOUT_FIX.ahk',
    'DETECT_STEP2_COORDS.ahk',
]

# ?? 鍮뚮뱶 ?????????????????????????????????????????????????????????????????
def build():
    print(f'Building deploy package...')
    print(f'  SRC  = {SRC}')
    print(f'  DEST = {DEST}')
    print()

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    copied = 0

    # 猷⑦듃 ?뚯씪
    for fname in INCLUDE_FILES:
        src_f = SRC / fname
        if src_f.exists():
            shutil.copy2(src_f, DEST / fname)
            copied += 1
            print(f'  [OK] {fname}')
        else:
            print(f'  [MISS] {fname}')

    # core/ ui/ ?붾젆?좊━
    for dname in INCLUDE_DIRS:
        src_d = SRC / dname
        dst_d = DEST / dname
        if src_d.exists():
            shutil.copytree(src_d, dst_d,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            n = sum(1 for _ in dst_d.rglob('*.py'))
            copied += n
            print(f'  [OK] {dname}/  ({n} py files)')
        else:
            print(f'  [MISS] {dname}/')

    # scripts/ (?좏깮 ?뚯씪留?
    dst_scripts = DEST / 'scripts'
    dst_scripts.mkdir()
    for fname in SCRIPTS_INCLUDE:
        src_f = SRC / 'scripts' / fname
        if src_f.exists():
            shutil.copy2(src_f, dst_scripts / fname)
            copied += 1
            print(f'  [OK] scripts/{fname}')
        else:
            print(f'  [MISS] scripts/{fname}')

    # configs/ ???쒗뵆由?(寃쎈줈 NOTSET?쇰줈 珥덇린??
    dst_configs = DEST / 'configs'
    dst_configs.mkdir()
    _write_config_template(dst_configs / 'current_config.ini')
    print(f'  [OK] configs/current_config.ini  (template)')

    # 鍮??대뜑 ?앹꽦
    for d in ['g4_results', 'reports']:
        (DEST / d).mkdir()
        (DEST / d / '.gitkeep').write_text('')
    print(f'  [OK] g4_results/  reports/  (empty)')

    # SETUP.bat ?앹꽦
    _write_setup_bat(DEST / 'SETUP.bat')
    print(f'  [OK] SETUP.bat')

    # README.txt
    _write_readme(DEST / 'README.txt')
    print(f'  [OK] README.txt')

    print()
    print(f'Copied {copied} files ??{DEST}')
    print()
    print('Contents:')
    for item in sorted(DEST.iterdir()):
        if item.is_dir():
            n = sum(1 for _ in item.rglob('*') if _.is_file())
            print(f'  {item.name}/  ({n} files)')
        else:
            print(f'  {item.name}')
    return DEST


def _write_config_template(path):
    template = """\
[folders]
setfiles_path=NOTSET
terminal_path=NOTSET
work_folder=NOTSET
ea_path=NOTSET
html_save_path=NOTSET

[current_backtest]
set_file_path=NONE
has_set=0
period=M5
symbol=XAUUSD
ea_name=

[symbols]
sym1=XAUUSD
sym2=BTCUSD
sym3=USDJPY
sym4=NAS100
sym5=ERROR

[selection]
sym1Chk=1
sym2Chk=0
sym3Chk=0
sym4Chk=0
tfM5=1
ea_all=1

[test_date]
enable=1
from_date=2025.01.01
to_date=2026.06.30
"""
    path.write_text(template, encoding='utf-8')


def _write_setup_bat(path):
    content = """\
@echo off
chcp 65001 >nul
echo ============================================================
echo  EA AUTO MASTER V7.0 - SETUP
echo  Auto-detecting MT4 and AHK paths...
echo ============================================================
echo.

set "RUNTIME=%~dp0"
if "%RUNTIME:~-1%"=="\\" set "RUNTIME=%RUNTIME:~0,-1%"

REM --- MT4 detect ---
set "MT4=NOTSET"
if exist "C:\\AG TO DO\\MT4\\terminal.exe"      set "MT4=C:\\AG TO DO\\MT4"
if exist "C:\\MT4\\terminal.exe"                set "MT4=C:\\MT4"
if exist "D:\\MT4\\terminal.exe"                set "MT4=D:\\MT4"
if exist "C:\\Program Files\\MetaTrader 4\\terminal.exe" set "MT4=C:\\Program Files\\MetaTrader 4"
if exist "C:\\NEWOPTMISER\\MT4\\terminal.exe"   set "MT4=C:\\NEWOPTMISER\\MT4"

if "%MT4%"=="NOTSET" (
    echo [ERROR] MT4 not found. Please install MetaTrader 4 first.
    echo         Common paths checked:
    echo           C:\\AG TO DO\\MT4
    echo           C:\\MT4
    echo           D:\\MT4
    pause
    exit /b 1
)
echo [OK] MT4: %MT4%

REM --- Patch paths in config ---
python "%RUNTIME%\\scripts\\patch_paths.py" "%RUNTIME%" "%MT4%"
if errorlevel 1 (
    echo [ERROR] patch_paths.py failed
    pause
    exit /b 1
)
echo [OK] Config paths updated

REM --- Verify ---
echo.
echo Running verification...
cd /d "%RUNTIME%"
python verify_deploy.py
echo.
echo ============================================================
echo  SETUP COMPLETE
echo  Run START_ALL_v7.bat to start the optimizer
echo ============================================================
pause
"""
    path.write_text(content, encoding='utf-8')


def _write_readme(path):
    content = """\
EA AUTO MASTER v8.0 - Universal EA Parameter Optimizer
======================================================

REQUIREMENTS
  - Windows 10/11
  - Python 3.9+ (https://www.python.org)
  - MetaTrader 4 (with Strategy Tester)
  - AutoHotkey v1.x (https://www.autohotkey.com)

SETUP (first time on new computer)
  1. Copy this folder to any location (e.g., C:\\EA_MASTER_V7\\)
  2. Double-click SETUP.bat
  3. SETUP will auto-detect MT4 and configure paths

RUN
  - Double-click START_ALL_v7.bat
  - Each run = 1 optimization round (R4 -> R5 -> R6 ...)
  - Results saved in g4_results\\ folder

OPTIMIZATION STRATEGY
  R1-R2: LHS  (full parameter space, 50 scenarios)
  R3-R5: FOCUSED  (around top results, 50 scenarios)
  R6+:   GENETIC  (crossover + mutation, 50 scenarios)

13 PARAMETERS OPTIMIZED
  SL, TP, ATR, FastMA, SlowMA, ADXPeriod, ADXMin,
  RSIPeriod, RSILower, RSIUpper, MaxDD, MaxPositions, CooldownBars

PARAMETER ENCODING IN FILENAME
  G4v7_SC001_R5_SL042_TP0065_AT25_FM12_SM28_AX20_RL35_RH70_DD22_MP2_CD04.ex4
  SL=InpSLMultiplier x100  TP=InpTPMultiplier x10
  AT=ATR  FM=FastMA  SM=SlowMA  AX=ADXMin
  RL=RSILower  RH=RSIUpper  DD=MaxDD  MP=MaxPos  CD=CooldownBars

FOLDER STRUCTURE
  core\\          - optimizer engine (param_space, sampler, scorer, ea_template)
  ui\\            - GUI tabs
  scripts\\       - AHK helper scripts + path patcher
  configs\\       - runtime config (auto-updated)
  g4_results\\    - JSON result files per round
  reports\\       - HTML backtest reports (generated by MT4)
"""
    path.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    dest = build()
    print(f'\nDeploy package ready: {dest}')

