; CLOSE_SECURITY_WARNING.ahk
; Windows "Open File - Security Warning" 자동 Run 클릭
; START_ALL.bat 에서 백그라운드 실행됨

#NoEnv
#SingleInstance Force
SetTitleMatchMode, 2

; 최대 60초 동안 감시
Loop, 60 {
    IfWinExist, Open File - Security Warning
    {
        WinActivate, Open File - Security Warning
        Sleep, 200
        ControlClick, Button1, Open File - Security Warning
        Sleep, 300
    }
    Sleep, 1000
}
ExitApp
