; MT4 포터블 로그인 창 자동 닫기
; 창 제목: "Moneta Markets Trading MT4 Terminal"
; 취소 버튼 클릭

WinWait, Moneta Markets Trading MT4 Terminal, , 15
if ErrorLevel {
    ExitApp  ; 창 안 뜨면 그냥 종료
}

Sleep, 300
ControlClick, 취소, Moneta Markets Trading MT4 Terminal
Sleep, 300

; 혹시 안 닫혔으면 WinClose
IfWinExist, Moneta Markets Trading MT4 Terminal
    WinClose, Moneta Markets Trading MT4 Terminal

ExitApp
