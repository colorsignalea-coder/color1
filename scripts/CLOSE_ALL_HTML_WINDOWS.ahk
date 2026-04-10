#NoEnv
#SingleInstance Force

; 모든 HTML 창 즉시 닫기 스크립트

closedCount := 0
WinGet, wins, List

Loop, %wins% {
    winID := wins%A_Index%
    WinGetTitle, winTitle, ahk_id %winID%

    ; HTML 파일 창 감지
    if (InStr(winTitle, ".htm") or InStr(winTitle, ".html") or InStr(winTitle, "Strategy Tester Report") or InStr(winTitle, "시스템 트레이딩")) {
        WinClose, ahk_id %winID%
        closedCount++
        Sleep, 50
    }
}

MsgBox, 64, 완료, %closedCount%개의 HTML 창을 닫았습니다!

ExitApp