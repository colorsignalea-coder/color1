; set_2fc_combo.ahk — SOLO 2fc EA 6개 선택 + Gen + Run
; AHK 내부에서 ControlClick 사용 → g-label 정상 트리거
#NoEnv
#SingleInstance Force
SetTitleMatchMode, 2
DetectHiddenWindows, Off
SetControlDelay, 150

; SOLO 창 찾기
WinWait, COMBO BACKTESTER, , 10
if ErrorLevel {
    MsgBox, SOLO 창을 찾을 수 없습니다
    ExitApp
}
WinActivate, COMBO BACKTESTER

sleep, 500

; ── EA1~13 OFF (2fc 전용으로) ──────────────────────────────────
; BtComboEA1 (Survivor v2 SLTP) - 체크 해제
ControlGet, chk, Checked, , Button%_getCtrlIdx("BtComboEA1")%, COMBO BACKTESTER
Loop, 13 {
    ctrlName := "BtComboEA" . A_Index
    ControlGet, isChk, Checked, , %ctrlName%, COMBO BACKTESTER
    if (isChk = 1) {
        ControlClick, %ctrlName%, COMBO BACKTESTER
        sleep, 200
    }
}

sleep, 300

; ── EA14~19 ON (2fc 6개) ──────────────────────────────────────
Loop, 6 {
    n := A_Index + 13
    ctrlName := "BtComboEA" . n
    ControlGet, isChk, Checked, , %ctrlName%, COMBO BACKTESTER
    if (isChk = 0) {
        ControlClick, %ctrlName%, COMBO BACKTESTER
        sleep, 200
    }
}

sleep, 500

; ── Gen 클릭 ─────────────────────────────────────────────────
ControlClick, [Gen] 조합 생성, COMBO BACKTESTER
sleep, 2000

; ── Run 클릭 ─────────────────────────────────────────────────
ControlClick, [Run] 백테스트 시작, COMBO BACKTESTER
sleep, 500

FileAppend, [AHK] 2R 6EA Gen+Run 완료`n, %A_ScriptDir%\set_2fc_log.txt
ExitApp
