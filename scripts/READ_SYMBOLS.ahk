#NoEnv
#SingleInstance Force
CoordMode, Mouse, Screen

; =====================================================
; MT4 Symbol 목록 읽기 v1.40 (v2.0 통합)
; - v2.0: configs 폴더 사용
; - v1.40: 저장된 심볼 목록 표시, MT4 감지 개선
; =====================================================

; v2.0: 상위 폴더의 configs 사용
SetWorkingDir, %A_ScriptDir%\..
iniFile := A_WorkingDir "\configs\current_config.ini"

; 기존 저장된 심볼 읽기
savedSymbols := []
Loop, 10 {
    IniRead, tmpSym, %iniFile%, symbols, sym%A_Index%,
    if (tmpSym != "" && tmpSym != "ERROR")
        savedSymbols.Push(tmpSym)
    else
        savedSymbols.Push("")
}

Gui, Margin, 15, 15
Gui, Font, s11 Bold
Gui, Add, Text, w600 Center, MT4 Symbol 목록 읽기 v1.40

Gui, Font, s9 Normal
Gui, Add, Text, w600 y+10, MT4 Strategy Tester를 열고 [목록 읽기] 클릭

Gui, Add, Text, w600 y+15 0x10

; 왼쪽: MT4 Symbol 목록
Gui, Font, s9 Bold
Gui, Add, Text, x15 w280 y+10, MT4 Symbol 목록:

Gui, Font, s9 Normal
Gui, Add, ListBox, vSymbolList x15 w280 h250 y+5

Gui, Add, Text, x15 w280 y+10, 저장할 슬롯:
Gui, Add, DropDownList, vSlotSelect x15 w100 y+5, 슬롯1||슬롯2|슬롯3|슬롯4|슬롯5|슬롯6|슬롯7|슬롯8|슬롯9|슬롯10

; 오른쪽: 저장된 심볼 목록
Gui, Font, s9 Bold
Gui, Add, Text, x320 y85 w280, 저장된 Symbol (1~10):

Gui, Font, s9 Normal
savedListText := ""
Loop, 10 {
    sym := savedSymbols[A_Index]
    if (sym != "")
        savedListText .= A_Index . ": " . sym . "|"
    else
        savedListText .= A_Index . ": (빈 슬롯)|"
}
Gui, Add, ListBox, vSavedList x320 y105 w280 h250, %savedListText%

Gui, Add, Button, gDeleteSaved x320 y360 w135 h30, 🗑️ 선택 삭제
Gui, Add, Button, gClearAll x+10 yp w135 h30, 🗑️ 전체 삭제

Gui, Add, Text, x15 w600 y+20 0x10

Gui, Add, Button, gReadSymbols x15 w145 h35 y+10, 🔍 목록 읽기
Gui, Add, Button, gSaveSymbol x+10 w145 h35, 💾 선택 저장
Gui, Add, Button, gCopySymbol x+10 w145 h35, 📋 복사
Gui, Add, Button, gRefreshSaved x+10 w145 h35, 🔄 새로고침

Gui, Add, Button, gExitApp x15 w600 h30 y+15, 닫기

Gui, Show, AutoSize, MT4 Symbol 목록
return

ReadSymbols:
    ; MT4 찾기 (메인 창만, 대화상자 제외)
    mt4ID := 0
    WinGet, wins, List
    Loop, %wins% {
        id := wins%A_Index%
        WinGet, proc, ProcessName, ahk_id %id%
        if (proc = "terminal.exe") {
            WinGetClass, winClass, ahk_id %id%
            ; 대화상자 제외
            if (winClass = "#32770")
                continue
            WinGetTitle, title, ahk_id %id%
            ; 제목이 너무 짧으면 건너뜀
            if (StrLen(title) < 10)
                continue
            mt4ID := id
            break
        }
    }

    if (!mt4ID) {
        MsgBox, 48, 오류, MT4를 찾을 수 없습니다.`n`nterminal.exe가 실행 중인지 확인하세요.
        return
    }

    ; Symbol ComboBox
    IniRead, symbolComboClassNN, %iniFile%, tester_controls, symbol_combo, ComboBox3

    ; Strategy Tester가 열려있는지 확인
    ControlGet, symbolList, List,, %symbolComboClassNN%, ahk_id %mt4ID%

    if (symbolList = "") {
        MsgBox, 48, 오류, Symbol 목록을 읽을 수 없습니다.`n`n1. Strategy Tester가 열려있는지 확인 (Ctrl+R)`n2. [1단계: 컨트롤 감지] 먼저 실행
        return
    }

    GuiControl,, SymbolList, |

    symbolCount := 0
    Loop, Parse, symbolList, `n
    {
        if (A_LoopField != "") {
            ; 콤마가 있으면 앞부분만 사용 (예: "BTCUSD, Bitcoin" → "BTCUSD")
            symItem := A_LoopField
            if (InStr(symItem, ",")) {
                StringSplit, parts, symItem, `,
                symItem := Trim(parts1)
            }
            GuiControl,, SymbolList, %symItem%
            symbolCount++
        }
    }

    MsgBox, 64, 완료, %symbolCount%개 Symbol 발견!`n`n사용할 Symbol을 선택하세요.
return

SaveSymbol:
    GuiControlGet, selectedSymbol,, SymbolList
    GuiControlGet, slotSelect,, SlotSelect

    if (selectedSymbol = "") {
        MsgBox, 48, 경고, Symbol을 선택하세요!
        return
    }

    ; 콤마가 있으면 앞부분만 사용
    if (InStr(selectedSymbol, ",")) {
        StringSplit, parts, selectedSymbol, `,
        selectedSymbol := Trim(parts1)
    }

    ; 슬롯 번호 추출 (슬롯1 -> 1, 슬롯10 -> 10)
    RegExMatch(slotSelect, "\d+", slotNum)
    IniWrite, %selectedSymbol%, %iniFile%, symbols, sym%slotNum%

    ; 저장된 목록 새로고침
    Gosub, RefreshSaved

    MsgBox, 64, 저장 완료, %slotSelect%에 저장: %selectedSymbol%
return

CopySymbol:
    GuiControlGet, selectedSymbol,, SymbolList

    if (selectedSymbol = "") {
        MsgBox, 48, 경고, Symbol을 선택하세요!
        return
    }

    ; 콤마가 있으면 앞부분만 사용
    if (InStr(selectedSymbol, ",")) {
        StringSplit, parts, selectedSymbol, `,
        selectedSymbol := Trim(parts1)
    }

    Clipboard := selectedSymbol
    MsgBox, 64, 복사됨, 클립보드에 복사: %selectedSymbol%
return

RefreshSaved:
    ; 저장된 심볼 다시 읽기
    savedSymbols := []
    Loop, 10 {
        IniRead, tmpSym, %iniFile%, symbols, sym%A_Index%,
        if (tmpSym != "" && tmpSym != "ERROR")
            savedSymbols.Push(tmpSym)
        else
            savedSymbols.Push("")
    }

    ; 리스트박스 업데이트
    savedListText := ""
    Loop, 10 {
        sym := savedSymbols[A_Index]
        if (sym != "")
            savedListText .= A_Index . ": " . sym . "|"
        else
            savedListText .= A_Index . ": (빈 슬롯)|"
    }
    GuiControl,, SavedList, |%savedListText%
return

DeleteSaved:
    GuiControlGet, selectedSaved,, SavedList

    if (selectedSaved = "") {
        MsgBox, 48, 경고, 삭제할 슬롯을 선택하세요!
        return
    }

    ; 슬롯 번호 추출
    RegExMatch(selectedSaved, "^(\d+):", slotMatch)
    slotNum := slotMatch1

    if (slotNum = "") {
        MsgBox, 48, 오류, 슬롯 번호를 찾을 수 없습니다.
        return
    }

    MsgBox, 36, 삭제 확인, 슬롯%slotNum%의 심볼을 삭제하시겠습니까?
    IfMsgBox, No
        return

    IniDelete, %iniFile%, symbols, sym%slotNum%
    Gosub, RefreshSaved
    MsgBox, 64, 삭제 완료, 슬롯%slotNum% 삭제됨
return

ClearAll:
    MsgBox, 36, 전체 삭제, 저장된 모든 심볼을 삭제하시겠습니까?
    IfMsgBox, No
        return

    Loop, 10 {
        IniDelete, %iniFile%, symbols, sym%A_Index%
    }
    Gosub, RefreshSaved
    MsgBox, 64, 삭제 완료, 모든 심볼이 삭제되었습니다.
return

ExitApp:
GuiClose:
    ExitApp
return
