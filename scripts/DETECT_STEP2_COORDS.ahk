#NoEnv
#SingleInstance Force
CoordMode, Mouse, Screen
SetWorkingDir, %A_ScriptDir%

; =====================================================
; 2단계: 좌표 설정 v1.43 (v2.0 통합)
; - 십자가로 저장 위치 표시
; - 좌표 검증
; - v2.0: configs 폴더 사용
; =====================================================

; v2.0: 상위 폴더의 configs 사용
SetWorkingDir, %A_ScriptDir%\..
iniFile := A_WorkingDir "\configs\current_config.ini"

mt4ID := 0
wx := 0
wy := 0
ww := 0
wh := 0

; 좌표 저장 변수
relxReport := 0
relyReport := 0
relxRightClick := 0
relyRightClick := 0
relxSettings := 0
relySettings := 0
relxProgress := 0
relyProgress := 0
relxExpert := 0
relyExpert := 0

relxEADropdown := 0

relyEADropdown := 0

; =====================================================
; GUI 생성
; =====================================================
Gui, Margin, 15, 15
Gui, Font, s11 Bold
Gui, Add, Text, w500 Center, 2단계: 좌표 설정 v1.43

Gui, Font, s9 Normal
Gui, Add, Text, w500 Center y+3 cRed, ⚠️ MT4 창 크기를 고정한 후 진행!

Gui, Add, Text, w500 y+10 0x10

Gui, Font, s9 Bold
Gui, Add, Text, w500 y+8, 사용법:
Gui, Font, s9 Normal
Gui, Add, Text, w500 y+5, 1. [MT4 찾기] 클릭
Gui, Add, Text, w500 y+3, 2. MT4에서 원하는 위치에 마우스 이동
Gui, Add, Text, w500 y+3 cBlue, 3. 단축키 누르기 (F1~F5) → 빨간 십자가 표시됨!
Gui, Add, Text, w500 y+3, 4. 모든 좌표 설정 후 [저장]

Gui, Add, Text, w500 y+10 0x10

Gui, Font, s9 Bold
Gui, Add, Text, w500 y+8, MT4 정보:
Gui, Font, s9 Normal
Gui, Add, Text, vMT4Info w350 y+5, (미감지)
Gui, Add, Button, gFindMT4 x+10 yp-3 w120 h25, MT4 찾기

Gui, Add, Text, x15 w500 y+10 0x10

Gui, Font, s10 Bold
Gui, Add, Text, x15 w500 y+8 cBlue, 단축키 (마우스를 위치에 두고 누르기):

Gui, Font, s9 Normal

; F1: Report 탭
Gui, Add, Text, x15 w100 y+10, F1: Report 탭
Gui, Add, Edit, vCoordReport x+5 yp-3 w150 h22 ReadOnly, (미설정)
Gui, Add, Button, gTestReport x+5 yp w60 h22, 테스트
Gui, Add, Text, x+10 yp+3 cGray, ← 왼쪽 끝

; F2: 우클릭 영역
Gui, Add, Text, x15 w100 y+8, F2: 우클릭 영역
Gui, Add, Edit, vCoordRightClick x+5 yp-3 w150 h22 ReadOnly, (미설정)
Gui, Add, Button, gTestRightClick x+5 yp w60 h22, 테스트
Gui, Add, Text, x+10 yp+3 cGray, ← 화면 중앙

; F3: Settings 탭
Gui, Add, Text, x15 w100 y+8, F3: Settings 탭
Gui, Add, Edit, vCoordSettings x+5 yp-3 w150 h22 ReadOnly, (미설정)
Gui, Add, Button, gTestSettings x+5 yp w60 h22, 테스트
Gui, Add, Text, x+10 yp+3 cGray, ← Report 왼쪽

; F4: 진행바
Gui, Add, Text, x15 w100 y+8 cGray, F4: 진행바
Gui, Add, Edit, vCoordProgress x+5 yp-3 w150 h22 ReadOnly, (선택)
Gui, Add, Button, gTestProgress x+5 yp w60 h22, 테스트

; F5: Expert
Gui, Add, Text, x15 w100 y+8 cGray, F5: Expert 버튼
Gui, Add, Edit, vCoordExpert x+5 yp-3 w150 h22 ReadOnly, (선택)

Gui, Add, Button, gTestExpert x+5 yp w60 h22, 테스트

; F6: EA 드롭다운 (v4.6)
Gui, Add, Text, x15 w100 y+8 cBlue, F6: EA 드롭다운
Gui, Add, Edit, vCoordEADropdown x+5 yp-3 w150 h22 ReadOnly, (미설정)
Gui, Add, Button, gTestEADropdown x+5 yp w60 h22, 테스트
Gui, Add, Text, x+10 yp+3 cRed, *** EA선택 ***

Gui, Add, Text, x15 w500 y+10 0x10

; 저장 버튼
Gui, Add, Button, gSaveCoords x15 w240 h35 y+10, 💾 저장
Gui, Add, Button, gLoadCoords x+10 w240 h35 yp, 📂 기존 좌표 불러오기

Gui, Add, Text, x15 w500 y+10 0x10

Gui, Font, s8
Gui, Add, Text, x15 vStatusText w500 y+5 cGray, 상태: 대기 중

Gui, Add, Button, gGuiClose x15 w500 h30 y+10, 닫기

Gui, Show, AutoSize, 좌표 설정 v1.43
return

; =====================================================
; MT4 찾기
; =====================================================
FindMT4:
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
            if (!InStr(winTitle, "-") and !InStr(winTitle, ":"))
                continue
            mt4ID := id
            break
        }
    }
    
    if (!mt4ID) {
        GuiControl,, MT4Info, MT4를 찾을 수 없습니다!
        GuiControl,, StatusText, 상태: MT4를 실행하고 다시 시도하세요
        MsgBox, 48, 오류, MT4 (terminal.exe)를 찾을 수 없습니다!
        return
    }
    
    WinGetTitle, mt4Title, ahk_id %mt4ID%
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%

    ; 창 제목에서 브로커명과 계정번호 추출
    brokerName := ""
    accountNum := ""

    ; 패턴: "브로커명 - 계정번호" 또는 "계정번호 : 브로커명"
    if (RegExMatch(mt4Title, "^(.+?)\s*[-:]\s*(\d{5,12})", titleMatch)) {
        brokerName := Trim(titleMatch1)
        accountNum := titleMatch2
    } else if (RegExMatch(mt4Title, "(\d{5,12})\s*[-:]\s*(.+?)$", titleMatch2)) {
        accountNum := titleMatch2_1
        brokerName := Trim(titleMatch2_2)
    } else if (RegExMatch(mt4Title, "(\d{5,12})", accMatch)) {
        accountNum := accMatch1
        brokerName := mt4Title
    }

    ; MT4 정보 표시 (브로커 + 계정 + 크기)
    if (accountNum != "")
        mt4InfoText := brokerName . " [" . accountNum . "] (" . ww . "x" . wh . ")"
    else
        mt4InfoText := mt4Title . " (" . ww . "x" . wh . ")"

    GuiControl,, MT4Info, %mt4InfoText%
    GuiControl,, StatusText, 상태: MT4 찾음! 마우스를 위치에 두고 F1~F5 누르기

    MsgBox, 64, 완료, MT4 찾음!`n`n%mt4InfoText%`n`n마우스를 원하는 위치에 두고`nF1~F5를 누르세요.`n`n빨간 십자가가 저장된 위치를 표시합니다.
return

; =====================================================
; 테스트 버튼들
; =====================================================
TestReport:
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    if (relxReport = 0 and relyReport = 0) {
        MsgBox, 48, 오류, Report 탭 좌표가 설정되지 않았습니다!
        return
    }
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    testX := wx + Round(relxReport * ww)
    testY := wy + Round(relyReport * wh)
    Gosub, ShowCrossRed
    GuiControl,, StatusText, 테스트: Report 탭 (%testX%, %testY%)
return

TestRightClick:
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    if (relxRightClick = 0 and relyRightClick = 0) {
        MsgBox, 48, 오류, 우클릭 영역 좌표가 설정되지 않았습니다!
        return
    }
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    testX := wx + Round(relxRightClick * ww)
    testY := wy + Round(relyRightClick * wh)
    Gosub, ShowCrossBlue
    GuiControl,, StatusText, 테스트: 우클릭 영역 (%testX%, %testY%)
return

TestSettings:
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    if (relxSettings = 0 and relySettings = 0) {
        MsgBox, 48, 오류, Settings 탭 좌표가 설정되지 않았습니다!
        return
    }
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    testX := wx + Round(relxSettings * ww)
    testY := wy + Round(relySettings * wh)
    Gosub, ShowCrossGreen
    GuiControl,, StatusText, 테스트: Settings 탭 (%testX%, %testY%)
return

TestProgress:
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    if (relxProgress = 0 and relyProgress = 0) {
        MsgBox, 48, 오류, 진행바 좌표가 설정되지 않았습니다!
        return
    }
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    testX := wx + Round(relxProgress * ww)
    testY := wy + Round(relyProgress * wh)
    Gosub, ShowCrossYellow
    GuiControl,, StatusText, 테스트: 진행바 (%testX%, %testY%)
return

TestExpert:
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    if (relxExpert = 0 and relyExpert = 0) {
        MsgBox, 48, 오류, Expert 버튼 좌표가 설정되지 않았습니다!
        return
    }
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    testX := wx + Round(relxExpert * ww)
    testY := wy + Round(relyExpert * wh)
    Gosub, ShowCrossPurple
    GuiControl,, StatusText, 테스트: Expert 버튼 (%testX%, %testY%)
return

; =====================================================
; 십자가 표시 (라벨 방식)
; =====================================================
ShowCrossRed:
    crossColor := "Red"
    Gosub, DrawCross
return

ShowCrossBlue:
    crossColor := "0000FF"
    Gosub, DrawCross
return

ShowCrossGreen:
    crossColor := "00FF00"
    Gosub, DrawCross
return

ShowCrossYellow:
    crossColor := "FFFF00"
    Gosub, DrawCross
return

ShowCrossPurple:
    crossColor := "FF00FF"
    Gosub, DrawCross
return

DrawCross:
    ; 기존 십자가 제거
    Gui, CrossH:Destroy
    Gui, CrossV:Destroy
    
    crossSize := 30
    thickness := 4
    
    ; 수평선
    Gui, CrossH:New, +AlwaysOnTop -Caption +ToolWindow
    Gui, CrossH:Color, %crossColor%
    hx := testX - crossSize
    hy := testY - 2
    hw := crossSize * 2
    hh := thickness
    Gui, CrossH:Show, x%hx% y%hy% w%hw% h%hh% NoActivate
    
    ; 수직선
    Gui, CrossV:New, +AlwaysOnTop -Caption +ToolWindow
    Gui, CrossV:Color, %crossColor%
    vx := testX - 2
    vy := testY - crossSize
    vw := thickness
    vh := crossSize * 2
    Gui, CrossV:Show, x%vx% y%vy% w%vw% h%vh% NoActivate
    
    ; 2초 후 제거
    SetTimer, HideCross, -2000
return

HideCross:
    Gui, CrossH:Destroy
    Gui, CrossV:Destroy
return

; =====================================================
; 저장
; =====================================================
SaveCoords:
    ; 필수 좌표 확인
    missing := ""
    if (relxReport = 0 and relyReport = 0)
        missing .= "- Report 탭 (F1)`n"
    if (relxRightClick = 0 and relyRightClick = 0)
        missing .= "- 우클릭 영역 (F2)`n"
    if (relxSettings = 0 and relySettings = 0)
        missing .= "- Settings 탭 (F3)`n"
    
    if (missing != "") {
        MsgBox, 52, 경고, 다음 좌표가 설정되지 않았습니다:`n`n%missing%`n계속 저장하시겠습니까?
        IfMsgBox, No
            return
    }
    
    ; 저장
    if (relxReport != 0 or relyReport != 0) {
        IniWrite, %relxReport%, %iniFile%, coords, relx_report
        IniWrite, %relyReport%, %iniFile%, coords, rely_report
    }
    if (relxRightClick != 0 or relyRightClick != 0) {
        IniWrite, %relxRightClick%, %iniFile%, coords, relx_rightclick
        IniWrite, %relyRightClick%, %iniFile%, coords, rely_rightclick
    }
    if (relxSettings != 0 or relySettings != 0) {
        IniWrite, %relxSettings%, %iniFile%, coords, relx_settings
        IniWrite, %relySettings%, %iniFile%, coords, rely_settings
    }
    if (relxProgress != 0 or relyProgress != 0) {
        IniWrite, %relxProgress%, %iniFile%, coords, relx_progress
        IniWrite, %relyProgress%, %iniFile%, coords, rely_progress
    }
    if (relxEADropdown != 0 or relyEADropdown != 0) {
        IniWrite, %relxEADropdown%, %iniFile%, coords, relxSysTrading
        IniWrite, %relyEADropdown%, %iniFile%, coords, relySysTrading
    }
    if (relxExpert != 0 or relyExpert != 0) {
        IniWrite, %relxExpert%, %iniFile%, coords, relx5
        IniWrite, %relyExpert%, %iniFile%, coords, rely5
    }
    
    GuiControl,, StatusText, 상태: 저장 완료!
    MsgBox, 64, 완료, 좌표가 저장되었습니다!
return

; =====================================================
; 기존 좌표 불러오기
; =====================================================
LoadCoords:
    ; MT4가 없으면 자동으로 찾기
    if (!mt4ID) {
        Gosub, FindMT4
        if (!mt4ID) {
            MsgBox, 48, 오류, MT4를 찾을 수 없습니다!`n먼저 MT4를 실행하세요.
            return
        }
    }

    IniRead, relxReport, %iniFile%, coords, relx_report, 0
    IniRead, relyReport, %iniFile%, coords, rely_report, 0
    IniRead, relxRightClick, %iniFile%, coords, relx_rightclick, 0
    IniRead, relyRightClick, %iniFile%, coords, rely_rightclick, 0
    IniRead, relxSettings, %iniFile%, coords, relx_settings, 0
    IniRead, relySettings, %iniFile%, coords, rely_settings, 0
    IniRead, relxProgress, %iniFile%, coords, relx_progress, 0
    IniRead, relyProgress, %iniFile%, coords, rely_progress, 0
    IniRead, relxExpert, %iniFile%, coords, relx5, 0
    IniRead, relyExpert, %iniFile%, coords, rely5, 0
    
    relxReport += 0.0
    relyReport += 0.0
    relxRightClick += 0.0
    relyRightClick += 0.0
    relxSettings += 0.0
    relySettings += 0.0
    relxProgress += 0.0
    relyProgress += 0.0
    relxExpert += 0.0
    relyExpert += 0.0
    
    if (relxReport != 0 or relyReport != 0)
        GuiControl,, CoordReport, % Format("{:.3f}, {:.3f}", relxReport, relyReport)
    if (relxRightClick != 0 or relyRightClick != 0)
        GuiControl,, CoordRightClick, % Format("{:.3f}, {:.3f}", relxRightClick, relyRightClick)
    if (relxSettings != 0 or relySettings != 0)
        GuiControl,, CoordSettings, % Format("{:.3f}, {:.3f}", relxSettings, relySettings)
    if (relxProgress != 0 or relyProgress != 0)
        GuiControl,, CoordProgress, % Format("{:.3f}, {:.3f}", relxProgress, relyProgress)
    if (relxExpert != 0 or relyExpert != 0)
        GuiControl,, CoordExpert, % Format("{:.3f}, {:.3f}", relxExpert, relyExpert)
    
    GuiControl,, StatusText, 상태: 기존 좌표 불러옴! [테스트] 버튼으로 확인
    MsgBox, 64, 완료, 기존 좌표를 불러왔습니다!`n`n[테스트] 버튼으로 확인하세요.
return

; =====================================================
; 닫기
; =====================================================
GuiClose:
    Gui, CrossH:Destroy
    Gui, CrossV:Destroy
    ExitApp
return

; =====================================================
; 핫키: F1 = Report 탭
; =====================================================
F1::
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    
    MouseGetPos, mx, my
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    
    relxReport := (mx - wx) / ww
    relyReport := (my - wy) / wh
    
    warning := ""
    if (relxReport > 0.15)
        warning := " ⚠️X큼!"
    
    GuiControl,, CoordReport, % Format("{:.3f}, {:.3f}", relxReport, relyReport) . warning
    GuiControl,, StatusText, F1: Report 탭 저장 (%mx%, %my%)
    
    testX := mx
    testY := my
    Gosub, ShowCrossRed
    
    SoundBeep, 1000, 100
return

; =====================================================
; 핫키: F2 = 우클릭 영역
; =====================================================
F2::
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    
    MouseGetPos, mx, my
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    
    relxRightClick := (mx - wx) / ww
    relyRightClick := (my - wy) / wh
    
    GuiControl,, CoordRightClick, % Format("{:.3f}, {:.3f}", relxRightClick, relyRightClick)
    GuiControl,, StatusText, F2: 우클릭 영역 저장 (%mx%, %my%)
    
    testX := mx
    testY := my
    Gosub, ShowCrossBlue
    
    SoundBeep, 1000, 100
return

; =====================================================
; 핫키: F3 = Settings 탭
; =====================================================
F3::
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    
    MouseGetPos, mx, my
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    
    relxSettings := (mx - wx) / ww
    relySettings := (my - wy) / wh
    
    warning := ""
    if (relxSettings > 0.1)
        warning := " ⚠️X큼!"
    
    GuiControl,, CoordSettings, % Format("{:.3f}, {:.3f}", relxSettings, relySettings) . warning
    GuiControl,, StatusText, F3: Settings 탭 저장 (%mx%, %my%)
    
    testX := mx
    testY := my
    Gosub, ShowCrossGreen
    
    SoundBeep, 1000, 100
return

; =====================================================
; 핫키: F4 = 진행바
; =====================================================
F4::
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    
    MouseGetPos, mx, my
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    
    relxProgress := (mx - wx) / ww
    relyProgress := (my - wy) / wh
    
    GuiControl,, CoordProgress, % Format("{:.3f}, {:.3f}", relxProgress, relyProgress)
    GuiControl,, StatusText, F4: 진행바 저장 (%mx%, %my%)
    
    testX := mx
    testY := my
    Gosub, ShowCrossYellow
    
    SoundBeep, 1000, 100
return

; =====================================================
; 핫키: F5 = Expert properties 버튼
; =====================================================
F5::
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }

    MouseGetPos, mx, my
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%

    relxExpert := (mx - wx) / ww
    relyExpert := (my - wy) / wh

    GuiControl,, CoordExpert, % Format("{:.3f}, {:.3f}", relxExpert, relyExpert)
    GuiControl,, StatusText, F5: Expert 버튼 저장 (%mx%, %my%)

    testX := mx
    testY := my
    Gosub, ShowCrossPurple

    SoundBeep, 1000, 100
return

; =====================================================
; 핫키: F6 = EA 드롭다운 (v4.6)
; =====================================================
F6::
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    MouseGetPos, mx, my
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    relxEADropdown := (mx - wx) / ww
    relyEADropdown := (my - wy) / wh
    GuiControl,, CoordEADropdown, % Format("{:.3f}, {:.3f}", relxEADropdown, relyEADropdown)
    GuiControl,, StatusText, F6: EA 드롭다운 좌표 저장 (%mx%, %my%)

    testX := mx
    testY := my
    Gosub, ShowCrossRed

    SoundBeep, 1000, 100
return

TestEADropdown:
    if (!mt4ID) {
        MsgBox, 48, 오류, 먼저 [MT4 찾기] 클릭!
        return
    }
    if (relxEADropdown = 0 and relyEADropdown = 0) {
        MsgBox, 48, 오류, EA 드롭다운 좌표가 설정되지 않았습니다!
        return
    }
    WinGetPos, wx, wy, ww, wh, ahk_id %mt4ID%
    testX := wx + Round(relxEADropdown * ww)
    testY := wy + Round(relyEADropdown * wh)
    Gosub, ShowCrossRed
    GuiControl,, StatusText, 테스트: EA 드롭다운 위치 (%testX%, %testY%)
return

