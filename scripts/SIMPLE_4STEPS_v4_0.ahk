#NoEnv

#SingleInstance Force

CoordMode, Mouse, Screen

SetMouseDelay, 50

; =====================================================

; 4단계 백테스트 자동화 v3.5 (EA 중심)

; - SET 없을 때: EA_Symbol_TF_계정번호.htm

; - 중복 시: 날짜 추가 -> 시간 추가

; - v3.5: 테스트 기간(날짜) 설정 기능 추가

; =====================================================

; v2.0: 상위 폴더의 configs 사용

SetWorkingDir, %A_ScriptDir%\..

iniFile := A_WorkingDir "\configs\current_config.ini"

logFile := A_WorkingDir "\scripts\simple_4steps_v2_log.txt"

; 파라미터 (v2.0: EA이름도 파라미터로 받음 - 인코딩 문제 우회)

; 파라미터: EA이름(base64 or index), Symbol, TF, testNumber

paramEA := A_Args[1]
targetSymbol := A_Args[2]
targetPeriod := A_Args[3]
testNumber := A_Args[4]

; [FIX] A_Args 실패 시 INI 폴백 (symbol/period)
if (targetSymbol = "") {
    IniRead, targetSymbol, %iniFile%, current_backtest, symbol, SKIP
    FileAppend, [FALLBACK] symbol from INI: %targetSymbol%`n, %logFile%
}
if (targetPeriod = "") {
    IniRead, targetPeriod, %iniFile%, current_backtest, period, SKIP
    FileAppend, [FALLBACK] period from INI: %targetPeriod%`n, %logFile%
}
if (paramEA = "" or paramEA = "1") {
    iniEA := ""
    IniRead, iniEA, %iniFile%, current_backtest, ea_name, NONE
    if (iniEA != "NONE" and iniEA != "")
        paramEA := iniEA
}
FileAppend, [ARGS] arg1=%paramEA% arg2=%targetSymbol% arg3=%targetPeriod%`n, %logFile%

if (paramEA = "")

    paramEA := "1"

if (targetSymbol = "")

    targetSymbol := "SKIP"

if (targetPeriod = "")

    targetPeriod := "SKIP"

if (testNumber = "")

    testNumber := 0

; EA 이름 파라미터 처리: 숫자면 인덱스

if paramEA is integer

{

    targetEAIndex := paramEA

} else {

    ; [FIX v4.7] EA 이름 문자열이 전달된 경우 -> 0으로 설정하여 INI에서 ea_index 읽도록 강제
    targetEAIndex := 0

}

; EA 이름은 별도 텍스트 파일에서 읽기 (UTF-8 인코딩 문제 해결)

eaNameFile := A_WorkingDir "\configs\current_ea_name.txt"

filenameEA := ""

; [FIX v4.1] paramEA(arg1) 우선 사용 - v3.7 방식
if (paramEA != "" && paramEA != "1" && paramEA != "NONE") {
    filenameEA := paramEA
    if (!InStr(filenameEA, ".ex4"))
        filenameEA := filenameEA . ".ex4"
    FileAppend, [FIX] filenameEA from arg1: %filenameEA%`n, %logFile%
} else IfExist, %eaNameFile%

{

    FileRead, filenameEA, %eaNameFile%

    filenameEA := Trim(filenameEA)

    ; UTF-8 BOM 제거

    if (SubStr(filenameEA, 1, 3) = Chr(0xEF) Chr(0xBB) Chr(0xBF))

        filenameEA := SubStr(filenameEA, 4)

}

IfNotExist, %iniFile%

{

    MsgBox, 16, Error, INI 파일이 없습니다!`n%iniFile%

    ExitApp

}

; =====================================================

; 설정 읽기

; =====================================================

; EA 인덱스가 유효하지 않으면 INI에서 읽기

if (targetEAIndex = 0 || targetEAIndex = "") {

    IniRead, targetEAIndex, %iniFile%, current_backtest, ea_index, 1

}

; 파일명용 EA가 비어있으면 INI에서 읽기 (인코딩 깨질 수 있음 - 백업용)

if (filenameEA = "" || filenameEA = "NONE") {

    IniRead, filenameEA, %iniFile%, current_backtest, ea_name, NONE

}

IniRead, hasSet, %iniFile%, current_backtest, has_set, 0

IniRead, setFileName, %iniFile%, filename, set_file,

IniRead, accountNumber, %iniFile%, account, number, 0

; v2.0 FIX: tester.ini 직접 수정 (콤보박스 인식 실패 대비)

IniRead, terminalPath, %iniFile%, folders, terminal_path, NONE

IniRead, eaPath, %iniFile%, folders, ea_path, NONE

if (terminalPath != "NONE" && terminalPath != "") {

    StringReplace, terminalPath, terminalPath, /, \, All

    ; 포터블 MT4: tester.ini는 루트에 있음 (서브폴더 아님)
    testerIniPath := terminalPath "\tester.ini"
    if (!FileExist(testerIniPath))
        testerIniPath := terminalPath "\tester\tester.ini"  ; 비포터블 폴백

    ; EA 경로에서 Experts 이후 부분 추출 (예: FX_TR\EA_NAME)

    eaRelativePath := ""

    if (eaPath != "NONE" && eaPath != "" && filenameEA != "" && filenameEA != "NONE") {

        StringReplace, eaPath, eaPath, /, \, All

        ; Experts\ 이후 부분 찾기

        expertsPos := InStr(eaPath, "\Experts\")

        if (expertsPos > 0) {

            eaRelativePath := SubStr(eaPath, expertsPos + 9) . "\" . filenameEA

        } else {

            eaRelativePath := filenameEA

        }

        StringReplace, eaRelativePath, eaRelativePath, .ex4, , All

        ; tester.ini 업데이트

        IfExist, %testerIniPath%

        {

            IniWrite, %eaRelativePath%, %testerIniPath%, Tester, Expert
            IniWrite, %eaRelativePath%, %testerIniPath%, Tester, TestExpert

            IniWrite, %targetSymbol%, %testerIniPath%, Tester, Symbol
            IniWrite, %targetSymbol%, %testerIniPath%, Tester, TestSymbol

            ; Period 변환 (M5 -> 5, H1 -> 60 등)

            testerPeriod := targetPeriod

            if (targetPeriod = "M1")

                testerPeriod := "M1"

            else if (targetPeriod = "M5")

                testerPeriod := "M5"

            else if (targetPeriod = "M15")

                testerPeriod := "M15"

            else if (targetPeriod = "M30")

                testerPeriod := "M30"

            else if (targetPeriod = "H1")

                testerPeriod := "H1"

            else if (targetPeriod = "H4")

                testerPeriod := "H4"

            IniWrite, %testerPeriod%, %testerIniPath%, Tester, Period

            ; 날짜 설정 (testFromDate/testToDate 가 있을 때만)
            if (testFromDate != "" && testToDate != "") {
                IniWrite, %testFromDate%, %testerIniPath%, Tester, FromDate
                IniWrite, %testToDate%, %testerIniPath%, Tester, ToDate
                IniWrite, 1, %testerIniPath%, Tester, UseDate
            }

            FileAppend, [TESTER.INI] Updated: Expert=%eaRelativePath% Symbol=%targetSymbol% Period=%testerPeriod% From=%testFromDate% To=%testToDate%`n, %logFile%

            ; v4.2: tester.ini 수정 후 MT4가 이를 인식하도록 새로고침 시도

            ; Strategy Tester 창을 닫았다 열기 (Ctrl+R 토글) 대신

            ; F6 키로 tester 설정 다시 로드 시도

            global testerIniUpdated := true

        }

    }

}

FileAppend, `n=== SIMPLE 4 STEPS v3.5 - Test #%testNumber% ===`n, %logFile%

FileAppend, EA Index: %targetEAIndex%  FilenameEA: %filenameEA%`n, %logFile%

FileAppend, Symbol: %targetSymbol%  Period: %targetPeriod%`n, %logFile%

; =====================================================
; MT4 찾기 (모든 브로커) - Properties 창 제외
; =====================================================

; 먼저 모든 대화상자 닫기
Loop, 5
{
    IfWinExist, ahk_class #32770
    {
        WinClose, ahk_class #32770
        Sleep, 100
    }
    else
        break
}

mt4ID := 0
WinGet, wins, List
Loop, %wins% {
    id := wins%A_Index%
    WinGet, proc, ProcessName, ahk_id %id%
    if (proc = "terminal.exe") {
        WinGetClass, winClass, ahk_id %id%
        if (winClass = "#32770")
            continue

        WinGetTitle, winTitle, ahk_id %id%

        if (StrLen(winTitle) < 10)
            continue

        if (InStr(winTitle, "저장") or InStr(winTitle, "Save") or InStr(winTitle, "속성") or InStr(winTitle, "Properties"))
            continue

        if (!InStr(winTitle, "-") and !InStr(winTitle, ":"))
            continue

        mt4ID := id
        break
    }
}

if (!mt4ID) {
    FileAppend, ERROR: MT4 not found (terminal.exe with valid title)`n, %logFile%
    MsgBox, 16, Error, MT4 (terminal.exe)를 찾을 수 없습니다!
    ExitApp, 1
}

WinGetTitle, mt4Title, ahk_id %mt4ID%
FileAppend, MT4: %mt4Title%`n, %logFile%

WinMove, ahk_id %mt4ID%, , 0, 0, 960, 1036
Sleep, 100
WinActivate, ahk_id %mt4ID%
Sleep, 200

; v4.1: Ctrl+R 제거 (토글이라 열려있으면 닫힘)

WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%

; 컨트롤 읽기 (v2.6: 기본값을 INI 파일 기준으로 수정)
IniRead, startButtonClassNN, %iniFile%, tester_controls, start_button, Button10
IniRead, progressBarClassNN, %iniFile%, tester_controls, progress_bar, msctls_progress321
IniRead, periodComboClassNN, %iniFile%, tester_controls, period_combo, ComboBox4
IniRead, eaComboClassNN, %iniFile%, tester_controls, ea_combo, ComboBox2
IniRead, eaTypeComboClassNN, %iniFile%, tester_controls, ea_type_combo, ComboBox1
IniRead, symbolComboClassNN, %iniFile%, tester_controls, symbol_combo, ComboBox3

; v2.6: INI 읽기 디버깅
FileAppend, [DEBUG] INI Path: %iniFile%`n, %logFile%
FileAppend, [DEBUG] ea_combo raw: %eaComboClassNN%`n, %logFile%
FileAppend, [DEBUG] symbol_combo raw: %symbolComboClassNN%`n, %logFile%

; v2.6: symbol_combo가 비어있으면 기본값 사용
if (symbolComboClassNN = "" || symbolComboClassNN = "ERROR") {
    symbolComboClassNN := "ComboBox3"
    FileAppend, [DEBUG] symbol_combo was empty, using default: ComboBox3`n, %logFile%
}
; v3.5: 날짜 관련 컨트롤
IniRead, useDateCheckboxNN, %iniFile%, tester_controls, use_date_checkbox, ERROR
IniRead, fromDateEditNN, %iniFile%, tester_controls, from_date_edit, ERROR
IniRead, toDateEditNN, %iniFile%, tester_controls, to_date_edit, ERROR
; Visual mode 체크박스 (체크되어 있으면 해제해야 함)
IniRead, visualModeCheckboxNN, %iniFile%, tester_controls, visual_mode_checkbox, ERROR
; v3.5: 날짜 설정값
IniRead, testDateEnable, %iniFile%, test_date, enable, 0
IniRead, testFromDate, %iniFile%, test_date, from_date,
IniRead, testToDate, %iniFile%, test_date, to_date,

; [v8.0 fix] 날짜 읽은 후 tester.ini에 재동기화 (앞서 변수 비어있을 수 있음)
if (testFromDate != "" && testToDate != "") {
    IfExist, %testerIniPath%
    {
        IniWrite, %testFromDate%, %testerIniPath%, Tester, FromDate
        IniWrite, %testToDate%, %testerIniPath%, Tester, ToDate
        IniWrite, 1, %testerIniPath%, Tester, UseDate
        FileAppend, [TESTER.INI] Date re-sync: From=%testFromDate% To=%testToDate%`n, %logFile%
    }
}

FileAppend, Controls: EA=%eaComboClassNN% Symbol=%symbolComboClassNN% Period=%periodComboClassNN%`n, %logFile%
FileAppend, Date Controls: UseDate=%useDateCheckboxNN% From=%fromDateEditNN% To=%toDateEditNN%`n, %logFile%
FileAppend, Date Settings: Enable=%testDateEnable% From=%testFromDate% To=%testToDate%`n, %logFile%

; =====================================================
; [FIX v4.8] 조기 EA 타이핑 (v3.8 PASS 방식 이식)
; ^r 리프레시 전에 먼저 EA ComboBox에 이름 입력 - 동일 EA 반복 방지
; =====================================================
if (filenameEA != "" && filenameEA != "NONE") {
    earlySearchEA := StrReplace(filenameEA, ".ex4", "")
    FileAppend, [v4.8 EARLY] EA typing BEFORE ^r: %earlySearchEA%`n, %logFile%
    WinActivate, ahk_id %mt4ID%
    WinWaitActive, ahk_id %mt4ID%,, 2
    Sleep, 500
    ControlClick, %eaComboClassNN%, ahk_id %mt4ID%
    Sleep, 300
    Send, {Home}
    Sleep, 300
    Send, %earlySearchEA%
    Sleep, 500
    Send, {Enter}
    Sleep, 500
    FileAppend, [v4.8 EARLY] Done. Now checking ComboBox...`n, %logFile%
    ControlGet, earlySelectedEA, Choice,, %eaComboClassNN%, ahk_id %mt4ID%
    FileAppend, [v4.8 EARLY] EA ComboBox now shows: %earlySelectedEA%`n, %logFile%
}


; =====================================================
; STEP 0-0: Expert Advisor 타입 강제 설정 (자동 감지 방식)
; =====================================================
FileAppend, [STEP 0-0] Forcing Expert Advisor type...`n, %logFile%
FileAppend, Configured EA Type ComboBox: %eaTypeComboClassNN%`n, %logFile%

WinActivate, ahk_id %mt4ID%
Sleep, 100

; 먼저 EA Type ComboBox의 내용 확인
ControlGet, eaTypeList, List,, %eaTypeComboClassNN%, ahk_id %mt4ID%
FileAppend, EA Type ComboBox (%eaTypeComboClassNN%) contents: %eaTypeList%`n, %logFile%

; EA Type 콤보박스가 비어있거나 Expert/Indicator가 없으면 자동 감지
foundEaTypeCombo := ""
if (eaTypeList = "" or (!InStr(eaTypeList, "Expert") and !InStr(eaTypeList, "Indicator") and !InStr(eaTypeList, "지표"))) {
    FileAppend, EA Type ComboBox empty or invalid. Scanning all ComboBoxes...`n, %logFile%

    ; 모든 ComboBox 스캔하여 EA Type 찾기
    WinGet, scanControls, ControlList, ahk_id %mt4ID%
    Loop, Parse, scanControls, `n
    {
        scanCtrl := A_LoopField
        if (InStr(scanCtrl, "ComboBox")) {
            ControlGet, scanList, List,, %scanCtrl%, ahk_id %mt4ID%
            if (InStr(scanList, "Expert") or InStr(scanList, "Indicator") or InStr(scanList, "지표") or InStr(scanList, "전문가")) {
                foundEaTypeCombo := scanCtrl
                FileAppend, FOUND EA Type ComboBox: %scanCtrl%`n, %logFile%
                break
            }
        }
    }

    if (foundEaTypeCombo != "") {
        eaTypeComboClassNN := foundEaTypeCombo
    }
}

; v3.6: EA Type을 먼저 "Expert Advisor"로 변경하여 EA 목록 로드
; 한국어 MT4: "시스템 트레이딩" 또는 첫 번째 항목이 Expert Advisor
FileAppend, Checking EA list in: %eaComboClassNN%`n, %logFile%

; 현재 EA 목록 확인
ControlGet, testList, List,, %eaComboClassNN%, ahk_id %mt4ID%
testCount := 0
hasEx4 := false
Loop, Parse, testList, `n
{
    testCount++
    if (InStr(A_LoopField, ".ex4") || InStr(A_LoopField, ".mq4"))
        hasEx4 := true
}

FileAppend, EA ComboBox (%eaComboClassNN%): %testCount% items (hasEx4: %hasEx4%)`n, %logFile%

; EA 목록이 비어있으면 EA Type을 강제로 변경
if (testCount = 0 || !hasEx4) {
    FileAppend, EA ComboBox empty. Forcing Expert Advisor type...`n, %logFile%

    ; EA Type 콤보박스에서 첫 번째 항목 선택 (Expert Advisor / 시스템 트레이딩)
    Control, Choose, 1, %eaTypeComboClassNN%, ahk_id %mt4ID%
    Sleep, 300

    ; 변경 확인
    ControlGet, newType, Choice,, %eaTypeComboClassNN%, ahk_id %mt4ID%
    FileAppend, EA Type changed to: %newType%`n, %logFile%

    ; EA 목록 다시 확인
    Sleep, 200
    ControlGet, testList, List,, %eaComboClassNN%, ahk_id %mt4ID%
    testCount := 0
    hasEx4 := false
    Loop, Parse, testList, `n
    {
        testCount++
        if (InStr(A_LoopField, ".ex4") || InStr(A_LoopField, ".mq4"))
            hasEx4 := true
    }
    FileAppend, After type change - EA ComboBox: %testCount% items (hasEx4: %hasEx4%)`n, %logFile%
}

; v4.1: EA 목록이 비어있으면 tester.ini로 대체 (Ctrl+R 제거)
; tester.ini는 이미 스크립트 시작 시 업데이트됨

; 여전히 EA 목록이 비어있으면 다른 콤보박스에서 EA 목록 찾기
if (testCount = 0 || !hasEx4) {
    FileAppend, EA ComboBox still empty, scanning other ComboBoxes...`n, %logFile%
    WinGet, scanCtrls, ControlList, ahk_id %mt4ID%
    Loop, Parse, scanCtrls, `n
    {
        scanCtrl := A_LoopField
        if (InStr(scanCtrl, "ComboBox") && scanCtrl != eaTypeComboClassNN && scanCtrl != symbolComboClassNN && scanCtrl != periodComboClassNN) {
            ControlGet, scanList, List,, %scanCtrl%, ahk_id %mt4ID%
            scanCount := 0
            scanHasEx4 := false
            Loop, Parse, scanList, `n
            {
                scanCount++
                if (InStr(A_LoopField, ".ex4") || InStr(A_LoopField, ".mq4"))
                    scanHasEx4 := true
            }
            FileAppend, Scanning %scanCtrl%: %scanCount% items (hasEx4: %scanHasEx4%)`n, %logFile%
            if (scanCount > 2 && scanHasEx4) {
                FileAppend, FOUND EA list in %scanCtrl%`n, %logFile%
                eaComboClassNN := scanCtrl
                IniWrite, %scanCtrl%, %iniFile%, tester_controls, ea_combo
                testCount := scanCount
                break
            }
        }
    }
}

FileAppend, Final EA ComboBox: %eaComboClassNN%, EA count: %testCount%`n, %logFile%

; =====================================================
; [DELETED - DO NOT RESTORE] Ctrl+R / Send, ^r - PERMANENTLY REMOVED
; MT4 Strategy Tester 창을 닫아버려 테스트가 멈추는 직접 원인
; !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
; !! 절대로 Send ^r 또는 Ctrl+R 을 추가하지 말 것 !!
; !! 추가 즉시 백테스트 중단됨 - 사용자 명시 삭제 요청 !!
; !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

; =====================================================
; STEP 0-A: EA 선택 (v3.7 타이핑 방식 - 이름 직접 입력)
; =====================================================
FileAppend, [STEP 0-A] EA typing: name=%filenameEA%`n, %logFile%

WinActivate, ahk_id %mt4ID%
WinWaitActive, ahk_id %mt4ID%,, 2
Sleep, 500

if (filenameEA != "" && filenameEA != "NONE") {
    searchEA := StrReplace(filenameEA, ".ex4", "")
    ControlClick, %eaComboClassNN%, ahk_id %mt4ID%
    Sleep, 300
    Send, {Home}
    Sleep, 300
    Send, %searchEA%
    Sleep, 500
    Send, {Enter}
    Sleep, 500
    FileAppend, [v3.7] Typed EA name: %searchEA%`n, %logFile%
} else {
    FileAppend, [v3.7] WARNING: filenameEA empty, skipping EA selection`n, %logFile%
}

Sleep, 100
; 선택된 EA 이름을 ComboBox에서 직접 읽기 (가장 정확한 값)
ControlGet, selectedEA, Choice,, %eaComboClassNN%, ahk_id %mt4ID%
FileAppend, EA set to: %selectedEA%`n, %logFile%

; [FIX] EA 선택 검증 - 요청한 EA와 실제 선택된 EA 비교
if (filenameEA != "" && filenameEA != "NONE") {
    checkEA := StrReplace(selectedEA, ".ex4", "")
    expectedEA := StrReplace(filenameEA, ".ex4", "")
    if (checkEA != expectedEA) {
        FileAppend, [WARNING] EA MISMATCH! Expected=%expectedEA% Got=%checkEA%`n, %logFile%
        FileAppend, [WARNING] tester.ini has correct EA - MT4 will use tester.ini value`n, %logFile%
    } else {
        FileAppend, [OK] EA verified: %checkEA%`n, %logFile%
    }
}

; 파일명에 사용할 EA 이름: ComboBox에서 읽은 값, 비어있으면 filenameEA 사용
if (selectedEA != "")
    currentEA := selectedEA
else if (filenameEA != "" && filenameEA != "NONE")
    currentEA := filenameEA
else
    currentEA := selectedEA

; =====================================================
; STEP 0-B: Symbol 변경
; =====================================================
if (targetSymbol != "SKIP") {
    FileAppend, [STEP 0-B] Symbol: %targetSymbol%`n, %logFile%

    WinActivate, ahk_id %mt4ID%
    Sleep, 200

    ; 목록에서 검색
    symbolList := ""
    Loop, 3
    {
        ControlGet, symbolList, List,, %symbolComboClassNN%, ahk_id %mt4ID%
        if (symbolList != "")
            break
        WinActivate, ahk_id %mt4ID%
        Sleep, 200
    }

    if (symbolList = "") {
        FileAppend, ERROR: Cannot read symbol list`n, %logFile%
        ExitApp, 1
    }

    ; XAU와 GOLD 교차 검색
    searchKeyword := targetSymbol
    altKeyword := ""
    if (InStr(targetSymbol, "XAU") or InStr(targetSymbol, "xau"))
        altKeyword := "GOLD"
    else if (InStr(targetSymbol, "GOLD") or InStr(targetSymbol, "gold"))
        altKeyword := "XAU"

    foundIndex := 0
    searchIndex := 0
    Loop, Parse, symbolList, `n
    {
        searchIndex++
        checkSymbol := A_LoopField

        if (InStr(checkSymbol, ",")) {
            StringSplit, parts, checkSymbol, `,
            checkSymbol := Trim(parts1)
        }

        StringUpper, checkUpper, checkSymbol
        StringUpper, targetUpper, targetSymbol

        if (InStr(checkUpper, targetUpper)) {
            foundIndex := searchIndex
            break
        }
        if (altKeyword != "" and InStr(checkUpper, altKeyword)) {
            foundIndex := searchIndex
            break
        }
    }

    if (foundIndex > 0) {
        Control, Choose, %foundIndex%, %symbolComboClassNN%, ahk_id %mt4ID%
        Sleep, 100
        ControlGet, currentSymbol, Choice,, %symbolComboClassNN%, ahk_id %mt4ID%

        saveSymbol := currentSymbol
        if (InStr(saveSymbol, ",")) {
            StringSplit, parts, saveSymbol, `,
            saveSymbol := Trim(parts1)
        }

        FileAppend, Symbol set to: %currentSymbol%`n, %logFile%
        IniWrite, %saveSymbol%, %iniFile%, current_backtest, symbol
    } else {
        FileAppend, ERROR: Symbol "%targetSymbol%" not found!`n, %logFile%
        ExitApp, 1
    }
}

; =====================================================
; STEP 0-C: Period 변경
; =====================================================
if (targetPeriod != "SKIP") {
    FileAppend, [STEP 0-C] Period: %targetPeriod%`n, %logFile%

    WinActivate, ahk_id %mt4ID%
    Sleep, 100

    Control, ChooseString, %targetPeriod%, %periodComboClassNN%, ahk_id %mt4ID%
    Sleep, 200

    ControlGet, currentPeriod, Choice,, %periodComboClassNN%, ahk_id %mt4ID%
    FileAppend, Period set to: %currentPeriod%`n, %logFile%

    IniWrite, %currentPeriod%, %iniFile%, current_backtest, period
}

Sleep, 200

; =====================================================
; v3.5: STEP 0-D: 테스트 기간(날짜) 설정
; =====================================================
if (testDateEnable = 1) {
    FileAppend, [STEP 0-D] Setting test date range...`n, %logFile%

    WinActivate, ahk_id %mt4ID%
    Sleep, 100

    ; Use date 체크박스 활성화 (여러 방법 시도)
    useDateFound := false

    ; 방법 1: INI에서 읽은 체크박스 사용
    if (useDateCheckboxNN != "ERROR" && useDateCheckboxNN != "") {
        ControlGet, useDateState, Checked,, %useDateCheckboxNN%, ahk_id %mt4ID%
        if (!useDateState) {
            Control, Check,, %useDateCheckboxNN%, ahk_id %mt4ID%
            Sleep, 100
            FileAppend, Use date checkbox CHECKED (INI: %useDateCheckboxNN%)`n, %logFile%
        } else {
            FileAppend, Use date checkbox already checked`n, %logFile%
        }
        useDateFound := true
    }

    ; 방법 2: INI에 없으면 실시간으로 체크박스 검색
    if (!useDateFound) {
        FileAppend, Use date checkbox not in INI, searching...`n, %logFile%
        WinGet, ctrlList, ControlList, ahk_id %mt4ID%
        Loop, Parse, ctrlList, `n
        {
            ctrl := A_LoopField
            if (InStr(ctrl, "Button")) {
                ControlGetText, btnText, %ctrl%, ahk_id %mt4ID%
                ; "Use date", "날짜 사용", "기간", "date" 등 검색
                if (InStr(btnText, "Use date") or InStr(btnText, "날짜") or InStr(btnText, "기간") or InStr(btnText, "date") or InStr(btnText, "Date")) {
                    ; 시작/중지, Visual mode 등 제외
                    if (!InStr(btnText, "시작") and !InStr(btnText, "Start") and !InStr(btnText, "중지") and !InStr(btnText, "Stop") and !InStr(btnText, "Visual") and !InStr(btnText, "시각화") and !InStr(btnText, "최적화") and !InStr(btnText, "Optimization")) {
                        FileAppend, Found date checkbox: %ctrl% (%btnText%)`n, %logFile%
                        ControlGet, useDateState, Checked,, %ctrl%, ahk_id %mt4ID%
                        if (!useDateState) {
                            Control, Check,, %ctrl%, ahk_id %mt4ID%
                            Sleep, 100
                            FileAppend, Use date checkbox CHECKED (found: %ctrl%)`n, %logFile%
                        }
                        useDateFound := true
                        ; INI에 저장해서 다음번엔 바로 사용
                        IniWrite, %ctrl%, %iniFile%, tester_controls, use_date_checkbox
                        break
                    }
                }
            }
        }
    }

    ; 방법 3: 그래도 못 찾으면 Button 목록에서 가능한 후보 출력
    if (!useDateFound) {
        FileAppend, WARNING: Use date checkbox not found! Listing all buttons:`n, %logFile%
        WinGet, ctrlList, ControlList, ahk_id %mt4ID%
        Loop, Parse, ctrlList, `n
        {
            ctrl := A_LoopField
            if (InStr(ctrl, "Button")) {
                ControlGetText, btnText, %ctrl%, ahk_id %mt4ID%
                FileAppend,   %ctrl%: %btnText%`n, %logFile%
            }
        }
        FileAppend, Continuing with date setting (checkbox may not be checked)`n, %logFile%
    }

    ; From 날짜 설정 (SysDateTimePick32 - 필드별 입력)
    if (fromDateEditNN != "ERROR" && fromDateEditNN != "" && testFromDate != "") {
        ; 날짜 파싱 (yyyy.MM.dd 형식)
        StringSplit, dateParts, testFromDate, .
        fromYear := dateParts1
        fromMonth := dateParts2
        fromDay := dateParts3

        ; 컨트롤 위치 가져오기
        ControlGetPos, ctrlX, ctrlY, ctrlW, ctrlH, %fromDateEditNN%, ahk_id %mt4ID%
        WinGetPos, winX, winY,,, ahk_id %mt4ID%

        ; 컨트롤 클릭 (활성화)
        clickX := winX + ctrlX + 15
        clickY := winY + ctrlY + (ctrlH // 2)

        Click, %clickX%, %clickY%
        Sleep, 100

        ; MT4 DateTimePicker는 yyyy.MM.dd 형식
        ; 년도 입력 -> 오른쪽 화살표 -> 월 입력 -> 오른쪽 화살표 -> 일 입력
        Send, %fromYear%
        Sleep, 100
        Send, {Right}
        Sleep, 100
        Send, %fromMonth%
        Sleep, 100
        Send, {Right}
        Sleep, 100
        Send, %fromDay%
        Sleep, 100

        ; Enter로 확정
        Send, {Enter}
        Sleep, 100

        FileAppend, From date set to: %fromYear%.%fromMonth%.%fromDay% (field-by-field)`n, %logFile%
    }

    ; To 날짜 설정 (SysDateTimePick32)
    if (toDateEditNN != "ERROR" && toDateEditNN != "" && testToDate != "") {
        StringSplit, dateParts, testToDate, .
        toYear := dateParts1
        toMonth := dateParts2
        toDay := dateParts3

        ; 컨트롤 위치 가져오기
        ControlGetPos, ctrlX, ctrlY, ctrlW, ctrlH, %toDateEditNN%, ahk_id %mt4ID%
        WinGetPos, winX, winY,,, ahk_id %mt4ID%

        ; 컨트롤 클릭 (활성화)
        clickX := winX + ctrlX + 15
        clickY := winY + ctrlY + (ctrlH // 2)

        Click, %clickX%, %clickY%
        Sleep, 100

        ; 년도 입력 -> 오른쪽 화살표 -> 월 입력 -> 오른쪽 화살표 -> 일 입력
        Send, %toYear%
        Sleep, 100
        Send, {Right}
        Sleep, 100
        Send, %toMonth%
        Sleep, 100
        Send, {Right}
        Sleep, 100
        Send, %toDay%
        Sleep, 100

        ; Enter로 확정
        Send, {Enter}
        Sleep, 100

        FileAppend, To date set to: %toYear%.%toMonth%.%toDay% (field-by-field)`n, %logFile%
    }

    Sleep, 100
} else {
    FileAppend, [STEP 0-D] Date range disabled (using all data)`n, %logFile%

    ; 날짜 사용 체크박스 해제
    if (useDateCheckboxNN != "ERROR" && useDateCheckboxNN != "") {
        ControlGet, useDateState, Checked,, %useDateCheckboxNN%, ahk_id %mt4ID%
        if (useDateState) {
            Control, Uncheck,, %useDateCheckboxNN%, ahk_id %mt4ID%
            Sleep, 100
            FileAppend, Use date checkbox UNCHECKED`n, %logFile%
        }
    }
}

Sleep, 100

; =====================================================
; [v4.0] STEP 0-E: SET 파일 로드 -> tester.ini 직접 수정 방식
; =====================================================
IniRead, setFilePath, %iniFile%, current_backtest, set_file_path, ERROR
StringReplace, setFilePath, setFilePath, /, \, All

FileAppend, [STEP 0-E] SET loading via tester.ini modification`n, %logFile%
FileAppend, [DEBUG] setFilePath=%setFilePath%`n, %logFile%

if (setFilePath != "ERROR" && setFilePath != "" && FileExist(setFilePath)) {
    ; Read SET file content
    FileRead, setContent, %setFilePath%
    FileAppend, [DEBUG] SET file found and read successfully`n, %logFile%

    ; Get terminal path and tester.ini location
    IniRead, terminalPath, %iniFile%, folders, terminal_path, NOTSET
    if (terminalPath != "NOTSET") {
        StringReplace, terminalPath, terminalPath, /, \, All
        testerIniPath := terminalPath . "\tester.ini"
        if (!FileExist(testerIniPath))
            testerIniPath := terminalPath . "\tester\tester.ini"

        ; Get EA name for tester.ini section
        ; [FIX] eaRelativePath(gg\EA06 형식)를 우선 사용, 없으면 current_backtest 폴백
        if (eaRelativePath != "") {
            eaSection := eaRelativePath
        } else {
            IniRead, eaFileName, %iniFile%, current_backtest, ea_name, NOTSET
            StringReplace, eaSection, eaFileName, .ex4, , All
        }
        if (eaSection != "" && eaSection != "NOTSET") {
            setParamCount := 0

            ; [v4.1] Parse ALL parameters from SET file (Key=Value||... format)
            Loop, Parse, setContent, `n, `r
            {
                setLine := Trim(A_LoopField)
                if (setLine == "" || SubStr(setLine, 1, 1) == ";" || SubStr(setLine, 1, 1) == "[")
                    continue
                if RegExMatch(setLine, "^([^=]+)=([\d\.\-]+)\|", pm) {
                    pName  := Trim(pm1)
                    pValue := pm2
                    IniWrite, %pValue%, %testerIniPath%, %eaSection%, %pName%
                    setParamCount++
                } else if RegExMatch(setLine, "^([^=]+)=([^|]+)", pm) {
                    pName  := Trim(pm1)
                    pValue := Trim(pm2)
                    IniWrite, %pValue%, %testerIniPath%, %eaSection%, %pName%
                    setParamCount++
                }
            }
            FileAppend, [SUCCESS] STEP 0-E: SET 파라미터 %setParamCount%개 → tester.ini [%eaSection%] 주입 완료`n, %logFile%

            ; [v9.71] bt_combo SL/TP → InpFixedSL_1 / InpFixedTP_1 추가 주입
            IniRead, btComboSL, %iniFile%, bt_combo, sl, 0
            IniRead, btComboTP, %iniFile%, bt_combo, tp, 0
            if (btComboSL != "0" && btComboSL != "" && btComboSL != "NOTSET") {
                IniWrite, %btComboSL%, %testerIniPath%, %eaSection%, InpFixedSL_1
                IniWrite, %btComboTP%, %testerIniPath%, %eaSection%, InpFixedTP_1
                FileAppend, [SUCCESS] bt_combo SL=%btComboSL% TP=%btComboTP% 주입`n, %logFile%
            }
        } else {
            FileAppend, [WARNING] EA name not found in config`n, %logFile%
        }
    } else {
        FileAppend, [WARNING] Terminal path not found`n, %logFile%
    }
} else {
    FileAppend, [STEP 0-E] No SET file or file not found: %setFilePath%`n, %logFile%

    ; =====================================================
    ; [v9.72 FIX] STEP 0-E2: bt_combo 직접 주입 (SET 파일 없이도 동작)
    ; 조합 백테스트 경로에서는 SET 파일이 없으므로, bt_combo에서 직접 읽어 tester.ini에 주입
    ; =====================================================
    IniRead, btComboLot, %iniFile%, bt_combo, lot, 0
    IniRead, btComboSL, %iniFile%, bt_combo, sl, 0
    IniRead, btComboTP, %iniFile%, bt_combo, tp, 0
    IniRead, btComboEA, %iniFile%, bt_combo, ea_name, NOTSET

    if (btComboLot != "0" && btComboLot != "" && btComboLot != "NOTSET") {
        ; terminal_path에서 tester.ini 경로 확인
        IniRead, terminalPath, %iniFile%, folders, terminal_path, NOTSET
        if (terminalPath != "NOTSET") {
            StringReplace, terminalPath, terminalPath, /, \, All
            testerIniPath := terminalPath . "\tester.ini"
            if (!FileExist(testerIniPath))
                testerIniPath := terminalPath . "\tester\tester.ini"

            ; EA 섹션명 결정: paramEA(현재 실행 EA) 우선 사용 → 스태일 방지
            if (paramEA != "" && paramEA != "1") {
                eaSection := paramEA
            } else {
                IniRead, eaFileName, %iniFile%, resume, ea_name, NOTSET
                if (eaFileName = "NOTSET" || eaFileName = "") {
                    eaFileName := btComboEA . ".ex4"
                }
                StringReplace, eaSection, eaFileName, .ex4, , All
            }
            FileAppend, [STEP 0-E2] eaSection resolved: %eaSection%`n, %logFile%

            ; [FIX] TestExpertParameters 유지 (Python이 SET 파일 생성 + 경로 설정함)
            ; combo 모드에서는 삭제하지 않음 — MT4가 SET 파일에서 파라미터를 읽어야 함
            IniRead, existingSetParam, %testerIniPath%, Tester, TestExpertParameters, NOTSET
            if (existingSetParam = "NOTSET" || existingSetParam = "") {
                FileAppend, [STEP 0-E2] No TestExpertParameters found (OK - will use tester.ini sections)`n, %logFile%
            } else {
                FileAppend, [STEP 0-E2] Keeping TestExpertParameters=%existingSetParam% (SET file mode)`n, %logFile%
            }

            ; [FIX] EA 섹션에서 BT_Patch 전용 키 제거 (이전 BT_Patch 실행 잔존 방지)
            IniDelete, %testerIniPath%, %eaSection%, InpBTLotIndex
            IniDelete, %testerIniPath%, %eaSection%, InpBTSLIndex
            IniDelete, %testerIniPath%, %eaSection%, InpBTTPIndex
            FileAppend, [STEP 0-E2 FIX] Deleted BT_Patch keys from [%eaSection%]`n, %logFile%

            ; [_BT EA FIX] _BT suffix EA는 InpBTMode=1 필수
            ; runner가 tester.ini에 기록한 InpBTMode를 AHK가 삭제하지 않도록 복원
            if (InStr(eaSection, "_BT")) {
                IniWrite, 1, %testerIniPath%, %eaSection%, InpBTMode
                FileAppend, [STEP 0-E2 BT_FIX] Restored InpBTMode=1 for _BT EA: %eaSection%`n, %logFile%
            }

            ; Lots_1 주입
            IniWrite, %btComboLot%, %testerIniPath%, %eaSection%, Lots_1
            FileAppend, [STEP 0-E2] Written Lots_1=%btComboLot% to tester.ini [%eaSection%]`n, %logFile%

            ; InpFixedSL / InpFixedTP 주입 (SLTP EA 파라미터명)
            if (btComboSL != "0" && btComboSL != "" && btComboSL != "NOTSET") {
                IniWrite, %btComboSL%, %testerIniPath%, %eaSection%, InpFixedSL
                IniWrite, %btComboTP%, %testerIniPath%, %eaSection%, InpFixedTP
                ; 구형 호환용 (InpFixedSL_1 도 함께 쓰는 EA 대비)
                IniWrite, %btComboSL%, %testerIniPath%, %eaSection%, InpFixedSL_1
                IniWrite, %btComboTP%, %testerIniPath%, %eaSection%, InpFixedTP_1
                FileAppend, [STEP 0-E2] Written InpFixedSL=%btComboSL% InpFixedTP=%btComboTP% to [%eaSection%]`n, %logFile%
            }
        } else {
            FileAppend, [WARNING] STEP 0-E2: terminal_path not found, skipping bt_combo injection`n, %logFile%
        }
    } else {
        FileAppend, [STEP 0-E2] bt_combo lot=0 or not set - no injection needed`n, %logFile%
    }
}

Sleep, 200

; =====================================================
; STEP 0-F: Inputs 탭에서 Lots_1 직접 수정 (START 전)
; =====================================================
if (setFilePath != "ERROR" && setFilePath != "" && FileExist(setFilePath)) {
    FileAppend, [STEP 0-F] Modifying Lots_1 in Inputs tab...`n, %logFile%
    
    ; Read lot size from SET file (supports Lots_1, LotSize, Lots, lot_size, etc.)
    FileRead, setContent, %setFilePath%
    lotsValue := ""
    if RegExMatch(setContent, "im)^(?:Lots_1|LotSize|Lots|lot_size|InpLots)=([\d\.]+)", match)
        lotsValue := match1
    if (lotsValue != "") {
        FileAppend, [DEBUG] Target lot=%lotsValue%`n, %logFile%
        
        ; Click Inputs/Settings tab in Tester window
        WinActivate, ahk_id %mt4ID%
        Send, ^{Tab}
        Sleep, 200
        
        ; Try to find Lots_1 edit field and modify it
        Loop, 20 {
            editCtrl := "Edit" . A_Index
            ControlGetText, ctrlText, %editCtrl%, ahk_id %mt4ID%
            if (ctrlText == "0.01" || ctrlText == "0.10" || ctrlText == "0.05") {
                ControlSetText, %editCtrl%, %lotsValue%, ahk_id %mt4ID%
                FileAppend, [SUCCESS] Set %editCtrl% to %lotsValue%`n, %logFile%
                Sleep, 100
            }
        }
        
        FileAppend, [STEP 0-F] Attempted to set Lots_1 in tester inputs`n, %logFile%
    }
}

Sleep, 200

; =====================================================
; STEP 0-G: Expert Properties → SET 파일 로드 (MT4 GUI 모드 유일한 방법)
; tester.ini [EA] 섹션은 MT4 GUI 모드에서 무시됨
; Expert Properties 다이얼로그에서 직접 Load 해야 파라미터 적용됨
; =====================================================
IniRead, termPathG, %iniFile%, folders, terminal_path, NOTSET
if (termPathG != "NOTSET") {
    StringReplace, termPathG, termPathG, /, \, All
    testerIniPathG := termPathG . "\tester.ini"
    IniRead, setParamFile, %testerIniPathG%, Tester, TestExpertParameters, NOTSET

    if (setParamFile != "NOTSET" && setParamFile != "") {
        ; SET 파일 전체 경로 구성 (tester/ 폴더에 저장됨)
        comboSetPath := termPathG . "\tester\" . setParamFile
        if (!FileExist(comboSetPath))
            comboSetPath := termPathG . "\MQL4\Experts\" . setParamFile

        if (FileExist(comboSetPath)) {
            FileAppend, [STEP 0-G] Loading SET file via Expert Properties: %comboSetPath%`n, %logFile%

            WinActivate, ahk_id %mt4ID%
            Sleep, 300

            ; 현재 열린 창 목록 기록 (나중에 새 창 감지용)
            beforeWins := ""
            WinGet, bwList, List
            Loop, %bwList%
            {
                bwHwnd := bwList%A_Index%
                beforeWins .= bwHwnd . ","
            }

            ; Expert Properties 열기: F7 키가 가장 안정적
            WinActivate, ahk_id %mt4ID%
            Sleep, 200
            Send, {F7}
            FileAppend, [STEP 0-G] Sent F7 to open Expert Properties`n, %logFile%
            Sleep, 1500

            ; 새로 나타난 창 찾기 (이전에 없던 창 = Expert Properties 다이얼로그)
            epHwnd := 0
            WinGet, awList, List
            Loop, %awList%
            {
                awHwnd := awList%A_Index%
                if (awHwnd = mt4ID)
                    continue
                if (!InStr(beforeWins, awHwnd . ",")) {
                    ; 새 창 발견 — 크기 확인 (Expert Properties는 작은 대화상자)
                    WinGetPos, _epX, _epY, _epW, _epH, ahk_id %awHwnd%
                    if (_epW < 900 && _epH < 700 && _epW > 100) {
                        epHwnd := awHwnd
                        WinGetTitle, epTitle, ahk_id %epHwnd%
                        FileAppend, [STEP 0-G] Expert Properties dialog found (new window): %epTitle% [%_epW%x%_epH%]`n, %logFile%
                        break
                    }
                }
            }

            if (epHwnd != 0) {
                WinActivate, ahk_id %epHwnd%
                Sleep, 300

                ; 모든 컨트롤 목록 + 버튼 텍스트 로깅
                WinGet, epCtrlList, ControlList, ahk_id %epHwnd%
                FileAppend, [STEP 0-G] Dialog controls:`n, %logFile%
                Loop, Parse, epCtrlList, `n
                {
                    _dc := A_LoopField
                    ControlGetText, _dcTxt, %_dc%, ahk_id %epHwnd%
                    if (_dcTxt != "")
                        FileAppend,   %_dc% = %_dcTxt%`n, %logFile%
                }

                ; "Inputs" 또는 "입력" 탭 클릭 (SysTabControl)
                Loop, Parse, epCtrlList, `n
                {
                    epCtrl := A_LoopField
                    if (InStr(epCtrl, "SysTabControl")) {
                        ; Inputs 탭은 보통 두 번째 (인덱스 1)
                        SendMessage, 0x1330, 1, 0, %epCtrl%, ahk_id %epHwnd%  ; TCM_SETCURSEL
                        Sleep, 100
                        ; 탭 변경 알림 (클릭으로 트리거)
                        ControlClick, %epCtrl%, ahk_id %epHwnd%,, LEFT, 1, x150 y10
                        Sleep, 500
                        FileAppend, [STEP 0-G] Inputs tab selected via %epCtrl%`n, %logFile%
                        break
                    }
                }

                ; "Load" / "불러오기" / "로드" 버튼 찾기 & 클릭
                loadClicked := false
                Loop, Parse, epCtrlList, `n
                {
                    ldCtrl := A_LoopField
                    if (!InStr(ldCtrl, "Button"))
                        continue
                    ControlGetText, ldBtnText, %ldCtrl%, ahk_id %epHwnd%
                    if (InStr(ldBtnText, "Load") || InStr(ldBtnText, "불러오기") || InStr(ldBtnText, "로드") || InStr(ldBtnText, "열기")) {
                        ControlClick, %ldCtrl%, ahk_id %epHwnd%
                        loadClicked := true
                        FileAppend, [STEP 0-G] Load button clicked: %ldCtrl% (%ldBtnText%)`n, %logFile%
                        break
                    }
                }

                if (loadClicked) {
                    Sleep, 1000

                    ; Open/열기 파일 다이얼로그 대기
                    fileDialogFound := false
                    Loop, 5
                    {
                        ; 새 파일 다이얼로그 창 찾기
                        WinGet, fdList, List
                        Loop, %fdList%
                        {
                            fdHwnd := fdList%A_Index%
                            if (fdHwnd = mt4ID || fdHwnd = epHwnd)
                                continue
                            WinGetTitle, fdTitle, ahk_id %fdHwnd%
                            WinGetClass, fdClass, ahk_id %fdHwnd%
                            if (InStr(fdTitle, "열기") || InStr(fdTitle, "Open") || InStr(fdClass, "#32770")) {
                                WinActivate, ahk_id %fdHwnd%
                                Sleep, 300
                                ; Edit1에 파일 경로 입력
                                ControlSetText, Edit1, %comboSetPath%, ahk_id %fdHwnd%
                                Sleep, 300
                                ControlSend, Edit1, {Enter}, ahk_id %fdHwnd%
                                Sleep, 500
                                fileDialogFound := true
                                FileAppend, [STEP 0-G] File dialog: entered path and confirmed`n, %logFile%
                                break
                            }
                        }
                        if (fileDialogFound)
                            break
                        Sleep, 500
                    }
                    if (!fileDialogFound)
                        FileAppend, [STEP 0-G WARN] File open dialog not found`n, %logFile%
                } else {
                    FileAppend, [STEP 0-G WARN] Load button not found. Buttons available:`n, %logFile%
                    Loop, Parse, epCtrlList, `n
                    {
                        _bc := A_LoopField
                        if (!InStr(_bc, "Button"))
                            continue
                        ControlGetText, _bcTxt, %_bc%, ahk_id %epHwnd%
                        FileAppend,   %_bc% = %_bcTxt%`n, %logFile%
                    }
                }

                ; OK 버튼 클릭하여 Expert Properties 닫기
                Sleep, 500
                if (WinExist("ahk_id " . epHwnd)) {
                    WinActivate, ahk_id %epHwnd%
                    Sleep, 200
                    okClicked := false
                    Loop, Parse, epCtrlList, `n
                    {
                        okCtrl := A_LoopField
                        if (!InStr(okCtrl, "Button"))
                            continue
                        ControlGetText, okBtnText, %okCtrl%, ahk_id %epHwnd%
                        if (okBtnText = "OK") {
                            ControlClick, %okCtrl%, ahk_id %epHwnd%
                            okClicked := true
                            FileAppend, [STEP 0-G] OK clicked - Expert Properties closed`n, %logFile%
                            break
                        }
                    }
                    if (!okClicked) {
                        Send, {Enter}
                        FileAppend, [STEP 0-G] OK via Enter key`n, %logFile%
                    }
                }
                Sleep, 500
                FileAppend, [STEP 0-G] SET file load completed`n, %logFile%
            } else {
                FileAppend, [STEP 0-G WARN] Expert Properties dialog not detected (no new window after F7)`n, %logFile%
            }
        } else {
            FileAppend, [STEP 0-G] SET file not found: %comboSetPath%`n, %logFile%
        }
    } else {
        FileAppend, [STEP 0-G] No TestExpertParameters in tester.ini - skipping`n, %logFile%
    }
} else {
    FileAppend, [STEP 0-G] terminal_path not set - skipping`n, %logFile%
}

Sleep, 200

; =====================================================
; [PRE-STEP 1] Visual Mode 강제 해제 (시각화 절대 금지)
; Start 클릭 전 무조건 해제 - Wait Loop 감지보다 먼저 실행해야 함
; =====================================================
WinActivate, ahk_id %mt4ID%
Sleep, 100
if (visualModeCheckboxNN != "ERROR" && visualModeCheckboxNN != "") {
    ControlGet, _vsState, Checked,, %visualModeCheckboxNN%, ahk_id %mt4ID%
    if (_vsState = 1) {
        Control, Uncheck,, %visualModeCheckboxNN%, ahk_id %mt4ID%
        Sleep, 150
        FileAppend, [PRE-STEP1] Visual Mode FORCE UNCHECKED (Start 전 강제해제)`n, %logFile%
    } else {
        FileAppend, [PRE-STEP1] Visual Mode already OFF`n, %logFile%
    }
} else {
    ; visualModeCheckboxNN 미설정 → Button 목록에서 자동 탐색
    WinGet, _vsBtnList, ControlList, ahk_id %mt4ID%
    Loop, Parse, _vsBtnList, `n
    {
        _vsCtrl := A_LoopField
        if (!InStr(_vsCtrl, "Button"))
            continue
        ControlGetText, _vsBtnTxt, %_vsCtrl%, ahk_id %mt4ID%
        if (InStr(_vsBtnTxt, "Visual") || InStr(_vsBtnTxt, "시각화")) {
            ControlGet, _vsState, Checked,, %_vsCtrl%, ahk_id %mt4ID%
            if (_vsState = 1) {
                Control, Uncheck,, %_vsCtrl%, ahk_id %mt4ID%
                Sleep, 150
                FileAppend, [PRE-STEP1] Visual Mode FORCE UNCHECKED (%_vsCtrl%) - auto found`n, %logFile%
                ; INI에 저장
                IniWrite, %_vsCtrl%, %iniFile%, tester_controls, visual_mode_checkbox
            }
            break
        }
    }
}
Sleep, 100

; =====================================================
; STEP 1: 시작 버튼 클릭 (v1.45 방식 - ControlClick 우선)
; =====================================================
FileAppend, [STEP 1] Start button`n, %logFile%

WinActivate, ahk_id %mt4ID%
Sleep, 100

; 방법 1: ControlClick (더 안정적)
ControlClick, %startButtonClassNN%, ahk_id %mt4ID%
Sleep, 200

; 클릭 확인 (버튼이 Stop으로 바뀌었는지)
ControlGetText, btnText, %startButtonClassNN%, ahk_id %mt4ID%
if (!InStr(btnText, "중지") and !InStr(btnText, "Stop")) {
    FileAppend, ControlClick may have failed, trying coordinate click...`n, %logFile%

    ; 방법 2: 좌표 클릭 (fallback)
    IniRead, relx9, %iniFile%, coords, relx9, 0.8625
    IniRead, rely9, %iniFile%, coords, rely9, 0.9044

    relx9 := relx9 + 0.0
    rely9 := rely9 + 0.0

    absX := wx + Round(relx9 * ww)
    absY := wy + Round(rely9 * wh)

    MouseMove, %absX%, %absY%, 0
    Sleep, 100
    Click, 1
}

FileAppend, Start CLICKED`n, %logFile%

; =====================================================
; STEP 2: 완료 대기 (모드 감시 추가)
; =====================================================
FileAppend, [STEP 2] Waiting...`n, %logFile%

Sleep, 1000

startTime := A_TickCount
maxWaitTime := 7200000
checkInterval := 500  ; [v1.17 OPTIMIZED] 2000 -> 500

buttonWasStop := false
lastProgressPct := 0
modeCheckCounter := 0

Loop {
    elapsed := A_TickCount - startTime

    if (elapsed > maxWaitTime) {
        FileAppend, TIMEOUT: 2hr exceeded`n, %logFile%
        GoSub, SignalCompletion
    }

    WinActivate, ahk_id %mt4ID%
    Sleep, 100

    ; =====================================================
    ; 모드 감시: EA Type이 Indicator로 변경되었는지, Visual mode가 켜졌는지 확인
    ; =====================================================
    modeCheckCounter++
    if (Mod(modeCheckCounter, 5) = 0) {  ; 5회마다 모드 체크 (약 2.5초마다)
        needsRecovery := false
        recoveryReason := ""

        ; 1. EA Type 체크
        ControlGet, currentType, Choice,, %eaTypeComboClassNN%, ahk_id %mt4ID%

        ; EA Type이 Indicator나 Script로 변경된 경우에만 복구
        ; 한국어 MT4: "전문가 고문" = Expert Advisor, "지표" = Indicator
        ; 깨진 한글 (cp949): 시스템 트레이더 등도 Expert Advisor로 간주
        isIndicatorMode := (InStr(currentType, "Indicator") || InStr(currentType, "지표") || InStr(currentType, "인디케이터"))
        isScriptMode := (InStr(currentType, "Script") || InStr(currentType, "스크립트"))

        ; Indicator나 Script 모드일 때만 복구 필요
        if (isIndicatorMode || isScriptMode) {
            needsRecovery := true
            recoveryReason := "Type changed to: " . currentType
        }

        ; 2. Visual Mode 체크 (체크되어 있으면 해제 - 선택금지)
        if (visualModeCheckboxNN != "ERROR" && visualModeCheckboxNN != "") {
            ControlGet, visualState, Checked,, %visualModeCheckboxNN%, ahk_id %mt4ID%
            if (visualState = 1) {
                ; Visual mode가 켜져있으면 즉시 해제 (선택금지)
                Control, Uncheck,, %visualModeCheckboxNN%, ahk_id %mt4ID%
                Sleep, 100
                FileAppend, [VISUAL MODE] UNCHECKED (선택금지)`n, %logFile%
            }
        }

        ; 복구 필요 시 실행 (Indicator/Script 모드로 변경된 경우만)
        if (needsRecovery) {
            FileAppend, [MODE ALERT] %recoveryReason% - FORCING recovery`n, %logFile%

            ; 진행 중인 테스트 중단
            ControlGetText, btnText, %startButtonClassNN%, ahk_id %mt4ID%
            if (InStr(btnText, "중지") or InStr(btnText, "Stop")) {
                ControlClick, %startButtonClassNN%, ahk_id %mt4ID%
                Sleep, 500
                FileAppend, [MODE RECOVERY] Stopped current test`n, %logFile%
            }

            ; Expert Advisor 모드로 강제 변경
            Control, ChooseString, Expert Advisor, %eaTypeComboClassNN%, ahk_id %mt4ID%
            Sleep, 300

            ; 실패 시 인덱스로 시도
            ControlGet, checkType, Choice,, %eaTypeComboClassNN%, ahk_id %mt4ID%
            if (!InStr(checkType, "Expert")) {
                Control, Choose, 1, %eaTypeComboClassNN%, ahk_id %mt4ID%
                Sleep, 300
                FileAppend, [MODE RECOVERY] Used Choose 1 for Expert mode`n, %logFile%
            }

            ; EA 다시 선택 [v3.7] 타이핑 방식
            if (filenameEA != "" && filenameEA != "NONE") {
                Sleep, 500
                recovSearchEA := StrReplace(filenameEA, ".ex4", "")
                ControlClick, %eaComboClassNN%, ahk_id %mt4ID%
                Sleep, 300
                Send, {Home}
                Sleep, 300
                Send, %recovSearchEA%
                Sleep, 500
                Send, {Enter}
                Sleep, 500
                FileAppend, [MODE RECOVERY] Reselected EA by typing: %recovSearchEA% (v3.7)`n, %logFile%
            }

            ; Symbol 다시 선택 (필요 시)
            if (targetSymbol != "SKIP") {
                IniRead, currentSymbolCheck, %iniFile%, current_backtest, symbol, NONE
                if (currentSymbolCheck != "NONE" && currentSymbolCheck != "") {
                    ; Symbol 재설정 로직은 복잡하므로 INI에서 읽어서 재설정
                    Sleep, 100
                    FileAppend, [MODE RECOVERY] Symbol should be: %currentSymbolCheck%`n, %logFile%
                }
            }

            ; Period 다시 선택
            if (targetPeriod != "SKIP") {
                Control, ChooseString, %targetPeriod%, %periodComboClassNN%, ahk_id %mt4ID%
                Sleep, 100
                FileAppend, [MODE RECOVERY] Reselected Period: %targetPeriod%`n, %logFile%
            }

            ; 날짜 설정 복원 (testDateEnable이 1인 경우)
            if (testDateEnable = 1) {
                if (useDateCheckboxNN != "ERROR" && useDateCheckboxNN != "") {
                    Control, Check,, %useDateCheckboxNN%, ahk_id %mt4ID%
                    Sleep, 100
                }
            }

            ; 테스트 재시작
            Sleep, 200
            ControlClick, %startButtonClassNN%, ahk_id %mt4ID%
            Sleep, 500
            FileAppend, [MODE RECOVERY] Restarted test with Expert Advisor mode`n, %logFile%

            ; 카운터 리셋
            buttonWasStop := false
            lastProgressPct := 0
            continue
        }
    }

    ControlGetText, buttonText, %startButtonClassNN%, ahk_id %mt4ID%
    StringReplace, buttonText, buttonText, %A_Space%, , All

    isStopButton := (InStr(buttonText, "중지") or InStr(buttonText, "Stop"))
    isStartButton := (InStr(buttonText, "시작") or InStr(buttonText, "Start"))

    progressPct := 0
    SendMessage, 0x408, 0, 0, %progressBarClassNN%, ahk_id %mt4ID%
    progressPos := ErrorLevel
    if (progressPos != "FAIL" and progressPos > 0) {
        SendMessage, 0x407, 0, 0, %progressBarClassNN%, ahk_id %mt4ID%
        progressMax := ErrorLevel
        if (progressMax != "FAIL" and progressMax > 0) {
            progressPct := Round((progressPos / progressMax) * 100)
        }
    }

    if (progressPct > lastProgressPct + 9) {
        FileAppend, Progress: %progressPct%`%`n, %logFile%
        lastProgressPct := progressPct
    }

    if (progressPct >= 100 and isStartButton) {
        FileAppend, Complete: 100`% + Start button`n, %logFile%
        break
    }

    if (isStopButton) {
        buttonWasStop := true
    } else if (isStartButton and buttonWasStop) {
        FileAppend, Complete: Stop->Start button change`n, %logFile%
        break
    }

    if (progressPct >= 100 and elapsed > 10000) {
        FileAppend, Complete: 100`%`n, %logFile%
        break
    }

    if (elapsed > 30000 and isStartButton and !isStopButton) {
        FileAppend, Complete: Timeout + Start button`n, %logFile%
        break
    }

    Sleep, %checkInterval%
}

Sleep, 500
FileAppend, Backtest DONE`n, %logFile%

; =====================================================
; Report 탭 클릭 (강화된 활성화)
; =====================================================
FileAppend, [Report Tab] Clicking...`n, %logFile%

; MT4 윈도우 강제 활성화 (단일 시도)
WinActivate, ahk_id %mt4ID%
Sleep, 200

IniRead, relx11, %iniFile%, coords, relx11, NONE
if (relx11 = "NONE")
    IniRead, relx11, %iniFile%, coords, relx_report, 0.259

IniRead, rely11, %iniFile%, coords, rely11, NONE
if (rely11 = "NONE")
    IniRead, rely11, %iniFile%, coords, rely_report, 0.940

relx11 := relx11 + 0.0
rely11 := rely11 + 0.0

WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%

absX := wx + Round(relx11 * ww)
absY := wy + Round(rely11 * wh)

; 추가 활성화
WinActivate, ahk_id %mt4ID%
Sleep, 200

MouseMove, %absX%, %absY%, 0
Sleep, 200
Click, 1
FileAppend, Report tab CLICKED`n, %logFile%
Sleep, 2500

; =====================================================
; STEP 3: HTML 저장 (v7 - 파일명 먼저 빌드 후 다이얼로그 즉시 처리)
; =====================================================
FileAppend, [STEP 3] HTML Save`n, %logFile%

; =====================================================
; [1단계] 파일명 먼저 빌드 (다이얼로그 열기 전)
; =====================================================

; 저장 경로
IniRead, saveFolder, %iniFile%, folders, html_save_path, ERROR
if (saveFolder = "ERROR" or saveFolder = "") {
    IniRead, saveFolder, %iniFile%, folders, setfiles_path, ERROR
}
if (saveFolder = "ERROR" or saveFolder = "") {
    IniRead, saveFolder, %iniFile%, folders, ea_path, ERROR
}
if (saveFolder = "ERROR" or saveFolder = "") {
    MsgBox, 16, 오류, 저장 폴더가 설정되지 않았습니다!
    GoSub, SignalCompletion
}

StringReplace, saveFolder, saveFolder, /, \, All
if (SubStr(saveFolder, 0) = "\")
    saveFolder := SubStr(saveFolder, 1, StrLen(saveFolder)-1)
FileAppend, Save folder: %saveFolder%`n, %logFile%

; EA 이름 결정
if (filenameEA != "" && filenameEA != "NONE") {
    currentEA := filenameEA
    FileAppend, [FILENAME] Using parameter EA: %currentEA%`n, %logFile%
} else if (selectedEA != "" && selectedEA != "NONE") {
    currentEA := selectedEA
    FileAppend, [FILENAME] Using ComboBox EA: %currentEA%`n, %logFile%
} else {
    currentEA := "UnknownEA"
    FileAppend, [FILENAME] WARNING: No EA name, using UnknownEA`n, %logFile%
}
; [ea-report-filename 스킬] .ex4 제거
StringReplace, currentEA, currentEA, .ex4, , All

IniRead, currentSymbol, %iniFile%, current_backtest, symbol, NONE
IniRead, currentPeriod, %iniFile%, current_backtest, period, NONE
IniRead, hasSet, %iniFile%, current_backtest, has_set, 0
IniRead, setFileName, %iniFile%, filename, set_file,
IniRead, accountNumber, %iniFile%, account, number, 0
if (currentSymbol = "NONE")
    currentSymbol := ""
if (currentPeriod = "NONE")
    currentPeriod := ""

baseSetName := setFileName
StringReplace, baseSetName, baseSetName, .set, , All

FormatTime, todayDate, , yyyyMMdd
FormatTime, todayTime, , MMddHHmmss

IniRead, testDateEnable, %iniFile%, test_date, enable, 0
IniRead, testFromDate, %iniFile%, test_date, from_date,
IniRead, testToDate, %iniFile%, test_date, to_date,
FileAppend, [PERIOD] enable=%testDateEnable% from=%testFromDate% to=%testToDate%`n, %logFile%

testPeriodStr := ""
if (testDateEnable = 1 && testFromDate != "" && testToDate != "") {
    fromDateClean := StrReplace(testFromDate, ".", "")
    toDateClean := StrReplace(testToDate, ".", "")
    testPeriodStr := fromDateClean . "-" . toDateClean
    FileAppend, [FILENAME] Test period: %testPeriodStr%`n, %logFile%
}

htmlFileName := ""
if (currentEA != "")
    htmlFileName := currentEA
if (currentSymbol != "") {
    if (htmlFileName != "")
        htmlFileName .= "_"
    htmlFileName .= currentSymbol
}
if (currentPeriod != "") {
    cleanPeriod := RegExReplace(currentPeriod, "\s*\(.*\)", "")
    cleanPeriod := Trim(cleanPeriod)
    if (htmlFileName != "")
        htmlFileName .= "_"
    htmlFileName .= cleanPeriod
}
if (testPeriodStr != "") {
    htmlFileName .= "_" . testPeriodStr
}
htmlFileName .= "_" . todayTime

; [FIX] 라운드 번호를 파일명 끝에 추가 → R1/R2/R3 중복 방지
IniRead, roundNum, %iniFile%, current_backtest, round_num, R1
if (roundNum != "" && roundNum != "NOTSET" && roundNum != "ERROR")
    htmlFileName .= "_" . roundNum

FileAppend, [FILENAME] %htmlFileName%`n, %logFile%

IfNotExist, %saveFolder%
    FileCreateDir, %saveFolder%

finalHtmlName := htmlFileName
testPath := saveFolder . "\" . finalHtmlName . ".htm"
IfExist, %testPath%
{
    FileAppend, [DUPLICATE] %finalHtmlName%.htm exists`n, %logFile%
    suffix := 1
    Loop {
        finalHtmlName := htmlFileName . "-" . suffix
        testPath := saveFolder . "\" . finalHtmlName . ".htm"
        IfNotExist, %testPath%
            break
        suffix++
        if (suffix > 99)
            break
    }
}

fullSavePath := saveFolder . "\" . finalHtmlName . ".htm"
FileAppend, [PRE-BUILD] %fullSavePath%`n, %logFile%

; [v7] 클립보드 미리 준비 (다이얼로그 열기 전)
Clipboard := fullSavePath
ClipWait, 2
FileAppend, [CLIPBOARD] Ready`n, %logFile%

; =====================================================
; [2단계] 우클릭 좌표 계산 후 다이얼로그 열기
; =====================================================
IniRead, relxRC, %iniFile%, coords, relx_rightclick, NONE
IniRead, relyRC, %iniFile%, coords, rely_rightclick, NONE
if (relxRC = "NONE" or relyRC = "NONE") {
    reportTabX := wx + Round(relx11 * ww)
    pixelsAbove := 75
    relYOffset := pixelsAbove / wh
    rightClickY := wy + Round((rely11 - relYOffset) * wh)
    FileAppend, [STEP 3] Fallback coords`n, %logFile%
} else {
    relxRC := relxRC + 0.0
    relyRC := relyRC + 0.0
    reportTabX := wx + Round(relxRC * ww)
    rightClickY := wy + Round(relyRC * wh)
    FileAppend, [STEP 3] Calibrated coords: relx=%relxRC% rely=%relyRC%`n, %logFile%
}

WinActivate, ahk_id %mt4ID%
Sleep, 300
MouseMove, %reportTabX%, %rightClickY%, 0
Sleep, 500
Click, Right
FileAppend, Right clicked`n, %logFile%
Sleep, 1500
Send, s
FileAppend, Sent 's' key`n, %logFile%
Sleep, 800

; =====================================================
; [3단계] 다이얼로그 활성화 대기 후 즉시 붙여넣기 (5회 재시도)
; =====================================================
saveDialogOK := 0
Loop, 5 {
    WinWaitActive, ahk_class #32770,, 4
    if (!ErrorLevel) {
        saveDialogOK := 1
        break
    }
    FileAppend, WARNING: Save dialog retry %A_Index%/5`n, %logFile%
    WinActivate, ahk_id %mt4ID%
    Sleep, 500
    MouseMove, %reportTabX%, %rightClickY%, 0
    Sleep, 300
    Click, Right
    Sleep, 1500
    Send, s
    Sleep, 800
}
if (!saveDialogOK) {
    FileAppend, ERROR: Save dialog failed!`n, %logFile%
    Goto, SkipSave
}

FileAppend, Save dialog ACTIVE`n, %logFile%
Sleep, 200

; 파일명 필드: ^a 전체선택 -> ^v 붙여넣기 (다이얼로그가 활성화된 상태)
Send, ^a
Sleep, 100
Send, ^v
Sleep, 300
FileAppend, [SAVE] Clipboard pasted: %fullSavePath%`n, %logFile%
Send, {Enter}
Sleep, 1000

; 덮어쓰기 처리
Loop, 5 {
    IfWinExist, ahk_class #32770
    {
        WinGetText, dlgText, ahk_class #32770
        if (InStr(dlgText, "이미") or InStr(dlgText, "already") or InStr(dlgText, "바꾸") or InStr(dlgText, "replace")) {
            FileAppend, Overwrite dialog detected`n, %logFile%
            Send, {Enter}
            Sleep, 200
            break
        }
    }
    Sleep, 100
}

Sleep, 800
IfExist, %fullSavePath%
    FileAppend, SUCCESS: %fullSavePath%`n, %logFile%
else
    FileAppend, WARNING: File not saved`n, %logFile%

; [fix_report_layout] HTM 저장 직후 레이아웃 자동 수정
IfExist, %fullSavePath%
{
    _pyExe := ""
    Loop, 6 {
        _pyVer := 9 + A_Index  ; 10~15
        _pyTry := "C:\Python3" . _pyVer . "\python.exe"
        IfExist, %_pyTry%
        {
            _pyExe := _pyTry
            break
        }
        _pyTry := "C:\Users\" . A_UserName . "\AppData\Local\Programs\Python\Python3" . _pyVer . "\python.exe"
        IfExist, %_pyTry%
        {
            _pyExe := _pyTry
            break
        }
    }
    if (_pyExe = "")
        _pyExe := "python"
    _fixScript := "C:\NEWOPTIMISER\fix_report_layout.py"
    IfExist, %_fixScript%
    {
        Run, %_pyExe% "%_fixScript%" "%saveFolder%",, Hide
        FileAppend, [fix_report_layout] 실행: %saveFolder%`n, %logFile%
    }
}

; [HTML 창 닫기] zen-run 모드에서 SOLO 없이도 브라우저 창 자동 닫기
Run, C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NonInteractive -NoProfile -WindowStyle Hidden -Command "Get-Process msedge,chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match '.htm' } | ForEach-Object { $_.CloseMainWindow() }",, Hide
Sleep, 200

SkipSave:
; =====================================================
; STEP 4: Settings 탭
; =====================================================
FileAppend, [STEP 4] Settings tab`n, %logFile%

IniRead, relx14, %iniFile%, coords, relx14, NONE
if (relx14 = "NONE")
    IniRead, relx14, %iniFile%, coords, relx_settings, 0.060

IniRead, rely14, %iniFile%, coords, rely14, NONE
if (rely14 = "NONE")
    IniRead, rely14, %iniFile%, coords, rely_settings, 0.946

relx14 := relx14 + 0.0
rely14 := rely14 + 0.0

WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%

absX := wx + Round(relx14 * ww)
absY := wy + Round(rely14 * wh)

WinActivate, ahk_id %mt4ID%
Sleep, 100
MouseMove, %absX%, %absY%, 0
Sleep, 200
Click, 1

FileAppend, Settings tab CLICKED`n, %logFile%
FileAppend, === v3.5 DONE ===`n, %logFile%

Sleep, 200
GoSub, SignalCompletion

; 완료 알림 플래그 (SOLO 2.0 연동용)
SignalCompletion:
    completionMarker := (A_Args.MaxIndex() >= 5 && A_Args[5] != "") ? A_Args[5] : A_WorkingDir "\configs\test_completed.flag"
    FileAppend, [SIGNAL] Writing completion flag: %completionMarker%`n, %logFile%
    FileDelete, %completionMarker%
    FileAppend, DONE, %completionMarker%
    if ErrorLevel
        FileAppend, [ERROR] Failed to write completion flag! ErrorLevel=%ErrorLevel%`n, %logFile%
    else
        FileAppend, [SIGNAL] Completion flag written OK`n, %logFile%
    ExitApp
return

