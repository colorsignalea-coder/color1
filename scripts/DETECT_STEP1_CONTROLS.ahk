#NoEnv
#SingleInstance Force
CoordMode, Mouse, Screen

; =====================================================
; 1단계: 기본 컨트롤 감지 (v3.5)
; 시작버튼, EA, Symbol, Period, 진행바
; v3.5: Use date 체크박스, From/To 날짜 컨트롤 추가
; - v2.0: configs 폴더 사용
; =====================================================

; v2.0: 상위 폴더의 configs 사용
SetWorkingDir, %A_ScriptDir%\..
iniFile := A_WorkingDir "\configs\current_config.ini"

global startButtonClass := ""
global progressBarClass := ""
global periodComboClass := ""
global eaComboClass := ""
global eaTypeComboClass := ""
global symbolComboClass := ""
global visualModeCheckbox := ""
; v3.5: 날짜 관련 컨트롤
global useDateCheckbox := ""
global fromDateEdit := ""
global toDateEdit := ""

Gui, Margin, 15, 15
Gui, Font, s11 Bold
Gui, Add, Text, w380 Center, 1단계: 기본 컨트롤 감지

Gui, Font, s9 Normal
Gui, Add, Text, w380 Center y+3 cBlue, (시작버튼, EA, Symbol, Period, 진행바)

Gui, Add, Text, w380 y+15 0x10

Gui, Add, Text, w380 y+10, 1. MT4 실행
Gui, Add, Text, w380 y+5, 2. Strategy Tester 열기 (Ctrl+R)
Gui, Add, Text, w380 y+5, 3. [자동 감지] 클릭
Gui, Add, Text, w380 y+5, 4. [저장] 클릭
Gui, Add, Text, w380 y+5 cRed, 5. [2단계] 실행 (Report 탭 좌표)

Gui, Add, Text, w380 y+15 0x10

Gui, Font, s9 Bold
Gui, Add, Text, w380 y+10, 감지 결과:

Gui, Font, s9 Normal
Gui, Add, Text, vMT4Label w380 y+8, MT4: (미감지)
Gui, Add, Text, vStartBtnLabel w380 y+5, 시작버튼: (미감지)
Gui, Add, Text, vProgressLabel w380 y+5, 진행바: (미감지)
Gui, Add, Text, vEaTypeLabel w380 y+5, EA타입: (미감지)
Gui, Add, Text, vEaLabel w380 y+5, EA: (미감지)
Gui, Add, Text, vSymbolLabel w380 y+5, Symbol: (미감지)
Gui, Add, Text, vPeriodLabel w380 y+5, Period: (미감지)
Gui, Add, Text, vVisualLabel w380 y+5, 시각화: (미감지)
Gui, Add, Text, vUseDateLabel w380 y+5, 날짜사용: (미감지)
Gui, Add, Text, vFromDateLabel w380 y+5, 시작일: (미감지)
Gui, Add, Text, vToDateLabel w380 y+5, 종료일: (미감지)

Gui, Add, Text, w380 y+15 0x10

Gui, Add, Button, gAutoDetect w185 h35 y+10, 🔍 자동 감지
Gui, Add, Button, gSaveSettings x+10 w185 h35, 💾 저장

Gui, Add, Button, gRunStep2 x15 w380 h35 y+10, ▶ 2단계: Report 탭 좌표 설정

Gui, Add, Button, gSaveDebugInfo x15 w380 h30 y+10 cBlue, 📋 디버그 정보 저장

Gui, Add, Button, gExitApp x15 w380 h30 y+15, 닫기

Gui, Show, AutoSize, 1단계: 기본 컨트롤
return

AutoDetect:
    ; MT4 찾기 (메인 창만, 대화상자 제외)
    mt4ID := 0
    mt4Title := ""
    WinGet, wins, List
    Loop, %wins% {
        id := wins%A_Index%
        WinGet, proc, ProcessName, ahk_id %id%
        if (proc = "terminal.exe") {
            WinGetClass, winClass, ahk_id %id%
            ; 대화상자(#32770) 제외
            if (winClass = "#32770")
                continue
            WinGetTitle, title, ahk_id %id%
            ; 제목이 짧거나 비어있으면 건너뜀
            if (StrLen(title) < 10)
                continue
            ; 저장/속성 대화상자 제외
            if (InStr(title, "저장") or InStr(title, "Save") or InStr(title, "속성") or InStr(title, "Properties"))
                continue
            mt4ID := id
            mt4Title := title
            break
        }
    }

    if (!mt4ID) {
        MsgBox, 48, 오류, MT4를 찾을 수 없습니다.`n`nterminal.exe가 실행 중인지 확인하세요.
        return
    }

    GuiControl,, MT4Label, MT4: %mt4Title%

    ; Strategy Tester가 열려있는지 확인 (시작 버튼 또는 진행바 존재 여부)
    WinGet, ctrlList, ControlList, ahk_id %mt4ID%
    hasTesterControls := false
    Loop, Parse, ctrlList, `n
    {
        ctrl := A_LoopField
        if (InStr(ctrl, "msctls_progress32")) {
            hasTesterControls := true
            break
        }
    }

    ; Strategy Tester가 없으면 경고만 표시
    if (!hasTesterControls) {
        MsgBox, 48, Strategy Tester, Strategy Tester가 열려있지 않은 것 같습니다.`n`nMT4에서 Ctrl+R을 눌러 Strategy Tester를 먼저 열어주세요.
        return
    }
    
    startButtonClass := ""
    progressBarClass := ""
    periodComboClass := ""
    eaComboClass := ""
    eaTypeComboClass := ""
    symbolComboClass := ""
    visualModeCheckbox := ""
    useDateCheckbox := ""
    fromDateEdit := ""
    toDateEdit := ""

    ; 디버그용 - 모든 Button 텍스트 수집
    debugButtonList := ""
    ; 디버그용 - 모든 ComboBox 정보 수집
    debugComboList := ""

    Loop, Parse, ctrlList, `n
    {
        ctrl := A_LoopField

        ; 시작/중지 버튼
        if (InStr(ctrl, "Button")) {
            ControlGetText, btnText, %ctrl%, ahk_id %mt4ID%

            ; 디버그: 모든 Button 텍스트 수집
            debugButtonList .= ctrl . ": " . btnText . "`n"

            if (InStr(btnText, "시작") or InStr(btnText, "Start") or InStr(btnText, "중지") or InStr(btnText, "Stop")) {
                startButtonClass := ctrl
            }
            ; 시각화 체크박스 감지 (Visual mode)
            if (InStr(btnText, "Visual") or InStr(btnText, "시각화")) {
                ; 체크박스 상태 확인
                ControlGet, checkState, Checked,, %ctrl%, ahk_id %mt4ID%
                visualModeCheckbox := ctrl
            }
            ; v3.5: Use date 체크박스 감지 - 더 넓은 범위로 검색
            ; "Use date", "날짜 사용", "기간 사용", "날짜", "date", "사용" 등
            ; 한국어 MT4: "기간 사용" 또는 비슷한 텍스트
            if (InStr(btnText, "Use date") or InStr(btnText, "날짜") or InStr(btnText, "기간") or InStr(btnText, "date") or InStr(btnText, "Date") or InStr(btnText, "사용")) {
                ; 시작/중지 버튼이 아닌 경우에만
                if (!InStr(btnText, "시작") and !InStr(btnText, "Start") and !InStr(btnText, "중지") and !InStr(btnText, "Stop") and !InStr(btnText, "Visual") and !InStr(btnText, "시각화") and !InStr(btnText, "최적화") and !InStr(btnText, "Optimization")) {
                    useDateCheckbox := ctrl
                }
            }
        }

        ; v3.5: 날짜 컨트롤 감지 (SysDateTimePick32 - DateTime Picker)
        if (InStr(ctrl, "SysDateTimePick32")) {
            if (fromDateEdit = "")
                fromDateEdit := ctrl
            else if (toDateEdit = "")
                toDateEdit := ctrl
        }

        ; 진행바
        if (InStr(ctrl, "msctls_progress32")) {
            progressBarClass := ctrl
        }

        ; ComboBox 분석 - 모든 콤보박스 검사
        if (InStr(ctrl, "ComboBox")) {
            ControlGet, comboText, Choice,, %ctrl%, ahk_id %mt4ID%

            ; 콤보박스의 전체 항목 목록 가져오기
            ControlGet, comboItems, List,, %ctrl%, ahk_id %mt4ID%

            ; 디버그: 모든 ComboBox 정보 수집
            debugComboList .= ctrl . ": [" . comboText . "] Items: " . StrReplace(comboItems, "`n", ", ") . "`n"

            ; EA Type 콤보박스 감지 (Expert Advisor, Indicator, Script 등 포함)
            if (InStr(comboItems, "Expert Advisor") or InStr(comboItems, "Indicator") or InStr(comboItems, "지표") or InStr(comboItems, "전문가")) {
                eaTypeComboClass := ctrl
            }
            ; Period
            else if (RegExMatch(comboText, "^(M1|M5|M15|M30|H1|H4|D1|W1|MN)$")) {
                periodComboClass := ctrl
            }
            ; Symbol (통화쌍 패턴 - 더 넓은 범위)
            else if (RegExMatch(comboText, "i)(USD|EUR|GBP|JPY|AUD|NZD|CAD|CHF|BTC|ETH|XAU|GOLD|NAS|US100|US30|US500|OIL|CL-|WTI|SPX|DAX|FTSE|NK225|HSI|UKX|DE30|JP225|HK50|USTEC|USDX|DXY|ft$)")) {
                symbolComboClass := ctrl
            }
            ; Symbol (콤보박스 항목 목록에서 통화쌍 패턴 검색)
            else if (RegExMatch(comboItems, "i)(USD|EUR|GBP|JPY|AUD|XAU|GOLD|BTC|NAS)")) {
                symbolComboClass := ctrl
            }
            ; EA 콤보박스 (Period, Symbol, EA Type이 아니고 .ex4 파일명 포함)
            else if (InStr(comboItems, ".ex4") or InStr(comboText, ".ex4") or RegExMatch(comboText, "_v\d") or RegExMatch(comboText, "EA")) {
                eaComboClass := ctrl
            }
        }
    }

    ; Symbol 콤보박스가 감지되지 않으면 ComboBox3을 기본값으로 (MT4 일반적인 순서)
    if (symbolComboClass = "" || symbolComboClass = eaTypeComboClass || symbolComboClass = eaComboClass || symbolComboClass = periodComboClass) {
        symbolComboClass := "ComboBox3"
    }

    ; EA 콤보박스가 감지되지 않으면 EA Type과 다른 콤보박스를 기본값으로 사용
    if (eaComboClass = "" || eaComboClass = eaTypeComboClass) {
        ; EA Type 콤보박스가 ComboBox2면 ComboBox1을, 아니면 ComboBox2를 사용
        if (eaTypeComboClass = "ComboBox2")
            eaComboClass := "ComboBox1"
        else if (eaTypeComboClass = "ComboBox1")
            eaComboClass := "ComboBox2"
        else
            eaComboClass := "ComboBox1"
    }
    
    ; 결과 표시
    if (startButtonClass != "")
        GuiControl,, StartBtnLabel, 시작버튼: %startButtonClass% ✓
    else
        GuiControl,, StartBtnLabel, 시작버튼: 찾지 못함 ❌
    
    if (progressBarClass != "")
        GuiControl,, ProgressLabel, 진행바: %progressBarClass% ✓
    else
        GuiControl,, ProgressLabel, 진행바: 찾지 못함 ❌
    
    ; EA Type 콤보박스 결과 표시
    if (eaTypeComboClass != "") {
        ControlGet, eaTypeName, Choice,, %eaTypeComboClass%, ahk_id %mt4ID%
        GuiControl,, EaTypeLabel, EA타입: %eaTypeComboClass% (%eaTypeName%) ✓
    } else {
        GuiControl,, EaTypeLabel, EA타입: 찾지 못함 ❌ (수동 설정 필요)
    }

    if (eaComboClass != "") {
        ControlGet, eaName, Choice,, %eaComboClass%, ahk_id %mt4ID%
        if (eaName != "")
            GuiControl,, EaLabel, EA: %eaComboClass% (%eaName%) ✓
        else
            GuiControl,, EaLabel, EA: %eaComboClass% (기본값) ✓
    }

    if (symbolComboClass != "") {
        ControlGet, symbolName, Choice,, %symbolComboClass%, ahk_id %mt4ID%
        GuiControl,, SymbolLabel, Symbol: %symbolComboClass% (%symbolName%) ✓
    } else {
        GuiControl,, SymbolLabel, Symbol: 찾지 못함 ❌
    }
    
    if (periodComboClass != "") {
        ControlGet, periodName, Choice,, %periodComboClass%, ahk_id %mt4ID%
        GuiControl,, PeriodLabel, Period: %periodComboClass% (%periodName%) ✓
    } else {
        GuiControl,, PeriodLabel, Period: 찾지 못함 ❌
    }

    ; v3.6: SendMessage로 체크 상태 정확히 확인 (BM_GETCHECK = 0x00F0)
    if (visualModeCheckbox != "") {
        SendMessage, 0x00F0, 0, 0, %visualModeCheckbox%, ahk_id %mt4ID%
        visualState := ErrorLevel
        if (visualState = "FAIL")
            visualState := 0
        visualStateText := (visualState = 1) ? "체크됨" : "체크안됨"
        GuiControl,, VisualLabel, 시각화: %visualModeCheckbox% (%visualStateText%) ✓
    } else {
        GuiControl,, VisualLabel, 시각화: 찾지 못함 ❌
    }

    ; v3.5: 날짜 관련 컨트롤 결과 표시
    ; v3.6: 여러 방법으로 체크 상태 확인
    if (useDateCheckbox != "") {
        ; 방법 1: SendMessage BM_GETCHECK
        SendMessage, 0x00F0, 0, 0, %useDateCheckbox%, ahk_id %mt4ID%
        useDateState := ErrorLevel

        ; 방법 2: ControlGet Checked (백업)
        if (useDateState = "FAIL" || useDateState = "") {
            ControlGet, useDateState, Checked,, %useDateCheckbox%, ahk_id %mt4ID%
        }

        ; 방법 3: 날짜 컨트롤 활성화 여부로 간접 확인
        ; SysDateTimePick32가 활성화되어 있으면 체크된 것
        if (useDateState != 1 && fromDateEdit != "") {
            ControlGet, dateEnabled, Enabled,, %fromDateEdit%, ahk_id %mt4ID%
            if (dateEnabled = 1)
                useDateState := 1
        }

        useDateStateText := (useDateState = 1) ? "체크됨" : "체크안됨"
        GuiControl,, UseDateLabel, 날짜사용: %useDateCheckbox% (%useDateStateText%) ✓
    } else {
        GuiControl,, UseDateLabel, 날짜사용: 찾지 못함 ❌ (디버그 필요)
    }

    if (fromDateEdit != "") {
        ControlGetText, fromDateText, %fromDateEdit%, ahk_id %mt4ID%
        GuiControl,, FromDateLabel, 시작일: %fromDateEdit% (%fromDateText%) ✓
    } else {
        GuiControl,, FromDateLabel, 시작일: 찾지 못함 ❌
    }

    if (toDateEdit != "") {
        ControlGetText, toDateText, %toDateEdit%, ahk_id %mt4ID%
        GuiControl,, ToDateLabel, 종료일: %toDateEdit% (%toDateText%) ✓
    } else {
        GuiControl,, ToDateLabel, 종료일: 찾지 못함 ❌
    }

    if (startButtonClass = "" or progressBarClass = "")
        MsgBox, 48, 결과, Strategy Tester 열려있는지 확인 (Ctrl+R)
    else if (eaTypeComboClass = "") {
        ; EA Type 콤보박스를 못 찾은 경우 - 디버그 정보 표시
        MsgBox, 48, 경고, 1단계 감지 완료 (EA타입 콤보박스 미감지)`n`nEA Type 콤보박스를 찾지 못했습니다.`n아래 ComboBox 목록에서 확인하세요:`n`n%debugComboList%`n`n[저장] 후 수동으로 INI 파일의 ea_type_combo를 수정하세요.
    } else if (useDateCheckbox = "") {
        ; 날짜 체크박스를 못 찾은 경우 - 디버그 정보 표시
        MsgBox, 48, 경고, 1단계 감지 완료 (날짜 체크박스 미감지)`n`nUse date 체크박스를 찾지 못했습니다.`n아래 Button 목록에서 날짜 관련 항목을 확인하세요:`n`n%debugButtonList%`n`n[저장] 후 수동으로 INI 파일을 수정하거나`n다시 감지를 시도하세요.
    } else
        MsgBox, 64, 완료, 1단계 감지 완료!`n`n[저장] 후 [2단계] 실행하세요.
return

SaveSettings:
    if (startButtonClass = "") {
        MsgBox, 48, 경고, 먼저 [자동 감지] 실행
        return
    }
    
    IniWrite, %startButtonClass%, %iniFile%, tester_controls, start_button
    IniWrite, %progressBarClass%, %iniFile%, tester_controls, progress_bar
    IniWrite, %periodComboClass%, %iniFile%, tester_controls, period_combo
    IniWrite, %eaComboClass%, %iniFile%, tester_controls, ea_combo
    IniWrite, %eaTypeComboClass%, %iniFile%, tester_controls, ea_type_combo
    IniWrite, %symbolComboClass%, %iniFile%, tester_controls, symbol_combo
    IniWrite, %visualModeCheckbox%, %iniFile%, tester_controls, visual_mode_checkbox
    ; v3.5: 날짜 관련 컨트롤 저장
    IniWrite, %useDateCheckbox%, %iniFile%, tester_controls, use_date_checkbox
    IniWrite, %fromDateEdit%, %iniFile%, tester_controls, from_date_edit
    IniWrite, %toDateEdit%, %iniFile%, tester_controls, to_date_edit

    MsgBox, 64, 저장 완료, 1단계 저장됨!`n`n시작버튼: %startButtonClass%`n진행바: %progressBarClass%`nEA: %eaComboClass%`nEA타입: %eaTypeComboClass%`nSymbol: %symbolComboClass%`nPeriod: %periodComboClass%`n시각화: %visualModeCheckbox%`n날짜사용: %useDateCheckbox%`n시작일: %fromDateEdit%`n종료일: %toDateEdit%`n`n이제 [2단계]를 실행하세요.
return

RunStep2:
    f := A_ScriptDir "\DETECT_STEP2_COORDS.ahk"
    IfExist, %f%
        Run, "%f%"
    else
        MsgBox, 16, 오류, DETECT_STEP2_COORDS.ahk 파일이 없습니다!
return

SaveDebugInfo:
    ; 디버그 정보 파일로 저장
    debugFile := A_WorkingDir "\configs\debug_controls.txt"

    ; MT4 찾기
    mt4ID := 0
    WinGet, wins, List
    Loop, %wins% {
        id := wins%A_Index%
        WinGet, proc, ProcessName, ahk_id %id%
        if (proc = "terminal.exe") {
            mt4ID := id
            break
        }
    }

    if (!mt4ID) {
        MsgBox, 48, 오류, MT4를 찾을 수 없습니다.
        return
    }

    WinGetTitle, mt4Title, ahk_id %mt4ID%
    WinGet, ctrlList, ControlList, ahk_id %mt4ID%

    ; 디버그 파일 작성
    FileDelete, %debugFile%
    FileAppend, === MT4 Control Debug Info ===`n, %debugFile%
    FileAppend, MT4 Title: %mt4Title%`n, %debugFile%
    FileAppend, `n=== All ComboBoxes ===`n, %debugFile%

    Loop, Parse, ctrlList, `n
    {
        ctrl := A_LoopField
        if (InStr(ctrl, "ComboBox")) {
            ControlGet, comboText, Choice,, %ctrl%, ahk_id %mt4ID%
            ControlGet, comboItems, List,, %ctrl%, ahk_id %mt4ID%

            FileAppend, `n[%ctrl%]`n, %debugFile%
            FileAppend, Current: %comboText%`n, %debugFile%
            FileAppend, Items:`n, %debugFile%

            itemIdx := 0
            Loop, Parse, comboItems, `n
            {
                itemIdx++
                FileAppend,   %itemIdx%: %A_LoopField%`n, %debugFile%
            }
        }
    }

    FileAppend, `n=== All Buttons ===`n, %debugFile%
    Loop, Parse, ctrlList, `n
    {
        ctrl := A_LoopField
        if (InStr(ctrl, "Button")) {
            ControlGetText, btnText, %ctrl%, ahk_id %mt4ID%
            FileAppend, [%ctrl%] %btnText%`n, %debugFile%
        }
    }

    FileAppend, `n=== Date Controls ===`n, %debugFile%
    Loop, Parse, ctrlList, `n
    {
        ctrl := A_LoopField
        if (InStr(ctrl, "SysDateTimePick32")) {
            ControlGetText, dateText, %ctrl%, ahk_id %mt4ID%
            FileAppend, [%ctrl%] %dateText%`n, %debugFile%
        }
    }

    MsgBox, 64, 저장 완료, 디버그 정보가 저장되었습니다:`n%debugFile%`n`n파일을 열어서 ComboBox 목록을 확인하세요.
    Run, notepad.exe "%debugFile%"
return

ExitApp:
GuiClose:
    ExitApp
return
