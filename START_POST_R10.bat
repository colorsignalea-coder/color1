@echo off
chcp 65001 > nul
title POST-R10 자동 검증 대기

echo ============================================================
echo  POST-R10 종합 검증 자동 예약 스크립트
echo  - R10 완료 자동 감지 후 즉시 시작
echo  - GOLD + BTC x M5 + M30 = 4콤보
echo  - 100개 시나리오 x 4콤보 = 400 백테스트
echo ============================================================
echo.

cd /d "%~dp0"

REM Python 경로 자동 탐색
set PYTHON=python
where python >nul 2>&1 || set PYTHON=python3
where %PYTHON% >nul 2>&1 || (
    echo [ERROR] Python을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo [INFO] R10 완료 대기 중... (최대 12시간)
echo [INFO] 이 창을 닫지 마세요.
echo.

REM post_r10_validation.py 실행 (내부에서 R10 완료 대기)
%PYTHON% post_r10_validation.py

echo.
echo ============================================================
echo  POST-R10 검증 완료!
echo ============================================================
pause
