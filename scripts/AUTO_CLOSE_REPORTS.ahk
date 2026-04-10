#NoEnv
#SingleInstance Force
SetBatchLines, -1

; AUTO_CLOSE_REPORTS.ahk v8.0
; [v8.0] 5분 시간 기반 자동 닫기 + 실행 시 즉시 시작
; 30초마다 체크 / 창별 최초 발견 시각 추적 → 5분 경과 시 닫기

INTERVAL_MS   := 30000   ; 30초마다 체크
CLOSE_AFTER_S := 300     ; 5분 (300초) 후 닫기

; 창 ID → 최초 발견 시각(A_TickCount) 저장
firstSeen := {}

SetTimer, CloseReports, %INTERVAL_MS%
return

CloseReports:
    now := A_TickCount

    WinGet, wins, List
    Loop, %wins% {
        winID    := wins%A_Index%
        WinGetTitle, winTitle, ahk_id %winID%
        WinGetClass, winClass, ahk_id %winID%

        ; ── 백테스트 리포트 창 감지 ──
        isReport := (InStr(winTitle, ".htm") or InStr(winTitle, ".html")
                     or InStr(winTitle, "Strategy Tester Report")
                     or InStr(winTitle, "Backtest") or InStr(winTitle, "Report"))

        if (isReport) {
            ; 최초 발견 시각 기록
            if (!firstSeen.HasKey(winID))
                firstSeen[winID] := now

            elapsedMs := now - firstSeen[winID]
            elapsedS  := elapsedMs // 1000

            ; 5분 경과 → 자동 닫기
            if (elapsedS >= CLOSE_AFTER_S) {
                WinClose, ahk_id %winID%
                Sleep, 200
                firstSeen.Delete(winID)
            }
        }

        ; ── Excel 자동 닫기 (즉시) ──
        if (winClass = "XLMAIN" and InStr(winTitle, ".xls")) {
            WinActivate, ahk_id %winID%
            Sleep, 100
            WinClose, ahk_id %winID%
            Sleep, 300
            IfWinExist, ahk_class #32770
                ControlClick, Button2, ahk_class #32770
        }
    }

    ; 닫힌 창 ID를 firstSeen에서 정리
    for id, t in firstSeen {
        IfWinNotExist, ahk_id %id%
            firstSeen.Delete(id)
    }

    ; IE 프로세스 찌꺼기 정리
    Process, Exist, iexplore.exe
    if (ErrorLevel != 0)
        Process, Close, iexplore.exe
return
