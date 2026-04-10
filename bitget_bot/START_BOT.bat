@echo off
chcp 65001 >nul
echo ============================================
echo  Bitget G4v7 Bot - SC032_R7
echo ============================================
echo.
echo  DEMO_MODE=True 로 실행중 (데모 계좌)
echo  실거래: config.py 에서 DEMO_MODE = False 로 변경
echo           + API_KEY / API_SECRET / API_PASSPHRASE 입력
echo.
cd /d "%~dp0"
python bot.py
pause
