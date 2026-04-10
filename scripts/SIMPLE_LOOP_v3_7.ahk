#NoEnv
#SingleInstance Force
SetWorkingDir, %A_ScriptDir%\..
SetTitleMatchMode, 2
SetControlDelay, 50

; [PORTABLE] Python 자동 감지
global pythonExePath := ""
EnvGet, localAppData, LOCALAPPDATA
pythonSearchPaths := ["C:\Python313\python.exe"
    , "C:\Python312\python.exe"
    , "C:\Python311\python.exe"
    , "C:\Python310\python.exe"
    , localAppData . "\Programs\Python\Python313\python.exe"
    , localAppData . "\Programs\Python\Python312\python.exe"
    , localAppData . "\Programs\Python\Python311\python.exe"]
for idx, pp in pythonSearchPaths {
    if FileExist(pp) {
        pythonExePath := pp
        break
    }
}
if (pythonExePath = "") {
    RunWait, %ComSpec% /c "where python > "%A_Temp%\python_path.txt"", , Hide
    FileRead, pythonExePath, %A_Temp%\python_path.txt
    pythonExePath := Trim(RegExReplace(pythonExePath, "\r?\n.*"))
    if (!FileExist(pythonExePath))
        pythonExePath := "python"
}

; =====================================================
; 명령줄 인수 체크 (/auto 지원)
; =====================================================
global autoStartMode := false
Loop, %0%
{
    param := %A_Index%
    if (param = "/auto" || param = "-auto" || param = "--auto")
    {
        autoStartMode := true
        break
    }
}

; =====================================================
; SIMPLE LOOP v1.1 - [v3.8] Test Order Options Added
; Updated by Antigravity - IDs: 202531, 20250430
; - v1.1: Added Loop Order Options (A: EA-First, B: Period-First)
; - Base: v3.7.2 NC FINAL
; =====================================================

iniFile := A_ScriptDir . "\..\configs\current_config.ini"
logFile := A_ScriptDir . "\simple_loop_v3_7_log.txt"

FileDelete, %logFile%
FileAppend, === LOOP STARTED (v3.7.2 FINAL + PAUSE FIXED) ===`n, %logFile%

; Pre-Flight Cleanup
RunWait, %ComSpec% /c taskkill /F /IM AutoHotkey.exe /FI "WINDOWTITLE eq SIMPLE_4STEPS*" /T,, Hide
Sleep, 1000

; Global Variables
global isPaused := false
global isStopped := false
global resumeMode := false
global resumeTargetIndex := 0
global loopOrder := "A"
IniRead, loopOrder, %iniFile%, settings, loop_order, A
global zeroTradeCount := 0 
global skipCurrentEA := false 

; Live Analysis Global Variables
global laTotalTests := 0, laProfitTests := 0, laLossTests := 0
global laTotalProfit := 0, laTotalLoss := 0, laMaxDD := 0
global laGrossProfit := 0, laGrossLoss := 0, laTotalTrades := 0
global laTotalWonTrades := 0, laTotalLostTrades := 0
global laLastFile := "", analyzedFiles := {}
global htmlSaveFolder := "D:\report for backtest\BRT2.3"
global eaFolder, currentEAFile, eaName ; [v3.9] Made global for AnalyzeLatestReport access

; =====================================================
; 설정 로드 (Subroutine for Reload)
; =====================================================
Gosub, LoadSettingsV36Standalone
    len := selectedEAs.Length()
    FileAppend, [DEBUG] StartLoop EA Count: %len%
, %logFile%

; =====================================================
; GUI
; =====================================================
Gui, Font, s10 Bold
Gui, Add, Text, x10 w560 Center, [SIMPLE LOOP v3.7.2]
Gui, Font, s8 Normal

Gui, Font, s8 Bold cOrange
Gui, Add, Text, vEACountText x10 w560 y+5, EA: %activeEACount% Selected
Gui, Font, s7 Normal
Gui, Add, Edit, x10 w560 h35 y+2 ReadOnly, %eaListStr%

Gui, Add, Text, w560 y+5 0x10 x10

Gui, Font, s8 Bold cBlue
Gui, Add, Text, vSymTFText x10 w560 y+5, Pairs(%symCount%): %symList%  |  TF(%tfCount%): %tfList%

Gui, Font, s8 Bold cPurple
Gui, Add, Text, vPeriodTitleText x10 w560 y+5, Test Period (%periodCount%)
Gui, Font, s7 Normal
Gui, Add, Edit, x10 w560 h50 y+2 ReadOnly, %periodList%

Gui, Add, Text, w560 y+5 0x10 x10

Gui, Font, s9 Bold cRed
Gui, Add, Text, vTotalTestsText x10 w560 y+3, Total: %activeEACount% x %symCount% x %tfCount% x %periodCount% = %totalTests% Tests
Gui, Font, s7 Normal cDarkGreen
orderDisplayStr := (loopOrder = "B") ? "Order: Period → Symbol → TF → EA" : "Order: EA → Symbol → TF → Period"
Gui, Add, Text, vOrderDisplay x10 w560 y+2, %orderDisplayStr%

; 테스트 순서 선택 추가
Gui, Font, s8 Bold cTeal
Gui, Add, Text, x10 w80 y+5, 테스트순서:
Gui, Font, s8 Normal
loopOrderIdx := (loopOrder = "B") ? 2 : 1
Gui, Add, DropDownList, x+3 yp-2 w250 vLoopOrderSelect gLoopOrderChanged Choose%loopOrderIdx%, Option A (EA우선-소규모)|Option B (전체분산-대규모)

Gui, Add, Text, w560 y+5 0x10 x10

Gui, Font, s8 Bold
Gui, Add, Text, x10 w560 y+3, Progress
Gui, Font, s8 Normal
Gui, Add, Progress, vProgressBar x10 w560 h20 y+3 cGreen, 0
Gui, Add, Text, vCurrentText x10 w560 y+3, Waiting...
Gui, Add, Text, vStatusText x10 w280 y+2, Status: Ready
Gui, Add, Text, vSkippedText x+5 w275 yp, Skipped: 0

Gui, Add, Text, w560 y+5 0x10 x10

; Live Analysis (v2.5 Style)
Gui, Font, s8 Bold cPurple
Gui, Add, Text, x10 w560 y+5, Live Analysis
Gui, Font, s7 Normal
Gui, Add, Text, vLiveAnalysisText x10 w560 y+2, Waiting...
Gui, Add, Text, vLiveProfitText x10 w560 y+2, P.Tests: 0 | L.Tests: 0 | Trades: 0 (W:0 L:0)
Gui, Add, Text, vLiveNetText x10 w560 y+2, Net: $0.00 | GrossP: $0.00 | GrossL: $0.00
Gui, Add, Text, vLiveLastEA x10 w560 y+2 cBlue, Last EA: -

Gui, Add, Text, w560 y+5 0x10 x10

Gui, Add, Button, gButtonStart vBtnStart x10 w120 h40 y+5, Start New
Gui, Add, Button, gButtonResume vBtnResume x+5 w120 h40, Resume
Gui, Add, Button, gButtonPause vBtnPause x+5 w100 h40, Pause
Gui, Add, Button, gButtonStop vBtnStop x+5 w100 h40, Stop

Gui, Add, Text, w560 y+5 0x10 x10

; Window Management Controls (v3.7.2)
Gui, Font, s8 Bold
Gui, Add, Text, vWindowCountText x10 w350 y+5, Wins: 0 | Files: 0
Gui, Font, s7 Normal
Gui, Add, Button, gForceCloseWindows x+10 w120 h20, Force Close HTML
Gui, Font, s8 Normal

Gui, Add, Text, w560 y+5 0x10 x10

; HTML Threshold Controls (v3.7.2)
IniRead, htmlCloseThreshold, %iniFile%, settings, html_close_threshold, 20
IniRead, htmlKeepCount, %iniFile%, settings, html_keep_count, 10
Gui, Font, s8 Bold cTeal
Gui, Add, Text, x10 w100 y+3, HTML Limit:
Gui, Font, s8 Normal
Gui, Add, Button, gHtmlThresholdDown x+5 yp-2 w20 h18, -
Gui, Add, Text, vHtmlThresholdText x+3 yp+2 w30 Center, %htmlCloseThreshold%
Gui, Add, Button, gHtmlThresholdUp x+3 yp-2 w20 h18, +
Gui, Add, Text, x+10 yp+2, (Keep:
Gui, Add, Text, vHtmlKeepText x+2 yp w25, %htmlKeepCount%
Gui, Add, Text, x+0 yp, )

; Timer for Window Count
SetTimer, UpdateWindowCount, 2000

Gui, Show, w580 h750, SIMPLE LOOP v1.1

; Auto Start Mode: /auto 인수로 실행 시 2초 후 자동 시작
if (autoStartMode) {
    GuiControl,, StatusText, [AUTO MODE] 2초 후 자동 시작...
    SetTimer, AutoStartLoop, -2000
}

return

AutoStartLoop:
    GuiControl,, StatusText, [AUTO MODE] Starting...
    IniWrite, 0, %iniFile%, resume_v35, last_index
    isPaused := false
    resumeMode := false
    Goto, StartLoop
return

ButtonStart:
    GuiControl,, StatusText, Resetting...
    IniWrite, 0, %iniFile%, resume_v35, last_index
    isPaused := false
    isStopped := false
    resumeMode := false
    testCounter := 0
    skippedCount := 0
    Goto, StartLoop
return

ButtonResume:
    GuiControl,, StatusText, Resuming...
    IniRead, savedIdx, %iniFile%, resume_v35, last_index, 0
    if (savedIdx == 0) {
        MsgBox, 48, Resume, No saved progress found (v3.5).
        return
    }
    resumeMode := true
    resumeTargetIndex := savedIdx
    isPaused := false
    Goto, StartLoop
return

ButtonStop:
    Reload
return

ButtonPause:
    isPaused := !isPaused
    if (isPaused) {
        GuiControl,, BtnPause, Resume (Paused)
        GuiControl,, StatusText, Status: PAUSED
    } else {
        GuiControl,, BtnPause, Pause
        GuiControl,, StatusText, Status: Running
    }
return

GuiClose:
    ExitApp
return

LoopOrderChanged:
    Gui, Submit, NoHide
    loopOrder := (LoopOrderSelect = "Option B (전체분산-대규모)") ? "B" : "A"
    IniWrite, %loopOrder%, %iniFile%, settings, loop_order
    if (loopOrder = "B")
        GuiControl,, OrderDisplay, Order: Period → Symbol → TF → EA
    else
        GuiControl,, OrderDisplay, Order: EA → Symbol → TF → Period
return

ManualWindowFix:
    Gosub, WindowFixer
return

WindowFixer:
    ; NC version might not need aggressive window fixing, but included if user wants
return

UpdateWindowCount:
    SetTitleMatchMode, 2
    WinGet, idList1, List, TripleSuperTrend
    WinGet, idList2, List, Strategy Tester
    
    ; Combine counts
    totalWindows := idList1 + idList2
    
    ; Count HTML files for accurate progress tracking
    IniRead, htmlPathDir, %iniFile%, folders, html_save_path, D:\report for backtest\BRT2.3
    fileCount := 0
    ; File counting disabled for speed
        fileCount := "N/A"
        
    GuiControl,, WindowCountText, Wins: %totalWindows% | Files: %fileCount%
return

ForceCloseWindows:
    SetTitleMatchMode, 2
    WinGet, idList1, List, TripleSuperTrend
    WinGet, idList2, List, Strategy Tester
    totalWindows := idList1 + idList2
    
    if (totalWindows == 0) {
        MsgBox, 64, Info, No report windows (TripleSuperTrend/Strategy Tester) found.
        return
    }
    
    MsgBox, 4, Confirm, Close %totalWindows% report windows?
    IfMsgBox Yes
    {
        Loop, %idList1%
        {
            this_id := idList1%A_Index%
            WinClose, ahk_id %this_id%
        }
        Loop, %idList2%
        {
            this_id := idList2%A_Index%
            WinClose, ahk_id %this_id%
        }
        GuiControl,, WindowCountText, Report Windows: 0
    }
return

StartLoop:
    ; Reload Settings before starting
    Gosub, LoadSettingsV36Standalone
    
    if (totalTests = 0) {
        MsgBox, 48, 설정 오류, 체크된 EA, 심볼, 타임프레임 또는 기간이 없습니다.`n테스트 설정을 확인해 주세요.
        return
    }
    
    if (loopOrder = "B") {
        Gosub, StartLoopOptionB
    } else {
        Gosub, StartLoopOptionA
    }
return

StartLoopOptionA:
    activeEA_Count := selectedEAs.Length()
    FileAppend, [DEBUG] StartLoop EA Count: %activeEA_Count%`n, %logFile%
    FileAppend, [START] Beginning loop execution (Option A)`n, %logFile%
    
    testCounter := 0
    skippedCount := 0
    
    IniRead, htmlPath, %iniFile%, folders, html_save_path, D:\report for backtest\BRT2.3
    StringReplace, htmlPath, htmlPath, /, \, All
    htmlSaveFolder := htmlPath 
    
    GuiControl, Disable, BtnStart
    GuiControl, Disable, BtnResume
    
    Loop, %activeEA_Count%
    {
        eaIdx := A_Index
        currentEAFile := selectedEAs[eaIdx]
        eaName := StrReplace(currentEAFile, ".ex4", "")
        zeroTradeCount := 0
        skipCurrentEA := false
        FileDelete, %eaFolder%\no_trade\diagnosis_%eaName%.txt 
        
        Loop, 10
        {
            sIdx := A_Index
            if (sym%sIdx%Chk != 1 || sym%sIdx% == "")
                continue
            if (skipCurrentEA)
                break
            currentSym := sym%sIdx%
            
            Loop, 6
            {
                tIdx := A_Index
                currentTF := ""
                if (tIdx=1 && tfM1 = 1) 
                    currentTF:="M1"
                else if (tIdx=2 && tfM5 = 1) 
                    currentTF:="M5"
                else if (tIdx=3 && tfM15 = 1) 
                    currentTF:="M15"
                else if (tIdx=4 && tfM30 = 1) 
                    currentTF:="M30"
                else if (tIdx=5 && tfH1 = 1) 
                    currentTF:="H1"
                else if (tIdx=6 && tfH4 = 1) 
                    currentTF:="H4"
                
                if (currentTF == "")
                    continue
                if (skipCurrentEA)
                    break
                
                Loop, 24
                {
                    pIdx := A_Index
                    ; === PAUSE/STOP CHECK ===
                    if (isStopped)
                    {
                        FileAppend, [STOP] Detected isStopped in OptionA loop`n, %logFile%
                        return
                    }
                    Loop
                    {
                        if (!isPaused)
                            break
                        Sleep, 500
                        if (isStopped)
                            return
                    }

                    IniRead, pEnable, %iniFile%, test_date, enable%pIdx%, 0
                    if (pEnable != 1)
                        continue
                    if (skipCurrentEA)
                        break
                    
                    IniRead, pFrom, %iniFile%, test_date, from_date%pIdx%,
                    IniRead, pTo, %iniFile%, test_date, to_date%pIdx%,
                    if (pFrom == "" || pTo == "")
                        continue
                    
                    Gosub, ExecuteOneTest
                }
            }
        }
    }
    Gosub, FinalizeLoop
return

StartLoopOptionB:
    activeEA_Count := selectedEAs.Length()
    FileAppend, [DEBUG] StartLoop EA Count: %activeEA_Count%`n, %logFile%
    FileAppend, [START] Beginning loop execution (Option B)`n, %logFile%
    
    testCounter := 0
    skippedCount := 0
    
    IniRead, htmlPath, %iniFile%, folders, html_save_path, D:\report for backtest\BRT2.3
    StringReplace, htmlPath, htmlPath, /, \, All
    htmlSaveFolder := htmlPath 
    
    GuiControl, Disable, BtnStart
    GuiControl, Disable, BtnResume
    
    ; ===== Period Loop (바깥) =====
    Loop, 24
    {
        pIdx := A_Index
        IniRead, pEnable, %iniFile%, test_date, enable%pIdx%, 0
        if (pEnable != 1)
            continue
        
        IniRead, pFrom, %iniFile%, test_date, from_date%pIdx%,
        IniRead, pTo, %iniFile%, test_date, to_date%pIdx%,
        if (pFrom == "" || pTo == "")
            continue
        
        ; ===== Symbol Loop =====
        Loop, 10
        {
            sIdx := A_Index
            if (sym%sIdx%Chk != 1 || sym%sIdx% == "")
                continue
            currentSym := sym%sIdx%
            
            ; ===== TF Loop =====
            Loop, 6
            {
                tIdx := A_Index
                currentTF := ""
                if (tIdx=1 && tfM1 = 1) 
                    currentTF:="M1"
                else if (tIdx=2 && tfM5 = 1) 
                    currentTF:="M5"
                else if (tIdx=3 && tfM15 = 1) 
                    currentTF:="M15"
                else if (tIdx=4 && tfM30 = 1) 
                    currentTF:="M30"
                else if (tIdx=5 && tfH1 = 1) 
                    currentTF:="H1"
                else if (tIdx=6 && tfH4 = 1) 
                    currentTF:="H4"
                
                if (currentTF == "")
                    continue
                
                ; ===== EA Loop (안쪽) =====
                Loop, %activeEA_Count%
                {
                    eaIdx := A_Index
                    currentEAFile := selectedEAs[eaIdx]
                    eaName := StrReplace(currentEAFile, ".ex4", "")
                    
                    ; === PAUSE/STOP CHECK ===
                    if (isStopped)
                    {
                        FileAppend, [STOP] Detected isStopped in OptionB loop`n, %logFile%
                        return
                    }
                    Loop
                    {
                        if (!isPaused)
                            break
                        Sleep, 500
                        if (isStopped)
                            return
                    }
                    
                    Gosub, ExecuteOneTest
                }
            }
        }
    }
    Gosub, FinalizeLoop
return

ExecuteOneTest:
    ; === STATE SYNC ===
    IniWrite, 1, %iniFile%, test_date, enable
    IniWrite, %pFrom%, %iniFile%, test_date, from_date
    IniWrite, %pTo%, %iniFile%, test_date, to_date

    Gosub, CheckAndCloseOldHTML

    ; === AUTO-SKIP LOGIC ===
    pFromClean := StrReplace(pFrom, ".", "")
    pToClean := StrReplace(pTo, ".", "")
    testPeriodStr := "_" . pFromClean . "-" . pToClean
    eaClean := RegExReplace(eaName, "[\\/:*?""<>|]", "")
    targetDir := htmlPath . "\" . eaClean
    searchPattern := targetDir . "\" . eaClean . "_" . currentSym . "_" . currentTF . testPeriodStr . "_*.htm"
    
    fileFound := false
    Loop, Files, %searchPattern%
    {
        fileFound := true
        break
    }
    
    if (fileFound) {
        skippedCount++
        testCounter++ ; still count it as a "processed" test for index purposes
        GuiControl,, SkippedText, Skipped: %skippedCount%
        GuiControl,, CurrentText, Skipping (Exists): %eaName% %currentSym%
        FileAppend, [SKIP] Found existing: %eaClean%_%currentSym%_%currentTF%%testPeriodStr%`n, %logFile%
        return
    }

    ; === RESUME BTN LOGIC ===
    testCounter++
    if (resumeMode && testCounter <= resumeTargetIndex) {
        GuiControl,, CurrentText, Fast-Forwarding #%testCounter%...
        return
    }
    if (resumeMode) {
        resumeMode := false 
        FileAppend, [RESUME] Resuming actual work from Test #%testCounter%`n, %logFile%
    }

    ; === RUN TEST ===
    IniWrite, %testCounter%, %iniFile%, resume_v35, last_index
    progressPct := Round((testCounter / totalTests) * 100, 1)
    GuiControl,, ProgressBar, %progressPct%
    GuiControl,, CurrentText, [%testCounter%/%totalTests%] %eaName% | %currentSym% | %currentTF%
    GuiControl,, StatusText, RUNNING (Period %pIdx%)
    
    FileAppend, [RUN] #%testCounter%: %eaName% %currentSym% %currentTF% %pFrom%~%pTo%`n, %logFile%
    
    ; EA Name File
    eaNameFile := A_WorkingDir . "\configs\current_ea_name.txt"
    FileDelete, %eaNameFile%
    FileAppend, %currentEAFile%, %eaNameFile%, UTF-8
    
    ; Run 4Steps Script
    runnerScript := A_ScriptDir . "\SIMPLE_4STEPS_v4_0.ahk"
    completionMarker := A_WorkingDir . "\configs\test_completed.flag"
    FileDelete, %completionMarker%
    
    Run, "%A_AhkPath%" "%runnerScript%" "%eaName%" "%currentSym%" "%currentTF%" "%testCounter%" "%pFrom%" "%pTo%"
    
    ; Wait for completion
    timeout := 300000
    uStartTime := A_TickCount
    Loop {
        if (FileExist(completionMarker)) {
            FileAppend, [DONE] Test #%testCounter% completed`n, %logFile%
            break
        }
        if (A_TickCount - uStartTime > timeout) {
            FileAppend, [TIMEOUT] Test #%testCounter% timeout`n, %logFile%
            break
        }
        if (isStopped) {
            RunWait, %ComSpec% /c taskkill /F /IM AutoHotkey.exe /FI "WINDOWTITLE eq SIMPLE_4STEPS*" /T,, Hide
            return
        }
        Sleep, 500
    }
    
    ; Live Analysis
    Sleep, 500
    Gosub, AnalyzeLatestReport
    Sleep, 500
return

FinalizeLoop:
    FileAppend, === ALL COMPLETED ===`n, %logFile%
    GuiControl,, StatusText, COMPLETED!
    GuiControl,, CurrentText, All tests finished
    MsgBox, 64, 완료, 전체 테스트 완료!`n총: %testCounter%개`nSkip: %skippedCount%개, 3

    ; [AUTO-ANALYZE] Only run if tests were actually processed
    if (testCounter > 0) {
        analyzerScript := A_ScriptDir . "\..\BacktestAnalyzer_v1.7.py"
        SplitPath, htmlSaveFolder,, analyzeFolder
        if (FileExist(analyzerScript) && analyzeFolder != "" && FileExist(analyzeFolder)) {
            GuiControl,, StatusText, 분석 중...
            GuiControl,, CurrentText, 분석기 실행 중...
            
            ; [v3.9] 분석기 실행 (보이는 창으로)
            RunWait, "%pythonExePath%" "%analyzerScript%" "%analyzeFolder%",, UseErrorLevel
            
            ; [NEW] 분석 완료 팝업 자동 닫기
            Sleep, 500
            WinWait, ahk_class #32770,, 3  ; 3초 대기
            if (!ErrorLevel) {
                ; "Processed" 또는 "Complete" 텍스트가 있는 팝업 찾기
                WinGetText, popupText, ahk_class #32770
                if (InStr(popupText, "Processed") || InStr(popupText, "Complete") || InStr(popupText, "완료")) {
                    WinClose, ahk_class #32770
                    Sleep, 200
                }
            }
        }
    } else {
        FileAppend, [DEBUG] FinalizeLoop reached with 0 tests. Skipping Analyzer.`n, %logFile%
    }

    IniWrite, 0, %iniFile%, resume_v35, last_index
    GuiControl, Enable, BtnStart
    GuiControl, Enable, BtnResume
    ExitApp
return

Esc:: ExitApp

; =====================================================
; Live Analysis (v2.5 Trusted Logic)
; =====================================================
AnalyzeLatestReport:
    global htmlSaveFolder, laLastFile, analyzedFiles
    global laTotalTests, laProfitTests, laLossTests, laTotalProfit, laTotalLoss, laMaxDD
    global laGrossProfit, laGrossLoss, laTotalTrades
    global laTotalWonTrades, laTotalLostTrades ; Added for v3.9 logic
    global eaFolder, currentEAFile, eaName ; [v3.9] Access global EA info
    global zeroTradeCount, skipCurrentEA ; [v3.9] Access global no-trade counters

    if (htmlSaveFolder = "" || !FileExist(htmlSaveFolder)) {
        return
    }

    ; Find most recent .htm file
    latestFile := ""
    latestTime := 0

    ; [v3.7.2] Optimized: Read path directly instead of recursive scanning
    lastReportFile := A_ScriptDir "\..\configs\last_report_path.txt"
    if FileExist(lastReportFile) {
        FileRead, latestFile, %lastReportFile%
        latestFile := Trim(latestFile)
    }

    if (latestFile = "" || !FileExist(latestFile)) {
        ; Fallback to older method if file not found (non-recursive for speed)
        Loop, %htmlSaveFolder%\*.htm
        {
            FileGetTime, modTime, %A_LoopFileLongPath%
            if (modTime > latestTime) {
                latestTime := modTime
                latestFile := A_LoopFileLongPath
            }
        }
    }

    if (latestFile = "")
        return

    ; Skip if already analyzed
    if (analyzedFiles.HasKey(latestFile))
        return

    ; Mark as analyzed
    analyzedFiles[latestFile] := 1
    laLastFile := latestFile

    ; File size check (max 5MB to prevent Out of Memory)
    FileGetSize, fileSize, %latestFile%
    if (fileSize > 5242880) {
        FileAppend, [WARN] Skipping analysis - file too large: %fileSize% bytes`n, %logFile%
        return
    }

    FileRead, content, %latestFile%
    if (ErrorLevel)
        return

    ; Parse EA name from title
    eaNameParsed := "Unknown"
    if (RegExMatch(content, "i)<title>.*?:\s*(.+?)</title>", titleMatch)) {
        eaNameParsed := Trim(titleMatch1)
    }

    ; Parse trades
    trades := 0
    if (RegExMatch(content, "<td>[^<]*</td><td align=right>(\d+)</td><td>[^<]*\(won\s*%\)", korMatch)) {
        trades := korMatch1
    } else if (RegExMatch(content, "align=right>(\d+)</td><td[^>]*>.*?won\s*%", trMatch)) {
        trades := trMatch1
    } else if (RegExMatch(content, "i)Total Trades.*?<[^>]*>\s*(\d+)", trMatch2)) {
        trades := trMatch2_1
    }

    ; Parse profit/grossprofit/grossloss (Korean pattern)
    profit := 0
    gProfit := 0
    gLoss := 0

    if (RegExMatch(content, "<td align=right>(-?[\d\.]+)</td><td>[^<]*</td><td align=right>([\d\.]+)</td><td>[^<]*</td><td align=right>(-[\d\.]+)</td></tr>", korProfit)) {
        profit := korProfit1
        gProfit := korProfit2
        gLoss := korProfit3
    } else if (RegExMatch(content, "i)Total Net Profit.*?<[^>]*>\s*(-?[\d,\.]+)", profMatch)) {
        profit := StrReplace(profMatch1, ",", "")
    }

    ; Parse Gross Profit/Loss (English)
    if (gProfit = 0) {
        if (RegExMatch(content, "i)Gross Profit.*?<[^>]*>\s*(-?[\d,\.]+)", gpMatch)) {
            gProfit := StrReplace(gpMatch1, ",", "")
        }
    }
    if (gLoss = 0) {
        if (RegExMatch(content, "i)Gross Loss.*?<[^>]*>\s*(-?[\d,\.]+)", glMatch)) {
            gLoss := StrReplace(glMatch1, ",", "")
        }
    }

    ; Parse drawdown
    dd := 0
    if (RegExMatch(content, "<td align=right>(\d+\.?\d*)%\s*\([\d\.]+\)</td>", korDD)) {
        dd := korDD1
    } else if (RegExMatch(content, "i)Maximal Drawdown.*?(\d+\.?\d*)\s*\((\d+\.?\d*)%\)", ddMatch)) {
        dd := ddMatch2
    } else if (RegExMatch(content, "align=right>(\d+\.?\d*)%\s*\([\d,\.]+\)</td></tr>", ddMatch2)) {
        dd := ddMatch2_1
    }

    ; Parse Win Rate & Won/Lost Trades (v3.9 - Ultimate Fix)
    winRate := 0
    wonTrades := 0
    lostTrades := 0

    ; [Permissive Match] Grab the first number after "Profit trades" tag
    if (RegExMatch(content, "is)Profit trades[^\d]+(\d+)", pTradeMatch)) {
        wonTrades := pTradeMatch1
    }
    
    if (RegExMatch(content, "is)Loss trades[^\d]+(\d+)", lTradeMatch)) {
        lostTrades := lTradeMatch1
    }

    ; Win Rate Parsing (Existing Working Logic)
    if (RegExMatch(content, "won\s*%\)[^<]*</td><td[^>]*align=right>\d+\s*\((\d+\.?\d*)%\)", winMatch)) {
        winRate := winMatch1
    } else if (RegExMatch(content, "i)Profit Trades.*?\((\d+\.?\d*)%\)", winMatch2)) {
        winRate := winMatch2_1
    }

    ; [Fallback Calculation] If regex failed but we have Total Trades and Win Rate
    if (wonTrades = 0 && trades > 0 && winRate > 0) {
        wonTrades := Round(trades * (winRate / 100))
        lostTrades := trades - wonTrades
    }
    
    ; If we have wonTrades but lostTrades is 0 (and Total is known), calculate lost
    if (wonTrades > 0 && lostTrades = 0 && trades > 0) {
        lostTrades := trades - wonTrades
    }

    ; Update live analysis
    laTotalTests++
    laTotalTrades += trades
    
    ; Accumulate Won/Lost Trades
    laTotalWonTrades += wonTrades
    laTotalLostTrades += lostTrades

    if (profit + 0 > 0) {
        laProfitTests++
        laTotalProfit += profit
    } else if (profit + 0 < 0) {
        laLossTests++
        laTotalLoss += profit
    }

    laGrossProfit += gProfit
    laGrossLoss += gLoss

    if (dd + 0 > laMaxDD)
        laMaxDD := dd

    ; Update GUI (v3.9: Clearer labels for user)
    netProfit := laTotalProfit + laTotalLoss
    netProfitStr := Format("{:+.2f}", netProfit)
    grossPStr := Format("{:+.2f}", laGrossProfit)
    grossLStr := Format("{:.2f}", laGrossLoss)

    liveText1 := "Tests: " . laTotalTests . " | MaxDD: " . laMaxDD . "% | WinRate: " . winRate . "%"
    liveText2 := "P.Tests: " . laProfitTests . " | L.Tests: " . laLossTests . " | Trades: " . laTotalTrades . " (W:" . laTotalWonTrades . " L:" . laTotalLostTrades . ")"
    liveText3 := "Net: $" . netProfitStr . " | GrossP: $" . grossPStr . " | GrossL: $" . grossLStr
    liveText4 := "Last: " . eaNameParsed

    GuiControl,, LiveAnalysisText, %liveText1%
    GuiControl,, LiveProfitText, %liveText2%
    GuiControl,, LiveNetText, %liveText3%
    GuiControl,, LiveLastEA, %liveText4%

    FileAppend, [LIVE ANALYSIS] Analyzed %latestFile% | Trades: %trades% (W:%wonTrades% L:%lostTrades%) | Profit: %profit%`n, %logFile%

    ; [v3.9] No Trade Detection & Diagnosis
    if (trades = 0) {
        zeroTradeCount++
        FileAppend, [WARN] Zero Trades Detected (%zeroTradeCount%/5) for %eaName%`n, %logFile%
        
        ; [v3.9] Diagnosis Logic
        IniRead, termPath, %iniFile%, folders, terminal_path
        FormatTime, todayStr, , yyyyMMdd
        testerLog := termPath . "\tester\logs\" . todayStr . ".log"
        
        diagnosisMsg := "Reason: Unknown (Check Manual)"
        
        if (FileExist(testerLog)) {
             ; [v3.9 Fix] Memory Crash Fix: Read only last 2KB
             fObj := FileOpen(testerLog, "r")
             if (fObj) {
                 fSize := fObj.Length
                 if (fSize > 2000) {
                     fObj.Seek(fSize - 2000, 0)
                 }
                 recentLog := fObj.Read()
                 fObj.Close()
             } else {
                 recentLog := ""
             }

             if (InStr(recentLog, "OrderSend error 131"))
                diagnosisMsg := "Reason: Invalid Trade Volume (Err 131)"
             else if (InStr(recentLog, "zero divide"))
                diagnosisMsg := "Reason: Zero Divide (Code Bug)"
             else if (InStr(recentLog, "history data"))
                diagnosisMsg := "Reason: Missing History Data"
             else if (InStr(recentLog, "mismatched charts"))
                diagnosisMsg := "Reason: Mismatched Charts"
             else if (InStr(recentLog, "critical error"))
                diagnosisMsg := "Reason: Critical Execution Error"
        }

        ; [v3.9 Fix] Close Excessive Report Windows
        SetTitleMatchMode, 2
        WinGet, idList, List, Strategy Tester
        if (idList > 100) {
            Loop, %idList%
            {
                this_id := idList%A_Index%
                WinClose, ahk_id %this_id%
            }
            Sleep, 1000
        }
        
        noTradeDir := eaFolder . "no_trade"
        IfNotExist, %noTradeDir%
            FileCreateDir, %noTradeDir%
            
        FileAppend, [Run #%laTotalTests%] %diagnosisMsg%`n, %noTradeDir%\diagnosis_%eaName%.txt
        
    } else {
        zeroTradeCount := 0
    }

    if (zeroTradeCount >= 5) {
        skipCurrentEA := true
        
        noTradeDir := eaFolder . "no_trade"
        IfNotExist, %noTradeDir%
            FileCreateDir, %noTradeDir%
            
        ; Move EA File
        sourcePath := eaFolder . currentEAFile
        destPath := noTradeDir . "\" . currentEAFile
        
        FileMove, %sourcePath%, %destPath%, 1
        
        GuiControl,, StatusText, REMOVED: %eaName% (5x No Trade)
        FileAppend, [REMOVE] Moved %currentEAFile% to no_trade folder (5 consecutive no-trades)`n, %logFile%
        
        MsgBox, 48, EA Removed, %eaName% has been moved to no_trade folder due to 5 consecutive runs with 0 trades., 2
    }

return

; =====================================================
; 설정 로드 (Improvement based on v2.5 Logic)
; =====================================================
LoadSettingsV36Standalone:
    iniFile := A_ScriptDir . "\..\configs\current_config.ini"
    logFile := A_ScriptDir . "\simple_loop_v3_7_log.txt"
    
    ; 1. EA Folder
    IniRead, eaFolder, %iniFile%, folders, ea_path, NONE
    StringReplace, eaFolder, eaFolder, /, \, All
    if (SubStr(eaFolder, StrLen(eaFolder)) != "\")
        eaFolder .= "\"
        
    FileAppend, [DEBUG] Loading EA Folder: %eaFolder%`n, %logFile%

    IniRead, htmlSaveFolder, %iniFile%, folders, html_save_path, NONE
    StringReplace, htmlSaveFolder, htmlSaveFolder, /, \, All

    ; 2. EA Selection
    activeEACount := 0
    selectedEAs := []
    
    IniRead, eaAll, %iniFile%, selection, ea_all, 1
    
    Loop, 5 {
        IniRead, ea%A_Index%, %iniFile%, selection, ea%A_Index%, 0
    }

    if (eaFolder != "" && FileExist(eaFolder)) {
        FileAppend, [DEBUG] Scanning files...`n, %logFile%
        oldDir := A_WorkingDir
        SetWorkingDir, %eaFolder%
        
        Loop, *.ex4
        {
            shouldAdd := false
            if (eaAll = 1 || eaAll = "true") {
                shouldAdd := true
            } else {
                idx := A_Index
                if (idx <= 5 && ea%idx% == 1)
                    shouldAdd := true
            }
            
            if (shouldAdd) {
                selectedEAs.Push(A_LoopFileName)
                activeEACount++
                FileAppend, [DEBUG] Added: %A_LoopFileName%`n, %logFile%
            }
        }
        SetWorkingDir, %oldDir%
        
        ; Sort
        eaCountSort := selectedEAs.Length()
        if (eaCountSort > 1) {
            Loop, % eaCountSort - 1 {
                iSort := A_Index
                Loop, % eaCountSort - iSort {
                    jSort := A_Index
                    kSort := jSort + 1
                    val1 := selectedEAs[jSort]
                    val2 := selectedEAs[kSort]
                    if (val1 > val2) {
                        selectedEAs[jSort] := val2
                        selectedEAs[kSort] := val1
                    }
                }
            }
        }
    } else {
        FileAppend, [ERROR] Folder invalid: %eaFolder%`n, %logFile%
    }

    ; 3. Date Settings
    periodList := ""
    periodCount := 0
    Loop, 24 {
        idx := A_Index
        IniRead, pEnable, %iniFile%, test_date, enable%idx%, 0
        IniRead, pFrom, %iniFile%, test_date, from_date%idx%,
        IniRead, pTo, %iniFile%, test_date, to_date%idx%,
        testDateEnable%idx% := pEnable
        testFromDate%idx% := pFrom
        testToDate%idx% := pTo
        if (pEnable == 1) {
            periodCount++
            periodList .= "[" idx "] " pFrom " ~ " pTo . "|" 
        }
    }

    ; 4. Symbol & Timeframe (Simplified Read)
    displaySymCount := 0
    symList := ""
    Loop, 10 {
        IniRead, symName, %iniFile%, symbols, sym%A_Index%,
        rawSym := symName
        if (InStr(rawSym, ","))
            symName := Trim(SubStr(rawSym, 1, InStr(rawSym, ",") - 1))
        
        IniRead, chk, %iniFile%, selection, sym%A_Index%Chk, 0
        sym%A_Index% := symName
        sym%A_Index%Chk := chk
        
        if (chk == 1 && symName != "") {
            displaySymCount++
            symList .= symName . " "
        }
    }
    
    displayTfCount := 0
    tfList := ""
    tfNames := ["M1","M5","M15","M30","H1","H4"]
    For each, tfName in tfNames {
        IniRead, tfVal, %iniFile%, selection, tf%tfName%, 0
        tf%tfName% := tfVal ; Ensure global var is set
        if (tfVal = 1) {
            displayTfCount++
            tfList .= tfName . " "
        }
    }

    ; Update GUI
    symCount := displaySymCount
    tfCount := displayTfCount
    totalTests := activeEACount * symCount * tfCount * periodCount
    
    FileAppend, [DEBUG] Totals - EA:%activeEACount%, Sym:%symCount%, TF:%tfCount%, Period:%periodCount% = %totalTests% tests`n, %logFile%
    
    GuiControl,, EACountText, EA: %activeEACount% Selected
    GuiControl,, TotalTestsText, Total: %activeEACount% x %symCount% x %tfCount% x %periodCount% = %totalTests% Tests
return

; =====================================================
; HTML 창 제한 (v3.7.2: 테스트 카운터 기반)
; =====================================================
CheckAndCloseOldHTML:
    global htmlTestCounter
    if (!htmlTestCounter)
        htmlTestCounter := 0

    htmlTestCounter++

    IniRead, htmlCloseThreshold, %iniFile%, settings, html_close_threshold, 20
    IniRead, htmlKeepCount, %iniFile%, settings, html_keep_count, 10

    FileAppend, [HTML CHECK] Test #%htmlTestCounter% / %htmlCloseThreshold%`n, %logFile%

    ; 테스트 횟수가 threshold에 도달하면 탭 정리
    if (htmlTestCounter >= htmlCloseThreshold) {
        tabsToClose := htmlTestCounter - htmlKeepCount
        FileAppend, [HTML CLOSE] %htmlTestCounter% tests reached. Closing %tabsToClose% tabs...`n, %logFile%

        if WinExist("ahk_class Chrome_WidgetWin_1") {
            WinActivate
            Sleep, 300

            tabsClosed := 0
            Loop, %tabsToClose%
            {
                Send, ^w
                Sleep, 80
                tabsClosed++

                if (Mod(A_Index, 10) = 0)
                    Sleep, 200
            }

            FileAppend, [HTML CLOSE] Closed %tabsClosed% Chrome tabs`n, %logFile%
        }

        htmlTestCounter := 0
    }
return

; =====================================================
; HTML Threshold Controls
; =====================================================
HtmlThresholdUp:
    htmlCloseThreshold += 10
    if (htmlCloseThreshold > 100)
        htmlCloseThreshold := 20
    htmlKeepCount := htmlCloseThreshold - (htmlCloseThreshold > 10 ? 10 : 1)
    if (htmlKeepCount < 1)
        htmlKeepCount := 1
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    GuiControl,, HtmlKeepText, %htmlKeepCount%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
    IniWrite, %htmlKeepCount%, %iniFile%, settings, html_keep_count
return

HtmlThresholdDown:
    htmlCloseThreshold -= 10
    if (htmlCloseThreshold < 2)
        htmlCloseThreshold := 2
    htmlKeepCount := htmlCloseThreshold - (htmlCloseThreshold > 10 ? 10 : 1)
    if (htmlKeepCount < 1)
        htmlKeepCount := 1
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    GuiControl,, HtmlKeepText, %htmlKeepCount%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
    IniWrite, %htmlKeepCount%, %iniFile%, settings, html_keep_count
return
