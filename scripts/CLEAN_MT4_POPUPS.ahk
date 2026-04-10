#NoEnv
#SingleInstance Force
SetTitleMatchMode, 2

; MT4 Startup Popup Auto-Closer v1.0
; Target: ahk_class #32770 (Standard Dialog Class)

startTime := A_TickCount
Loop {
    ; Monitor for 30 seconds (MT4 startup wait time)
    if (A_TickCount - startTime > 30000)
        break

    ; Check MT4 dialog boxes (#32770)
    if WinExist("ahk_class #32770") {
        WinGetTitle, title, ahk_class #32770
        WinGet, proc, ProcessName, ahk_class #32770
        
        ; Check if popup is from terminal.exe
        if (proc = "terminal.exe") {
            ; Close windows with titles containing Login, Account, Open, or empty titles
            if (title = "" or InStr(title, "Login") or InStr(title, "Account") or InStr(title, "Open")) {
                WinClose, ahk_class #32770
                Sleep, 500
                continue
            }
        }
    }
    
    Sleep, 1000
}

ExitApp
