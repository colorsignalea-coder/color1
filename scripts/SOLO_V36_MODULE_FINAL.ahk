; =====================================================
; SOLO_V36_MODULE.ahk
; Integrated v3.6 Logic for SOLO_ALL_IN_ONE.ahk
; [수정 완료] v3.6 LoadAllSettings 복구 및 루프 로직 개선
; [v3.7.1] HTML Limit 및 자동 탭 관리 기능 추가
; =====================================================

global htmlTestCounter := 0

; =====================================================
; v3.6 4Steps Launcher (Single Run)
; =====================================================
RunStepV36:
    Gosub, SaveSettings
    Gosub, SaveDateSettings
    
    scriptPath := scriptsFolder . "\SIMPLE_4STEPS_v3_7.ahk" ; v3.7로 연결
    
    if (!FileExist(scriptPath)) {
        MsgBox, 48, Error, Script not found:`n%scriptPath%
        return
    }
    
    Run, "%A_AhkPath%" "%scriptPath%"
return

; =====================================================
; [중요] v3.6 내부 루프 실행 (메뉴 설정 연동)
; =====================================================
RunLoopV36Internal:
    ; [중요] 현재 GUI 설정 저장
    Gosub, SaveSettings
    Gosub, SaveDateSettings
    
    ; [수정됨] 설정 다시 로드 (동기화 보장)
    Gosub, LoadAllSettings
    
    ; EA 폴더 경로 재확인 및 로드
    IniRead, eaFolder, %iniFile%, folders, ea_path, NOTSET
    StringReplace, eaFolder, eaFolder, /, \, All
    
    selectedEAs := []
    activeEACount := 0
    
    if (eaFolder != "NOTSET" && eaFolder != "") {
        Loop, %eaFolder%\*.ex4
        {
            shouldAdd := false
            if (eaAll = 1) {
                shouldAdd := true
            } else {
                idx := A_Index
                if (idx <= 5 && ea%idx% == 1)
                    shouldAdd := true
            }
            
            if (shouldAdd) {
                selectedEAs.Push(A_LoopFileName)
                activeEACount++
            }
        }
    }
    
    ; Symbol 개수 (LoadAllSettings에서 갱신됨)
    symCount := 0
    Loop, 10 {
        if (sym%A_Index%Chk = 1 && sym%A_Index% != "")
            symCount++
    }
    
    ; TF 개수
    tfCount := 0
    if (tfM1) tfCount++
    if (tfM5) tfCount++
    if (tfM15) tfCount++
    if (tfM30) tfCount++
    if (tfH1) tfCount++
    if (tfH4) tfCount++
    
    ; Period 개수
    periodCount := 0
    Loop, 24 {
        if (testDateEnable%A_Index% = 1)
            periodCount++
    }
    
    ; 총 테스트 예상 횟수
    totalTests := activeEACount * symCount * tfCount * periodCount
    
    ; GUI 상단 텍스트 업데이트
    GuiControl,, CurrentText, [준비] EA: %activeEACount% | Sym: %symCount% | TF: %tfCount% | Period: %periodCount%
    GuiControl,, StatusText, 총 %totalTests% 테스트 시작 준비
    
    ; 사용자 확인 메시지
    MsgBox, 4, v3.6 Loop, EA: %activeEACount%`nSymbol: %symCount%`nTF: %tfCount%`nPeriod: %periodCount%`n`n총 %totalTests% 테스트를 시작하시겠습니까?
    IfMsgBox, No
        return
    
    htmlTestCounter := 0 ; 카운터 초기화
    ; 실제 메인 루프 진입
    Gosub, MainLoopV36
return

; =====================================================
; [중요] 실제 테스트 실행 루프 (MainLoopV36)
; =====================================================
MainLoopV36:
    testCounter := 0
    
    ; 1. EA Loop
    Loop % selectedEAs.Length() {
        eaIdx := A_Index
        currentEAFile := selectedEAs[eaIdx]
        eaName := StrReplace(currentEAFile, ".ex4", "")
        
        ; 2. Symbol Loop
        Loop, 10 {
            sIdx := A_Index
            if (sym%sIdx%Chk != 1 || sym%sIdx% == "")
                continue
            
            currentSym := sym%sIdx%
            
            ; 3. TF Loop
            Loop, 6 {
                tIdx := A_Index
                currentTF := ""
                
                if (tIdx=1 && tfM1) {
                    currentTF:="M1"
                } else if (tIdx=2 && tfM5) {
                    currentTF:="M5"
                } else if (tIdx=3 && tfM15) {
                    currentTF:="M15"
                } else if (tIdx=4 && tfM30) {
                    currentTF:="M30"
                } else if (tIdx=5 && tfH1) {
                    currentTF:="H1"
                } else if (tIdx=6 && tfH4) {
                    currentTF:="H4"
                }
                
                if (currentTF == "")
                    continue
                
                ; 4. Period Loop
                Loop, 24 {
                    pIdx := A_Index
                    
                    if (testDateEnable%pIdx% != 1)
                        continue
                    
                    useFromDate := testFromDate%pIdx%
                    useToDate := testToDate%pIdx%
                    
                    testCounter++
                    htmlTestCounter++ ; HTML 카운터 증가
                    
                    ; GUI 진행상황 업데이트
                    progressPct := Round((testCounter / totalTests) * 100, 1)
                    GuiControl,, ProgressBar, %progressPct%
                    GuiControl,, CurrentText, [%testCounter%/%totalTests%] %eaName% | %currentSym% | %currentTF% | P%pIdx%
                    GuiControl,, StatusText, %useFromDate% ~ %useToDate%
                    
                    ; [중요] 현재 테스트 정보 INI 저장 (Runner가 참조함)
                    IniWrite, %currentEAFile%, %iniFile%, current_backtest, ea_name
                    IniWrite, %currentSym%, %iniFile%, current_backtest, symbol
                    IniWrite, %currentTF%, %iniFile%, current_backtest, period
                    IniWrite, 1, %iniFile%, test_date, enable
                    IniWrite, %useFromDate%, %iniFile%, test_date, from_date
                    IniWrite, %useToDate%, %iniFile%, test_date, to_date
                    
                    ; [v3.9] 리포트 저장 경로 동적 생성 (Root/Date/EA_Name)
                    ; 기본 경로는 AutoDetect에서 설정된 값을 사용하되, 고정된 루트가 아닌 경우를 위해 D:/ C:/ 체크
                    baseFolder := "D:/report for backtest"
                    if (!FileExist("D:\"))
                        baseFolder := "C:/report for backtest"
                    
                    FormatTime, todayDate, , yyyyMMdd
                    dynamicReportPath := baseFolder . "/" . todayDate . "/" . eaName
                    
                    if (!FileExist(dynamicReportPath))
                        FileCreateDir, %dynamicReportPath%
                    
                    ; INI에 현재 리포트 경로 업데이트 (Runner 참조)
                    IniWrite, %dynamicReportPath%, %iniFile%, folders, html_save_path
                    
                    ; 4Steps 실행 (개별 테스트)
                    scriptPath := scriptsFolder . "\SIMPLE_4STEPS_v3_7.ahk" ; v3.7로 연결
                    Run, "%A_AhkPath%" "%scriptPath%" "%eaName%" "%currentSym%" "%currentTF%" "%testCounter%" "%useFromDate%" "%useToDate%"
                    
                    ; 완료 대기 (Flag 파일 감지)
                    completionMarker := A_WorkingDir . "\configs\test_completed.flag"
                    FileDelete, %completionMarker%
                    
                    timeout := 300000 ; 5분 타임아웃
                    startTime := A_TickCount
                    
                    Loop {
                        if (FileExist(completionMarker))
                            break
                        if (A_TickCount - startTime > timeout)
                            break
                        Sleep, 500
                    }
                    
                    ; [v3.7.1] HTML Limit 체크 및 정리
                    CheckAndCloseOldHTML()
                    
                    Sleep, 2000 ; 안정화 대기
                }
            }
        }
    }
    
    MsgBox, 64, 완료, 전체 %testCounter% 테스트 완료!
return

; =====================================================
; [v3.7.1] HTML Limit 및 자동 탭 관리 함수
; =====================================================
CheckAndCloseOldHTML() {
    global htmlCloseThreshold, htmlKeepCount, htmlTestCounter
    
    ; 설정값 확인 (기본값 20/10)
    if (htmlCloseThreshold = "" || htmlCloseThreshold = 0)
        htmlCloseThreshold := 20
    if (htmlKeepCount = "" || htmlKeepCount = 0)
        htmlKeepCount := 10
        
    ; 현재 HTML 창 개수 확인
    WinGet, id, list, ahk_class Chrome_WidgetWin_1
    windowCount := id
    
    ; 가시적인 백테스트 리포트 창만 필터링 (선택 사항, 여기선 전체 크롬 탭 기준)
    ; 만약 HTML 카운터가 임계값을 넘었거나 실제 창 개수가 넘었을 때 처리
    if (windowCount >= htmlCloseThreshold) {
        ; 가장 오래된 탭부터 닫기 (Ctrl+W 활용)
        closeCount := windowCount - htmlKeepCount
        if (closeCount > 0) {
            Loop, %closeCount% {
                ; 크롬 창 활성화 시 순서대로 탭 닫기 로직 (간소화)
                ; 실제로는 CLOSE_ALL_HTML_WINDOWS.ahk의 로직을 활용하거나 직접 WinClose
                WinGet, id_list, list, ahk_class Chrome_WidgetWin_1
                if (id_list > 0) {
                    this_id := id_list%id_list% ; 마지막 ID(가장 먼저 열린 것일 확률 높음)
                    WinClose, ahk_id %this_id%
                    Sleep, 500
                }
            }
        }
    }
}

; =====================================================
; [수정됨] 설정 로드 함수 (LoadAllSettings)
; - 기존의 단순 복귀가 아닌 실제 INI 값을 읽도록 수정됨
; =====================================================
LoadAllSettings:
    ; EA 폴더 경로 재확인
    IniRead, eaFolder, %iniFile%, folders, ea_path, NOTSET
    StringReplace, eaFolder, eaFolder, /, \, All
    
    ; HTML 저장 폴더
    IniRead, htmlSaveFolder, %iniFile%, folders, html_save_path, NOTSET
    StringReplace, htmlSaveFolder, htmlSaveFolder, /, \, All

    ; HTML Limit 설정 읽기
    IniRead, htmlCloseThreshold, %iniFile%, settings, html_close_threshold, 20
    IniRead, htmlKeepCount, %iniFile%, settings, html_keep_count, 10

    ; -----------------------------------------------------
    ; [수정] INI에서 심볼, TF, 기간 설정 다시 읽기 (필수)
    ; -----------------------------------------------------

    ; 1. Symbol Selection (Up to 10)
    Loop, 10 {
        IniRead, sym%A_Index%, %iniFile%, symbols, sym%A_Index%,
        ; Remove comma if present
        rawSym := sym%A_Index%
        commaPos := InStr(rawSym, ",")
        if (commaPos > 0)
            sym%A_Index% := Trim(SubStr(rawSym, 1, commaPos - 1))
            
        IniRead, sym%A_Index%Chk, %iniFile%, selection, sym%A_Index%Chk, 0
    }

    ; 2. Timeframe Selection
    IniRead, tfM1, %iniFile%, selection, tfM1, 0
    IniRead, tfM5, %iniFile%, selection, tfM5, 0
    IniRead, tfM15, %iniFile%, selection, tfM15, 0
    IniRead, tfM30, %iniFile%, selection, tfM30, 0
    IniRead, tfH1, %iniFile%, selection, tfH1, 0
    IniRead, tfH4, %iniFile%, selection, tfH4, 0

    ; 3. Date Settings (24 Periods)
    Loop, 24 {
        idx := A_Index
        IniRead, tempEnable, %iniFile%, test_date, enable%idx%, 0
        IniRead, tempFrom, %iniFile%, test_date, from_date%idx%,
        IniRead, tempTo, %iniFile%, test_date, to_date%idx%,
        
        testDateEnable%idx% := tempEnable
        testFromDate%idx% := tempFrom
        testToDate%idx% := tempTo
    }
    
    ; -----------------------------------------------------

    ; Symbol 개수 계산
    symCount := 0
    Loop, 10 {
        if (sym%A_Index%Chk = 1 && sym%A_Index% != "")
            symCount++
    }
    
    ; TF 개수 계산
    tfCount := 0
    if (tfM1) tfCount++
    if (tfM5) tfCount++
    if (tfM15) tfCount++
    if (tfM30) tfCount++
    if (tfH1) tfCount++
    if (tfH4) tfCount++
    
    ; Period 개수 계산
    periodCount := 0
    Loop, 24 {
        if (testDateEnable%A_Index% = 1)
            periodCount++
    }
    
    ; 총 테스트 개수
    totalTests := activeEACount * symCount * tfCount * periodCount
return
