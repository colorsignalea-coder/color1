
WinWait, MT4 COMBO BACKTESTER, , 5
IfWinNotExist, MT4 COMBO BACKTESTER
{
    MsgBox, SOLO 창 없음
    ExitApp
}
WinActivate, MT4 COMBO BACKTESTER
Sleep, 500
ControlClick, ★ TEST 1 COMBO, MT4 COMBO BACKTESTER
Sleep, 1500
ControlClick, [Gen] 조합 생성, MT4 COMBO BACKTESTER
Sleep, 2000
ControlClick, [Run] 백테스트 시작, MT4 COMBO BACKTESTER
Sleep, 500
ExitApp
