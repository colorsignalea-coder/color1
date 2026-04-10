@echo off
chcp 65001 >nul
echo ============================================
echo  BingX G4v7 Bot - SC032_R7
echo ============================================
echo.
echo  DRY_RUN=True 로 실행중 (페이퍼 트레이딩)
echo  실거래: config.py 에서 DRY_RUN = False 로 변경
echo           + API_KEY / API_SECRET 입력
echo.
cd /d "%~dp0"
python bot.py
pause
