#NoEnv
#SingleInstance Force
CoordMode, Mouse, Screen
SetWorkingDir, %A_ScriptDir%

; MT4 전문가 목록 새로고침 스크립트 (User F6 Coordinate Based)
; -----------------------------------------------------------------------------

; 1. MT4 창 활성화
WinActivate, ahk_class MetaQuotes::MetaTrader::4.00
WinWaitActive, ahk_class MetaQuotes::MetaTrader::4.00, , 2
if ErrorLevel {
    Tooltip, [ERROR] MT4 window not found!
    Sleep, 2000
    ExitApp
}

; 2. Esc 눌러서 혹시 열려있을지 모를 메뉴 닫기
Send, {Esc}
Sleep, 300

; 3. [F6] 좌표 정보 읽기
iniFile := A_ScriptDir . "\..\configs\current_config.ini"
IniRead, relX, %iniFile%, coords, relxSysTrading, ERROR
IniRead, relY, %iniFile%, coords, relySysTrading, ERROR

; 미세 조정: relxSysTrading이 없으면 relx6 시도
if (relX = "ERROR") {
    IniRead, relX, %iniFile%, coords, relx6, ERROR
    IniRead, relY, %iniFile%, coords, rely6, ERROR
}

; 4. 실제 우클릭 및 새로고침 수행
WinGetPos, wx, wy, ww, wh, ahk_class MetaQuotes::MetaTrader::4.00

if (relX != "ERROR") {
    ; 절대 좌표 계산
    targetX := wx + (relX * ww)
    targetY := wy + (relY * wh)
    
    ; 눈으로 확인할 수 있게 천천히 이동 (Speed 2)
    CoordMode, Mouse, Screen
    MouseMove, %targetX%, %targetY%, 2
    Tooltip, % "[MT4 Refresh] Right Clicking @ (" . targetX . ", " . targetY . ")"
    Sleep, 500
    
    ; 우클릭 (MouseClick이 변수 사용에 더 안정적임)
    MouseClick, Right, %targetX%, %targetY%
    Sleep, 1000  ; 메뉴 뜰 때까지 대기 (중요)
    
    ; 메뉴 아래로 4칸 이동 후 Enter (사용자 요청 로직)
    Tooltip, [MT4 Refresh] Selecting 4th item (Refresh)
    Send, {Down 4}
    Sleep, 400
    Send, {Enter}
    
    Tooltip, [MT4 Refresh] Done
    Sleep, 1500
} else {
    ; 좌표가 없을 때의 기본 동작 (네비게이터 대략적 중간 위치 우클릭 시도)
    Tooltip, [MT4 Refresh] F6 Not Set! Trying default location
    defX := wx + 100
    defY := wy + 300
    MouseClick, Right, %defX%, %defY%
    Sleep, 1000
    Send, {Down 4}
    Sleep, 400
    Send, {Enter}
    Sleep, 1500
}

Tooltip
ExitApp
