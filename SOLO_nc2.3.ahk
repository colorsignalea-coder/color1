#NoEnv

#SingleInstance Force

SetWorkingDir, %A_ScriptDir%

; #NoTrayIcon removed for visibility (User Request)

#Persistent

; =====================================================
; MT4 SOLO ALL IN ONE v5.3 (Portable Master Integrated)
; Updated by Antigravity - IDs: 202531, 20250430
; - nc2.0: NO KEYBOARD/MOUSE mode - WinActivate 제거, ControlClick NA + ControlSend
; - v5.3: [NEW] Portable Auto-Detection, MT4 Sibling Discovery
; =====================================================

global currentProfile := "기본"

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
    ; PATH에서 찾기
    RunWait, %ComSpec% /c "where python > "%A_Temp%\python_path.txt"", , Hide
    FileRead, pythonExePath, %A_Temp%\python_path.txt
    pythonExePath := Trim(RegExReplace(pythonExePath, "\r?\n.*"))
    if (!FileExist(pythonExePath))
        pythonExePath := "python"
}

global configsFolder := A_ScriptDir . "\configs"

global profilesFolder := A_ScriptDir . "\configs\profiles"

global scriptsFolder := A_ScriptDir . "\scripts"

global iniFile := ""

; 폴더 생성

IfNotExist, %configsFolder%

    FileCreateDir, %configsFolder%

IfNotExist, %profilesFolder%

    FileCreateDir, %profilesFolder%

IfNotExist, %scriptsFolder%

    FileCreateDir, %scriptsFolder%

; current_config.ini 파일 경로 설정

iniFile := configsFolder . "\current_config.ini"

; 현재 프로필 로드

IniRead, currentProfile, %iniFile%, system, current_profile, 기본

; =====================================================

; 설정 변수

; =====================================================

global workFolder := ""

global setFolder := ""

global terminalPath := ""

global sym1 := ""

global sym2 := ""

global sym3 := ""

global sym4 := ""

global sym5 := ""

global sym1Chk := 0

global sym2Chk := 0

global sym3Chk := 0

global sym4Chk := 0

global sym5Chk := 0

global eaAll := 1

global ea1 := 0

global ea2 := 0

global ea3 := 0

global ea4 := 0

global ea5 := 0

global tfM1 := 0

global tfM5 := 0

global tfM15 := 0

global tfM30 := 0

global tfH1 := 0

global tfH4 := 0

; v3.7: 날짜 설정 변수 (최대 24개 기간 - 3열 x 8행)

global testDateEnable1 := 0, testFromDate1 := "", testToDate1 := ""

global testDateEnable2 := 0, testFromDate2 := "", testToDate2 := ""

global testDateEnable3 := 0, testFromDate3 := "", testToDate3 := ""

global testDateEnable4 := 0, testFromDate4 := "", testToDate4 := ""

global testDateEnable5 := 0, testFromDate5 := "", testToDate5 := ""

global testDateEnable6 := 0, testFromDate6 := "", testToDate6 := ""

global testDateEnable7 := 0, testFromDate7 := "", testToDate7 := ""

global testDateEnable8 := 0, testFromDate8 := "", testToDate8 := ""

global testDateEnable9 := 0, testFromDate9 := "", testToDate9 := ""

global testDateEnable10 := 0, testFromDate10 := "", testToDate10 := ""

global testDateEnable11 := 0, testFromDate11 := "", testToDate11 := ""

global testDateEnable12 := 0, testFromDate12 := "", testToDate12 := ""

global testDateEnable13 := 0, testFromDate13 := "", testToDate13 := ""

global testDateEnable14 := 0, testFromDate14 := "", testToDate14 := ""

global testDateEnable15 := 0, testFromDate15 := "", testToDate15 := ""

global testDateEnable16 := 0, testFromDate16 := "", testToDate16 := ""

global testDateEnable17 := 0, testFromDate17 := "", testToDate17 := ""

global testDateEnable18 := 0, testFromDate18 := "", testToDate18 := ""

global testDateEnable19 := 0, testFromDate19 := "", testToDate19 := ""

global testDateEnable20 := 0, testFromDate20 := "", testToDate20 := ""

global testDateEnable21 := 0, testFromDate21 := "", testToDate21 := ""

global testDateEnable22 := 0, testFromDate22 := "", testToDate22 := ""

global testDateEnable23 := 0, testFromDate23 := "", testToDate23 := ""

global testDateEnable24 := 0, testFromDate24 := "", testToDate24 := ""

global maxPeriods := 24  ; 최대 기간 수

; v3.6: 창 위치 고정 변수

global isWindowLocked := false

global savedWinX := 0, savedWinY := 0

; v3.9: 로그 모니터링 변수

global LogMonitorActive := false

global LogMonitorInterval := 600000  ; 10분

global LogMaxSizeGB := 10

; v2.7 Solo Globals

global isPaused := false, isStopped := false, startTime := 0

global stepsPID := 0, isResuming := false

global activeEACount := 0, selectedEAs := []

global completedTests := {}, skippedCount := 0

global laTotalTests := 0, laProfitTests := 0, laLossTests := 0

global laTotalProfit := 0, laTotalLoss := 0, laMaxDD := 0

global laGrossProfit := 0, laGrossLoss := 0, laTotalTrades := 0

global laLastFile := "", analyzedFiles := {}

global noTradeCounter, laLastTrades   ; [NO_TRADE SKIP]
noTradeCounter := {}
laLastTrades   := 0

global eaIndex, eaName, symName, tfName, currentTest, totalTests

; [v8.0] Worker GUI 통합 변수
global masterIP := "127.0.0.1"
global workerPID := 0
global workerConnected := false
global workerID := 1
global secWorkerVisible := true

; 설정 로드

LoadAllSettings()

; 터미널 ID 및 계정 번호 읽기

IniRead, terminalId, %iniFile%, folders, terminal_id, UNKNOWN

IniRead, accountNumber, %iniFile%, account, number, 0

; 창 위치 설정 읽기

IniRead, savedWinX, %iniFile%, window, pos_x, 100

IniRead, savedWinY, %iniFile%, window, pos_y, 100

IniRead, isWindowLocked, %iniFile%, window, locked, 0

; v3.7: INI에서 저장된 경로 직접 읽기

IniRead, savedTerminalPath, %iniFile%, folders, terminal_path, NOTSET

IniRead, savedSetFolder, %iniFile%, folders, setfiles_path, NOTSET

IniRead, savedEAPath, %iniFile%, folders, ea_path, NOTSET

IniRead, savedHtmlPath, %iniFile%, folders, html_save_path, NOTSET

; =====================================================

; GUI 생성 (콤팩트 + 스크롤)

; =====================================================

; 화면 작업 영역 크기 확인

SysGet, WorkArea, MonitorWorkArea

screenHeight := WorkAreaBottom - WorkAreaTop

; GUI 높이 결정 (노트북 화면 대응: 더 작게)

guiHeight := (screenHeight > 800) ? 620 : (screenHeight - 100)

if (guiHeight < 400)

    guiHeight := 400

Gui, +LastFound +Resize -MaximizeBox +0x200000 ; WS_VSCROLL + Resizable (AlwaysOnTop removed as default per user request)

Gui, Margin, 15, 10

Gui, Color, F0F0F0

guiHwnd := WinExist()

; 스크롤 설정

global SIF_RANGE := 0x1, SIF_PAGE := 0x2, SIF_POS := 0x4, SIF_ALL := 0x17

global scrollY := 0

global scrollHeight := 1100 ; 전체 콘텐츠 높이 (예상) - 나중에 자동 계산 가능

global windowHeight := guiHeight

; 스크롤메시지 핸들러 연결

OnMessage(0x115, "OnVScroll") ; WM_VSCROLL

OnMessage(0x20a, "OnMouseWheel") ; WM_MOUSEWHEEL

; ─── 타이틀 헤더 ─────────────────────────────────────────────
Gui, Font, s13 Bold c7B00FF
Gui, Add, Text, x15 w660 h40 +0x200 Center y10 c7B00FF, MT4 SOLO nc2.3 [NC Mode]
Gui, Font, s8 Normal
Gui, Add, Text, x15 w660 h18 +0x200 Center y+0 c1565C0, v5.3  서버 연동 + 스크롤 + 자동 분석 + NO_TRADE_SKIP
Gui, Font, s8 Normal
Gui, Add, Button, gScrollToTop x553 y12 w60 h20, ⬆ 상단
Gui, Add, Button, gScrollToBottom x553 y+3 w60 h20, ⬇ 하단

; ─── 로그 & 히스토리 관리 및 모니터링 ────────────────────────────
Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h26 +0x200 Background0x004D40 y+6, 📊 로그 히스토리 관리 및 모니터링
Gui, Font, s8 Normal cBlack

; 행1: 백테스터 로그  (기본: 자동삭제 중)
Gui, Add, Text, x15 y+6 w120 h18 +0x200 BackgroundF5F5F5, 백테스터 로그 크기:
Gui, Add, Text, vLogFolderSizeText x+4 yp w90 c0066CC, -
Gui, Add, Text, vLogSuppressStatus x+8 yp w110 c800080, ● OFF (자동삭제중)
Gui, Add, Button, gForceCleanLogs x+8 yp-2 w110 h22, 🗑️ 로그 즉시 삭제
Gui, Add, Button, gRefreshMonitor x+4 yp w60 h22, 🔄 갱신

; 행2: 히스토리 통화쌍별
Gui, Add, Text, x15 y+6 w120 h18 +0x200 BackgroundF5F5F5, 히스토리 통화쌍별:
Gui, Add, Text, vHistorySizeText x+4 yp w90 c0066CC, -
Gui, Add, Text, x+4 yp w40 c800000, / 10 GB
Gui, Add, Button, gForceCleanHistory x+8 yp-2 w100 h22, 🗑️ 히스토리 정리
Gui, Add, Text, x+8 yp+2 w45, 🌐 HTML:
Gui, Add, Text, vHtmlTabCount x+3 yp w70 c0066CC, 탭: 0개

; 프로그레스 바
Gui, Add, Progress, vHistoryProgressBar x15 w560 h12 y+6 cGreen, 0
Gui, Add, Text, vHistoryProgressText x+6 yp+2 w75, 0

; ─── 섹션1: 마스터 서버 연동 ─────────────────────────────────
IniRead, masterIP, %iniFile%, worker, master_ip, 127.0.0.1
IniRead, workerID, %iniFile%, worker, worker_id, 1

Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0x0277BD y+8, 📡 마스터 서버 연동 (Worker GUI)
Gui, Font, s8 Normal cBlack

Gui, Add, Text, vWorkerStatusDot x15 y+6 w15 cRed, ●
Gui, Add, Text, vWorkerStatusText x+3 yp w100, 연결 안됨
Gui, Add, Text, x+8 yp w55, Master IP:
Gui, Add, Edit, vMasterIPEdit x+3 yp-2 w125 h20, %masterIP%
Gui, Add, Text, x+8 yp+2 w55, Worker ID:
Gui, Add, Edit, vWorkerIDEdit x+3 yp-2 w45 h20, %workerID%

Gui, Add, Text, x15 y+6 w55, IP모드:
Gui, Add, DropDownList, vIPModeSelect x+5 yp-2 w130 h60, Virtual (100.x)||Local (DHCP)
Gui, Add, Text, vMyIPText x+10 yp+2 w210 cBlue, 내 IP: 감지중...

Gui, Add, Button, gStartWorkerSync vBtnWorkerStart x15 w175 h28 y+6 cGreen, 🚀 서버 연동 시작
Gui, Add, Button, gStopWorkerSync vBtnWorkerStop x+4 yp w175 h28, 🛑 연동 중지
Gui, Add, Button, gCheckServerStatus x+4 yp w155 h28, 📊 서버 상태 확인

; ─── 섹션2: 최적화 루프 ──────────────────────────────────────
Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0xB71C1C y+8, 🔄 최적화 루프 제어
Gui, Font, s9 Normal cBlack

Gui, Add, Button, gStartOptLoop vBtnOptLoop x15 w338 h35 y+6 cRed, 🔄 최적화 자동 루프 시작 (서버↔백테스트↔분석↔반복)
Gui, Add, Button, gStopOptLoop vBtnOptStop x+4 yp w338 h35, ⏹ 최적화 루프 중지

Gui, Font, s9 Bold cPurple
Gui, Add, Text, vOptLoopStatus x15 y+5 w660, 최적화 루프: 대기 중
Gui, Font, s8 Normal cBlack

; ─── 섹션3: 진행 상태 ────────────────────────────────────────
Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0x1B5E20 y+8, 📊 진행 상태 (v5.3)

Gui, Add, Progress, vProgressBar x15 w660 h22 y+6, 0

Gui, Font, s10 Bold c0066CC
Gui, Add, Text, vCurrentText x15 w660 y+5, 대기 중...
Gui, Font, s8 Normal c0066CC
Gui, Add, Text, vStatusText x15 w660 y+4, 상태: 준비
Gui, Add, Text, vTimeText x15 w660 y+3, 경과: 0분 0초
Gui, Add, Text, vSkippedText x15 w660 y+3, 건너뛴 테스트: 0개 (기존 완료)

; ─── 섹션4: Live Analysis ─────────────────────────────────────
Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0x4A148C y+6, 📈 Live Analysis
Gui, Font, s8 Normal cBlack

Gui, Add, Text, vLiveAnalysisText x15 w660 y+5, Waiting...
Gui, Add, Text, vLiveProfitText x15 w660 y+3, Profit: 0 | Loss: 0 | Trades: 0
Gui, Add, Text, vLiveNetText x15 w660 y+3, Net: $0.00 | GrossP: $0.00 | GrossL: $0.00
Gui, Add, Text, vLiveLastEA x15 w660 y+3 cBlue, Last EA: -

; ─── 섹션5: 테스트 설정 ──────────────────────────────────────
global loopOrder
IniRead, loopOrder, %iniFile%, settings, loop_order, A

Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0x263238 y+6, ⚙️ 테스트 설정
Gui, Font, s8 Normal cBlack

Gui, Font, s8 Bold c263238
Gui, Add, Text, x15 y+6 w72, 테스트순서:
Gui, Font, s8 Normal
loopOrderIdx := (loopOrder = "B") ? 2 : 1
Gui, Add, DropDownList, x+5 yp-2 w258 vLoopOrderSelect gLoopOrderChanged Choose%loopOrderIdx%, Option A (EA우선-소규모)|Option B (전체분산-대규모)

global htmlCloseThreshold, htmlStepSize, htmlBrowserTarget, htmlNewCount, htmlOpenCount, htmlCloseCount
global htmlAnalCount, analNewCount
global logEnabled := false  ; [★ LOG] 기본 OFF → 테스터 로그 생성 안 함
global analyzeInterval := 0  ; N개 완료마다 중간분석 실행 (0=비활성)
global nextAnalyzeAt := 0    ; 다음 분석 실행 카운터 목표
IniRead, htmlCloseThreshold, %iniFile%, settings, html_close_threshold, 10
IniRead, htmlStepSize, %iniFile%, settings, html_step_size, 3
IniRead, htmlBrowserTarget, %iniFile%, settings, html_browser_target, both
IniRead, analyzeInterval, %iniFile%, settings, analyze_interval, 0  ; [nc2.3 FIX] 시작 시 INI에서 복원
htmlNewCount  := 0
htmlOpenCount := 0
htmlCloseCount := 0
htmlAnalCount := 0
analNewCount  := 0

; ── HTML 브라우저 선택 ─────────────────────────────────
Gui, Font, s8 Bold c263238
Gui, Add, Text, x15 y+6 w72, HTML 브라우저:
Gui, Font, s8 Normal
Gui, Add, Radio, vHtmlBrowserChrome gHtmlBrowserChanged x+5 yp, Chrome
Gui, Add, Radio, vHtmlBrowserEdge   gHtmlBrowserChanged x+8 yp, Edge
Gui, Add, Radio, vHtmlBrowserBoth   gHtmlBrowserChanged x+8 yp, 둘다
if (htmlBrowserTarget = "chrome")
    GuiControl,, HtmlBrowserChrome, 1
else if (htmlBrowserTarget = "edge")
    GuiControl,, HtmlBrowserEdge, 1
else
    GuiControl,, HtmlBrowserBoth, 1

; ── HTML Limit + 단계 ────────────────────────────────
Gui, Font, s8 Bold c263238
Gui, Add, Text, x15 y+6 w72, HTML Limit:
Gui, Font, s8 Normal
Gui, Add, Button, gHtmlThresholdDown x+5 yp-2 w22 h20, -
Gui, Add, Text, vHtmlThresholdText x+3 yp+2 w38 Center, %htmlCloseThreshold%
Gui, Add, Button, gHtmlThresholdUp x+3 yp-2 w22 h20, +
Gui, Add, Text, x+8 yp+2, 단계:
Gui, Add, Button, gHtmlStep1  x+4 yp-2 w30 h20, x1
Gui, Add, Button, gHtmlStep10 x+2 yp    w30 h20, x10
Gui, Add, Button, gHtmlStep50 x+2 yp    w30 h20, x50
Gui, Add, Button, gCloseHTMLWindows x480 yp-2 w160 h24, [Del] Force Close HTML

; ── 신규/닫음/분석 카운터 (대형) ──────────────────────
Gui, Font, s8 Normal cBlack
Gui, Add, Text, x15 y+8, 신규:
Gui, Font, s16 Bold c990000
Gui, Add, Text, vHtmlNewCountText x+3 yp-8 w60 Center, 0개
Gui, Font, s8 Normal cBlack
Gui, Add, Text, x+10 yp+8, 닫음:
Gui, Font, s16 Bold c006600
Gui, Add, Text, vHtmlCloseCountText x+3 yp-8 w50 Center, 0회
Gui, Font, s8 Normal cBlack
Gui, Add, Text, x+10 yp+8, 분석:
Gui, Font, s16 Bold c0000AA
Gui, Add, Text, vHtmlAnalCountText x+3 yp-8 w50 Center, 0회
Gui, Font, s8 Normal cBlack

; ── [삭제]프리셋 ─────────────────────────────────────
Gui, Font, s8 Bold c555555
Gui, Add, Text, x15 y+6 w66 h20 +0x200, [삭제]프리셋:
Gui, Font, s8 Normal
Gui, Add, Button, gHtmlPreset1   x+3 yp-2 w28 h20, 1
Gui, Add, Button, gHtmlPreset10  x+2 yp   w32 h20, 10
Gui, Add, Button, gHtmlPreset50  x+2 yp   w32 h20, 50
Gui, Add, Button, gHtmlPreset100 x+2 yp   w38 h20, 100
Gui, Add, Button, gHtmlPreset200 x+2 yp   w38 h20, 200
Gui, Add, Button, gHtmlPreset500 x+2 yp   w38 h20, 500

; ── [분석]프리셋 ─────────────────────────────────────
Gui, Font, s8 Bold cFF6600
Gui, Add, Text, x15 y+6 w66 h20 +0x200, [분석]프리셋:
Gui, Font, s8 Normal cBlack
Gui, Add, Button, gAnalInterval0   x+3 yp-2 w30 h20, OFF
Gui, Add, Button, gAnalInterval5   x+2 yp   w28 h20, 5
Gui, Add, Button, gAnalInterval50  x+2 yp   w32 h20, 50
Gui, Add, Button, gAnalInterval100 x+2 yp   w38 h20, 100
Gui, Add, Button, gAnalInterval200 x+2 yp   w38 h20, 200
Gui, Add, Button, gAnalInterval300 x+2 yp   w38 h20, 300
Gui, Add, Text, vAnalIntervalText x+6 yp+2 w120, (비활성)

; ── Since 리셋 버튼 (중복분석 방지 타임스탬프 초기화) ──
Gui, Font, s8 Normal cBlack
Gui, Add, Button, gResetSinceTimestamp x+8 yp w100 h20, [Since 리셋]

; ── 신규분석/분석한 횟수 카운터 (대형) ──────────────────
Gui, Font, s8 Normal cBlack
Gui, Add, Text, x15 y+8, 신규분석:
Gui, Font, s16 Bold cCC5500
Gui, Add, Text, vAnalNewCountText x+3 yp-8 w60 Center, 0개
Gui, Font, s8 Normal cBlack
Gui, Add, Text, x+10 yp+8, 분석한:
Gui, Font, s16 Bold c5500AA
Gui, Add, Text, vAnalDoneCountText x+3 yp-8 w50 Center, 0회
Gui, Font, s8 Normal cBlack

Gui, Font, s9 Bold
Gui, Add, Button, gStartManualMode vBtnManual x15 w150 h32 y+8, [MANUAL TRIGGER]
Gui, Add, Button, gStartAutoMode vBtnAuto x+4 yp w150 h32 cRed, [AUTO TRIGGER]
Gui, Add, Button, gButtonResume vBtnResume x+4 yp w88 h32 Disabled, [이어서]
Gui, Add, Button, gButtonPause vBtnPause x+4 yp w88 h32 Disabled, [일시정지]
Gui, Add, Button, gButtonStop vBtnStop x+4 yp w88 h32 Disabled, [중단]
Gui, Font, s8 Normal cBlack

; ─── 섹션6: 터미널 정보 ──────────────────────────────────────
Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0x1A237E y+8, 📌 현재 터미널 정보
Gui, Font, s8 Normal cBlack

Gui, Add, Text, x15 w70 y+6, 터미널 ID:
Gui, Add, Text, vTerminalIdText x+3 yp w280 cBlue, %terminalId%

Gui, Add, Text, x15 w70 y+5, 계정번호:
Gui, Add, Edit, vAccountNumEdit x+3 yp-2 w120 h20, %accountNumber%
Gui, Add, Button, gSaveAccountNum x+4 yp w50 h20, 저장
Gui, Add, Button, gDetectAccountNum x+4 yp w80 h20, 🔍 감지

lockBtnText := isWindowLocked ? "🔓 고정 해제" : "🔒 위치 고정"
Gui, Add, Button, gToggleWindowLock vBtnLock x15 w92 h22 y+5, %lockBtnText%
Gui, Add, Button, gSaveWindowPos x+4 yp w82 h22, 💾 위치저장
Gui, Add, Button, gFixMT4Window x+4 yp w82 h22 cRed, 🔧 MT4고정
Gui, Add, Button, gToggleAlwaysOnTop x+4 yp w90 h22, 🔝 항상위에
Gui, Add, Button, gSetWindowSmall x+4 yp w42 h22, 작게
Gui, Add, Button, gSetWindowMedium x+3 yp w42 h22, 중간
Gui, Add, Button, gSetWindowLarge x+3 yp w42 h22, 크게

; ─── 섹션7: 새 컴퓨터 설정 ───────────────────────────────────
Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0xBF360C y+8, 🖥️ 새 컴퓨터 설정
Gui, Font, s8 Normal cBlack

Gui, Add, Button, gRunNewComputerSetup x15 w218 h28 y+6, 🔧 새 컴퓨터 설정 마법사
Gui, Add, Button, gAutoDetect x+4 yp w218 h28, 🔍 자동 감지
Gui, Add, Button, gRunCleanupManager x+4 yp w218 h28 cGreen, 🧹 Cleanup Manager 1.9

Gui, Add, Button, gToggleLogMonitor x15 y+5 w218 h25 vLogMonitorBtn, 🔄 로그 모니터 시작
Gui, Add, Button, gClearTesterLogs x+4 yp w218 h25, 🗑️ 즉시 정리
Gui, Add, Button, gCheckTesterLogSize x+4 yp w218 h25, 📊 크기 확인

; [★ LOG] 테스터 로그 ON/OFF 토글 (기본: OFF = 로그 생성 안 함)
Gui, Font, s9 Bold
Gui, Add, Button, gToggleLogEnabled vLogEnabledBtn x15 y+6 w450 h28 c800080, 🔇 테스터 로그: OFF (기본) — 클릭하면 ON (로그 생성 허용)
Gui, Font, s8 Normal cBlack

; ─── 섹션8: 컴퓨터 프로필 ────────────────────────────────────
Gui, Font, s9 Bold c0066CC
Gui, Add, Text, x15 w660 h24 +0x200 Background0x37474F y+8, 💻 컴퓨터 프로필
Gui, Font, s8 Normal cBlack

Gui, Add, Text, x15 w50 y+6, 프로필:
Gui, Add, DropDownList, vProfileSelect gLoadProfile x+5 yp-3 w150, %currentProfile%
Gui, Add, Button, gSaveAsNewProfile x+5 yp w70 h23, 새 저장
Gui, Add, Button, gSaveProfile x+3 yp w65 h23, 덮어쓰기
Gui, Add, Button, gDeleteProfile x+3 yp w45 h23, 삭제
Gui, Add, Button, gRestartApp x+3 yp w60 h23, 재실행
Gui, Add, Button, gReloadSettings x+3 yp w65 h23, 새로고침

; 프로필 목록 로드
LoadProfileList()

Gui, Add, Text, x15 w660 y+8 0x10

Gui, Add, Text, x15 w660 y+8 0x10

; =====================================================

; 경로 설정 (v3.7: 저장된 경로 표시 추가)

; =====================================================

Gui, Font, s9 Bold

Gui, Add, Text, x15 w200 y+8, 📁 경로 설정

; v3.7: "저장하고 새로고침" 버튼 추가

Gui, Font, s8 Bold cGreen

Gui, Add, Button, gSaveAndRefresh x400 yp-2 w150 h22, 💾 저장하고 새로고침

Gui, Add, Button, gRefreshSavedDisplay x+5 yp w100 h22, 🔄 표시 갱신

Gui, Font, s8 Normal

; [v4.1] 작업폴더 경로 - 선택 가능 (내부에서 먼저 검색)
IniRead, workFolder, %iniFile%, folders, work_folder, %A_ScriptDir%
if (workFolder = "" || workFolder = "ERROR")
    workFolder := A_ScriptDir
Gui, Add, Text, x15 w80 y+8, 작업폴더:
Gui, Add, Edit, vWorkFolderEdit x+3 yp-2 w400 h22 ReadOnly cBlue, %workFolder%
Gui, Add, Button, gSelectWorkFolder x+3 yp w70 h22, 찾아보기

; 터미널 경로

Gui, Add, Text, x15 w80 y+8, 터미널:

Gui, Add, Edit, vTerminalPathEdit x+3 yp-2 w400 h22 ReadOnly, %terminalPath%

Gui, Add, Button, gSelectTerminal x+3 yp w70 h22, 찾아보기

; v3.7: 저장된 터미널 경로 표시

Gui, Font, s7 c0066CC

Gui, Add, Text, vSavedTerminalText x100 y+2 w555, [저장됨] %savedTerminalPath%

Gui, Font, s8 Normal

; SET 파일 경로

Gui, Add, Text, x15 w80 y+5, SET 폴더:

Gui, Add, Edit, vSetFolderEdit x+3 yp-2 w400 h22 ReadOnly, %setFolder%

Gui, Add, Button, gSelectSetFolder x+3 yp w70 h22, 찾아보기

; v3.7: 저장된 SET 경로 표시

Gui, Font, s7 c0066CC

Gui, Add, Text, vSavedSetFolderText x100 y+2 w555, [저장됨] %savedSetFolder%

Gui, Font, s8 Normal

; EA 폴더 경로 (v3.6 추가)

IniRead, eaFolderPath, %iniFile%, folders, ea_path, NOTSET

if (eaFolderPath = "" || eaFolderPath = "ERROR")

    eaFolderPath := "NOTSET"

Gui, Add, Text, x15 w80 y+5, EA 폴더:

Gui, Add, Edit, vEAFolderEdit x+3 yp-2 w400 h22 ReadOnly, %eaFolderPath%

Gui, Add, Button, gSelectEAFolder x+3 yp w70 h22, 찾아보기

; v3.7: 저장된 EA 경로 표시

Gui, Font, s7 c0066CC

Gui, Add, Text, vSavedEAPathText x100 y+2 w555, [저장됨] %savedEAPath%

Gui, Font, s8 Normal

; 리포트 저장 경로 (신규)

IniRead, htmlSavePath, %iniFile%, folders, html_save_path, NOTSET

if (htmlSavePath = "" || htmlSavePath = "ERROR")

    htmlSavePath := "NOTSET"

; [v7.7 FIX] htmlSaveFolder 시작 시 INI에서 초기화 (AnalyzeLatestReport 타이머 즉시 동작)
if (htmlSavePath != "NOTSET" && htmlSavePath != "")
    htmlSaveFolder := htmlSavePath

Gui, Add, Text, x15 w80 y+5, 리포트폴더:

Gui, Add, Edit, vHtmlSavePathEdit x+3 yp-2 w400 h22 ReadOnly, %htmlSavePath%

Gui, Add, Button, gSelectHtmlSaveFolder x+3 yp w70 h22, 찾아보기

; v3.7: 저장된 HTML 경로 표시

Gui, Font, s7 c0066CC

Gui, Add, Text, vSavedHtmlPathText x100 y+2 w555, [저장됨] %savedHtmlPath%

Gui, Font, s8 Normal

; SET 파일 개수 표시

setFileCount := 0

if (setFolder != "NOTSET" && setFolder != "") {

    StringReplace, setFolderWin, setFolder, /, \, All

    IfExist, %setFolderWin%

    {

        Loop, %setFolderWin%\*.set

            setFileCount++

    }

}

; EA 파일 개수 표시

eaFileCount := 0

if (eaFolderPath != "NOTSET" && eaFolderPath != "") {

    StringReplace, eaFolderWin, eaFolderPath, /, \, All

    IfExist, %eaFolderWin%

    {

        Loop, %eaFolderWin%\*.ex4

            eaFileCount++

    }

}

; 리포트 파일 개수 표시

reportFileCount := 0

if (htmlSavePath != "NOTSET" && htmlSavePath != "") {

    StringReplace, htmlSavePathWin, htmlSavePath, /, \, All

    IfExist, %htmlSavePathWin%

    {

        Loop, %htmlSavePathWin%\*.htm

            reportFileCount++

    }

}

; useSetFiles 설정 읽기

IniRead, useSetFiles, %iniFile%, selection, useSetFiles, 0

Gui, Add, Text, x100 vSetFileCountText y+5 c0000FF, SET 파일: %setFileCount%개

Gui, Add, Text, x220 yp vEAFileCountText cPurple, EA 파일: %eaFileCount%개

Gui, Add, Text, x350 yp vReportFileCountText cGreen, 리포트: %reportFileCount%개

; SET 파일 사용 옵션 (한 줄에)

Gui, Font, s8 Bold cDarkGreen

Gui, Add, Text, x15 w660 y+8, 📋 SET 파일 사용 방식:

Gui, Font, s8 Normal

Gui, Add, Radio, vUseSetRadio0 gSaveSetOption x15 y+5, SET 없음 (EA기본)

Gui, Add, Radio, vUseSetRadio1 gSaveSetOption x+15 yp, SET만 사용

Gui, Add, Radio, vUseSetRadio2 gSaveSetOption x+15 yp, SET + EA기본

; 현재 설정에 따라 라디오 버튼 선택

if (useSetFiles = 2)

    GuiControl,, UseSetRadio2, 1

else if (useSetFiles = 1)

    GuiControl,, UseSetRadio1, 1

else

    GuiControl,, UseSetRadio0, 1

Gui, Add, Text, x15 w660 y+8 0x10

; 히스토리 확인 (경로 설정과 테스트 기간 사이)

Gui, Add, Button, gCheckHistory x15 w215 h30 y+5, 📅 히스토리 데이터 확인

Gui, Add, Button, gOpenHistoryCenter x+5 yp w215 h30, ⚡ 1분봉 자동 다운로드 (선택됨)

Gui, Add, Text, x15 w660 y+8 0x10

; =====================================================

; v3.7: 테스트 기간 설정 (최대 24개 - 3열 x 8행)

; =====================================================

Gui, Font, s9 Bold cPurple

Gui, Add, Text, x15 w200 y+8, 📅 테스트 기간 설정

; v3.8: 전체 선택/해제 버튼

Gui, Font, s8 Normal

Gui, Add, Button, gSelectAllPeriods x220 yp-2 w60 h20, 전체선택

Gui, Add, Button, gDeselectAllPeriods x+2 yp w60 h20, 전체해제

Gui, Add, Button, gAddMorePeriods x+5 yp w60 h20 cGreen, +4개

; v3.8: 기간 프리셋 저장/불러오기 (이름 편집 가능) - 동적 로드

presetList := GetPresetList()

Gui, Add, ComboBox, vDatePresetSelect x+10 yp w100 h200, %presetList%

Gui, Add, Button, gSaveDatePreset x+2 yp w40 h20, 저장

Gui, Add, Button, gLoadDatePreset x+2 yp w40 h20, 불러

; v3.8: 선택된 기간 일괄 설정

Gui, Font, s7 Normal cBlue

Gui, Add, Text, x15 y+5, [선택된 기간 일괄 설정]

Gui, Font, s7 Normal

Gui, Add, Text, x+5 yp, 기준:

Gui, Add, Radio, vDateBaseRadio1 x+2 yp Checked, 시작일

Gui, Add, Radio, vDateBaseRadio2 x+2 yp, 종료일

Gui, Add, DateTime, vBatchBaseDT x+5 yp-2 w80 h18, yyyy.MM.dd

; 기간 버튼들 (전/후)

Gui, Add, Button, gBatchDate1MBefore x15 y+3 w35 h18, 1월전

Gui, Add, Button, gBatchDate2MBefore x+1 yp w35 h18, 2월전

Gui, Add, Button, gBatchDate3MBefore x+1 yp w35 h18, 3월전

Gui, Add, Button, gBatchDate6MBefore x+1 yp w35 h18, 6월전

Gui, Add, Button, gBatchDate1YBefore x+1 yp w35 h18, 1년전

Gui, Add, Button, gBatchDate18MBefore x+1 yp w40 h18, 18월전

Gui, Add, Button, gBatchDate2YBefore x+1 yp w35 h18, 2년전

Gui, Add, Button, gBatchDate1MAfter x+10 yp w35 h18, 1월후

Gui, Add, Button, gBatchDate2MAfter x+1 yp w35 h18, 2월후

Gui, Add, Button, gBatchDate3MAfter x+1 yp w35 h18, 3월후

Gui, Add, Button, gBatchDate6MAfter x+1 yp w35 h18, 6월후

Gui, Add, Button, gBatchDate1YAfter x+1 yp w35 h18, 1년후

Gui, Font, s7 Normal

Gui, Add, Text, x15 y+3, 체크된 기간만 순서대로 테스트

; =====================================================

; 24개 기간 설정 - 3열 x 8행 배치 (Loop 8 Starts Below)

Loop, 8 {

    row := A_Index

    idx1 := row           ; 열1: 1-8

    idx2 := row + 8       ; 열2: 9-16

    idx3 := row + 16      ; 열3: 17-24

    ; 열1 (기간 1-8)

    fromDT%idx1% := StrReplace(testFromDate%idx1%, ".", "")

    toDT%idx1% := StrReplace(testToDate%idx1%, ".", "")

    if (fromDT%idx1% = "" || StrLen(fromDT%idx1%) != 8)

        fromDT%idx1% := A_YYYY . A_MM . A_DD

    if (toDT%idx1% = "" || StrLen(toDT%idx1%) != 8)

        toDT%idx1% := A_YYYY . A_MM . A_DD

    chkVal1 := testDateEnable%idx1%

    fromVal1 := fromDT%idx1%

    toVal1 := toDT%idx1%

    Gui, Add, Checkbox, vTestDateChk%idx1% Checked%chkVal1% x15 y+2 w40, %idx1%
    Gui, Add, DateTime, vTestFromDT%idx1% x+1 yp-2 w80 Choose%fromVal1%, yyyy.MM.dd
    Gui, Add, Text, vTestDateSep%idx1% x+1 yp+4, ~
    Gui, Add, DateTime, vTestToDT%idx1% x+1 yp-2 w80 Choose%toVal1%, yyyy.MM.dd

    ; 열2 (기간 9-16)
    fromDT%idx2% := StrReplace(testFromDate%idx2%, ".", "")
    toDT%idx2% := StrReplace(testToDate%idx2%, ".", "")
    if (fromDT%idx2% = "" || StrLen(fromDT%idx2%) != 8)
        fromDT%idx2% := A_YYYY . A_MM . A_DD
    if (toDT%idx2% = "" || StrLen(toDT%idx2%) != 8)
        toDT%idx2% := A_YYYY . A_MM . A_DD
    chkVal2 := testDateEnable%idx2%
    fromVal2 := fromDT%idx2%
    toVal2 := toDT%idx2%

    Gui, Add, Checkbox, vTestDateChk%idx2% Checked%chkVal2% x240 yp+2 w40, %idx2%
    Gui, Add, DateTime, vTestFromDT%idx2% x+1 yp-2 w80 Choose%fromVal2%, yyyy.MM.dd
    Gui, Add, Text, vTestDateSep%idx2% x+1 yp+4, ~
    Gui, Add, DateTime, vTestToDT%idx2% x+1 yp-2 w80 Choose%toVal2%, yyyy.MM.dd

    ; 열3 (기간 17-24)
    fromDT%idx3% := StrReplace(testFromDate%idx3%, ".", "")
    toDT%idx3% := StrReplace(testToDate%idx3%, ".", "")
    if (fromDT%idx3% = "" || StrLen(fromDT%idx3%) != 8)
        fromDT%idx3% := A_YYYY . A_MM . A_DD
    if (toDT%idx3% = "" || StrLen(toDT%idx3%) != 8)
        toDT%idx3% := A_YYYY . A_MM . A_DD
    chkVal3 := testDateEnable%idx3%
    fromVal3 := fromDT%idx3%
    toVal3 := toDT%idx3%

    Gui, Add, Checkbox, vTestDateChk%idx3% Checked%chkVal3% x465 yp+2 w40, %idx3%
    Gui, Add, DateTime, vTestFromDT%idx3% x+1 yp-2 w80 Choose%fromVal3%, yyyy.MM.dd
    Gui, Add, Text, vTestDateSep%idx3% x+1 yp+4, ~
    Gui, Add, DateTime, vTestToDT%idx3% x+1 yp-2 w80 Choose%toVal3%, yyyy.MM.dd

}

Gui, Add, Text, x15 w660 y+5 0x10

; =====================================================

; Symbol 설정

; =====================================================

Gui, Font, s9 Bold

Gui, Add, Text, x15 w200 y+8, 📊 Symbol 설정

Gui, Font, s9 Bold cBlue

Gui, Add, Text, x280 yp w380, 💾 저장된 Symbol (INI)

Gui, Font, s8 Normal

; Symbol 목록 (콤팩트하게)

Gui, Add, Checkbox, vSym1Chk Checked%sym1Chk% x15 y+5, 1:
Gui, Add, Edit, vSym1Edit x+3 yp-2 w100 h20, %sym1%
Gui, Add, Text, vSym1SavedText x280 yp+2 w370 cBlue, [INI] sym1 = %sym1%

Gui, Add, Checkbox, vSym2Chk Checked%sym2Chk% x15 y+3, 2:
Gui, Add, Edit, vSym2Edit x+3 yp-2 w100 h20, %sym2%
Gui, Add, Text, vSym2SavedText x280 yp+2 w370 cBlue, [INI] sym2 = %sym2%

Gui, Add, Checkbox, vSym3Chk Checked%sym3Chk% x15 y+3, 3:
Gui, Add, Edit, vSym3Edit x+3 yp-2 w100 h20, %sym3%
Gui, Add, Text, vSym3SavedText x280 yp+2 w370 cBlue, [INI] sym3 = %sym3%

Gui, Add, Checkbox, vSym4Chk Checked%sym4Chk% x15 y+3, 4:
Gui, Add, Edit, vSym4Edit x+3 yp-2 w100 h20, %sym4%
Gui, Add, Text, vSym4SavedText x280 yp+2 w370 cBlue, [INI] sym4 = %sym4%

Gui, Add, Checkbox, vSym5Chk Checked%sym5Chk% x15 y+3, 5:
Gui, Add, Edit, vSym5Edit x+3 yp-2 w100 h20, %sym5%
Gui, Add, Text, vSym5SavedText x280 yp+2 w370 cBlue, [INI] sym5 = %sym5%

Gui, Add, Checkbox, vSym6Chk Checked%sym6Chk% x15 y+3, 6:
Gui, Add, Edit, vSym6Edit x+3 yp-2 w100 h20, %sym6%
Gui, Add, Text, vSym6SavedText x280 yp+2 w370 cBlue, [INI] sym6 = %sym6%

Gui, Add, Checkbox, vSym7Chk Checked%sym7Chk% x15 y+3, 7:
Gui, Add, Edit, vSym7Edit x+3 yp-2 w100 h20, %sym7%
Gui, Add, Text, vSym7SavedText x280 yp+2 w370 cBlue, [INI] sym7 = %sym7%

Gui, Add, Checkbox, vSym8Chk Checked%sym8Chk% x15 y+3, 8:
Gui, Add, Edit, vSym8Edit x+3 yp-2 w100 h20, %sym8%
Gui, Add, Text, vSym8SavedText x280 yp+2 w370 cBlue, [INI] sym8 = %sym8%

Gui, Add, Checkbox, vSym9Chk Checked%sym9Chk% x15 y+3, 9:
Gui, Add, Edit, vSym9Edit x+3 yp-2 w100 h20, %sym9%
Gui, Add, Text, vSym9SavedText x280 yp+2 w370 cBlue, [INI] sym9 = %sym9%

Gui, Add, Checkbox, vSym10Chk Checked%sym10Chk% x15 y+3, 10:
Gui, Add, Edit, vSym10Edit x+3 yp-2 w100 h20, %sym10%
Gui, Add, Text, vSym10SavedText x280 yp+2 w370 cBlue, [INI] sym10 = %sym10%

Gui, Add, Text, x15 w660 y+8 0x10

; =====================================================

; EA 및 Timeframe 설정 (한 줄에)

; =====================================================

Gui, Font, s9 Bold

Gui, Add, Text, x15 w150 y+8, 🤖 EA 선택

Gui, Font, s8 Normal

Gui, Add, Checkbox, vEAAllChk Checked%eaAll% x15 y+5, 폴더 전부(All)
Gui, Add, Checkbox, vEA1Chk Checked%ea1% x+10 yp, 1
Gui, Add, Checkbox, vEA2Chk Checked%ea2% x+10 yp, 2
Gui, Add, Checkbox, vEA3Chk Checked%ea3% x+10 yp, 3
Gui, Add, Checkbox, vEA4Chk Checked%ea4% x+10 yp, 4
Gui, Add, Checkbox, vEA5Chk Checked%ea5% x+10 yp, 5

Gui, Font, s9 Bold
Gui, Add, Text, x300 yp-5, ⏰ Timeframe
Gui, Font, s8 Normal

Gui, Add, Checkbox, vTFM1Chk Checked%tfM1% x300 y+5, M1
Gui, Add, Checkbox, vTFM5Chk Checked%tfM5% x+8 yp, M5
Gui, Add, Checkbox, vTFM15Chk Checked%tfM15% x+8 yp, M15
Gui, Add, Checkbox, vTFM30Chk Checked%tfM30% x+8 yp, M30
Gui, Add, Checkbox, vTFH1Chk Checked%tfH1% x+8 yp, H1
Gui, Add, Checkbox, vTFH4Chk Checked%tfH4% x+8 yp, H4

Gui, Add, Text, x15 w660 y+8 0x10

; =====================================================

; 초기 설정

; =====================================================

Gui, Font, s9 Bold

Gui, Add, Text, x15 w660 y+8, 🔧 초기 설정 (새 컴퓨터만)

Gui, Font, s8 Normal

Gui, Add, Button, gRunDetectStep1 x15 w210 h28 y+5, 1단계: 컨트롤 감지

Gui, Add, Button, gRunDetectStep2 x+5 yp w210 h28, 2단계: 좌표 설정

Gui, Add, Button, gRunReadSymbols x+5 yp w210 h28, 3단계: Symbol 읽기

Gui, Add, Text, x15 w660 y+8 0x10

; =====================================================

; 백테스트 실행

; =====================================================

Gui, Font, s10 Bold

Gui, Add, Text, x15 w660 y+8, 🚀 백테스트 실행

Gui, Font, s8 Normal cGray

Gui, Add, Text, x15 w660 y+3, v1.45 (SET 중심) | v2.0 (EA 중심) | v2.1/v8.0 (기간 Loop)

; v1.45 버튼

Gui, Add, Button, gRunSimpleLoop x15 w130 h35 y+5, 🔄 v1.45 Loop

Gui, Add, Button, gRun4Steps x+5 yp w130 h35, ⚡ v1.45 4Step

; v2.0 버튼

Gui, Add, Button, gRun4StepsOnce x+5 yp w130 h35, ⚡ v2.0 4Step

; v3.6 Loop & v8.0 Loop (Large Buttons)

; (v3.5 Removed as requested)

Gui, Add, Button, gRunLoopV36Internal_v2 x15 w325 h40 y+5 cBlue, 🛡️ v3.6 Simple Loop (Integrated)

Gui, Add, Button, gRunLoopV25 x+5 yp w325 h40, 🔄 v8.0 Loop

; v3.6 4Step & Tools

Gui, Add, Button, gRunStepV36 x15 w325 h35 y+5, ⚡ v3.6 4Steps (v2.0 Save)

Gui, Add, Button, gRunDualLauncher x+5 yp w325 h35, 🚀 MT4 Dual Launcher

; (Deleted NC Buttons and Old Master Loop)

Gui, Add, Text, x15 w660 y+8 0x10

Gui, Add, Text, x15 w660 y+8 0x10

; =====================================================

; 도구

; =====================================================

Gui, Font, s9 Bold

Gui, Add, Text, x15 w660 y+8, ⚙️ 도구 및 리포트

Gui, Font, s8 Normal

; 1열

Gui, Add, Button, gReloadSettingsV39 x15 w160 h30 y+5, 🔄 설정 즉시 불러오기

Gui, Add, Button, gRunCollectReports x+5 yp w160 h30, 📂 리포트 모아보기

Gui, Add, Button, gCloseHTMLWindows x+5 yp w160 h30, 🗑️ HTML 창 닫기

Gui, Add, Button, gShowHelp x+5 yp w160 h30, 📖 사용 가이드

; 백테스트 분석기 (v3.6 신규)

Gui, Font, s9 Bold cGreen

Gui, Add, Button, gRunBacktestAnalyzer x15 w160 h35 y+8, 📊 분석기 (AHK)

Gui, Add, Button, gRunPythonAnalyzer x+5 yp w160 h35, 🐍 분석기 (Python)

Gui, Add, Button, gGenerateQuickReport x+5 yp w160 h35, 📝 간단 보고서

Gui, Add, Button, gOpenReportsFolder x+5 yp w100 h35, 📁 리포트

Gui, Font, s8 Normal

; 2열 (폴더 열기)

Gui, Add, Button, gOpenSetFolder x15 w105 h25 y+5, SET 폴더

Gui, Add, Button, gOpenTerminalFolder x+3 yp w105 h25, 터미널

Gui, Add, Button, gOpenConfigFolder x+3 yp w105 h25, 설정폴더

Gui, Add, Button, gOpenScriptFolder x+3 yp w105 h25, 스크립트

Gui, Add, Button, gCheckSettings x+3 yp w105 h25, 설정확인

Gui, Add, Button, gExitApp x+3 yp w105 h25, 종료

; [v8.0] 하단 상단이동 버튼
Gui, Add, Text, x15 w660 y+8 0x10
Gui, Add, Button, gScrollToTop x15 w660 h28 y+5, ⬆️ 맨 위로 (상단으로 이동)

; GUI 표시 (저장된 위치 또는 화면 중앙)

if (savedWinX > 0 && savedWinY > 0) {
    Gui, Show, w700 h%guiHeight% x%savedWinX% y%savedWinY%, MT4 SOLO nc2.3 [NC Mode]
} else {
    Gui, Show, w700 h%guiHeight% Center, MT4 SOLO nc2.3 [NC Mode]
}

SetScrollRange() ; 스크롤 범위 설정

; [nc2.3 FIX] 시작 시 분석 간격 GUI 표시 동기화 (INI에서 복원한 값 반영)
if (analyzeInterval > 0)
    GuiControl,, AnalIntervalText, [%analyzeInterval%개마다]
else
    GuiControl,, AnalIntervalText, (비활성)

; 창 위치 고정 타이머 시작 (고정 상태일 때만)

if (isWindowLocked)

    SetTimer, EnforceWindowPosition, 100

global isAutoStart := false

lastSaveTick := 0

; SetTimer, StartAutoMode, -2000 ; [DISABLED] User requested manual start

SetTimer, AutoStartWorkerSync, -2000 ; [v8.0] 워커 자동 연동 시작

; [v8.0] IPC: Python Worker → command.json → SOLO 7.0 → test_completed.flag
global cmdEA := "", cmdSymbol := "", cmdTF := "", cmdIter := 1
global cmdIterNum := 1, cmdTotalSets := "?", cmdFromDate := "", cmdToDate := "", cmdSetFile := ""
SetTimer, CheckAutoTriggerCommand, 1000

; [v7.7] 시작시 자동감지 4회 실행
global autoDetectBootMode := 0
SetTimer, StartupAutoDetect4x, -2000

; [v1.5] 마지막 세션 환경 비교
SetTimer, CheckLastSession, -3000

; [v8.0] 설정 파일 변경 감지 (500ms 주기)
global lastConfigChecksum := ""
SetTimer, MonitorConfigChanges, 500

; [v8.0] 실시간 리포트 분석 타이머 (5초마다)
SetTimer, AnalyzeLatestReport, 5000

; [v8.0] 전체 완료 감지 타이머 (3초마다 all_done.flag 체크)
SetTimer, CheckAllDone, 3000

; [★ MONITOR] 로그 & 히스토리 모니터 UI 갱신 (5초마다)
SetTimer, UpdateMonitorUI, 5000

; [★ LOG] 테스터 로그 억제 타이머 (500ms마다 로그파일 삭제, 기본 OFF 상태)
SetTimer, SuppressTesterLogsTimer, 500

return

AutoStartWorkerSync:
    Gosub, StartWorkerSync
return

; Button Handlers

StartAutoMode:
    isResuming := false
    isPaused := false
    isStopped := false
    startTime := A_TickCount
    isAutoStart := true
    MsgBox, 64, 자동 모드, 자동 모드로 시작합니다 (확인창 없음), 1
    Gosub, RunLoopV27Solo
return

StartManualMode:
    isResuming := false
    isPaused := false
    isStopped := false
    startTime := A_TickCount
    isAutoStart := false
    Gosub, RunLoopV27Solo
return


return

; 창 크기 조정 시 처리

GuiSize:

    if (A_EventInfo = 1)  ; 최소화

        return

    ; 창 크기가 변경되면 windowHeight 업데이트

    global windowHeight := A_GuiHeight

    ; 스크롤바 범위 재설정

    SetScrollRange()

return

; =====================================================

; 설정 로드 함수

; =====================================================

LoadAllSettings() {

    global

    ; 경로 설정 읽기

    IniRead, setFolder, %iniFile%, folders, setfiles_path, NOTSET

    if (terminalPath = "" || terminalPath = "ERROR" || !FileExist(terminalPath)) {
        ; [v5.3 PORTABLE] 상위 폴더의 MT4 지능적 탐색
        tempMT4 := A_ScriptDir . "\..\MT4\terminal.exe"
        if FileExist(tempMT4)
            terminalPath := tempMT4
        else
            terminalPath := "NOTSET"
    }

    ; [v2.8] EA 폴더 및 SET 파일 옵션 추가 로드
    IniRead, eaFolderPath, %iniFile%, folders, ea_path, NOTSET
    if (eaFolderPath = "" || eaFolderPath = "ERROR")
        eaFolderPath := "NOTSET"
        
    IniRead, useSetFiles, %iniFile%, selection, useSetFiles, 0

    ; [FIXED] Enforce clean Report Path if pointing to AppData (MT4 default)

    IniRead, htmlSavePath, %iniFile%, folders, html_save_path, %A_ScriptDir%\Reports

    

    ; 강제 재설정: 경로가 비었거나 AppData가 포함되어 있다면 로컬 Reports 폴더로 변경

    if (htmlSavePath = "" || InStr(htmlSavePath, "AppData") || htmlSavePath = "NOTSET") {

        htmlSavePath := A_ScriptDir . "\Reports"

        IfNotExist, %htmlSavePath%

            FileCreateDir, %htmlSavePath%

        

        ; 변경된 경로 INI에 즉시 저장

        IniWrite, %htmlSavePath%, %iniFile%, folders, html_save_path

    }

    ; Symbol 읽기 (10개 지원)

    Loop, 10 {

        IniRead, sym%A_Index%, %iniFile%, symbols, sym%A_Index%,

        ; 쉼표 제거 (Clean Loading)

        rawSym := sym%A_Index%

        commaPos := InStr(rawSym, ",")

        if (commaPos > 0)

            sym%A_Index% := Trim(SubStr(rawSym, 1, commaPos - 1))

    }

    ; Symbol 선택 상태 (10개 지원)

    IniRead, sym1Chk, %iniFile%, selection, sym1Chk, 0

    IniRead, sym2Chk, %iniFile%, selection, sym2Chk, 0

    IniRead, sym3Chk, %iniFile%, selection, sym3Chk, 0

    IniRead, sym4Chk, %iniFile%, selection, sym4Chk, 0

    IniRead, sym5Chk, %iniFile%, selection, sym5Chk, 0

    IniRead, sym6Chk, %iniFile%, selection, sym6Chk, 0

    IniRead, sym7Chk, %iniFile%, selection, sym7Chk, 0

    IniRead, sym8Chk, %iniFile%, selection, sym8Chk, 0

    IniRead, sym9Chk, %iniFile%, selection, sym9Chk, 0

    IniRead, sym10Chk, %iniFile%, selection, sym10Chk, 0

    ; EA 선택 상태

    IniRead, eaAll, %iniFile%, selection, ea_all, 1

    IniRead, ea1, %iniFile%, selection, ea1, 0

    IniRead, ea2, %iniFile%, selection, ea2, 0

    IniRead, ea3, %iniFile%, selection, ea3, 0

    IniRead, ea4, %iniFile%, selection, ea4, 0

    IniRead, ea5, %iniFile%, selection, ea5, 0

    ; Timeframe 선택 상태

    IniRead, tfM1, %iniFile%, selection, tfM1, 0

    IniRead, tfM5, %iniFile%, selection, tfM5, 0

    IniRead, tfM15, %iniFile%, selection, tfM15, 0

    IniRead, tfM30, %iniFile%, selection, tfM30, 1

    IniRead, tfH1, %iniFile%, selection, tfH1, 1

    IniRead, tfH4, %iniFile%, selection, tfH4, 0

    ; v3.7: 날짜 설정 읽기 (10개 기간)

    FormatTime, defaultToday, , yyyy.MM.dd

    Loop, 24 {

        idx := A_Index

        IniRead, tempEnable, %iniFile%, test_date, enable%idx%, 0

        IniRead, tempFrom, %iniFile%, test_date, from_date%idx%,

        IniRead, tempTo, %iniFile%, test_date, to_date%idx%,

        ; 기본값 설정

        if (tempFrom = "" || tempFrom = "ERROR")

            tempFrom := defaultToday

        if (tempTo = "" || tempTo = "ERROR")

            tempTo := defaultToday

        testDateEnable%idx% := tempEnable

        testFromDate%idx% := tempFrom

        testToDate%idx% := tempTo

    }
    
    ; [v2.8] 변수 로드 후 GUI 컨트롤 업데이트 (설지 유실 방지 핵심)
    UpdateGuiFromVariables()
}

UpdateGuiFromVariables() {
    global
    if (guiHwnd = "" || guiHwnd = 0)
        return
    Gui, %guiHwnd%:Default
    
    ; 경로 설정
    GuiControl,, TerminalPathEdit, %terminalPath%
    GuiControl,, SetFolderEdit, %setFolder%
    GuiControl,, EAFolderEdit, %eaFolderPath%
    GuiControl,, HtmlSavePathEdit, %htmlSavePath%
    
    ; 저장된 경로 텍스트 업데이트
    GuiControl,, SavedTerminalText, [저장됨] %terminalPath%
    GuiControl,, SavedSetFolderText, [저장됨] %setFolder%
    GuiControl,, SavedEAPathText, [저장됨] %eaFolderPath%
    GuiControl,, SavedHtmlPathText, [저장됨] %htmlSavePath%
    
    ; Symbol
    Loop, 10 {
        idx := A_Index
        GuiControl,, Sym%idx%Chk, % sym%idx%Chk
        GuiControl,, Sym%idx%Edit, % sym%idx%
    }
    
    ; EA
    GuiControl,, EAAllChk, %eaAll%
    Loop, 5 {
        idx := A_Index
        GuiControl,, EA%idx%Chk, % ea%idx%
    }
    
    ; TF
    GuiControl,, TFM1Chk, %tfM1%
    GuiControl,, TFM5Chk, %tfM5%
    GuiControl,, TFM15Chk, %tfM15%
    GuiControl,, TFM30Chk, %tfM30%
    GuiControl,, TFH1Chk, %tfH1%
    GuiControl,, TFH4Chk, %tfH4%
    
    ; Dates (24개)
    Loop, 24 {
        idx := A_Index
        GuiControl,, TestDateChk%idx%, % testDateEnable%idx%
        
        fromDT := testFromDate%idx%
        toDT := testToDate%idx%
        
        ; yyyy.MM.dd -> yyyyMMddhhmmss (DateTime Choose 포맷)
        if (fromDT != "") {
            cleanFrom := StrReplace(fromDT, ".", "")
            GuiControl,, TestFromDT%idx%, %cleanFrom%
        }
        if (toDT != "") {
            cleanTo := StrReplace(toDT, ".", "")
            GuiControl,, TestToDT%idx%, %cleanTo%
        }
    }
    
    ; 계정 번호
    GuiControl,, AccountNumEdit, %accountNumber%
    
    ; SET 파일 방식 라디오 버튼
    if (useSetFiles = 2)
        GuiControl,, UseSetRadio2, 1
    else if (useSetFiles = 1)
        GuiControl,, UseSetRadio1, 1
    else
        GuiControl,, UseSetRadio0, 1
        
    ; 상태바 표시 갱신
    UpdateSetFileCount()
}

SaveSettings:

    ; [FIX] Force update variables from GUI (with Context)

    Gui, %guiHwnd%:Default

    Gui, %guiHwnd%:Submit, NoHide

    

    ; GUI에서 현재 값 읽기

    GuiControlGet, setFolder,, SetFolderEdit

    GuiControlGet, terminalPath,, TerminalPathEdit

    ; [FIX] Direct Variable Assignment (Submit -> Logic Vars)

    

    ; Symbol Checkboxes (Submit variable -> Logic variable)

    sym1Chk := Sym1Chk

    sym2Chk := Sym2Chk

    sym3Chk := Sym3Chk

    sym4Chk := Sym4Chk

    sym5Chk := Sym5Chk

    sym6Chk := Sym6Chk

    sym7Chk := Sym7Chk

    sym8Chk := Sym8Chk

    sym9Chk := Sym9Chk

    sym10Chk := Sym10Chk

    ; Symbol Edits

    sym1 := Sym1Edit

    sym2 := Sym2Edit

    sym3 := Sym3Edit

    sym4 := Sym4Edit

    sym5 := Sym5Edit

    sym6 := Sym6Edit

    sym7 := Sym7Edit

    sym8 := Sym8Edit

    sym9 := Sym9Edit

    sym10 := Sym10Edit

    ; EA Checkboxes

    eaAll := EAAllChk

    ea1 := EA1Chk

    ea2 := EA2Chk

    ea3 := EA3Chk

    ea4 := EA4Chk

    ea5 := EA5Chk

    ; Timeframe Checkboxes

    tfM1 := TFM1Chk

    tfM5 := TFM5Chk

    tfM15 := TFM15Chk

    tfM30 := TFM30Chk

    tfH1 := TFH1Chk

    tfH4 := TFH4Chk

    ; INI 파일에 저장

    IniWrite, %setFolder%, %iniFile%, folders, setfiles_path

    IniWrite, %terminalPath%, %iniFile%, folders, terminal_path

    ; [v4.1] 작업폴더 저장
    GuiControlGet, currentWorkFolder,, WorkFolderEdit
    if (currentWorkFolder != "" && currentWorkFolder != "ERROR")
        IniWrite, %currentWorkFolder%, %iniFile%, folders, work_folder

    ; v3.8: EA 경로, 리포트 경로도 함께 저장

    GuiControlGet, currentEAPath,, EAFolderEdit

    GuiControlGet, currentHtmlPath,, HtmlSavePathEdit

    if (currentEAPath != "" && currentEAPath != "NOTSET")

        IniWrite, %currentEAPath%, %iniFile%, folders, ea_path

    if (currentHtmlPath != "" && currentHtmlPath != "NOTSET")

        IniWrite, %currentHtmlPath%, %iniFile%, folders, html_save_path

    ; Symbol 저장 (10개 지원)

    IniWrite, %sym1%, %iniFile%, symbols, sym1

    IniWrite, %sym2%, %iniFile%, symbols, sym2

    IniWrite, %sym3%, %iniFile%, symbols, sym3

    IniWrite, %sym4%, %iniFile%, symbols, sym4

    IniWrite, %sym5%, %iniFile%, symbols, sym5

    IniWrite, %sym6%, %iniFile%, symbols, sym6

    IniWrite, %sym7%, %iniFile%, symbols, sym7

    IniWrite, %sym8%, %iniFile%, symbols, sym8

    IniWrite, %sym9%, %iniFile%, symbols, sym9

    IniWrite, %sym10%, %iniFile%, symbols, sym10

    ; 선택 상태 저장 (10개 지원)

    IniWrite, %sym1Chk%, %iniFile%, selection, sym1Chk

    IniWrite, %sym2Chk%, %iniFile%, selection, sym2Chk

    IniWrite, %sym3Chk%, %iniFile%, selection, sym3Chk

    IniWrite, %sym4Chk%, %iniFile%, selection, sym4Chk

    IniWrite, %sym5Chk%, %iniFile%, selection, sym5Chk

    IniWrite, %sym6Chk%, %iniFile%, selection, sym6Chk

    IniWrite, %sym7Chk%, %iniFile%, selection, sym7Chk

    IniWrite, %sym8Chk%, %iniFile%, selection, sym8Chk

    IniWrite, %sym9Chk%, %iniFile%, selection, sym9Chk

    IniWrite, %sym10Chk%, %iniFile%, selection, sym10Chk

    IniWrite, %eaAll%, %iniFile%, selection, ea_all

    IniWrite, %ea1%, %iniFile%, selection, ea1

    IniWrite, %ea2%, %iniFile%, selection, ea2

    IniWrite, %ea3%, %iniFile%, selection, ea3

    IniWrite, %ea4%, %iniFile%, selection, ea4

    IniWrite, %ea5%, %iniFile%, selection, ea5

    IniWrite, %tfM1%, %iniFile%, selection, tfM1

    IniWrite, %tfM5%, %iniFile%, selection, tfM5

    IniWrite, %tfM15%, %iniFile%, selection, tfM15

    IniWrite, %tfM30%, %iniFile%, selection, tfM30

    IniWrite, %tfH1%, %iniFile%, selection, tfH1

    IniWrite, %tfH4%, %iniFile%, selection, tfH4

    ; 오른쪽 저장된 Symbol 표시 업데이트 (INI에서 읽은 값) - 10개 지원

    GuiControl,, Sym1SavedText, [INI] sym1 = %sym1%

    GuiControl,, Sym2SavedText, [INI] sym2 = %sym2%

    GuiControl,, Sym3SavedText, [INI] sym3 = %sym3%

    GuiControl,, Sym4SavedText, [INI] sym4 = %sym4%

    GuiControl,, Sym5SavedText, [INI] sym5 = %sym5%

    GuiControl,, Sym6SavedText, [INI] sym6 = %sym6%

    GuiControl,, Sym7SavedText, [INI] sym7 = %sym7%

    GuiControl,, Sym8SavedText, [INI] sym8 = %sym8%

    GuiControl,, Sym9SavedText, [INI] sym9 = %sym9%

    GuiControl,, Sym10SavedText, [INI] sym10 = %sym10%

    ; SET 파일 개수 업데이트

    UpdateSetFileCount()

    ; [v1.5] 마지막 작업 세션 저장 (재가동 시 환경 비교용)
    FormatTime, _sessionTime,, yyyy-MM-dd HH:mm:ss
    IniWrite, %A_ComputerName%, %iniFile%, last_session, pc_name
    IniWrite, %workFolder%, %iniFile%, last_session, work_folder
    IniWrite, %eaFolderPath%, %iniFile%, last_session, ea_path
    IniWrite, %terminalPath%, %iniFile%, last_session, terminal_path
    IniWrite, %_sessionTime%, %iniFile%, last_session, saved_time

return

; =====================================================

; v3.7: 저장하고 새로고침 (저장 후 즉시 화면 갱신)

; =====================================================

SaveAndRefresh:

    ; 먼저 설정 저장

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    ; v3.7 FIX: 완벽한 동기화를 위해 재로드

    Gosub, ReloadSettings

    return

    ; EA 경로 저장 (GUI에서 읽기)

    GuiControlGet, currentEAPath,, EAFolderEdit

    if (currentEAPath != "" && currentEAPath != "NOTSET")

        IniWrite, %currentEAPath%, %iniFile%, folders, ea_path

    ; HTML 경로 저장

    GuiControlGet, currentHtmlPath,, HtmlSavePathEdit

    if (currentHtmlPath != "" && currentHtmlPath != "NOTSET")

        IniWrite, %currentHtmlPath%, %iniFile%, folders, html_save_path

    ; Symbol 강제 저장 (GUI에서 다시 읽어서 저장)

    GuiControlGet, s1,, Sym1Edit

    GuiControlGet, s2,, Sym2Edit

    GuiControlGet, s3,, Sym3Edit

    GuiControlGet, s4,, Sym4Edit

    GuiControlGet, s5,, Sym5Edit

    GuiControlGet, s6,, Sym6Edit

    GuiControlGet, s7,, Sym7Edit

    GuiControlGet, s8,, Sym8Edit

    GuiControlGet, s9,, Sym9Edit

    GuiControlGet, s10,, Sym10Edit

    IniWrite, %s1%, %iniFile%, symbols, sym1

    IniWrite, %s2%, %iniFile%, symbols, sym2

    IniWrite, %s3%, %iniFile%, symbols, sym3

    IniWrite, %s4%, %iniFile%, symbols, sym4

    IniWrite, %s5%, %iniFile%, symbols, sym5

    IniWrite, %s6%, %iniFile%, symbols, sym6

    IniWrite, %s7%, %iniFile%, symbols, sym7

    IniWrite, %s8%, %iniFile%, symbols, sym8

    IniWrite, %s9%, %iniFile%, symbols, sym9

    IniWrite, %s10%, %iniFile%, symbols, sym10

    ; Symbol 체크 상태도 강제 저장

    GuiControlGet, c1,, Sym1Chk

    GuiControlGet, c2,, Sym2Chk

    GuiControlGet, c3,, Sym3Chk

    GuiControlGet, c4,, Sym4Chk

    GuiControlGet, c5,, Sym5Chk

    GuiControlGet, c6,, Sym6Chk

    GuiControlGet, c7,, Sym7Chk

    GuiControlGet, c8,, Sym8Chk

    GuiControlGet, c9,, Sym9Chk

    GuiControlGet, c10,, Sym10Chk

    IniWrite, %c1%, %iniFile%, selection, sym1Chk

    IniWrite, %c2%, %iniFile%, selection, sym2Chk

    IniWrite, %c3%, %iniFile%, selection, sym3Chk

    IniWrite, %c4%, %iniFile%, selection, sym4Chk

    IniWrite, %c5%, %iniFile%, selection, sym5Chk

    IniWrite, %c6%, %iniFile%, selection, sym6Chk

    IniWrite, %c7%, %iniFile%, selection, sym7Chk

    IniWrite, %c8%, %iniFile%, selection, sym8Chk

    IniWrite, %c9%, %iniFile%, selection, sym9Chk

    IniWrite, %c10%, %iniFile%, selection, sym10Chk

    ; 저장된 경로 표시 갱신

    Gosub, RefreshSavedDisplay

    MsgBox, 64, 저장 완료, 모든 설정이 저장되고 화면이 갱신되었습니다.`n`nSymbol: %s1%, %s2%, %s3%

return

; =====================================================

; v3.7: 저장된 경로 표시 갱신

; =====================================================

RefreshSavedDisplay:

    ; INI에서 저장된 경로 다시 읽기

    IniRead, savedTerminalPath, %iniFile%, folders, terminal_path, NOTSET

    IniRead, savedSetFolder, %iniFile%, folders, setfiles_path, NOTSET

    IniRead, savedEAPath, %iniFile%, folders, ea_path, NOTSET

    IniRead, savedHtmlPath, %iniFile%, folders, html_save_path, NOTSET

    ; [v4.1] 작업폴더 갱신
    IniRead, savedWorkFolder, %iniFile%, folders, work_folder, NOTSET
    if (savedWorkFolder != "NOTSET" && savedWorkFolder != "")
        GuiControl,, WorkFolderEdit, %savedWorkFolder%

    ; GUI 업데이트

    GuiControl,, SavedTerminalText, [저장됨] %savedTerminalPath%

    GuiControl,, SavedSetFolderText, [저장됨] %savedSetFolder%

    GuiControl,, SavedEAPathText, [저장됨] %savedEAPath%

    GuiControl,, SavedHtmlPathText, [저장됨] %savedHtmlPath%

    ; Symbol 저장된 값도 업데이트 (10개 지원)

    IniRead, s1, %iniFile%, symbols, sym1,

    IniRead, s2, %iniFile%, symbols, sym2,

    IniRead, s3, %iniFile%, symbols, sym3,

    IniRead, s4, %iniFile%, symbols, sym4,

    IniRead, s5, %iniFile%, symbols, sym5,

    IniRead, s6, %iniFile%, symbols, sym6,

    IniRead, s7, %iniFile%, symbols, sym7,

    IniRead, s8, %iniFile%, symbols, sym8,

    IniRead, s9, %iniFile%, symbols, sym9,

    IniRead, s10, %iniFile%, symbols, sym10,

    GuiControl,, Sym1SavedText, [INI] sym1 = %s1%

    GuiControl,, Sym2SavedText, [INI] sym2 = %s2%

    GuiControl,, Sym3SavedText, [INI] sym3 = %s3%

    GuiControl,, Sym4SavedText, [INI] sym4 = %s4%

    GuiControl,, Sym5SavedText, [INI] sym5 = %s5%

    GuiControl,, Sym6SavedText, [INI] sym6 = %s6%

    GuiControl,, Sym7SavedText, [INI] sym7 = %s7%

    GuiControl,, Sym8SavedText, [INI] sym8 = %s8%

    GuiControl,, Sym9SavedText, [INI] sym9 = %s9%

    GuiControl,, Sym10SavedText, [INI] sym10 = %s10%

return

; =====================================================

; v3.7: Cleanup Manager 1.8 실행

; =====================================================

; (Deleted old RunCleanupManager v1.8 logic to avoid duplicate label error)

; =====================================================

; v3.9: 로그 모니터링 변수 (10분 간격, 10GB 기준)

; =====================================================

global LogMonitorActive := false

global LogMonitorInterval := 600000  ; 10분 (600초)

global LogMaxSizeGB := 10  ; 10GB 초과시 정리

; =====================================================

; v3.9: 로그 모니터 토글

; =====================================================

ToggleLogMonitor:

    if (LogMonitorActive) {

        ; 모니터 중지

        SetTimer, MonitorTesterLogs, Off

        LogMonitorActive := false

        GuiControl,, LogMonitorBtn, 🔄 로그 모니터 시작

        MsgBox, 64, 로그 모니터, 모니터링이 중지되었습니다.

    } else {

        ; 모니터 시작

        LogMonitorActive := true

        GuiControl,, LogMonitorBtn, ⏹️ 모니터 중지

        SetTimer, MonitorTesterLogs, %LogMonitorInterval%

        ; 즉시 한번 실행

        GoSub, MonitorTesterLogs

        MsgBox, 64, 로그 모니터, 모니터링 시작됨`n10분마다 10GB 이상 로그 자동 정리`n(테스트 중에도 정리 가능)

    }

return

; =====================================================

; v3.9: 로그 모니터링 타이머 함수 (모든 터미널 대상, truncate 방식)

; =====================================================

MonitorTesterLogs:

    ; 10GB in bytes

    maxSizeBytes := LogMaxSizeGB * 1073741824

    cleanedCount := 0

    ; PowerShell로 모든 터미널 로그 정리 (truncate 방식 - 테스트 중에도 가능)

    psScript := ""

    psScript .= "( `n"

    psScript .= "    $maxSize = 10GB `n"

    psScript .= "    $paths = @( `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Terminal\*\tester\logs\*.log', `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Terminal\*\MQL4\Logs\*.log', `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Terminal\*\MQL5\Logs\*.log', `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Tester\*\*\logs\*.log' `n"

    psScript .= "    ) `n"

    psScript .= "    $cleaned = 0 `n"

    psScript .= "    foreach ($pattern in $paths) { `n"

    psScript .= "        Get-ChildItem $pattern -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt $maxSize } | ForEach-Object { `n"

    psScript .= "            try { `n"

    psScript .= "                $fs = New-Object System.IO.FileStream($_.FullName, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite) `n"

    psScript .= "                $fs.SetLength(0) `n"

    psScript .= "                $fs.Close() `n"

    psScript .= "                $cleaned++ `n"

    psScript .= "            } catch {} `n"

    psScript .= "        } `n"

    psScript .= "    } `n"

    psScript .= "    Write-Output $cleaned `n"

    psScript .= ") `n"

    RunWait, powershell -ExecutionPolicy Bypass -Command "%psScript%",, Hide

    if (cleanedCount > 0) {

        TrayTip, 로그 정리됨, %cleanedCount%개 파일 정리됨, 1

    }

return

; =====================================================

; v3.8: 테스터 로그 크기 확인

; =====================================================

CheckTesterLogSize:

    IniRead, termPath, %iniFile%, folders, terminal_path, NONE

    if (termPath = "NONE" || termPath = "") {

        MsgBox, 48, 오류, 터미널 경로가 설정되지 않았습니다.

        return

    }

    StringReplace, termPath, termPath, /, \, All

    testerLogsPath := termPath . "\tester\logs"

    totalSizeMB := 0

    fileCount := 0

    largeFiles := ""

    Loop, %testerLogsPath%\*.log

    {

        fileCount++

        fileSizeMB := Round(A_LoopFileSize / 1024 / 1024, 1)

        totalSizeMB += fileSizeMB

        if (A_LoopFileSize > 524288000) {  ; 500MB

            largeFiles .= A_LoopFileName " (" fileSizeMB " MB)`n"

        }

    }

    msg := "테스터 로그 폴더: " testerLogsPath "`n`n"

    msg .= "총 파일 수: " fileCount "`n"

    msg .= "총 크기: " Round(totalSizeMB, 1) " MB`n`n"

    if (largeFiles != "") {

        msg .= "⚠️ 500MB 이상 파일:`n" largeFiles

    } else {

        msg .= "✅ 500MB 이상 파일 없음"

    }

    MsgBox, 64, 테스터 로그 크기, %msg%

return

; =====================================================

; v3.9: 테스터 로그 즉시 정리 (모든 터미널, truncate 방식)

; =====================================================

ClearTesterLogs:

    MsgBox, 36, 확인, 모든 MT4 터미널의 로그를 정리하시겠습니까?`n(테스트 중에도 정리 가능)

    IfMsgBox, No

        return

    ; PowerShell로 모든 터미널 로그 정리 (truncate 방식)

    psScript := ""

    psScript .= "( `n"

    psScript .= "    $paths = @( `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Terminal\*\tester\logs\*.log', `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Terminal\*\MQL4\Logs\*.log', `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Terminal\*\MQL5\Logs\*.log', `n"

    psScript .= "        '" . A_AppData . "\MetaQuotes\Tester\*\*\logs\*.log' `n"

    psScript .= "    ) `n"

    psScript .= "    $totalGB = 0 `n"

    psScript .= "    $cleaned = 0 `n"

    psScript .= "    foreach ($pattern in $paths) { `n"

    psScript .= "        Get-ChildItem $pattern -ErrorAction SilentlyContinue | ForEach-Object { `n"

    psScript .= "            if ($_.Length -gt 1MB) { `n"

    psScript .= "                $sizeGB = $_.Length / 1GB `n"

    psScript .= "                try { `n"

    psScript .= "                    $fs = New-Object System.IO.FileStream($_.FullName, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite) `n"

    psScript .= "                    $fs.SetLength(0) `n"

    psScript .= "                    $fs.Close() `n"

    psScript .= "                    $totalGB += $sizeGB `n"

    psScript .= "                    $cleaned++ `n"

    psScript .= "                } catch {} `n"

    psScript .= "            } `n"

    psScript .= "        } `n"

    psScript .= "    } `n"

    psScript .= "    Write-Output ('{0} files, {1:N2} GB' -f $cleaned, $totalGB) `n"

    psScript .= ") `n"

    RunWait, powershell -ExecutionPolicy Bypass -Command "%psScript%" > "%A_Temp%\logclean_result.txt",, Hide

    FileRead, result, %A_Temp%\logclean_result.txt

    FileDelete, %A_Temp%\logclean_result.txt

    MsgBox, 64, 완료, 로그 정리 완료`n%result%

return

; =====================================================

; v3.7: 날짜 설정 저장 (10개 기간)

; =====================================================

SaveDateSettings:

    ; [FIX] Validate GUI Context

    Gui, %guiHwnd%:Default

    Gui, %guiHwnd%:Submit, NoHide

    Loop, 24 {

        idx := A_Index

        

        ; Using variables updated by Gui, Submit

        chkVal := TestDateChk%idx%

        fromVal := TestFromDT%idx%

        toVal := TestToDT%idx%

        ; DateTime에서 yyyy.MM.dd 형식으로 변환

        FormatTime, fromStr, %fromVal%, yyyy.MM.dd

        FormatTime, toStr, %toVal%, yyyy.MM.dd

        testDateEnable%idx% := chkVal

        testFromDate%idx% := fromStr

        testToDate%idx% := toStr

        IniWrite, %chkVal%, %iniFile%, test_date, enable%idx%

        IniWrite, %fromStr%, %iniFile%, test_date, from_date%idx%

        IniWrite, %toStr%, %iniFile%, test_date, to_date%idx%

    }

return

; =====================================================

; v3.7: 테스트 기간 추가 기능

; =====================================================

AddMorePeriods:

    ; 현재 활성화되지 않은 기간 4개를 활성화

    addedCount := 0

    Loop, 24 {

        idx := A_Index

        if (testDateEnable%idx% = 0 && addedCount < 4) {

            testDateEnable%idx% := 1

            GuiControl,, TestDateChk%idx%, 1

            addedCount++

        }

    }

    if (addedCount > 0) {

        Gosub, SaveDateSettings

        MsgBox, 64, 기간 추가, %addedCount%개의 기간이 추가되었습니다.

    } else {

        MsgBox, 48, 알림, 이미 모든 기간(24개)이 활성화되어 있습니다.

    }

return

; 빠른 날짜 설정 버튼 (기간1에 적용)

SetQuickDate1Y:

    todayDT := A_YYYY . A_MM . A_DD

    oneYearAgoDT := (A_YYYY - 1) . A_MM . A_DD

    GuiControl,, TestFromDT1, %oneYearAgoDT%

    GuiControl,, TestToDT1, %todayDT%

    GuiControl,, TestDateChk1, 1

    Gosub, SaveDateSettings

return

SetQuickDate6M:

    todayDT := A_YYYY . A_MM . A_DD

    monthsAgo := A_MM - 6

    yearAgo := A_YYYY

    if (monthsAgo <= 0) {

        monthsAgo += 12

        yearAgo -= 1

    }

    sixMonthsAgoDT := yearAgo . SubStr("0" . monthsAgo, -1) . A_DD

    GuiControl,, TestFromDT1, %sixMonthsAgoDT%

    GuiControl,, TestToDT1, %todayDT%

    GuiControl,, TestDateChk1, 1

    Gosub, SaveDateSettings

return

SetQuickDate3M:

    todayDT := A_YYYY . A_MM . A_DD

    monthsAgo := A_MM - 3

    yearAgo := A_YYYY

    if (monthsAgo <= 0) {

        monthsAgo += 12

        yearAgo -= 1

    }

    threeMonthsAgoDT := yearAgo . SubStr("0" . monthsAgo, -1) . A_DD

    GuiControl,, TestFromDT1, %threeMonthsAgoDT%

    GuiControl,, TestToDT1, %todayDT%

    GuiControl,, TestDateChk1, 1

    Gosub, SaveDateSettings

return

SetQuickDateThisY:

    todayDT := A_YYYY . A_MM . A_DD

    thisYearStartDT := A_YYYY . "0101"

    GuiControl,, TestFromDT1, %thisYearStartDT%

    GuiControl,, TestToDT1, %todayDT%

    GuiControl,, TestDateChk1, 1

    Gosub, SaveDateSettings

return

; =====================================================

; v3.8: 전체 선택/해제

; =====================================================

SelectAllPeriods:

    Loop, 24 {

        GuiControl,, TestDateChk%A_Index%, 1

    }

    Gosub, SaveDateSettings

    MsgBox, 64, 완료, 모든 기간(24개)을 선택했습니다.

return

DeselectAllPeriods:

    Loop, 24 {

        GuiControl,, TestDateChk%A_Index%, 0

    }

    Gosub, SaveDateSettings

    MsgBox, 64, 완료, 모든 기간 선택을 해제했습니다.

return

; =====================================================

; v3.8: 기간 프리셋 저장/불러오기 (10개)

; =====================================================

SaveDatePreset:

    GuiControlGet, presetName,, DatePresetSelect

    if (presetName = "") {

        MsgBox, 48, 오류, 프리셋을 선택하세요.

        return

    }

    presetFile := configsFolder . "\date_presets.ini"

    ; 현재 기간 설정 저장

    Loop, 24 {

        idx := A_Index

        GuiControlGet, chkVal,, TestDateChk%idx%

        GuiControlGet, fromVal,, TestFromDT%idx%

        GuiControlGet, toVal,, TestToDT%idx%

        FormatTime, fromStr, %fromVal%, yyyy.MM.dd

        FormatTime, toStr, %toVal%, yyyy.MM.dd

        IniWrite, %chkVal%, %presetFile%, %presetName%, enable%idx%

        IniWrite, %fromStr%, %presetFile%, %presetName%, from%idx%

        IniWrite, %toStr%, %presetFile%, %presetName%, to%idx%

    }

    MsgBox, 64, 저장 완료, "%presetName%"에 기간 설정을 저장했습니다.

    ; 리스트 갱신 (새로 추가된 항목 반영)

    newList := "|" . GetPresetList()

    GuiControl,, DatePresetSelect, %newList%

    GuiControl, ChooseString, DatePresetSelect, %presetName%

return

LoadDatePreset:

    GuiControlGet, presetName,, DatePresetSelect

    if (presetName = "") {

        MsgBox, 48, 오류, 프리셋을 선택하세요.

        return

    }

    ; ★★★ 권장6개 프리셋 (하드코딩) ★★★

    if (presetName = "권장6개") {

        ; 먼저 전체 해제

        Loop, 24 {

            GuiControl,, TestDateChk%A_Index%, 0

        }

        ; 권장 6개 기간 설정 (외부 제출용)

        ; 1. 장기 전체 6년 (2020-2025) - 외부 제출용

        GuiControl,, TestDateChk1, 1

        GuiControl,, TestFromDT1, 20200101

        GuiControl,, TestToDT1, 20251231

        ; 2. 2025년 전체 - 올해 검증 필수

        GuiControl,, TestDateChk2, 1

        GuiControl,, TestFromDT2, 20250101

        GuiControl,, TestToDT2, 20251231

        ; 3. 트럼프 관세 충격 (2025.01-04) - 극한 변동성

        GuiControl,, TestDateChk3, 1

        GuiControl,, TestFromDT3, 20250101

        GuiControl,, TestToDT3, 20250430

        ; 4. 2024년 전체 - 비교 기준

        GuiControl,, TestDateChk4, 1

        GuiControl,, TestFromDT4, 20240101

        GuiControl,, TestToDT4, 20241231

        ; 5. 코로나 폭락 (2020.02-05) - 역대급 하락장

        GuiControl,, TestDateChk5, 1

        GuiControl,, TestFromDT5, 20200201

        GuiControl,, TestToDT5, 20200531

        ; 6. 2022년 하락장 - 약세장 생존력

        GuiControl,, TestDateChk6, 1

        GuiControl,, TestFromDT6, 20220101

        GuiControl,, TestToDT6, 20221231

        Gosub, SaveDateSettings

        MsgBox, 64, 권장6개 로드, 외부 제출용 권장 6개 기간이 설정되었습니다.`n`n1. 장기 6년 (2020.01-2025.12) 🏆`n2. 2025년 전체 ⭐`n3. 트럼프 관세 (2025.01-04)`n4. 2024년 비교 기준`n5. 코로나 폭락 (2020.02-05)`n6. 2022년 하락장

        return

    }

    ; ★★★ 권장8개 프리셋 (하드코딩) ★★★

    if (presetName = "권장8개") {

        ; 먼저 전체 해제

        Loop, 24 {

            GuiControl,, TestDateChk%A_Index%, 0

        }

        ; 권장 8개 기간 설정 (2025년 분기별)

        ; 1. 전체 1년

        GuiControl,, TestDateChk1, 1

        GuiControl,, TestFromDT1, 20250101

        GuiControl,, TestToDT1, 20251231

        ; 2. 상반기

        GuiControl,, TestDateChk2, 1

        GuiControl,, TestFromDT2, 20250101

        GuiControl,, TestToDT2, 20250630

        ; 3. 하반기

        GuiControl,, TestDateChk3, 1

        GuiControl,, TestFromDT3, 20250701

        GuiControl,, TestToDT3, 20251231

        ; 4. Q1 (1분기)

        GuiControl,, TestDateChk4, 1

        GuiControl,, TestFromDT4, 20250101

        GuiControl,, TestToDT4, 20250331

        ; 5. Q2 (2분기)

        GuiControl,, TestFromDT5, 20250401

        GuiControl,, TestToDT5, 20250630

        ; 6. Q3 (3분기)

        GuiControl,, TestDateChk6, 1

        GuiControl,, TestFromDT6, 20250701

        GuiControl,, TestToDT6, 20250930

        ; 7. Q4 (4분기)

        GuiControl,, TestDateChk7, 1

        GuiControl,, TestFromDT7, 20251001

        GuiControl,, TestToDT7, 20251231

        ; 8. 1월 제외 (안정 구간)

        GuiControl,, TestDateChk8, 1

        GuiControl,, TestFromDT8, 20250301

        GuiControl,, TestToDT8, 20251231

        Gosub, SaveDateSettings

        MsgBox, 64, 권장8개 로드, 2025년 분기별 8개 기간이 설정되었습니다.`n`n1. 전체 1년 (2025.01-12)`n2. 상반기 (2025.01-06)`n3. 하반기 (2025.07-12)`n4. Q1 (2025.01-03)`n5. Q2 (2025.04-06)`n6. Q3 (2025.07-09)`n7. Q4 (2025.10-12)`n8. 1월 제외 (2025.03-12)

        return

    }

    presetFile := configsFolder . "\date_presets.ini"

    IfNotExist, %presetFile%

    {

        MsgBox, 48, 오류, 저장된 프리셋이 없습니다.

        return

    }

    ; 프리셋에서 기간 설정 불러오기

    loadedCount := 0

    Loop, 24 {

        idx := A_Index

        IniRead, chkVal, %presetFile%, %presetName%, enable%idx%,

        IniRead, fromStr, %presetFile%, %presetName%, from%idx%,

        IniRead, toStr, %presetFile%, %presetName%, to%idx%,

        if (chkVal != "" && chkVal != "ERROR") {

            GuiControl,, TestDateChk%idx%, %chkVal%

            fromDT := StrReplace(fromStr, ".", "")

            toDT := StrReplace(toStr, ".", "")

            if (fromDT != "" && StrLen(fromDT) = 8)

                GuiControl,, TestFromDT%idx%, %fromDT%

            if (toDT != "" && StrLen(toDT) = 8)

                GuiControl,, TestToDT%idx%, %toDT%

            loadedCount++

        }

    }

    if (loadedCount > 0) {

        Gosub, SaveDateSettings

        MsgBox, 64, 불러오기 완료, "%presetName%"에서 기간 설정을 불러왔습니다.

    } else {

        MsgBox, 48, 오류, "%presetName%"에 저장된 설정이 없습니다.

    }

return

; =====================================================

; v3.8: 선택된 기간 일괄 설정 함수

; =====================================================

; 날짜 계산 함수

CalculateDate(baseDate, months, direction) {

    ; baseDate: YYYYMMDD 형식

    year := SubStr(baseDate, 1, 4)

    month := SubStr(baseDate, 5, 2)

    day := SubStr(baseDate, 7, 2)

    if (direction = "before") {

        month -= months

        while (month <= 0) {

            month += 12

            year -= 1

        }

    } else {

        month += months

        while (month > 12) {

            month -= 12

            year += 1

        }

    }

    ; 월 포맷 (01-12)

    month := SubStr("0" . month, -1)

    ; 일자 유효성 체크 (해당 월의 마지막 날 초과 방지)

    daysInMonth := 31

    if (month = "04" || month = "06" || month = "09" || month = "11")

        daysInMonth := 30

    else if (month = "02") {

        if (Mod(year, 4) = 0 && (Mod(year, 100) != 0 || Mod(year, 400) = 0))

            daysInMonth := 29

        else

            daysInMonth := 28

    }

    if (day > daysInMonth)

        day := daysInMonth

    day := SubStr("0" . day, -1)

    return year . month . day

}

; 일괄 설정 적용 함수

ApplyBatchDate(months, direction) {

    global

    ; 기준 날짜 가져오기

    GuiControlGet, baseDT,, BatchBaseDT

    FormatTime, baseDTStr, %baseDT%, yyyyMMdd

    ; 시작일/종료일 기준 확인

    GuiControlGet, isFromBase,, DateBaseRadio1

    ; 계산된 날짜

    newDate := CalculateDate(baseDTStr, months, direction)

    ; 선택된 기간에만 적용

    appliedCount := 0

    Loop, 24 {

        idx := A_Index

        GuiControlGet, isChecked,, TestDateChk%idx%

        if (isChecked = 1) {

            if (isFromBase = 1) {

                ; 시작일 기준: 시작일 = 계산된 날짜, 종료일 = 기준 날짜

                GuiControl,, TestFromDT%idx%, %newDate%

                GuiControl,, TestToDT%idx%, %baseDTStr%

            } else {

                ; 종료일 기준: 시작일 = 기준 날짜, 종료일 = 계산된 날짜

                GuiControl,, TestFromDT%idx%, %baseDTStr%

                GuiControl,, TestToDT%idx%, %newDate%

            }

            appliedCount++

        }

    }

    if (appliedCount > 0) {

        Gosub, SaveDateSettings

        MsgBox, 64, 완료, %appliedCount%개 기간에 적용했습니다.

    } else {

        MsgBox, 48, 알림, 선택된 기간이 없습니다.`n먼저 기간을 체크하세요.

    }

}

; 버튼 핸들러 - 전 (Before)

BatchDate1MBefore:

    ApplyBatchDate(1, "before")

return

BatchDate2MBefore:

    ApplyBatchDate(2, "before")

return

BatchDate3MBefore:

    ApplyBatchDate(3, "before")

return

BatchDate6MBefore:

    ApplyBatchDate(6, "before")

return

BatchDate1YBefore:

    ApplyBatchDate(12, "before")

return

BatchDate18MBefore:

    ApplyBatchDate(18, "before")

return

BatchDate2YBefore:

    ApplyBatchDate(24, "before")

return

; 버튼 핸들러 - 후 (After)

BatchDate1MAfter:

    ApplyBatchDate(1, "after")

return

BatchDate2MAfter:

    ApplyBatchDate(2, "after")

return

BatchDate3MAfter:

    ApplyBatchDate(3, "after")

return

BatchDate6MAfter:

    ApplyBatchDate(6, "after")

return

BatchDate1YAfter:

    ApplyBatchDate(12, "after")

return

UpdateSetFileCount() {

    global setFolder, SetFileCountText, iniFile

    setFileCount := 0

    if (setFolder != "NOTSET" && setFolder != "") {

        StringReplace, setFolderWin, setFolder, /, \, All

        IfExist, %setFolderWin%

        {

            Loop, %setFolderWin%\*.set

                setFileCount++

        }

    }

    GuiControl,, SetFileCountText, SET 파일: %setFileCount%개

    ; EA 파일 개수 업데이트

    IniRead, eaFolderPath, %iniFile%, folders, ea_path, NOTSET

    eaFileCount := 0

    if (eaFolderPath != "NOTSET" && eaFolderPath != "") {

        StringReplace, eaFolderWin, eaFolderPath, /, \, All

        IfExist, %eaFolderWin%

        {

            Loop, %eaFolderWin%\*.ex4

                eaFileCount++

        }

    }

    GuiControl,, EAFileCountText, EA 파일: %eaFileCount%개

    ; 리포트 파일 개수 업데이트

    IniRead, htmlSavePath, %iniFile%, folders, html_save_path, NOTSET

    reportFileCount := 0

    if (htmlSavePath != "NOTSET" && htmlSavePath != "") {

        StringReplace, htmlSavePathWin, htmlSavePath, /, \, All

        IfExist, %htmlSavePathWin%

        {

            Loop, %htmlSavePathWin%\*.htm

                reportFileCount++

        }

    }

    GuiControl,, ReportFileCountText, 리포트: %reportFileCount%개

}

; =====================================================

; SET 파일 사용 옵션 저장

; =====================================================

SaveSetOption:

    GuiControlGet, radio0,, UseSetRadio0

    GuiControlGet, radio1,, UseSetRadio1

    GuiControlGet, radio2,, UseSetRadio2

    if (radio2)

        useSetFiles := 2

    else if (radio1)

        useSetFiles := 1

    else

        useSetFiles := 0

    IniWrite, %useSetFiles%, %iniFile%, selection, useSetFiles

return

ReloadSettings:
    LoadAllSettings()
return

    ; GUI 업데이트

    GuiControl,, SetFolderEdit, %setFolder%

    GuiControl,, TerminalPathEdit, %terminalPath%

    GuiControl,, EAFolderEdit, %eaFolderPath%

    GuiControl,, HtmlSavePathEdit, %htmlSavePath%

    GuiControl,, Sym1Edit, %sym1%

    GuiControl,, Sym2Edit, %sym2%

    GuiControl,, Sym3Edit, %sym3%

    GuiControl,, Sym4Edit, %sym4%

    GuiControl,, Sym5Edit, %sym5%

    GuiControl,, Sym1Chk, %sym1Chk%

    GuiControl,, Sym2Chk, %sym2Chk%

    GuiControl,, Sym3Chk, %sym3Chk%

    GuiControl,, Sym4Chk, %sym4Chk%

    GuiControl,, Sym5Chk, %sym5Chk%

    GuiControl,, EAAllChk, %eaAll%

    GuiControl,, EA1Chk, %ea1%

    GuiControl,, EA2Chk, %ea2%

    GuiControl,, EA3Chk, %ea3%

    GuiControl,, EA4Chk, %ea4%

    GuiControl,, EA5Chk, %ea5%

    GuiControl,, TFM1Chk, %tfM1%

    GuiControl,, TFM5Chk, %tfM5%

    GuiControl,, TFM15Chk, %tfM15%

    GuiControl,, TFM30Chk, %tfM30%

    GuiControl,, TFH1Chk, %tfH1%

    GuiControl,, TFH4Chk, %tfH4%

    ; SET 파일 사용 옵션 라디오 버튼 업데이트

    GuiControl,, UseSetRadio0, 0

    GuiControl,, UseSetRadio1, 0

    GuiControl,, UseSetRadio2, 0

    if (useSetFiles = 2)

        GuiControl,, UseSetRadio2, 1

    else if (useSetFiles = 1)

        GuiControl,, UseSetRadio1, 1

    else

        GuiControl,, UseSetRadio0, 1

    ; v3.7: 날짜 설정 GUI 업데이트 (10개 기간)

    Loop, 24 {

        idx := A_Index

        chkVal := testDateEnable%idx%

        fromVal := testFromDate%idx%

        toVal := testToDate%idx%

        GuiControl,, TestDateChk%idx%, %chkVal%

        reloadFromDT := StrReplace(fromVal, ".", "")

        reloadToDT := StrReplace(toVal, ".", "")

        if (reloadFromDT != "" && StrLen(reloadFromDT) = 8)

            GuiControl,, TestFromDT%idx%, %reloadFromDT%

        if (reloadToDT != "" && StrLen(reloadToDT) = 8)

            GuiControl,, TestToDT%idx%, %reloadToDT%

    }

    ; 오른쪽 저장된 Symbol 표시 업데이트 (INI에서 읽은 값) - 10개 지원

    GuiControl,, Sym1SavedText, [INI] sym1 = %sym1%

    GuiControl,, Sym2SavedText, [INI] sym2 = %sym2%

    GuiControl,, Sym3SavedText, [INI] sym3 = %sym3%

    GuiControl,, Sym4SavedText, [INI] sym4 = %sym4%

    GuiControl,, Sym5SavedText, [INI] sym5 = %sym5%

    GuiControl,, Sym6SavedText, [INI] sym6 = %sym6%

    GuiControl,, Sym7SavedText, [INI] sym7 = %sym7%

    GuiControl,, Sym8SavedText, [INI] sym8 = %sym8%

    GuiControl,, Sym9SavedText, [INI] sym9 = %sym9%

    GuiControl,, Sym10SavedText, [INI] sym10 = %sym10%

    ; v3.7: 저장된 경로 표시 갱신

    Gosub, RefreshSavedDisplay

    UpdateSetFileCount()

    ; 활성화된 기간 개수 세기

    enabledPeriods := 0

    Loop, 6 {

        if (testDateEnable%A_Index% = 1)

            enabledPeriods++

    }

    MsgBox, 64, 새로고침 완료, 모든 설정을 다시 불러왔습니다.`n`n활성화된 기간: %enabledPeriods%개

return

; =====================================================

; 프로필 관리 함수 (v3.4 - profiles 폴더 사용)

; =====================================================

LoadProfileList() {

    global profilesFolder, ProfileSelect, currentProfile

    profileList := "기본"

    ; profiles 폴더에서 프로필 목록 로드

    IfExist, %profilesFolder%

    {

        Loop, %profilesFolder%\*.ini

        {

            profileName := StrReplace(A_LoopFileName, ".ini", "")

            profileList .= "|" . profileName

        }

    }

    GuiControl,, ProfileSelect, %profileList%

    GuiControl, ChooseString, ProfileSelect, %currentProfile%

}

LoadProfile:

    GuiControlGet, ProfileSelect

    selectedProfile := ProfileSelect

    if (selectedProfile = "기본") {

        MsgBox, 64, 안내, 기본 프로필입니다. 현재 설정을 그대로 사용합니다.

        return

    }

    ; 프로필 INI 파일 경로 (profiles 폴더에서)

    profileIni := profilesFolder . "\" selectedProfile ".ini"

    IfNotExist, %profileIni%

    {

        MsgBox, 48, 오류, 프로필 파일을 찾을 수 없습니다:`n%profileIni%

        return

    }

    ; 프로필 파일을 current_config.ini로 복사하기 전에 현재 경로 백업

    currentTerminal := terminalPath

    currentSetFolder := setFolder

    FileCopy, %profileIni%, %iniFile%, 1

    ; 복사된 설정에서 경로 읽기

    IniRead, newTerminal, %iniFile%, folders, terminal_path, NOTSET

    IniRead, newSetFolder, %iniFile%, folders, setfiles_path, NOTSET

    ; 경로 유효성 검사 및 복원

    ; 1. 터미널 경로가 없고 기존 경로가 유효하면 복원

    IfNotExist, %newTerminal%

    {

        if (currentTerminal != "NOTSET" && currentTerminal != "") {

            IniWrite, %currentTerminal%, %iniFile%, folders, terminal_path

        }

    }

    ; 2. Set 폴더가 없고 기존 폴더가 유효하면 복원

    IfNotExist, %newSetFolder%

    {

        if (currentSetFolder != "NOTSET" && currentSetFolder != "") {

             IniWrite, %currentSetFolder%, %iniFile%, folders, setfiles_path

        }

    }

    currentProfile := selectedProfile

    IniWrite, %currentProfile%, %iniFile%, system, current_profile

    ; 설정 다시 로드

    Gosub, ReloadSettings

    MsgBox, 64, 프로필 로드 완료, 프로필 "%currentProfile%"을(를) 로드했습니다.`n`n만약 저장된 경로가 유효하지 않으면`n현재 컴퓨터의 경로 설정을 유지했습니다.

return

SaveAsNewProfile:

    InputBox, newName, 새 프로필 저장, 프로필 이름을 입력하세요 (예: 집PC, 회사PC):,, 350, 150

    if ErrorLevel

        return

    if (newName = "") {

        MsgBox, 48, 오류, 프로필 이름을 입력하세요.

        return

    }

    if (newName = "기본") {

        MsgBox, 48, 오류, "기본"은 예약된 이름입니다. 다른 이름을 사용하세요.

        return

    }

    ; 먼저 현재 설정 저장

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    ; 프로필 생성 (현재 설정 복사)

    profileIni := profilesFolder . "\" newName ".ini"

    FileCopy, %iniFile%, %profileIni%, 1

    currentProfile := newName

    IniWrite, %currentProfile%, %iniFile%, system, current_profile

    LoadProfileList()

    GuiControl, ChooseString, ProfileSelect, %currentProfile%

    MsgBox, 64, 저장 완료, 프로필 "%newName%"을(를) 생성했습니다.`n`n이 프로필에는 현재 PC의 모든 설정이 저장되었습니다:`n- 터미널 경로`n- EA 경로`n- HTML 저장 경로`n- Symbol, EA, Timeframe 설정`n- 테스트 날짜 설정

return

SaveProfile:

    if (currentProfile = "기본") {

        MsgBox, 48, 안내, 기본 프로필은 덮어쓸 수 없습니다.`n"새 이름 저장" 버튼을 사용하세요.

        return

    }

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    ; 현재 설정을 프로필 파일에도 저장

    profileIni := profilesFolder . "\" currentProfile ".ini"

    FileCopy, %iniFile%, %profileIni%, 1

    MsgBox, 64, 저장 완료, 프로필 "%currentProfile%"에 모든 설정을 덮어썼습니다.

return

DeleteProfile:

    if (currentProfile = "기본") {

        MsgBox, 48, 오류, 기본 프로필은 삭제할 수 없습니다.

        return

    }

    MsgBox, 36, 확인, 프로필 "%currentProfile%"을(를) 삭제하시겠습니까?`n`n이 작업은 되돌릴 수 없습니다.

    IfMsgBox, No

        return

    profileIni := profilesFolder . "\" currentProfile ".ini"

    FileDelete, %profileIni%

    currentProfile := "기본"

    IniWrite, %currentProfile%, %iniFile%, system, current_profile

    LoadProfileList()

    MsgBox, 64, 삭제 완료, 프로필을 삭제했습니다.`n현재 설정은 그대로 유지됩니다.

return

; =====================================================

; 경로 선택 (v3.8: 저장된 경로에서 시작)

; =====================================================

SelectWorkFolder:

    ; 현재 작업폴더 기준으로 시작
    GuiControlGet, currentWork,, WorkFolderEdit
    if (currentWork = "" || !FileExist(currentWork))
        currentWork := A_ScriptDir
    StringReplace, currentWork, currentWork, /, \, All

    FileSelectFolder, selectedWork, *%currentWork%, 3, 작업 폴더 선택 (터미널/EA/SET 기본 검색 위치)

    if (selectedWork != "") {
        StringReplace, selectedWork, selectedWork, \, /, All
        workFolder := selectedWork
        GuiControl,, WorkFolderEdit, %workFolder%
        IniWrite, %workFolder%, %iniFile%, folders, work_folder
        ; 작업폴더 변경 시 하위 경로 자동 탐지 안내
        MsgBox, 64, 작업폴더 설정, 작업폴더가 설정되었습니다.`n%workFolder%`n`n이제 터미널/SET/EA/리포트 찾아보기 시 이 폴더 내에서 먼저 검색합니다.
    }

return

SelectTerminal:

    ; [v7.52] 작업폴더 상/하/형제 우선 탐색 → 없으면 저장값 사용
    GuiControlGet, workFolder,, WorkFolderEdit
    StringReplace, workFolder, workFolder, /, \, All
    startPath := ""
    ; 1) 작업폴더 자체
    if (FileExist(workFolder . "\terminal.exe"))
        startPath := workFolder
    ; 2) 형제 폴더 terminal.exe (부모의 다른 하위 폴더)
    if (startPath = "") {
        SplitPath, workFolder, , wfParent
        if (wfParent != "" && FileExist(wfParent)) {
            Loop, %wfParent%\*.*, 2
            {
                if (A_LoopFileFullPath != workFolder && FileExist(A_LoopFileFullPath . "\terminal.exe")) {
                    startPath := A_LoopFileFullPath
                    break
                }
            }
        }
    }
    ; 3) 형제 폴더 MQL4\Experts (포터블 데이터 폴더)
    if (startPath = "") {
        SplitPath, workFolder, , wfParent
        if (wfParent != "" && FileExist(wfParent)) {
            Loop, %wfParent%\*.*, 2
            {
                if (A_LoopFileFullPath != workFolder && FileExist(A_LoopFileFullPath . "\MQL4\Experts")) {
                    startPath := A_LoopFileFullPath
                    break
                }
            }
        }
    }
    ; 4) 상위 폴더 최대 3단계
    if (startPath = "") {
        parentDir := workFolder
        Loop, 3 {
            SplitPath, parentDir, , newParent
            if (newParent = "" || newParent = parentDir)
                break
            parentDir := newParent
            if (FileExist(parentDir . "\terminal.exe")) {
                startPath := parentDir
                break
            }
        }
    }
    ; 5) 하위 1단계
    if (startPath = "") {
        Loop, %workFolder%\*.*, 2
        {
            if (FileExist(A_LoopFileFullPath . "\terminal.exe")) {
                startPath := A_LoopFileFullPath
                break
            }
        }
    }
    ; 6) 저장값 또는 작업폴더로 fallback
    if (startPath = "") {
        IniRead, savedTerm, %iniFile%, folders, terminal_path, NOTSET
        startPath := (savedTerm != "NOTSET" && savedTerm != "" && savedTerm != "ERROR") ? savedTerm : workFolder
    }
    StringReplace, startPath, startPath, /, \, All

    FileSelectFolder, selectedFolder, *%startPath%, 3, 터미널 폴더 선택

    if (selectedFolder != "") {

        StringReplace, selectedFolder, selectedFolder, \, /, All

        GuiControl,, TerminalPathEdit, %selectedFolder%

        Gosub, SaveSettings

        ; v3.7: 저장 후 표시 갱신

        Gosub, RefreshSavedDisplay

    }

return

SelectSetFolder:

    ; [v7.52] 작업폴더 상/하/형제 우선 탐색 → 없으면 저장값 사용
    GuiControlGet, workFolder,, WorkFolderEdit
    StringReplace, workFolder, workFolder, /, \, All
    startPath := ""
    ; 1) 작업폴더 내 set_files 탐색
    if (FileExist(workFolder . "\configs\set_files"))
        startPath := workFolder . "\configs\set_files"
    else if (FileExist(workFolder . "\set_files"))
        startPath := workFolder . "\set_files"
    ; 2) 형제 폴더 MQL4\Files 탐색 (우선)
    if (startPath = "") {
        SplitPath, workFolder, , wfParent
        if (wfParent != "" && FileExist(wfParent)) {
            Loop, %wfParent%\*.*, 2
            {
                sibPath := A_LoopFileFullPath
                if (sibPath != workFolder) {
                    if (FileExist(sibPath . "\MQL4\Files\BY_STRATEGY")) {
                        startPath := sibPath . "\MQL4\Files\BY_STRATEGY"
                        break
                    } else if (FileExist(sibPath . "\MQL4\Files")) {
                        startPath := sibPath . "\MQL4\Files"
                        break
                    }
                }
            }
        }
    }
    ; 3) 상위 폴더 MQL4\Files 탐색
    if (startPath = "") {
        parentDir := workFolder
        Loop, 3 {
            SplitPath, parentDir, , newParent
            if (newParent = "" || newParent = parentDir)
                break
            parentDir := newParent
            if (FileExist(parentDir . "\MQL4\Files")) {
                startPath := parentDir . "\MQL4\Files"
                break
            }
        }
    }
    ; 4) 저장값 또는 작업폴더로 fallback
    if (startPath = "") {
        IniRead, savedSet, %iniFile%, folders, setfiles_path, NOTSET
        startPath := (savedSet != "NOTSET" && savedSet != "" && savedSet != "ERROR") ? savedSet : workFolder
    }
    StringReplace, startPath, startPath, /, \, All

    FileSelectFolder, selectedFolder, *%startPath%, 3, SET 파일 폴더 선택

    if (selectedFolder != "") {

        StringReplace, selectedFolder, selectedFolder, \, /, All

        GuiControl,, SetFolderEdit, %selectedFolder%

        Gosub, SaveSettings

        ; v3.7: 저장 후 표시 갱신

        Gosub, RefreshSavedDisplay

    }

return

SelectHtmlSaveFolder:

    ; 작업폴더 우선 → 저장된 경로
    GuiControlGet, workFolder,, WorkFolderEdit
    IniRead, startPath, %iniFile%, folders, html_save_path, NOTSET
    if (startPath = "NOTSET" || startPath = "" || startPath = "ERROR") {
        ; 작업폴더 내 Reports 또는 report 폴더 탐색
        if (FileExist(workFolder . "\Reports"))
            startPath := workFolder . "\Reports"
        else if (FileExist(workFolder . "\report"))
            startPath := workFolder . "\report"
        else
            startPath := workFolder
    }
    StringReplace, startPath, startPath, /, \, All

    FileSelectFolder, selectedFolder, *%startPath%, 3, 리포트 저장 폴더 선택

    if (selectedFolder != "") {

        StringReplace, selectedFolder, selectedFolder, \, /, All

        GuiControl,, HtmlSavePathEdit, %selectedFolder%

        IniWrite, %selectedFolder%, %iniFile%, folders, html_save_path
        IniWrite, %selectedFolder%, %iniFile%, folders, report_base_path  ; [v7.7] base 경로 저장

        ; 리포트 파일 개수 업데이트

        reportFileCount := 0

        StringReplace, htmlSavePathWin, selectedFolder, /, \, All

        IfExist, %htmlSavePathWin%

        {

            Loop, %htmlSavePathWin%\*.htm

                reportFileCount++

        }

        GuiControl,, ReportFileCountText, 리포트: %reportFileCount%개

        ; v3.7: 저장 후 표시 갱신

        Gosub, RefreshSavedDisplay

    }

return

SelectEAFolder:

    ; [v7.52] 작업폴더 상/하/형제 우선 탐색 → 없으면 저장값 사용
    GuiControlGet, workFolder,, WorkFolderEdit
    StringReplace, workFolder, workFolder, /, \, All
    startPath := ""
    ; 1) 작업폴더 내 MQL4\Experts
    if (FileExist(workFolder . "\MQL4\Experts"))
        startPath := workFolder . "\MQL4\Experts"
    else if (FileExist(workFolder . "\Experts"))
        startPath := workFolder . "\Experts"
    ; 2) 형제 폴더 MQL4\Experts (우선)
    if (startPath = "") {
        SplitPath, workFolder, , wfParent
        if (wfParent != "" && FileExist(wfParent)) {
            Loop, %wfParent%\*.*, 2
            {
                if (A_LoopFileFullPath != workFolder && FileExist(A_LoopFileFullPath . "\MQL4\Experts")) {
                    startPath := A_LoopFileFullPath . "\MQL4\Experts"
                    break
                }
            }
        }
    }
    ; 3) 상위 폴더 MQL4\Experts
    if (startPath = "") {
        parentDir := workFolder
        Loop, 3 {
            SplitPath, parentDir, , newParent
            if (newParent = "" || newParent = parentDir)
                break
            parentDir := newParent
            if (FileExist(parentDir . "\MQL4\Experts")) {
                startPath := parentDir . "\MQL4\Experts"
                break
            }
        }
    }
    ; 4) 하위 1단계
    if (startPath = "") {
        Loop, %workFolder%\*.*, 2
        {
            if (FileExist(A_LoopFileFullPath . "\MQL4\Experts")) {
                startPath := A_LoopFileFullPath . "\MQL4\Experts"
                break
            }
        }
    }
    ; 5) 저장값 또는 작업폴더로 fallback
    if (startPath = "") {
        IniRead, savedEA, %iniFile%, folders, ea_path, NOTSET
        startPath := (savedEA != "NOTSET" && savedEA != "" && savedEA != "ERROR") ? savedEA : workFolder
    }
    StringReplace, startPath, startPath, /, \, All

    FileSelectFolder, selectedFolder, *%startPath%, 3, EA 파일 폴더 선택 (.ex4)

    if (selectedFolder != "") {

        StringReplace, selectedFolder, selectedFolder, \, /, All

        GuiControl,, EAFolderEdit, %selectedFolder%

        IniWrite, %selectedFolder%, %iniFile%, folders, ea_path

        ; EA 파일 개수 업데이트

        eaFileCount := 0

        StringReplace, eaFolderWin, selectedFolder, /, \, All

        IfExist, %eaFolderWin%

        {

            Loop, %eaFolderWin%\*.ex4

                eaFileCount++

        }

        GuiControl,, EAFileCountText, EA 파일: %eaFileCount%개

        ; v3.7: 저장 후 표시 갱신

        Gosub, RefreshSavedDisplay

    }

return

; =====================================================

; 새 컴퓨터 설정 마법사 실행

; =====================================================

RunNewComputerSetup:

    scriptPath := scriptsFolder . "\SETUP_NEW_COMPUTER.ahk"

    IfExist, %scriptPath%

    {

        Run, "%A_AhkPath%" "%scriptPath%"

        MsgBox, 64, 안내, 새 컴퓨터 설정 마법사를 실행했습니다.`n`n설정 완료 후 이 메뉴의 [새로고침] 버튼을 클릭하세요.

    }

    else

        MsgBox, 48, 오류, SETUP_NEW_COMPUTER.ahk 파일을 찾을 수 없습니다!`n`n경로: %scriptPath%

return

; [v7.7] 시작시 자동감지 1회 자동 실행 (팝업 4개 자동닫기)
StartupAutoDetect4x:
    autoDetectBootMode := 1
    Gosub, AutoDetect
    autoDetectBootMode := 0
return

AutoDetect:
    msgTimeout := autoDetectBootMode ? 1 : 0
    MsgBox, 64, 자동 감지, 실행 중인 터미널과 계정 정보를 검색합니다..., %msgTimeout%

    Gosub, DetectAccountNum

    foundPath := ""

    ; [작업폴더 내부만 탐색] AppData/프로세스 탐색 제거
    GuiControlGet, workFolder,, WorkFolderEdit
    StringReplace, workFolder, workFolder, /, \, All
    if (workFolder != "" && FileExist(workFolder)) {
        ; 1) 작업폴더 자체
        if (FileExist(workFolder . "\terminal.exe")) {
            foundPath := workFolder
            Goto, FinalizeDetection
        }
        ; 2) 작업폴더 하위 1단계 - terminal.exe 우선
        Loop, %workFolder%\*.*, 2
        {
            if (FileExist(A_LoopFileFullPath . "\terminal.exe")) {
                foundPath := A_LoopFileFullPath
                Goto, FinalizeDetection
            }
        }
        ; 3) 작업폴더 하위 1단계 - MQL4\Experts (포터블 데이터폴더)
        Loop, %workFolder%\*.*, 2
        {
            if (FileExist(A_LoopFileFullPath . "\MQL4\Experts")) {
                foundPath := A_LoopFileFullPath
                Goto, FinalizeDetection
            }
        }
        ; 4) 형제 폴더 (부모의 다른 하위 폴더) - terminal.exe 일반 모드만 검색
        SplitPath, workFolder, , wfParent
        if (wfParent != "" && FileExist(wfParent)) {
            Loop, %wfParent%\*.*, 2
            {
                sib := A_LoopFileFullPath
                if (sib != workFolder && FileExist(sib . "\terminal.exe")) {
                    foundPath := sib
                    Goto, FinalizeDetection
                }
            }
            Loop, %wfParent%\*.*, 2
            {
                sib := A_LoopFileFullPath
                if (sib != workFolder && FileExist(sib . "\MQL4\Experts")) {
                    foundPath := sib
                    Goto, FinalizeDetection
                }
            }
        }

        ; 5) 상위 폴더 탐색 (최대 3단계) + 각 상위의 직계 하위 폴더
        parentDir := workFolder
        Loop, 3 {
            SplitPath, parentDir, , newParent
            if (newParent = "" || newParent = parentDir)
                break
            parentDir := newParent
            if (FileExist(parentDir . "\terminal.exe")
                || FileExist(parentDir . "\Start_Portable.bat")) {
                foundPath := parentDir
                Goto, FinalizeDetection
            }
            if (FileExist(parentDir . "\MQL4\Experts")) {
                foundPath := parentDir
                Goto, FinalizeDetection
            }
            ; 상위 폴더의 직계 하위 폴더 탐색 (포터블 포함)
            Loop, %parentDir%\*.*, 2
            {
                _sub := A_LoopFileFullPath
                if (FileExist(_sub . "\terminal.exe")
                    || FileExist(_sub . "\Start_Portable.bat")
                    || FileExist(_sub . "\MQL4\Experts")) {
                    foundPath := _sub
                    Goto, FinalizeDetection
                }
            }
        }
    }

    ; A_ScriptDir 기준 상위 3단계 추가 탐색 (workFolder 탐색 실패 시 보완)
    ; [포터블 지원] terminal.exe 또는 Start_Portable.bat 존재 시 해당 폴더로 설정
    if (foundPath = "") {
        _sd := A_ScriptDir
        Loop, 3
        {
            SplitPath, _sd, , _sd
            if (_sd = "" || !FileExist(_sd))
                break
            Loop, %_sd%\*.*, 2
            {
                _sub := A_LoopFileFullPath
                if (FileExist(_sub . "\terminal.exe")
                    || FileExist(_sub . "\Start_Portable.bat")
                    || FileExist(_sub . "\MQL4\Experts")) {
                    foundPath := _sub
                    Goto, FinalizeDetection
                }
            }
        }
    }

FinalizeDetection:

    if (foundPath != "") {

        StringReplace, foundPath, foundPath, \\, /, All

        GuiControl,, TerminalPathEdit, %foundPath%

        eaPath := foundPath . "/MQL4/Experts"

        setPath := foundPath . "/MQL4/Files"

        ; [v7.52] 작업폴더 형제 폴더에 MQL4\Experts 있으면 우선 적용
        ;        예: C:\NEWOPTMISER\Worker_LOCAL → C:\NEWOPTMISER\MT4\MQL4\Experts
        GuiControlGet, wf_cur,, WorkFolderEdit
        if (wf_cur != "") {
            SplitPath, wf_cur, , wf_parent
            if (wf_parent != "" && FileExist(wf_parent)) {
                Loop, %wf_parent%\*.*, 2
                {
                    sibDir := A_LoopFileFullPath
                    if (sibDir != wf_cur && FileExist(sibDir . "\MQL4\Experts")) {
                        StringReplace, sibDir, sibDir, \, /, All
                        eaPath  := sibDir . "/MQL4/Experts"
                        if (FileExist(sibDir . "/MQL4/Files/BY_STRATEGY"))
                            setPath := sibDir . "/MQL4/Files/BY_STRATEGY"
                        else if (FileExist(sibDir . "/MQL4/Files"))
                            setPath := sibDir . "/MQL4/Files"
                        break
                    }
                }
            }
        }

        if (!InStr(setPath, "BY_STRATEGY") && FileExist(setPath "/BY_STRATEGY"))

            setPath .= "/BY_STRATEGY"

        GuiControl,, EAFolderEdit, %eaPath%

        GuiControl,, SetFolderEdit, %setPath%

        ; [v7.7] 유저 저장 경로 우선 / 없으면 기존 D:/C: 자동감지
        IniRead, reportPath, %iniFile%, folders, report_base_path, NOTSET
        if (reportPath = "NOTSET" || reportPath = "" || reportPath = "ERROR") {
            ; [v1.5] 배포용: 스크립트 폴더 기준 상대 경로
            reportPath := A_ScriptDir . "\reports"
        }
        StringReplace, reportPath, reportPath, /, \, All

        if (!FileExist(reportPath)) {

            FileCreateDir, %reportPath%

        }

        GuiControl,, HtmlSavePathEdit, %reportPath%

        Gosub, SaveSettings

        

        ; Dynamic label check to prevent "Target label does not exist"

        targetLabel := "ReloadSettingsV39"

        if (IsLabel(targetLabel))

            Gosub, %targetLabel%

        else if (IsLabel("ReloadSettings"))

            Gosub, ReloadSettings

            

        msgTimeout := autoDetectBootMode ? 1 : 0
        MsgBox, 64, 감지 완료, 모든 경로가 자동으로 설정 및 저장되었습니다.`n- 터미널: %foundPath%`n- 리포트: %reportPath%, %msgTimeout%

    } else {

        msgTimeout := autoDetectBootMode ? 1 : 0
        MsgBox, 16, 실패, 터미널 경로를 자동으로 찾을 수 없습니다. 수동으로 설정해주세요., %msgTimeout%

    }

return

RunDetectStep1:

    scriptPath := scriptsFolder . "\DETECT_STEP1_CONTROLS.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

RunDetectStep2:

    scriptPath := scriptsFolder . "\DETECT_STEP2_COORDS.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

RunReadSymbols:

    scriptPath := scriptsFolder . "\READ_SYMBOLS.ahk"

    IfExist, %scriptPath%

    {

        Run, "%A_AhkPath%" "%scriptPath%"

        MsgBox, 64, 안내, Symbol을 읽은 후 이 메뉴를 다시 열면`n자동으로 Symbol이 표시됩니다.

    }

    else

        MsgBox, 48, 오류, 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

; =====================================================

; 백테스트 실행

; =====================================================

RunSimpleLoop:

    ; 먼저 설정 저장

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    scriptPath := scriptsFolder . "\SIMPLE_LOOP_v1_45.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

Run4Steps:

    ; 먼저 설정 저장

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    scriptPath := scriptsFolder . "\SIMPLE_4STEPS_v1_45.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

; (Deleted unused RunSimpleLoopV2 logic)

; v2.0 4Step 단일 실행 (현재 설정으로 1회만 실행)

Run4StepsOnce:

    ; 먼저 설정 저장

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    scriptPath := scriptsFolder . "\SIMPLE_4STEPS_v2_0.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, v2.0 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

RunLoopV25:

    ; 먼저 설정 저장

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    ; v8.0 Loop 스크립트 실행 (기간 중심 + 상세 정보 표시)

    scriptPath := scriptsFolder . "\SIMPLE_LOOP_v2_5.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, v8.0 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

; (RunLoopV35Final removed as requested)

; (Run4StepsV35Final removed as requested)

; (Old RunDualLauncher removed)

RunNC4Step:

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    

    scriptPath := scriptsFolder . "\simple_4step_nc.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, NC 실행 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

RunNCLoop:

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    

    scriptPath := scriptsFolder . "\SIMPLE_LOOP_v3_0_NC.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, NC Loop 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

; ==============================================================================

; v2.7 SOLO LOGIC INTEGRATION

; ==============================================================================

LoadSelectedEAs:

    selectedEAs := []

    activeEACount := 0

    if (eaFolder = "")

        return

    Loop, %eaFolder%\*.ex4

    {

        shouldAdd := false

        if (eaAll) {

            shouldAdd := true

        } else {

            idx := A_Index

            if (idx <= 5) {

                if (ea%idx% == 1)

                    shouldAdd := true

            }

        }

        if (shouldAdd) {

            selectedEAs.Push(A_LoopFileName)

            activeEACount++

        }

    }

return

; =====================================================

; 기존 완료된 테스트 목록 로드 (HTML 파일 분석)

; v2.6: 빈 파일(0바이트) 또는 실패 보고서 제외

; =====================================================

LoadCompletedTests:

    completedTests := {}

    skippedCount := 0

    skippedEmptyFiles := 0

    if (htmlSaveFolder = "" || !FileExist(htmlSaveFolder)) {

        FileAppend, [COMPLETED TESTS] HTML folder not found, cannot check existing tests`n, %logFile%

        return

    }

    FileAppend, [COMPLETED TESTS] Scanning: %htmlSaveFolder%`n, %logFile%

    ; HTML 파일 스캔 (재귀: 모든 하위 폴더 포함)

    Loop, %htmlSaveFolder%\*.htm, , 1
    {
        fileName := A_LoopFileName
        filePath := A_LoopFileLongPath
        fileSize := A_LoopFileSize
        
        ; 100개 단위로 상태 업데이트 (사용자 피드백)
        if (Mod(A_Index, 100) = 0) {
            GuiControl,, StatusText, 상태: 기존 리포트 스캔 중 (%A_Index%개...)
        }

        if (fileSize < 1000) {
            skippedEmptyFiles++
            continue
        }

        ; [v2.7 RESTORED] 파일 내용 검증 - 거래가 0인 보고서 제외하여 '즉시 완료' 버그 수정
        ; 성능을 위해 전체를 읽지 않고 앞부분 4KB만 읽음
        fileObj := FileOpen(filePath, "r")
        if (IsObject(fileObj)) {
            fileContent := fileObj.Read(4096)
            fileObj.Close()
        } else {
            continue
        }

        ; 총 거래 횟수 확인 (패턴: align=right>숫자</td><td>...won)
        if (RegExMatch(fileContent, "align=right>(\d+)</td><td[^>]*>.*?won", tradeMatch)) {
            if (tradeMatch1 = 0 || tradeMatch1 = "") {
                skippedEmptyFiles++
                continue
            }
        } else {
            ; 4KB 내에 없으면 전체 읽기 시도 (안정성)
            FileRead, fileContentFull, %filePath%
            if (!RegExMatch(fileContentFull, "align=right>(\d+)</td><td[^>]*>.*?won", tradeMatch) || tradeMatch1 = 0) {
                skippedEmptyFiles++
                continue
            }
        }

        baseName := StrReplace(fileName, ".htm", "")

        ; YYYYMMDD-YYYYMMDD 패턴을 기준으로 testKey 추출
        if (RegExMatch(baseName, "^(.+)_(\d{8}-\d{8})_.*$", m)) {
            testKey := m1 . "_" . m2
            completedTests[testKey] := 1
        } else {
            ; 구형 파일명 호환
            lastUnderscore := InStr(baseName, "_", false, 0)
            if (lastUnderscore > 0) {
                baseName := SubStr(baseName, 1, lastUnderscore - 1)
                lastUnderscore := InStr(baseName, "_", false, 0)
                if (lastUnderscore > 0) {
                    testPeriod := SubStr(baseName, lastUnderscore + 1)
                    baseNameNoDate := SubStr(baseName, 1, lastUnderscore - 1)
                    testKey := baseNameNoDate . "_" . testPeriod
                    completedTests[testKey] := 1
                }
            }
        }
    }

    FileAppend, [COMPLETED TESTS] Skipped empty/failed reports: %skippedEmptyFiles%`n, %logFile%

    completedCount := 0

    for key, value in completedTests

        completedCount++

    FileAppend, [COMPLETED TESTS] Found %completedCount% completed tests`n, %logFile%

    ; 완료된 테스트 목록 로그에 기록 (처음 10개만)

    count := 0

    for key, value in completedTests {

        count++

        if (count <= 10) {

            FileAppend, [COMPLETED] %key%`n, %logFile%

        } else {

            FileAppend, [COMPLETED] ... and %completedCount% more`n, %logFile%

            break

        }

    }

return

; =====================================================

; 시작 버튼

; =====================================================

ButtonStart:

    Gui, Submit, NoHide

    ; Apply Edited Dates to Period 1

    if (EditFromDate != "")

        testFromDate1 := EditFromDate

    if (EditToDate != "")

        testToDate1 := EditToDate

    if (activeEACount == 0) {

        MsgBox, 48, 오류, 선택된 EA가 없습니다.

        return

    }

    if (symCount == 0) {

        MsgBox, 48, 오류, 선택된 통화쌍이 없습니다.

        return

    }

    if (tfCount == 0) {

        MsgBox, 48, 오류, 선택된 타임프레임이 없습니다.

        return

    }

    GuiControl, Disable, BtnStart

    GuiControl, Disable, BtnResume

    GuiControl, Enable, BtnPause

    GuiControl, Enable, BtnStop

    isPaused := false

    isStopped := false

    startTime := A_TickCount

    SetTimer, TimerUpdate, 1000

    isResuming := false

    ; [Option A/B] 루프 순서에 따라 분기
    IniRead, loopOrder, %iniFile%, settings, loop_order, A
    if (loopOrder = "B") {
        Gosub, MainLoopOptionB
    } else {
        Gosub, MainLoop
    }

return

ButtonResume:
    IniRead, resumeFromEA, %iniFile%, resume, ea_index, 0
    IniRead, resumeFromPeriod, %iniFile%, resume, period_index, 0
    IniRead, resumeFromSym, %iniFile%, resume, symbol_index, 0
    IniRead, resumeFromTF, %iniFile%, resume, timeframe_index, 0

    if (resumeFromEA = 0) {
        MsgBox, 48, 알림, 저장된 정보가 없습니다.
        return
    }

    IniRead, resumeEAName, %iniFile%, resume, ea_name,
    IniRead, resumeSymName, %iniFile%, resume, symbol_name,
    IniRead, resumeTFName, %iniFile%, resume, timeframe_name,
    IniRead, resumeTestNum, %iniFile%, resume, test_number, 0
    IniRead, resumeLastTime, %iniFile%, resume, last_save_time,

    MsgBox, 36, 이어서 시작, EA #%resumeFromEA% (%resumeEAName%)`nSymbol: %resumeSymName% | TF: %resumeTFName%`nPeriod #%resumeFromPeriod%`nTest #%resumeTestNum%`n마지막 저장: %resumeLastTime%`n`n이 위치부터 이어서 시작하시겠습니까?
    IfMsgBox, No
        return

    ; GUI 업데이트
    GuiControl, Disable, BtnManual
    GuiControl, Disable, BtnAuto
    GuiControl, Disable, BtnResume
    GuiControl, Enable, BtnPause
    GuiControl, Enable, BtnStop

    isPaused := false
    isStopped := false
    isResuming := true
    startTime := A_TickCount
    SetTimer, TimerUpdate, 1000

    Gosub, RunLoopV27Solo
return

ButtonPause:
    isPaused := !isPaused
    if (isPaused)
        GuiControl,, BtnPause, > 재개
    else
        GuiControl,, BtnPause, || 일시정지
return

ButtonStop:
    MsgBox, 308, 확인, 중단하시겠습니까?`n(현재 위치가 저장되어 이어서 시작 가능)
    IfMsgBox, Yes
        isStopped := true
return

TimerUpdate:

    elapsed := (A_TickCount - startTime) / 1000

    m := Floor(elapsed / 60)

    s := Floor(Mod(elapsed, 60))

    GuiControl,, TimeText, 경과: %m%분 %s%초

    ; 실제 리포트 개수 업데이트 (10초마다)

    if (Mod(Floor(elapsed), 10) = 0) {

        Gosub, RefreshReportCount

    }

return

RefreshReportCount:

    existingReportCount := 0

    if (htmlSaveFolder != "" && FileExist(htmlSaveFolder)) {

        Loop, %htmlSaveFolder%\*.htm

            existingReportCount++

    }

    GuiControl,, ExistingReportText, 실제 리포트 파일: %existingReportCount%개

return

; =====================================================

; Live Analysis (analyze latest report)

; =====================================================

AnalyzeLatestReport:

    global htmlSaveFolder, laLastFile, analyzedFiles

    global laTotalTests, laProfitTests, laLossTests, laTotalProfit, laTotalLoss, laMaxDD

    global laGrossProfit, laGrossLoss, laTotalTrades
    global laLastTrades

    if (htmlSaveFolder = "" || !FileExist(htmlSaveFolder))

        return

    ; Find most recent .htm file

    latestFile := ""

    latestTime := 0

    ; [FIX] Recursive loop causing crash (0xE06D7363). Changed to non-recursive.

    Loop, %htmlSaveFolder%\*.htm, , 0

    {

        FileGetTime, modTime, %A_LoopFileLongPath%

        if (modTime > latestTime) {

            latestTime := modTime

            latestFile := A_LoopFileLongPath

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

    ; We treat everything between "Profit trades" and the number as noise.

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
    laLastTrades  := trades   ; [NO_TRADE SKIP] 마지막 거래 수 저장

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

    ; Update GUI

    netProfit := laTotalProfit + laTotalLoss

    netProfitStr := Format("{:+.2f}", netProfit)

    grossPStr := Format("{:+.2f}", laGrossProfit)

    grossLStr := Format("{:.2f}", laGrossLoss)

    liveText1 := "Tests: " . laTotalTests . " | MaxDD: " . laMaxDD . "% | WinRate: " . winRate . "%"

    liveText2 := "Tests(P/L): " . laProfitTests . "/" . laLossTests . " | Trades(W/L): " . wonTrades . "/" . lostTrades

    liveText3 := "Net: $" . netProfitStr . " | GrossP: $" . grossPStr . " | GrossL: $" . grossLStr

    liveText4 := "Last: " . eaNameParsed

    GuiControl,, LiveAnalysisText, %liveText1%

    GuiControl,, LiveProfitText, %liveText2%

    GuiControl,, LiveNetText, %liveText3%

    GuiControl,, LiveLastEA, %liveText4%

return

; =====================================================

; 실시간 보고서 생성 (버튼)

; =====================================================

; =====================================================

; 메인 루프 (2.7 solo 기간 중심)

; =====================================================

; 테스트 순서: EA → Symbol → TF → Period (기간 1~6 연속)

; =====================================================

MainLoop:

    testCounter := 0

    FileAppend, === MainLoop Start ===`n, %logFile%

    FileAppend, EA: %activeEACount%, Sym: %symCount%, TF: %tfCount%, Period: %periodCount%`n, %logFile%

    FileAppend, Total Tests: %totalTests%`n, %logFile%

    ; ===== EA Loop =====

    Loop % selectedEAs.Length() {

        eaIdx := A_Index

        currentEAFile := selectedEAs[eaIdx]

        eaIndex := eaIdx

        eaName := currentEAFile

        StringReplace, eaName, eaName, .ex4, , All

        ; Resume Check (EA)

        if (isResuming && eaIdx < resumeFromEA) {

            continue

        }

        FileAppend, [EA %eaIdx%/%activeEACount%] %eaName%`n, %logFile%

        ; ===== Symbol Loop =====

        Loop, 5 {

            sIdx := A_Index

            if (sym%sIdx%Chk != 1 || sym%sIdx% == "")

                continue

            ; Resume Check (Symbol) - v2.6

            if (isResuming && eaIdx == resumeFromEA && sIdx < resumeFromSym) {

                continue

            }

            currentSym := sym%sIdx%

            symName := currentSym

            ; [NO_TRADE SKIP] 심볼 진입 시 스킵 플래그 초기화
            skipCurrentSymbol := false
            noTradeKeyLocal   := eaName . "|" . symName
            if (noTradeCounter[noTradeKeyLocal] >= 3) {
                FileAppend, [NO_TRADE_SKIP] %eaName% / %symName% : 3회 연속 0거래 -> 심볼 전체 스킵`n, %logFile%
                GuiControl,, StatusText, [NO TRADE SKIP] %eaName% / %symName%
                continue
            }

            ; ===== Timeframe Loop =====

            Loop, 6 {

                tIdx := A_Index

                currentTF := ""

                currentTFVal := 0

                if (tIdx=1 && tfM1) {

                    currentTF:="M1", currentTFVal:=1

                } else if (tIdx=2 && tfM5) {

                    currentTF:="M5", currentTFVal:=5

                } else if (tIdx=3 && tfM15) {

                    currentTF:="M15", currentTFVal:=15

                } else if (tIdx=4 && tfM30) {

                    currentTF:="M30", currentTFVal:=30

                } else if (tIdx=5 && tfH1) {

                    currentTF:="H1", currentTFVal:=60

                } else if (tIdx=6 && tfH4) {

                    currentTF:="H4", currentTFVal:=240

                }

                if (currentTF == "")

                    continue

                ; [NO_TRADE SKIP] TF 루프 스킵 체크
                if (skipCurrentSymbol)
                    continue

                ; Resume Check (Timeframe) - v2.6

                if (isResuming && eaIdx == resumeFromEA && sIdx == resumeFromSym && tIdx < resumeFromTF) {

                    continue

                }

                tfName := currentTF

                ; ===== Period Loop (기간 1~24) =====

                Loop, 24 {

                    pIdx := A_Index

                    ; Check Enable

                    if (testDateEnable%pIdx% != 1)

                        continue

                    ; [NO_TRADE SKIP] Period 루프 스킵 체크
                    if (skipCurrentSymbol)
                        continue

                    ; Resume Check (Period) - v2.6: 전체 위치 확인

                    if (isResuming && eaIdx == resumeFromEA && sIdx == resumeFromSym && tIdx == resumeFromTF && pIdx < resumeFromPeriod) {

                        continue

                    }

                    ; Reset Resume flag - v2.6: 정확한 위치에서만 해제

                    if (isResuming) {

                        if (eaIdx > resumeFromEA) {

                            isResuming := false

                        } else if (eaIdx == resumeFromEA && sIdx > resumeFromSym) {

                            isResuming := false

                        } else if (eaIdx == resumeFromEA && sIdx == resumeFromSym && tIdx > resumeFromTF) {

                            isResuming := false

                        } else if (eaIdx == resumeFromEA && sIdx == resumeFromSym && tIdx == resumeFromTF && pIdx >= resumeFromPeriod) {

                            isResuming := false

                        }

                    }

                    useFromDate := testFromDate%pIdx%

                    useToDate := testToDate%pIdx%

                    

                    ; [Safety Fix] 만약 동적 변수가 비어있으면 INI에서 직접 읽기

                    if (useFromDate = "")

                        IniRead, useFromDate, %iniFile%, test_date, from_date%pIdx%,

                    if (useToDate = "")

                        IniRead, useToDate, %iniFile%, test_date, to_date%pIdx%,

                    ; ===== 완료된 테스트인지 확인 (건너뛰기) =====

                    ; EA 이름에서 .ex4 제거

                    cleanEAName := StrReplace(currentEAFile, ".ex4", "")

                    ; 테스트 기간 형식 변환: yyyy.MM.dd → yyyyMMdd

                    fromDateClean := StrReplace(useFromDate, ".", "")

                    toDateClean := StrReplace(useToDate, ".", "")

                    testPeriodStr := fromDateClean . "-" . toDateClean

                    ; 테스트 키 생성: EA_심볼_타임프레임_테스트기간
                    testKey := cleanEAName . "_" . currentSym . "_" . currentTF . "_" . testPeriodStr

                    ; [OPTIMIZED] 온디맨드 방식의 완료 확인 (시작 지연 해결)
                    alreadyDone := false
                    if (completedTests.HasKey(testKey)) {
                        alreadyDone := true
                    } else {
                        ; 결과 폴더에서 해당 조건의 파일이 있는지 즉시 확인 (R: 하위폴더 포함)
                        ; 속도를 위해 특정 EA 폴더가 있다면 그곳만 먼저 확인하는 것이 좋으나, 
                        ; 범용성을 위해 htmlSaveFolder에서 검색
                        searchPattern := htmlSaveFolder . "\*" . testKey . "*.htm"
                        Loop, Files, %searchPattern%, R
                        {
                            ; 파일이 존재하고 크기가 유효하면 완료된 것으로 간주
                            if (A_LoopFileSize >= 1000) {
                                alreadyDone := true
                                completedTests[testKey] := 1 ; 메모리 캐시
                                break
                            }
                        }
                    }

                    ; 이미 완료된 테스트면 건너뛰기
                    if (alreadyDone) {
                        skippedCount++
                        FileAppend, [SKIP] Already completed: %testKey%`n, %logFile%
                        GuiControl,, StatusText, 건너뛰기: %testKey%
                        GuiControl,, SkippedText, 건너뛴 테스트: %skippedCount%개 (기존 완료)
                        Sleep, 10
                        continue
                    }

                    ; 일시정지 체크

                    while (isPaused) {

                        GuiControl,, StatusText, 상태: 일시정지 중...

                        Sleep, 1000

                    }

                    ; 중단 체크

                    if (isStopped) {

                        IniWrite, %eaIdx%, %iniFile%, resume, ea_index

                        IniWrite, %pIdx%, %iniFile%, resume, period_index

                        IniWrite, %sIdx%, %iniFile%, resume, symbol_index

                        IniWrite, %tIdx%, %iniFile%, resume, timeframe_index

                        IniWrite, %currentEAFile%, %iniFile%, resume, ea_name

                        IniWrite, %testCounter%, %iniFile%, resume, test_number

                        GuiControl, Enable, BtnStart

                        GuiControl, Enable, BtnResume

                        GuiControl, Disable, BtnPause

                        GuiControl, Disable, BtnStop

                        SetTimer, TimerUpdate, Off

                        GuiControl,, StatusText, 상태: 중단됨 (이어서 시작 가능)

                        MsgBox, 64, 중단, 테스트가 중단되었습니다.`n완료: %testCounter%/%totalTests%`n`n"이어서" 버튼으로 재개 가능

                        return

                    }

                    testCounter++

                    ; 진행상황 표시

                    GuiControl,, CurrentText, [%testCounter%/%totalTests%] %eaName% | %currentSym% | %currentTF% | P%pIdx%

                    GuiControl,, ProgressBar, % (testCounter / totalTests) * 100

                    GuiControl,, StatusText, 기간 %pIdx%: %useFromDate% ~ %useToDate%

                    FileAppend, [%testCounter%] %eaName% | %currentSym% | %currentTF% | P%pIdx% (%useFromDate%~%useToDate%)`n, %logFile%

                    ; [v7.7] 리포트 저장 경로 동적 생성 - 유저 설정 우선
                    IniRead, baseFolder, %iniFile%, folders, report_base_path, NOTSET
                    if (baseFolder = "NOTSET" || baseFolder = "" || baseFolder = "ERROR") {
                        ; [v1.5] 배포용: 스크립트 폴더 기준 상대 경로
                        baseFolder := A_ScriptDir . "/reports"
                    }
                    StringReplace, baseFolder, baseFolder, \, /, All

                    FormatTime, todayDate, , yyyyMMdd

                    dynamicReportPath := baseFolder . "/" . todayDate . "/" . cleanEAName

                    if (!FileExist(dynamicReportPath))

                        FileCreateDir, %dynamicReportPath%

                    

                    ; [OPTIMIZED] INI에 설정 저장 - 필요한 것만 최소화
                    IniWrite, %dynamicReportPath%, %iniFile%, folders, html_save_path
                    IniWrite, %currentEAFile%, %iniFile%, loop_state, current_ea
                    IniWrite, %currentSym%, %iniFile%, loop_state, current_sym
                    IniWrite, %currentTFVal%, %iniFile%, loop_state, current_tf_val
                    IniWrite, %useFromDate%, %iniFile%, loop_state, current_from
                    IniWrite, %useToDate%, %iniFile%, loop_state, current_to
                    IniWrite, %accountNumber%, %iniFile%, loop_state, account_num
                    
                    ; 기간 관련 설정 한 번에 쓰기 (v1.16)
                    IniWrite, 1, %iniFile%, test_date, enable
                    IniWrite, %useFromDate%, %iniFile%, test_date, from_date
                    IniWrite, %useToDate%, %iniFile%, test_date, to_date
                    
                    ; 진행 상황 정보 (최소화)
                    IniWrite, %eaIdx%|%pIdx%|%sIdx%|%tIdx%|%testCounter%, %iniFile%, resume, state_brief
                    IniWrite, %eaName%, %iniFile%, resume, ea_name

                    ; HTML 창 관리

                    Gosub, CheckAndCloseOldHTML
                    Gosub, CleanTesterHistory

                    ; 테스트 실행

                    Gosub, ExecuteStep

                    ; [FIXED] Report Saving managed by SIMPLE_4STEPS

                    ; Sleep, 1000

                    ; Gosub, GenerateLiveReport

                    ; Sleep, 1000

                    ; 실시간 분석 (테스트 완료 후) - [OPTIMIZED] Sleep 단축
                    Sleep, 300
                    Gosub, AnalyzeLatestReport

                    ; [NO_TRADE SKIP] 0거래 카운터 업데이트 (심볼별)
                    if (laLastTrades = 0) {
                        if (!noTradeCounter.HasKey(noTradeKeyLocal))
                            noTradeCounter[noTradeKeyLocal] := 0
                        noTradeCounter[noTradeKeyLocal] := noTradeCounter[noTradeKeyLocal] + 1
                        ntCnt := noTradeCounter[noTradeKeyLocal]
                        FileAppend, [NO_TRADE] %eaName% / %symName% : %ntCnt%/3 연속 0거래`n, %logFile%
                        if (ntCnt >= 3) {
                            skipCurrentSymbol := true
                            GuiControl,, StatusText, [NO TRADE x3] %eaName% / %symName% -> 스킵
                            FileAppend, [NO_TRADE_SKIP] %eaName% / %symName% : 3회 달성 -> 나머지 TF/Period 스킵`n, %logFile%
                        }
                    } else {
                        noTradeCounter[noTradeKeyLocal] := 0
                    }

                    ; [nc2.2] 분석 카운터 기반 트리거 (analNewCount)
                    Gosub, CheckAndRunAnalysis

                    ; Settings 탭으로 복귀 - [OPTIMIZED] Sleep 및 호출 최적화
                    Sleep, 200
                    Gosub, ClickSettingsTab
                    Sleep, 300

                }

            }

        }

    }

    ; 완료

    SetTimer, TimerUpdate, Off

    elapsed := Round((A_TickCount - startTime) / 60000)

    GuiControl, Enable, BtnStart

    GuiControl, Enable, BtnResume

    GuiControl, Disable, BtnPause

    GuiControl, Disable, BtnStop

    GuiControl,, ProgressBar, 100

    GuiControl,, StatusText, 상태: 완료!

    FileAppend, === COMPLETED: %testCounter% tests (skipped: %skippedCount%) in %elapsed% min ===`n, %logFile%

    IniWrite, 1, %iniFile%, status, v2_7_solo_completed

    IniWrite, 0, %iniFile%, resume, ea_index

    ; v2.0: 모든 테스트 완료 후 BacktestAnalyzer v1.7 자동 실행 (SUMMARY + Email)
    FileAppend, [AUTO-ANALYZE] === Starting Auto-Analyze sequence ===`n, %logFile%

    analyzerScript := A_ScriptDir . "\BacktestAnalyzer_v1.7.py"
    FileAppend, [AUTO-ANALYZE] Analyzer path: %analyzerScript%`n, %logFile%

    ; INI에서 리포트 저장 경로 읽기 → 날짜 폴더(모든 EA 포함)로 상위 이동
    IniRead, autoAnalyzePath, %iniFile%, folders, html_save_path, NOTSET
    StringReplace, autoAnalyzePath, autoAnalyzePath, /, \, All
    ; EA 폴더 → 날짜 폴더로 한 단계 올라가기 (모든 EA 결과 분석)
    SplitPath, autoAnalyzePath,, autoAnalyzePath
    FileAppend, [AUTO-ANALYZE] autoAnalyzePath (date folder): %autoAnalyzePath%`n, %logFile%

    if (FileExist(analyzerScript)) {
        FileAppend, [AUTO-ANALYZE] Analyzer file found OK`n, %logFile%
        if (autoAnalyzePath != "NOTSET" && autoAnalyzePath != "" && FileExist(autoAnalyzePath)) {
            FileAppend, [AUTO-ANALYZE] Running BacktestAnalyzer v1.7 on: %autoAnalyzePath%`n, %logFile%
            GuiControl,, StatusText, 상태: 분석기 실행 중...

            ; --auto 모드로 SUMMARY 폴더 생성 + --email로 리포트 메일 발송 (육안 실행)
            Run, %pythonExePath% "%analyzerScript%" --auto "%autoAnalyzePath%" --email, %A_ScriptDir%
            FileAppend, [AUTO-ANALYZE] Analyzer launched successfully.`n, %logFile%
        } else {
            FileAppend, [AUTO-ANALYZE] Skipped - invalid path: [%autoAnalyzePath%]`n, %logFile%
        }
    } else {
        FileAppend, [AUTO-ANALYZE] Skipped - analyzer NOT FOUND: %analyzerScript%`n, %logFile%
    }

    MsgBox, 64, 완료, 모든 테스트가 완료되었습니다!`n`n신규 테스트: %testCounter%회`n건너뛴 테스트: %skippedCount%회`n소요 시간: %elapsed%분

return

; =====================================================
; Option B: 전체 분산 루프 (Period → Symbol → TF → EA)
; EA가 많을 때 모든 EA가 골고루 테스트됨
; =====================================================
MainLoopOptionB:

    testCounter := 0

    FileAppend, === MainLoopOptionB Start (Period→Symbol→TF→EA) ===`n, %logFile%
    FileAppend, EA: %activeEACount%, Sym: %symCount%, TF: %tfCount%, Period: %periodCount%`n, %logFile%
    FileAppend, Total Tests: %totalTests%`n, %logFile%

    ; ===== Period Loop (바깥) =====
    Loop, 24 {

        pIdx := A_Index

        if (testDateEnable%pIdx% != 1)
            continue

        ; Resume Check (Period)
        if (isResuming && pIdx < resumeFromPeriod)
            continue

        useFromDate := testFromDate%pIdx%
        useToDate := testToDate%pIdx%

        if (useFromDate = "")
            IniRead, useFromDate, %iniFile%, test_date, from_date%pIdx%,
        if (useToDate = "")
            IniRead, useToDate, %iniFile%, test_date, to_date%pIdx%,

        fromDateClean := StrReplace(useFromDate, ".", "")
        toDateClean := StrReplace(useToDate, ".", "")
        testPeriodStr := fromDateClean . "-" . toDateClean

        FileAppend, [Period %pIdx%] %useFromDate% ~ %useToDate%`n, %logFile%

        ; ===== Symbol Loop =====
        Loop, 5 {

            sIdx := A_Index

            if (sym%sIdx%Chk != 1 || sym%sIdx% == "")
                continue

            if (isResuming && pIdx == resumeFromPeriod && sIdx < resumeFromSym)
                continue

            currentSym := sym%sIdx%
            symName := currentSym

            ; [NO_TRADE SKIP] 심볼 진입 시 스킵 플래그 초기화
            skipCurrentSymbol := false
            noTradeKeyLocal   := eaName . "|" . symName
            if (noTradeCounter[noTradeKeyLocal] >= 3) {
                FileAppend, [NO_TRADE_SKIP] %eaName% / %symName% : 3회 연속 0거래 -> 심볼 전체 스킵`n, %logFile%
                GuiControl,, StatusText, [NO TRADE SKIP] %eaName% / %symName%
                continue
            }

            ; ===== Timeframe Loop =====
            Loop, 6 {

                tIdx := A_Index
                currentTF := ""
                currentTFVal := 0

                if (tIdx=1 && tfM1) {
                    currentTF:="M1", currentTFVal:=1
                } else if (tIdx=2 && tfM5) {
                    currentTF:="M5", currentTFVal:=5
                } else if (tIdx=3 && tfM15) {
                    currentTF:="M15", currentTFVal:=15
                } else if (tIdx=4 && tfM30) {
                    currentTF:="M30", currentTFVal:=30
                } else if (tIdx=5 && tfH1) {
                    currentTF:="H1", currentTFVal:=60
                } else if (tIdx=6 && tfH4) {
                    currentTF:="H4", currentTFVal:=240
                }

                if (currentTF == "")
                    continue

                ; [NO_TRADE SKIP] TF 루프 스킵 체크
                if (skipCurrentSymbol)
                    continue

                if (isResuming && pIdx == resumeFromPeriod && sIdx == resumeFromSym && tIdx < resumeFromTF)
                    continue

                tfName := currentTF

                ; ===== EA Loop (안쪽 - 모든 EA 순환) =====
                Loop % selectedEAs.Length() {

                    eaIdx := A_Index
                    currentEAFile := selectedEAs[eaIdx]
                    eaIndex := eaIdx
                    eaName := currentEAFile
                    StringReplace, eaName, eaName, .ex4, , All

                    ; ===== 완료된 테스트인지 확인 (건너뛰기) =====
                    cleanEAName := StrReplace(currentEAFile, ".ex4", "")
                    testKey := cleanEAName . "_" . currentSym . "_" . currentTF . "_" . testPeriodStr
                    
                    alreadyDone := false
                    if (completedTests.HasKey(testKey)) {
                        alreadyDone := true
                    } else {
                        searchPattern := htmlSaveFolder . "\*" . testKey . "*.htm"
                        Loop, Files, %searchPattern%, R
                        {
                            if (A_LoopFileSize >= 1000) {
                                alreadyDone := true
                                completedTests[testKey] := 1
                                break
                            }
                        }
                    }

                    if (alreadyDone) {
                        skippedCount++
                        FileAppend, [SKIP-OptionB] Already completed: %testKey%`n, %logFile%
                        GuiControl,, StatusText, 건너뛰기: %testKey%
                        GuiControl,, SkippedText, 건너뛴 테스트: %skippedCount%개 (기존 완료)
                        Sleep, 10
                        continue
                    }

                    if (isResuming && pIdx == resumeFromPeriod && sIdx == resumeFromSym && tIdx == resumeFromTF && eaIdx < resumeFromEA)
                        continue

                    ; Reset Resume flag
                    if (isResuming) {
                        if (pIdx > resumeFromPeriod) {
                            isResuming := false
                        } else if (pIdx == resumeFromPeriod && sIdx > resumeFromSym) {
                            isResuming := false
                        } else if (pIdx == resumeFromPeriod && sIdx == resumeFromSym && tIdx > resumeFromTF) {
                            isResuming := false
                        } else if (pIdx == resumeFromPeriod && sIdx == resumeFromSym && tIdx == resumeFromTF && eaIdx >= resumeFromEA) {
                            isResuming := false
                        }
                    }

                    ; 완료된 테스트 확인 (건너뛰기)
                    cleanEAName := StrReplace(currentEAFile, ".ex4", "")
                    testKey := cleanEAName . "_" . currentSym . "_" . currentTF . "_" . testPeriodStr

                    if (completedTests.HasKey(testKey)) {
                        skippedCount++
                        FileAppend, [SKIP] Already completed: %testKey%`n, %logFile%
                        GuiControl,, StatusText, 건너뛰기: %testKey%
                        GuiControl,, SkippedText, 건너뛴 테스트: %skippedCount%개 (기존 완료)
                        Sleep, 100
                        continue
                    }

                    ; 일시정지 체크
                    while (isPaused) {
                        GuiControl,, StatusText, 상태: 일시정지 중...
                        Sleep, 1000
                    }

                    ; 중단 체크
                    if (isStopped) {
                        IniWrite, %eaIdx%, %iniFile%, resume, ea_index
                        IniWrite, %pIdx%, %iniFile%, resume, period_index
                        IniWrite, %sIdx%, %iniFile%, resume, symbol_index
                        IniWrite, %tIdx%, %iniFile%, resume, timeframe_index
                        IniWrite, %currentEAFile%, %iniFile%, resume, ea_name
                        IniWrite, %testCounter%, %iniFile%, resume, test_number
                        GuiControl, Enable, BtnStart
                        GuiControl, Enable, BtnResume
                        GuiControl, Disable, BtnPause
                        GuiControl, Disable, BtnStop
                        SetTimer, TimerUpdate, Off
                        GuiControl,, StatusText, 상태: 중단됨 (이어서 시작 가능)
                        MsgBox, 64, 중단, 테스트가 중단되었습니다.`n완료: %testCounter%/%totalTests%`n`n"이어서" 버튼으로 재개 가능
                        return
                    }

                    testCounter++

                    ; 진행상황 표시
                    GuiControl,, CurrentText, [%testCounter%/%totalTests%] %eaName% | %currentSym% | %currentTF% | P%pIdx%
                    GuiControl,, ProgressBar, % (testCounter / totalTests) * 100
                    GuiControl,, StatusText, 기간 %pIdx%: %useFromDate% ~ %useToDate%
                    FileAppend, [%testCounter%] %eaName% | %currentSym% | %currentTF% | P%pIdx% (%useFromDate%~%useToDate%)`n, %logFile%

                    ; [v7.7] 리포트 저장 경로 동적 생성 - 유저 설정 우선
                    IniRead, baseFolder, %iniFile%, folders, report_base_path, NOTSET
                    if (baseFolder = "NOTSET" || baseFolder = "" || baseFolder = "ERROR") {
                        ; [v1.5] 배포용: 스크립트 폴더 기준 상대 경로
                        baseFolder := A_ScriptDir . "/reports"
                    }
                    StringReplace, baseFolder, baseFolder, \, /, All
                    FormatTime, todayDate, , yyyyMMdd
                    dynamicReportPath := baseFolder . "/" . todayDate . "/" . cleanEAName
                    if (!FileExist(dynamicReportPath))
                        FileCreateDir, %dynamicReportPath%

                    ; INI 설정 저장
                    IniWrite, %dynamicReportPath%, %iniFile%, folders, html_save_path
                    IniWrite, %currentEAFile%, %iniFile%, loop_state, current_ea
                    IniWrite, %currentSym%, %iniFile%, loop_state, current_sym
                    IniWrite, %currentTFVal%, %iniFile%, loop_state, current_tf_val
                    IniWrite, %useFromDate%, %iniFile%, loop_state, current_from
                    IniWrite, %useToDate%, %iniFile%, loop_state, current_to
                    IniWrite, %accountNumber%, %iniFile%, loop_state, account_num

                    IniWrite, 1, %iniFile%, test_date, enable
                    IniWrite, %useFromDate%, %iniFile%, test_date, from_date
                    IniWrite, %useToDate%, %iniFile%, test_date, to_date

                    IniWrite, %eaIdx%|%pIdx%|%sIdx%|%tIdx%|%testCounter%, %iniFile%, resume, state_brief
                    IniWrite, %eaName%, %iniFile%, resume, ea_name

                    ; HTML 창 관리
                    Gosub, CheckAndCloseOldHTML
                    Gosub, CleanTesterHistory

                    ; 테스트 실행
                    Gosub, ExecuteStep

                    ; 실시간 분석
                    Sleep, 300
                    Gosub, AnalyzeLatestReport

                    ; [NO_TRADE SKIP] 0거래 카운터 업데이트 (심볼별)
                    if (laLastTrades = 0) {
                        if (!noTradeCounter.HasKey(noTradeKeyLocal))
                            noTradeCounter[noTradeKeyLocal] := 0
                        noTradeCounter[noTradeKeyLocal] := noTradeCounter[noTradeKeyLocal] + 1
                        ntCnt := noTradeCounter[noTradeKeyLocal]
                        FileAppend, [NO_TRADE] %eaName% / %symName% : %ntCnt%/3 연속 0거래`n, %logFile%
                        if (ntCnt >= 3) {
                            skipCurrentSymbol := true
                            GuiControl,, StatusText, [NO TRADE x3] %eaName% / %symName% -> 스킵
                            FileAppend, [NO_TRADE_SKIP] %eaName% / %symName% : 3회 달성 -> 나머지 TF/Period 스킵`n, %logFile%
                        }
                    } else {
                        noTradeCounter[noTradeKeyLocal] := 0
                    }

                    ; [nc2.2] 분석 카운터 기반 트리거 (analNewCount)
                    Gosub, CheckAndRunAnalysis

                    ; Settings 탭으로 복귀
                    Sleep, 200
                    Gosub, ClickSettingsTab
                    Sleep, 300

                }

            }

        }

    }

    ; 완료
    SetTimer, TimerUpdate, Off
    elapsed := Round((A_TickCount - startTime) / 60000)
    GuiControl, Enable, BtnStart
    GuiControl, Enable, BtnResume
    GuiControl, Disable, BtnPause
    GuiControl, Disable, BtnStop
    GuiControl,, ProgressBar, 100
    GuiControl,, StatusText, 상태: 완료! (Option B)
    FileAppend, === COMPLETED (Option B): %testCounter% tests (skipped: %skippedCount%) in %elapsed% min ===`n, %logFile%
    IniWrite, 1, %iniFile%, status, v2_7_solo_completed
    IniWrite, 0, %iniFile%, resume, ea_index

    ; 완료 후 BacktestAnalyzer 자동 실행
    analyzerScript := A_ScriptDir . "\BacktestAnalyzer_v1.7.py"
    IniRead, autoAnalyzePath, %iniFile%, folders, html_save_path, NOTSET
    StringReplace, autoAnalyzePath, autoAnalyzePath, /, \, All
    SplitPath, autoAnalyzePath,, autoAnalyzePath
    if (FileExist(analyzerScript) && autoAnalyzePath != "NOTSET" && autoAnalyzePath != "" && FileExist(autoAnalyzePath)) {
        GuiControl,, StatusText, 상태: 분석기 실행 중...
        Run, %pythonExePath% "%analyzerScript%" --auto "%autoAnalyzePath%" --email, %A_ScriptDir%
        FileAppend, [AUTO-ANALYZE] Analyzer launched on: %autoAnalyzePath%`n, %logFile%
    }

    MsgBox, 64, 완료, 모든 테스트가 완료되었습니다! (Option B)`n`n신규 테스트: %testCounter%회`n건너뛴 테스트: %skippedCount%회`n소요 시간: %elapsed%분

return

; =====================================================

; 테스트 실행

; =====================================================

ExecuteStep:
    ; EA 이름을 별도 파일에 저장
    eaNameFile := A_WorkingDir . "\configs\current_ea_name.txt"
    FileDelete, %eaNameFile%
    FileAppend, %eaName%, %eaNameFile%, UTF-8

    ; 4STEPS 실행 (v4.0 통합 버전 사용)
    scriptPath := scriptsFolder . "\SIMPLE_4STEPS_NC23.ahk"
    IfNotExist, %scriptPath%
        scriptPath := scriptsFolder . "\SIMPLE_4STEPS_v4_0.ahk"  ; fallback
    IfNotExist, %scriptPath%
        scriptPath := scriptsFolder . "\SIMPLE_4STEPS_v4_0.exe"

    if (!FileExist(scriptPath)) {
        MsgBox, 48, 오류, 4Steps NC 스크립트를 찾을 수 없습니다!`n%scriptPath%
        return
    }

    ; 이전 프로세스 정리
    Process, Close, SIMPLE_4STEPS_v4_0.exe
    WinClose, SIMPLE_4STEPS_v4_0.ahk
    WinWaitClose, SIMPLE_4STEPS_v4_0.ahk, , 1

    ; 내부 제어 버튼 활성화
    GuiControl, Enable, BtnPause
    GuiControl, Enable, BtnStop
    GuiControl, Disable, BtnResume

    ; Run 4Steps Script (v4.0 fixed version) - Passing EA Name instead of Index
    ; Updated by 202531, 20250430
    Run, "%A_AhkPath%" "%scriptPath%" "%eaName%" "%symName%" "%tfName%" "%testCounter%" "%useFromDate%" "%useToDate%", , , stepsPID

    ; 프로세스 완료 대기
    Loop {
        Process, Exist, %stepsPID%
        if (!ErrorLevel)
            break
        
        Sleep, 500

        ; 중단 체크
        if (isStopped) {
            Process, Close, %stepsPID%
            break
        }

        ; 일시정지 체크
        while (isPaused) {
            GuiControl,, StatusText, 상태: 일시정지 중...
            Sleep, 1000
            if (isStopped) {
                Process, Close, %stepsPID%
                break 2
            }
        }
    }
return

    stepStartTime := A_TickCount

    stepTimeout := 60 * 60 * 1000 ; 60 minutes

    Loop {

        Process, Exist, %stepsPID%

        if (!ErrorLevel)

            break

        

        ; [FIX] Timeout Check

        if (A_TickCount - stepStartTime > stepTimeout) {

            FileAppend, [WARN] Step Timed Out (>60m). Force closing PID %stepsPID%`n, %logFile%

            Process, Close, %stepsPID%

            break

        }

        Sleep, 500

        ; 중단 체크

        if (isStopped) {

            Process, Close, %stepsPID%

            break

        }

        ; 일시정지 체크

        while (isPaused) {

            GuiControl,, StatusText, 상태: 일시정지 중...

            Sleep, 1000

            if (isStopped) {

                Process, Close, %stepsPID%

                break 2

            }

        }

    }

return

; =====================================================

; HTML 창 제한

; =====================================================

CheckAndCloseOldHTML:
    ; [nc2.2] SOLO_9_87 스타일: 신규 누적 카운터 기준으로 닫기
    ; 신규 = 테스트 누적 카운터 (닫기 시 0 리셋)
    ; 닫음 = 닫기 실행 횟수
    global htmlCloseThreshold, htmlBrowserTarget, htmlNewCount, htmlOpenCount, htmlCloseCount

    htmlNewCount++  ; 테스트 1회당 1 증가

    IniRead, htmlCloseThreshold, %iniFile%, settings, html_close_threshold, 10
    IniRead, htmlBrowserTarget, %iniFile%, settings, html_browser_target, both

    ; 실제 열린 창 수 계산 (브라우저 타겟 필터)
    SetTitleMatchMode, 2
    WinGet, wAll, List, ahk_class Chrome_WidgetWin_1

    actualOpen := 0
    openIDs := []
    Loop, %wAll% {
        wid := wAll%A_Index%
        WinGet, procName, ProcessName, ahk_id %wid%
        if (htmlBrowserTarget = "chrome" && procName != "chrome.exe")
            continue
        if (htmlBrowserTarget = "edge" && procName != "msedge.exe")
            continue
        if (htmlBrowserTarget = "both" && procName != "chrome.exe" && procName != "msedge.exe")
            continue
        actualOpen++
        openIDs.Push(wid)
    }

    htmlOpenCount := actualOpen

    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    GuiControl,, HtmlNewCountText,  %htmlNewCount%개
    GuiControl,, HtmlCloseCountText, %htmlCloseCount%회
    FileAppend, [HTML CHECK] 신규: %htmlNewCount% / Limit: %htmlCloseThreshold% / 열림: %actualOpen% / 닫은횟수: %htmlCloseCount%`n, %logFile%

    if (htmlNewCount >= htmlCloseThreshold) {
        FileAppend, [HTML CLOSE] 신규%htmlNewCount%개 -> Limit%htmlCloseThreshold% 초과 -> 전체 닫기`n, %logFile%
        closedCount := 0
        for i, wid in openIDs {
            WinClose, ahk_id %wid%
            Sleep, 100
            closedCount++
        }
        htmlCloseCount++
        htmlNewCount  := 0
        htmlOpenCount := 0
        GuiControl,, HtmlNewCountText,  0개
        GuiControl,, HtmlCloseCountText, %htmlCloseCount%회
        FileAppend, [HTML CLOSE] %closedCount%개 창 닫음, 총 %htmlCloseCount%번째 닫기`n, %logFile%
    }
return

; =====================================================
; [nc2.2] 분석 카운터 기반 트리거 (CheckAndRunAnalysis)
; htmlNewCount처럼 독립적으로 동작:
;   analNewCount++ → analyzeInterval 초과 시 분석 실행 → analNewCount=0 리셋
; =====================================================

CheckAndRunAnalysis:
    global analyzeInterval, analNewCount, htmlAnalCount

    analNewCount++
    GuiControl,, AnalNewCountText, %analNewCount%개

    FileAppend, [ANAL CHECK] 신규분석: %analNewCount% / 분석간격: %analyzeInterval%`n, %logFile%

    if (analyzeInterval > 0 && analNewCount >= analyzeInterval) {
        FileAppend, [ANAL TRIGGER] 신규%analNewCount%개 -> 간격%analyzeInterval% 초과 -> 분석 실행`n, %logFile%
        analNewCount := 0
        GuiControl,, AnalNewCountText, 0개
        Gosub, RunIntervalAnalysis
    }
return

; =====================================================
; [★ LOG] 테스터 로그 ON/OFF 토글
; =====================================================

ToggleLogEnabled:
    logEnabled := !logEnabled
    IniRead, _tglTermPath, %iniFile%, folders, terminal_path, NOTSET
    StringReplace, _tglTermPath, _tglTermPath, /, \, All
    testerLogsDir := (_tglTermPath != "NOTSET" && _tglTermPath != "" && _tglTermPath != "ERROR") ? _tglTermPath . "\tester\logs" : ""
    if (logEnabled) {
        GuiControl,, LogEnabledBtn, 📝 테스터 로그: ON — 클릭하면 OFF (로그 차단)
        FormatTime, logTime,, HH:mm:ss
        ToolTip, [%logTime%] 테스터 로그: ON (로그 생성 허용), 0, 0
        SetTimer, RemoveToolTip, -2000
    } else {
        GuiControl,, LogEnabledBtn, 🔇 테스터 로그: OFF (기본) — 클릭하면 ON (로그 생성 허용)
        ; 즉시 기존 로그 삭제
        if (testerLogsDir != "" && FileExist(testerLogsDir)) {
            Loop, Files, %testerLogsDir%\*.log
                FileDelete, %A_LoopFileFullPath%
        }
        FormatTime, logTime,, HH:mm:ss
        ToolTip, [%logTime%] 테스터 로그: OFF — 기존 로그 삭제 완료, 0, 0
        SetTimer, RemoveToolTip, -2000
    }
return

; =====================================================
; [★ LOG] 테스터 로그 억제 타이머 (500ms 주기)
; logEnabled = false 이면 .log 파일 즉시 삭제
; =====================================================

SuppressTesterLogsTimer:
    if (logEnabled)
        return
    IniRead, _sltTermPath, %iniFile%, folders, terminal_path, NOTSET
    if (_sltTermPath = "NOTSET" || _sltTermPath = "" || _sltTermPath = "ERROR")
        return
    StringReplace, _sltTermPath, _sltTermPath, /, \, All
    testerLogsDir := _sltTermPath . "\tester\logs"
    if !FileExist(testerLogsDir)
        return
    Loop, Files, %testerLogsDir%\*.log
    {
        FileDelete, %A_LoopFileFullPath%
    }
return

RemoveToolTip:
    ToolTip
return

; =====================================================
; [★ HISTORY] 테스터 히스토리 정리 (10GB 초과 시 오래된 파일 삭제)
; 경로: [터미널 경로]\tester\history (설정 탭의 터미널 경로 사용)
; 10GB 초과 → 오래된 파일부터 삭제하여 7GB 이하로 줄임
; =====================================================

CleanTesterHistory:
    IniRead, _ctTermPath, %iniFile%, folders, terminal_path, NOTSET
    if (_ctTermPath = "NOTSET" || _ctTermPath = "" || _ctTermPath = "ERROR")
        return
    StringReplace, _ctTermPath, _ctTermPath, /, \, All
    historyDir := _ctTermPath . "\tester\history"
    if !FileExist(historyDir)
        return

    ; 전체 크기 계산 (KB 단위, 오버플로우 방지)
    totalKB := 0
    Loop, Files, %historyDir%\*.*, RF
        totalKB += A_LoopFileSizeKB

    limitKB   := 10485760  ; 10GB (10 * 1024 * 1024 KB)
    if (totalKB <= limitKB)
        return

    ; 10GB 초과 → 날짜 오름차순으로 파일 목록 수집 후 삭제
    FormatTime, logTime,, HH:mm:ss
    FileAppend, [%logTime%] HistoryClean: %totalKB%KB > 10GB → 정리 시작`n, %A_ScriptDir%\scripts\solo_remote_log.txt

    fileList := ""
    Loop, Files, %historyDir%\*.*, RF
        fileList .= A_LoopFileTimeModified . ";" . A_LoopFileSizeKB . ";" . A_LoopFileFullPath . "`n"

    Sort, fileList  ; 날짜 오름차순 → 가장 오래된 파일이 맨 앞

    targetKB := 7340032  ; 7GB 이하로 줄이기 (여유 공간 확보)
    Loop, Parse, fileList, `n
    {
        if (totalKB <= targetKB)
            break
        if (A_LoopField = "")
            continue
        pos1 := InStr(A_LoopField, ";")
        pos2 := InStr(A_LoopField, ";",, pos1 + 1)
        fileSizeKB := SubStr(A_LoopField, pos1 + 1, pos2 - pos1 - 1)
        filePath   := SubStr(A_LoopField, pos2 + 1)
        FileDelete, %filePath%
        if (ErrorLevel = 0)
            totalKB -= fileSizeKB
    }

    FileAppend, [%logTime%] HistoryClean: 완료 → 현재 약 %totalKB%KB`n, %A_ScriptDir%\scripts\solo_remote_log.txt
return

; =====================================================
; [★ MONITOR] 로그 & 히스토리 모니터 UI 갱신
; =====================================================

UpdateMonitorUI:
RefreshMonitor:
    ; ── 테스터 로그/히스토리 경로 INI에서 읽기
    IniRead, _umTermPath, %iniFile%, folders, terminal_path, NOTSET
    StringReplace, _umTermPath, _umTermPath, /, \, All
    _umBase := (_umTermPath != "NOTSET" && _umTermPath != "" && _umTermPath != "ERROR") ? _umTermPath : ""
    ; ── 테스터 로그 폴더 크기 계산
    logDir := (_umBase != "") ? _umBase . "\tester\logs" : ""
    logKB := 0
    if (logDir != "" && FileExist(logDir)) {
        Loop, Files, %logDir%\*.log
            logKB += A_LoopFileSizeKB
    }

    if (logKB < 1024)
        logSizeStr := logKB . " KB"
    else if (logKB < 1048576)
        logSizeStr := Round(logKB / 1024, 1) . " MB"
    else
        logSizeStr := Round(logKB / 1048576, 2) . " GB"

    GuiControl,, LogFolderSizeText, %logSizeStr%
    if (logEnabled)
        GuiControl,, LogSuppressStatus, ● ON  (생성중)
    else
        GuiControl,, LogSuppressStatus, ● OFF (억제중)

    ; ── 히스토리 폴더 크기 계산
    historyDir := (_umBase != "") ? _umBase . "\tester\history" : ""
    histKB := 0
    if FileExist(historyDir) {
        Loop, Files, %historyDir%\*.*, RF
            histKB += A_LoopFileSizeKB
    }

    if (histKB < 1024)
        histSizeStr := histKB . " KB"
    else if (histKB < 1048576)
        histSizeStr := Round(histKB / 1024, 1) . " MB"
    else
        histSizeStr := Round(histKB / 1048576, 2) . " GB"

    GuiControl,, HistorySizeText, %histSizeStr%

    ; ── 프로그레스 바 (10GB 기준 %)
    limitKB := 10485760
    pct := (limitKB > 0) ? Round((histKB / limitKB) * 100) : 0
    if (pct > 100)
        pct := 100
    GuiControl,, HistoryProgressBar, %pct%
    GuiControl,, HistoryProgressText, %pct%`%

    ; ── 프로그레스 바 색상 (사용량별)
    if (pct >= 80)
        GuiControl, +cFF3300, HistoryProgressBar
    else if (pct >= 50)
        GuiControl, +cFFAA00, HistoryProgressBar
    else
        GuiControl, +c00CC44, HistoryProgressBar

    ; ── HTML 탭 카운트 (Chrome 창 수)
    htmlCount := 0
    WinGet, wList, List, ahk_class Chrome_WidgetWin_1
    htmlCount := wList
    GuiControl,, HtmlTabCount, 탭: %htmlCount%개
return

; ─────────────────────────────────────────────────────
ForceCleanLogs:
    IniRead, _fclTermPath, %iniFile%, folders, terminal_path, NOTSET
    StringReplace, _fclTermPath, _fclTermPath, /, \, All
    logDir := (_fclTermPath != "NOTSET" && _fclTermPath != "" && _fclTermPath != "ERROR") ? _fclTermPath . "\tester\logs" : ""
    if (logDir = "") {
        MsgBox, 48, 로그 삭제, 터미널 경로가 설정되지 않았습니다.`n설정 탭에서 MT4 터미널 경로를 지정하세요.
        return
    }
    if !FileExist(logDir) {
        MsgBox, 48, 로그 삭제, 로그 폴더가 없습니다.`n경로: %logDir%
        return
    }
    Loop, Files, %logDir%\*.log
        FileDelete, %A_LoopFileFullPath%
    Gosub, UpdateMonitorUI
    ToolTip, [OK] 로그 파일 삭제 완료!, 0, 0
    SetTimer, RemoveToolTip, -2000
return

; ─────────────────────────────────────────────────────
ForceCleanHistory:
    IniRead, _fchTermPath, %iniFile%, folders, terminal_path, NOTSET
    StringReplace, _fchTermPath, _fchTermPath, /, \, All
    historyDir := (_fchTermPath != "NOTSET" && _fchTermPath != "" && _fchTermPath != "ERROR") ? _fchTermPath . "\tester\history" : ""
    if (historyDir = "") {
        MsgBox, 48, 히스토리 정리, 터미널 경로가 설정되지 않았습니다.`n설정 탭에서 MT4 터미널 경로를 지정하세요.
        return
    }
    if !FileExist(historyDir) {
        MsgBox, 48, 히스토리 정리, 히스토리 폴더가 없습니다.
        return
    }
    totalKB := 0
    Loop, Files, %historyDir%\*.*, RF
        totalKB += A_LoopFileSizeKB
    if (totalKB = 0) {
        MsgBox, 64, 히스토리 정리, 히스토리 폴더가 비어 있습니다.
        return
    }
    histGB := Round(totalKB / 1048576, 2)
    MsgBox, 36, 히스토리 즉시 정리, 현재 크기: %histGB% GB`n`n오래된 파일부터 삭제하여 3GB 이하로 줄입니다.`n계속하시겠습니까?
    IfMsgBox, No
        return

    fileList := ""
    Loop, Files, %historyDir%\*.*, RF
        fileList .= A_LoopFileTimeModified . ";" . A_LoopFileSizeKB . ";" . A_LoopFileFullPath . "`n"
    Sort, fileList

    targetKB := 3145728  ; 3GB
    Loop, Parse, fileList, `n
    {
        if (totalKB <= targetKB)
            break
        if (A_LoopField = "")
            continue
        pos1 := InStr(A_LoopField, ";")
        pos2 := InStr(A_LoopField, ";",, pos1 + 1)
        fileSizeKB := SubStr(A_LoopField, pos1 + 1, pos2 - pos1 - 1)
        filePath   := SubStr(A_LoopField, pos2 + 1)
        FileDelete, %filePath%
        if (ErrorLevel = 0)
            totalKB -= fileSizeKB
    }
    Gosub, UpdateMonitorUI
    MsgBox, 64, 완료, 히스토리 정리 완료!`n현재 약 %totalKB% KB 남음.
return

; =====================================================

; 테스터 로그 자동 정리 (500MB 이상 삭제)

; =====================================================

CleanupTesterLogs:

    ; 터미널 경로 읽기

    IniRead, terminalPath, %iniFile%, folders, terminal_path, NONE

    if (terminalPath = "NONE" || terminalPath = "") {

        return

    }

    StringReplace, terminalPath, terminalPath, /, \, All

    testerLogsPath := terminalPath . "\tester\logs"

    maxSizeMB := 500

    maxSizeBytes := maxSizeMB * 1024 * 1024

    deletedCount := 0

    deletedSizeMB := 0

    Loop, %testerLogsPath%\*.log

    {

        if (A_LoopFileSize > maxSizeBytes) {

            fileSizeMB := Round(A_LoopFileSize / 1024 / 1024, 1)

            FileDelete, %A_LoopFileFullPath%

            if (!ErrorLevel) {

                deletedCount++

                deletedSizeMB += fileSizeMB

                FileAppend, [LOG CLEANUP] Deleted: %A_LoopFileName% (%fileSizeMB% MB)`n, %logFile%

            }

        }

    }

    if (deletedCount > 0) {

        MsgBox, 64, 테스터 로그 정리, %deletedCount%개 로그 파일 삭제됨`n총 %deletedSizeMB% MB 확보, 3

    }

return

; =====================================================

; Run Setup Scripts

; =====================================================

RunControl1:

    Run, "%scriptsFolder%\DETECT_STEP1_CONTROLS.ahk"

return

RunControl2:

    Run, "%scriptsFolder%\DETECT_STEP2_COORDS.ahk"

return

; =====================================================

; Resize Actions

; =====================================================

; (Duplicate resize logic removed)

; =====================================================

; Fix MT4 Window Size Logic

; =====================================================

FixWindowSize:

    ; Find MT4 Terminal

    mt4Found := 0

    WinGet, wins, List

    Loop, %wins% {

        id := wins%A_Index%

        WinGet, proc, ProcessName, ahk_id %id%

        if (proc = "terminal.exe") {

            WinGetClass, winClass, ahk_id %id%

            if (winClass != "#32770") {

                mt4Found := id

                break

            }

        }

    }

    

    if (mt4Found) {

        WinMove, ahk_id %mt4Found%, , 0, 0, 960, 1036

        ; MsgBox, 64, Info, MT4 Window Resized to 960x1036, 1 ; Auto-close msgbox

    } else {

        MsgBox, 48, Error, MT4 Terminal not found for resizing.

    }

return

; =====================================================

; [FIXED] Report Saving Logic

; =====================================================

GenerateLiveReport:

    ; [SAFETY] Prevent double-save (Debounce 10 seconds)

    if (A_TickCount - lastSaveTick < 10000) {

        FileAppend, [SKIP] GenerateLiveReport skipped (Debounce active)`n, %logFile%

        return

    }

    lastSaveTick := A_TickCount

    ; [FIXED] Click Report Tab & Save Action (Corrected Position)

    Sleep, 1000

    IniRead, rxReport, %iniFile%, coords, relx_report, 0.282

    IniRead, ryReport, %iniFile%, coords, rely_report, 0.925

    WinGetPos, wx, wy, ww, wh, ahk_class MetaQuotes::MetaTrader::4.00

    clickX := wx + (ww * rxReport)

    clickY := wy + (wh * ryReport)

    MouseClick, Left, %clickX%, %clickY%, 1, 0

    Sleep, 1000

    IniRead, rxRight, %iniFile%, coords, relx_rightclick, 0.355

    IniRead, ryRight, %iniFile%, coords, rely_rightclick, 0.725

    clickRX := wx + (ww * rxRight)

    clickRY := wy + (wh * ryRight)

    MouseClick, Right, %clickRX%, %clickRY%, 1, 0

    Sleep, 1000

    Send, s

    Sleep, 2000

    ; [FIX] 창 제목이 아닌 클래스(#32770)로 감지 - 한국어/영어 무관
    WinWaitActive, ahk_class #32770, , 4
    if (!ErrorLevel)
    {

        ; Construct explicit filename [ea-report-filename 스킬: MMddHHmm, 테스트기간, 중복+N]

        FormatTime, timestamp, , MMddHHmm

        ; Ensure Variables exist (fallback)

        if (eaName == "")

             eaName := "UnknownEA"

        if (symName == "")

             symName := "UnknownSym"

        if (tfName == "")

             tfName := "UnknownTF"



        ; Remove illegal chars just in case

        cleanEAName := RegExReplace(eaName, "[\\/:*?""<>|]", "")
        ; [ea-report-filename 스킬] .ex4 제거
        StringReplace, cleanEAName, cleanEAName, .ex4, , All



        ; [FIXED] Create EA Subfolder logic

        currentHtmlFolder := htmlSaveFolder . "\" cleanEAName

        IfNotExist, %currentHtmlFolder%

            FileCreateDir, %currentHtmlFolder%

        ; 테스트 기간 읽기 (INI)
        IniRead, glTestDateEnable, %iniFile%, test_date, enable, 0
        IniRead, glTestFromDate, %iniFile%, test_date, from_date,
        IniRead, glTestToDate, %iniFile%, test_date, to_date,
        glTestPeriodStr := ""
        if (glTestDateEnable = 1 && glTestFromDate != "" && glTestToDate != "") {
            glFromClean := StrReplace(glTestFromDate, ".", "")
            glToClean := StrReplace(glTestToDate, ".", "")
            glTestPeriodStr := glFromClean . "-" . glToClean
        }

        ; 파일명 조합
        baseHtmlName := cleanEAName . "_" . symName . "_" . tfName
        if (glTestPeriodStr != "")
            baseHtmlName .= "_" . glTestPeriodStr
        baseHtmlName .= "_" . timestamp

        ; 중복처리 (+1, +2 ...)
        finalHtmlName := baseHtmlName
        testCheckPath := currentHtmlFolder . "\" . finalHtmlName . ".htm"
        IfExist, %testCheckPath%
        {
            dupSuffix := 1
            Loop {
                finalHtmlName := baseHtmlName . "+" . dupSuffix
                testCheckPath := currentHtmlFolder . "\" . finalHtmlName . ".htm"
                IfNotExist, %testCheckPath%
                    break
                dupSuffix++
                if (dupSuffix > 99)
                    break
            }
        }

        targetName := currentHtmlFolder . "\" . finalHtmlName . ".htm"

        ; [FIX v6] 클립보드 방식 - WinActivate 없음 (IME 우회, 포커스 유지)
        Clipboard := targetName
        ClipWait, 2
        Sleep, 100
        Send, ^a
        Sleep, 100
        Send, ^v
        Sleep, 300
        Send, {Enter}
        Sleep, 1000

        ; 덮어쓰기 처리
        Loop, 5 {
            IfWinExist, ahk_class #32770
            {
                WinGetText, dlgText, ahk_class #32770
                if (InStr(dlgText, "이미") or InStr(dlgText, "already") or InStr(dlgText, "바꾸") or InStr(dlgText, "replace")) {
                    Send, {Enter}
                    Sleep, 200
                    break
                }
            }
            Sleep, 100
        }

        Sleep, 1000

    }

    Sleep, 1000

    ; Resume original logic if any

; =====================================================

; 도구

; =====================================================

OpenSetFolder:

    GuiControlGet, setFolder,, SetFolderEdit

    if (setFolder != "NOTSET" && setFolder != "") {

        StringReplace, setFolderWin, setFolder, /, \, All

        IfExist, %setFolderWin%

            Run, explorer.exe "%setFolderWin%"

        else

            MsgBox, 48, 오류, 폴더가 존재하지 않습니다.

    } else {

        MsgBox, 48, 오류, SET 폴더를 먼저 설정하세요.

    }

return

; =====================================================

; Settings 탭 클릭 (루프 복구용)

; =====================================================

ClickSettingsTab:

    IniRead, relx14, %iniFile%, coords, relx_settings, 0.060

    IniRead, rely14, %iniFile%, coords, rely_settings, 0.946

    

    WinGetPos, wx, wy, ww, wh, ahk_class MetaQuotes::MetaTrader::4.00

    

    clickX := wx + (ww * relx14)

    clickY := wy + (wh * rely14)

    

    ; [NC2.0] ControlClick NA - WinActivate 불필요
    ControlClick, x%clickX% y%clickY%, ahk_class MetaQuotes::MetaTrader::4.00,,,, NA

return

OpenTerminalFolder:

    GuiControlGet, terminalPath,, TerminalPathEdit

    if (terminalPath != "NOTSET" && terminalPath != "") {

        StringReplace, terminalPathWin, terminalPath, /, \, All

        IfExist, %terminalPathWin%

            Run, explorer.exe "%terminalPathWin%"

        else

            MsgBox, 48, 오류, 폴더가 존재하지 않습니다.

    } else {

        MsgBox, 48, 오류, 터미널 폴더를 먼저 설정하세요.

    }

return

OpenConfigFolder:

    Run, explorer.exe "%configsFolder%"

return

OpenScriptFolder:

    Run, explorer.exe "%scriptsFolder%"

return

CheckSettings:

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    msg := "╔══════════════════════════════════════════╗`n"

    msg .= "║         현재 설정 (상세)                 ║`n"

    msg .= "╚══════════════════════════════════════════╝`n`n"

    msg .= "📌 프로필: " currentProfile "`n`n"

    msg .= "📁 경로 설정:`n"

    msg .= "   터미널: " terminalPath "`n"

    msg .= "   SET: " setFolder "`n`n"

    ; SET 파일 개수

    setFileCount := 0

    if (setFolder != "NOTSET" && setFolder != "") {

        StringReplace, setFolderWin, setFolder, /, \, All

        IfExist, %setFolderWin%

        {

            Loop, %setFolderWin%\*.set

                setFileCount++

        }

    }

    msg .= "   SET 파일: " setFileCount "개`n`n"

    ; v3.7: 날짜 설정 표시 (10개 기간)

    msg .= "📅 테스트 기간 (v3.7):`n"

    Loop, 24 {

        idx := A_Index

        if (testDateEnable%idx% = 1) {

            fromD := testFromDate%idx%

            toD := testToDate%idx%

            msg .= "   [✓] 기간" . idx . ": " . fromD . " ~ " . toD . "`n"

        }

    }

    msg .= "`n"

    msg .= "📊 Symbol 설정:`n"

    if (sym1 != "")

        msg .= "   [" (sym1Chk ? "✓" : " ") "] Symbol 1: " sym1 "`n"

    if (sym2 != "")

        msg .= "   [" (sym2Chk ? "✓" : " ") "] Symbol 2: " sym2 "`n"

    if (sym3 != "")

        msg .= "   [" (sym3Chk ? "✓" : " ") "] Symbol 3: " sym3 "`n"

    if (sym4 != "")

        msg .= "   [" (sym4Chk ? "✓" : " ") "] Symbol 4: " sym4 "`n"

    if (sym5 != "")

        msg .= "   [" (sym5Chk ? "✓" : " ") "] Symbol 5: " sym5 "`n"

    msg .= "`n"

    msg .= "🤖 EA 선택:`n"

    msg .= "   [" (ea1 ? "✓" : " ") "] EA 1   "

    msg .= "[" (ea2 ? "✓" : " ") "] EA 2   "

    msg .= "[" (ea3 ? "✓" : " ") "] EA 3   "

    msg .= "[" (ea4 ? "✓" : " ") "] EA 4   "

    msg .= "[" (ea5 ? "✓" : " ") "] EA 5`n`n"

    msg .= "⏰ Timeframe 선택:`n"

    msg .= "   [" (tfM1 ? "✓" : " ") "] M1   "

    msg .= "[" (tfM5 ? "✓" : " ") "] M5   "

    msg .= "[" (tfM15 ? "✓" : " ") "] M15   "

    msg .= "[" (tfM30 ? "✓" : " ") "] M30   "

    msg .= "[" (tfH1 ? "✓" : " ") "] H1   "

    msg .= "[" (tfH4 ? "✓" : " ") "] H4`n`n"

    msg .= "💾 설정 파일: " iniFile

    MsgBox, 64, 설정 확인, %msg%

return

ViewLog:

    logFile := scriptsFolder . "\simple_loop_log.txt"

    IfExist, %logFile%

        Run, notepad.exe "%logFile%"

    else

        MsgBox, 48, 알림, 로그 파일이 없습니다.

return

CloseHTMLWindows:
    ; [nc2.3] 백테스트 관련 모든 분석 파일 닫기
    ; 대상: 브라우저(HTML) + Excel(CSV/XLS/XLSX)
    _totalClosed := 0
    SetTitleMatchMode, 2

    ; ── 1) 브라우저 닫기 (Chrome/Edge) ──────────────────────
    WinGet, _chw, List, ahk_class Chrome_WidgetWin_1
    Loop, %_chw% {
        _chwID := _chw%A_Index%
        WinGet, _chwProc, ProcessName, ahk_id %_chwID%
        if (htmlBrowserTarget = "chrome" && _chwProc != "chrome.exe")
            continue
        if (htmlBrowserTarget = "edge" && _chwProc != "msedge.exe")
            continue
        if (htmlBrowserTarget = "both" && _chwProc != "chrome.exe" && _chwProc != "msedge.exe")
            continue
        WinClose, ahk_id %_chwID%
        _totalClosed++
        Sleep, 80
    }

    ; ── 2) Excel 닫기 (CSV/XLS/XLSX - 백테스트 리포트 제목 기준) ──
    ; 대상 키워드: Full_Report / Summary_Report / Backtest / .csv / .xls
    _xlKeywords := ["Full_Report", "Summary_Report", "Backtest", ".csv", ".xls"]
    WinGet, _xlList, List, ahk_exe EXCEL.EXE
    Loop, %_xlList% {
        _xlID := _xlList%A_Index%
        WinGetTitle, _xlTitle, ahk_id %_xlID%
        _xlMatch := false
        for ki, kw in _xlKeywords {
            if InStr(_xlTitle, kw) {
                _xlMatch := true
                break
            }
        }
        if (!_xlMatch)
            continue
        ; WinClose 후 "저장 안 함(N)" 자동 처리
        WinClose, ahk_id %_xlID%
        Sleep, 600
        ; Excel 저장 확인 다이얼로그 처리 (저장 안 함)
        IfWinExist, ahk_exe EXCEL.EXE
        {
            WinActivate, ahk_exe EXCEL.EXE
            Sleep, 200
            Send, !n   ; Alt+N = 저장 안 함
            Sleep, 200
        }
        _totalClosed++
        Sleep, 100
    }

    ; ── 3) 카운터/GUI 갱신 ───────────────────────────────────
    htmlNewCount  := 0
    htmlOpenCount := 0
    GuiControl,, HtmlNewCountText, 0개
    htmlCloseCount++
    GuiControl,, HtmlCloseCountText, %htmlCloseCount%회
    FileAppend, [CLOSE ALL] 총 %_totalClosed%개 닫음 (브라우저+Excel)`n, %logFile%
return

ShowHelp:

    helpFile := A_ScriptDir . "\docs\빠른시작가이드_v2.0.txt"

    IfExist, %helpFile%

        Run, notepad.exe "%helpFile%"

    else {

        msg := "MT4 백테스트 자동화 v3.7 사용법`n`n"

        msg .= "[ v3.7 신규: 저장 경로 표시 ]`n"

        msg .= "- 각 경로 아래에 [저장됨] 표시로 실제 저장값 확인`n"

        msg .= "- 저장하고 새로고침: 저장 후 화면 즉시 갱신`n"

        msg .= "- Cleanup Manager 1.8 버튼 추가`n`n"

        msg .= "[ v3.5 테스트 기간 설정 ]`n"

        msg .= "- 날짜 범위 사용 체크박스로 ON/OFF`n"

        msg .= "- 시작일/종료일: YYYY.MM.DD 형식`n"

        msg .= "- 빠른 설정: 최근 1년/6개월/3개월/올해`n`n"

        msg .= "[ 컴퓨터 프로필 기능 ]`n"

        msg .= "- 새 이름 저장: 현재 설정을 새 프로필로 저장`n"

        msg .= "- 드롭다운: 저장된 프로필 선택 및 불러오기`n"

        msg .= "- 덮어쓰기: 선택된 프로필에 현재 설정 덮어쓰기`n"

        msg .= "- 프로필에 모든 경로/설정 저장됨`n`n"

        msg .= "[ 초기 설정 (새 컴퓨터) ]`n"

        msg .= "1. 🔍 자동 감지 클릭`n"

        msg .= "2. 1~3단계 초기 설정 실행`n"

        msg .= "3. 프로필 저장 (다른 PC에서 사용 가능)`n`n"

        msg .= "[ 백테스트 실행 ]`n"

        msg .= "- v1.45 Loop: SET 파일 + EA (순차)`n"

        msg .= "- v2.0 Loop: EA 기본값 (순차)`n"

        msg .= "- 통합 실행: v1.45 완료 후 v2.0 자동 실행 (창 유지됨)`n`n"

        msg .= "★ v3.7: 저장된 경로 표시 + Cleanup Manager"

        MsgBox, 64, 사용 가이드, %msg%

    }

return

; =====================================================

; v2.7 Solo (NEW/FIXED) 통합 실행

; =====================================================

RunLoopV27Solo:
    ; 먼저 설정 저장
    Gosub, SaveSettings
    Gosub, SaveDateSettings
    
    ; [FIX] Reset timer and pause state for fresh start (if not resuming)
    if (!isResuming) {
        isPaused := false
        isStopped := false
        startTime := A_TickCount
    }
    
    ; Load EAs (History will be loaded after confirmation check)
    Gosub, LoadSelectedEAs

    

    if (activeEACount == 0) {

        MsgBox, 48, 오류, 선택된 EA가 없습니다.`nEA 폴더를 확인하거나 EA를 선택하세요.

        return

    }

    

    ; [AUTO] 확인 MsgBox 제거 - 즉시 시작
    
    ; [OPTIMIZED] 시작 지연 원인인 전체 스캔 제거 (루프 내부에서 개별 확인하도록 변경)
    ; Gosub, LoadCompletedTests
    completedTests := {} ; 초기화만 수행
    noTradeCounter := {} ; [NO_TRADE SKIP] EA별 심볼 0거래 카운터 초기화
    ; [중간분석] nextAnalyzeAt 초기화
    if (analyzeInterval > 0)
        nextAnalyzeAt := analyzeInterval
    else
        nextAnalyzeAt := 0

    

    ; Enable/Disable Buttons

    GuiControl, Enable, BtnPause

    GuiControl, Enable, BtnStop

    GuiControl, Disable, BtnResume

    

    ; Show status

    ; v1.19: totalTests 계산 로직 구문 오류 수정
    symCount := 0
    Loop, 10 {
        if (sym%A_Index%Chk == 1 && sym%A_Index% != "")
            symCount++
    }
    tfCount := 0
    if (tfM1) 
        tfCount++
    if (tfM5) 
        tfCount++
    if (tfM15) 
        tfCount++
    if (tfM30) 
        tfCount++
    if (tfH1) 
        tfCount++
    if (tfH4) 
        tfCount++
    periodCount := 0
    Loop, 24 {
        if (testDateEnable%A_Index% == 1)
            periodCount++
    }
    totalTests := activeEACount * symCount * tfCount * periodCount

    SetTimer, TimerUpdate, 1000
    ; [Option A/B] 루프 순서에 따라 분기
    IniRead, loopOrder, %iniFile%, settings, loop_order, A
    if (loopOrder = "B") {
        Gosub, MainLoopOptionB
    } else {
        Gosub, MainLoop
    }
return

RunMasterLoop:

    ; 먼저 설정 저장

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    scriptPath := scriptsFolder . "\MASTER_RUN.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 통합 실행 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

CheckHistory:

    Gosub, SaveSettings

    scriptPath := scriptsFolder . "\CHECK_HISTORY.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 히스토리 확인 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

RunCollectReports:

    Gosub, SaveSettings

    scriptPath := scriptsFolder . "\COLLECT_REPORTS.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 리포트 모으기 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

; (Old RunCleanupManager removed)

RunBacktestAnalyzer:

    Gosub, SaveSettings

    ; v3.3: Python 라이브러리 자동 설치 버전 우선 실행

    scriptPath := scriptsFolder . "\BACKTEST_ANALYZER_v3.3.ahk"

    IfExist, %scriptPath%

    {

        Run, "%A_AhkPath%" "%scriptPath%"

        return

    }

    scriptPath := scriptsFolder . "\BACKTEST_ANALYZER_v1.4.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else {

        ; v1.4 없으면 기존 버전 시도

        scriptPath := scriptsFolder . "\BACKTEST_ANALYZER.ahk"

        IfExist, %scriptPath%

            Run, "%A_AhkPath%" "%scriptPath%"

        else

            MsgBox, 48, 오류, 백테스트 분석기 스크립트를 찾을 수 없습니다:`n%scriptPath%

    }

return

RunPythonAnalyzer:

    ; 리포트 폴더 경로 읽기

    GuiControlGet, reportFolder,, HtmlSavePathEdit

    ; 분석기 스크립트 경로 (v4.1 우선)

    analyzerScript := A_ScriptDir . "\MT4_Report_Analyzer_v4_1.py"

    IfExist, %analyzerScript%

    {

        if (reportFolder != "" && reportFolder != "NOTSET") {

            StringReplace, reportFolderWin, reportFolder, /, \, All

            Run, python "%analyzerScript%" "%reportFolderWin%"

        } else {

            Run, python "%analyzerScript%"

        }

        return

    }

    ; scripts 폴더에서 찾기

    analyzerScript2 := scriptsFolder . "\MT4_Report_Analyzer.py"

    IfExist, %analyzerScript2%

    {

        if (reportFolder != "" && reportFolder != "NOTSET") {

            StringReplace, reportFolderWin, reportFolder, /, \, All

            Run, python "%analyzerScript2%" "%reportFolderWin%"

        } else {

            Run, python "%analyzerScript2%"

        }

        return

    }

    MsgBox, 48, 오류, Python 분석기를 찾을 수 없습니다.`n`n다음 경로를 확인하세요:`n- %analyzerScript%`n- %analyzerScript2%

return

; =====================================================

; v3.6: 간단 보고서 생성 (HTML 파일 분석)

; =====================================================

GenerateQuickReport:

    IniRead, htmlSavePath, %iniFile%, folders, html_save_path, NOTSET

    if (htmlSavePath = "NOTSET" || htmlSavePath = "") {

        MsgBox, 48, 오류, 리포트 폴더가 설정되지 않았습니다.

        return

    }

    StringReplace, htmlSavePathWin, htmlSavePath, /, \, All

    IfNotExist, %htmlSavePathWin%

    {

        MsgBox, 48, 오류, 리포트 폴더가 존재하지 않습니다:`n%htmlSavePathWin%

        return

    }

    ; 분석 시작

    totalReports := 0

    profitReports := 0

    lossReports := 0

    noTradeReports := 0

    totalProfit := 0

    totalLoss := 0

    maxDD := 0

    highDDCount := 0

    Loop, %htmlSavePathWin%\*.htm

    {

        totalReports++

        FileRead, content, %A_LoopFileLongPath%

        if (ErrorLevel)

            continue

        ; Check for trades

        trades := 0

        ; Korean pattern

        if (RegExMatch(content, "<td>[^<]*</td><td align=right>(\d+)</td><td>[^<]*\(won\s*%\)", korMatch)) {

            trades := korMatch1

        }

        ; English pattern

        else if (RegExMatch(content, "i)Total Trades.*?<[^>]*>\s*(\d+)", trMatch)) {

            trades := trMatch1

        }

        if (trades = 0 || trades = "") {

            noTradeReports++

            continue

        }

        ; Get profit

        profit := 0

        ; Korean pattern

        if (RegExMatch(content, "<td align=right>(-?[\d\.]+)</td><td>[^<]*</td><td align=right>[\d\.]+</td><td>[^<]*</td><td align=right>-[\d\.]+</td></tr>", korProfit)) {

            profit := korProfit1

        }

        ; English pattern

        else if (RegExMatch(content, "i)Total Net Profit.*?<[^>]*>\s*(-?[\d,\.]+)", profMatch)) {

            profit := StrReplace(profMatch1, ",", "")

        }

        if (profit + 0 > 0) {

            profitReports++

            totalProfit += profit

        } else if (profit + 0 < 0) {

            lossReports++

            totalLoss += profit

        }

        ; Get drawdown

        dd := 0

        ; Korean pattern

        if (RegExMatch(content, "<td align=right>(\d+\.?\d*)%\s*\([\d\.]+\)</td>", korDD)) {

            dd := korDD1

        }

        ; English pattern

        else if (RegExMatch(content, "i)Maximal Drawdown.*?(\d+\.?\d*)\s*\((\d+\.?\d*)%\)", ddMatch)) {

            dd := ddMatch2

        } else if (RegExMatch(content, "i)Relative Drawdown.*?(\d+\.?\d*)%", ddMatch2)) {

            dd := ddMatch2_1

        }

        if (dd + 0 > maxDD)

            maxDD := dd

        if (dd + 0 > 20)

            highDDCount++

    }

    ; Generate report

    FormatTime, currentTime, , yyyy-MM-dd HH:mm:ss

    netProfit := totalProfit + totalLoss

    report := "╔══════════════════════════════════════════════════╗`n"

    report .= "║     MT4 백테스트 간단 보고서 (v3.7)              ║`n"

    report .= "╚══════════════════════════════════════════════════╝`n`n"

    report .= "생성 시간: " . currentTime . "`n"

    report .= "분석 폴더: " . htmlSavePathWin . "`n`n"

    report .= "────────────────────────────────────────────────────`n"

    report .= "  📊 총 분석 리포트: " . totalReports . "개`n"

    report .= "────────────────────────────────────────────────────`n`n"

    report .= "  ✅ 수익 리포트: " . profitReports . "개`n"

    report .= "  ❌ 손실 리포트: " . lossReports . "개`n"

    report .= "  ⚪ 거래없음: " . noTradeReports . "개`n`n"

    report .= "────────────────────────────────────────────────────`n"

    report .= "  💰 총 수익 합계: $" . Format("{:+.2f}", totalProfit) . "`n"

    report .= "  💸 총 손실 합계: $" . Format("{:.2f}", totalLoss) . "`n"

    report .= "  📈 순이익: $" . Format("{:+.2f}", netProfit) . "`n"

    report .= "────────────────────────────────────────────────────`n`n"

    report .= "  📉 최대 DD: " . maxDD . "%`n"

    report .= "  ⚠️ 고위험 DD (>20%): " . highDDCount . "개`n`n"

    if (totalReports > 0) {

        winRate := Round((profitReports / (profitReports + lossReports)) * 100, 1)

        report .= "  🎯 승률: " . winRate . "% (" . profitReports . "/" . (profitReports + lossReports) . ")`n"

    }

    report .= "`n════════════════════════════════════════════════════`n"

    ; Save report file

    FormatTime, fileDate, , yyyyMMdd_HHmmss

    reportFile := htmlSavePathWin . "\QUICK_REPORT_" . fileDate . ".txt"

    FileDelete, %reportFile%

    FileAppend, %report%, %reportFile%, UTF-8

    MsgBox, 64, 간단 보고서, %report%`n`n보고서 저장: %reportFile%

return

OpenReportsFolder:

    IniRead, termPath, %iniFile%, folders, terminal_path, NOTSET

    if (termPath != "NOTSET" && termPath != "") {

        StringReplace, termPathWin, termPath, /, \, All

        reportsPath := termPathWin . "\templates"

        IfExist, %reportsPath%

            Run, explorer.exe "%reportsPath%"

        else

            MsgBox, 48, 알림, templates 폴더를 찾을 수 없습니다.

    } else {

        MsgBox, 48, 알림, 터미널 경로가 설정되지 않았습니다.

    }

return

OpenHistoryCenter:

    scriptPath := scriptsFolder . "\AUTO_DOWNLOAD.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, 자동 다운로드 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

ExitApp:

    ExitApp

return

; =====================================================

; 계정번호 저장/감지 (v3.6)

; =====================================================

SaveAccountNum:

    GuiControlGet, newAccountNum,, AccountNumEdit

    if (newAccountNum != "") {

        IniWrite, %newAccountNum%, %iniFile%, account, number

        MsgBox, 64, 저장 완료, 계정번호가 저장되었습니다: %newAccountNum%

    }

return

DetectAccountNum:

    ; MT4 터미널 창에서 계정번호 감지 시도

    detectedAccount := ""

    debugInfo := ""

    ; 방법 1: terminal.exe 프로세스 창 찾기 (가장 정확함)

    WinGet, terminalList, List, ahk_exe terminal.exe

    Loop, %terminalList%

    {

        thisWin := terminalList%A_Index%

        WinGetTitle, termTitle, ahk_id %thisWin%

        WinGetClass, termClass, ahk_id %thisWin%

        ; 대화상자 제외, 메인 창만 처리

        if (termClass = "#32770")

            continue

        if (StrLen(termTitle) < 10)

            continue

        debugInfo .= "terminal.exe: " . termTitle . "`n"

        ; 패턴1: "브로커명 - 계정번호" 형식 (가장 일반적)

        if (RegExMatch(termTitle, "\s*[-:]\s*(\d{6,12})", accMatch)) {

            detectedAccount := accMatch1

            debugInfo .= "Pattern1 matched: " . detectedAccount . "`n"

            break

        }

        ; 패턴2: "계정번호 : 브로커명" 형식

        if (RegExMatch(termTitle, "^(\d{6,12})\s*[-:]", accMatch2)) {

            detectedAccount := accMatch21

            debugInfo .= "Pattern2 matched: " . detectedAccount . "`n"

            break

        }

        ; 패턴3: 창 제목 끝에 있는 숫자 (fallback)

        if (RegExMatch(termTitle, "(\d{8,12})$", accMatch3)) {

            detectedAccount := accMatch31

            debugInfo .= "Pattern3 matched: " . detectedAccount . "`n"

            break

        }

    }

    ; 방법 2: 클래스명으로 찾기

    if (detectedAccount = "") {

        ; 다양한 MT4 클래스명 시도

        classNames := ["MetaQuotes::MetaTrader::4.00", "MetaTrader 4", "Afx:400000:0"]

        for idx, className in classNames {

            WinGetTitle, mt4Title, ahk_class %className%

            if (mt4Title != "" && StrLen(mt4Title) > 10) {

                debugInfo .= "Class " . className . ": " . mt4Title . "`n"

                ; 동일한 패턴 적용

                if (RegExMatch(mt4Title, "\s*[-:]\s*(\d{6,12})", accMatch4)) {

                    detectedAccount := accMatch41

                    break

                } else if (RegExMatch(mt4Title, "^(\d{6,12})\s*[-:]", accMatch5)) {

                    detectedAccount := accMatch51

                    break

                }

            }

        }

    }

    ; 방법 3: 모든 창 제목에서 MetaTrader 찾기 (fallback)

    if (detectedAccount = "") {

        WinGet, winList, List

        Loop, %winList%

        {

            thisWin := winList%A_Index%

            WinGetTitle, winTitle, ahk_id %thisWin%

            WinGetClass, winClass, ahk_id %thisWin%

            ; 대화상자 제외

            if (winClass = "#32770")

                continue

            ; MetaTrader 창 찾기

            if (InStr(winTitle, "MetaTrader") || InStr(winTitle, "MT4")) {

                if (StrLen(winTitle) < 10)

                    continue

                debugInfo .= "Found: " . winTitle . "`n"

                ; 제목에서 계정번호 추출 (- 또는 : 뒤의 숫자)

                if (RegExMatch(winTitle, "\s*[-:]\s*(\d{6,12})", accMatch6)) {

                    detectedAccount := accMatch61

                    break

                }

            }

        }

    }

    ; 방법 4: 터미널 폴더의 logs에서 추출 시도

    if (detectedAccount = "" && terminalPath != "NOTSET" && terminalPath != "") {

        StringReplace, termPathWin, terminalPath, /, \, All

        logsFolder := termPathWin . "\logs"

        ; 최신 로그 파일 찾기

        latestLog := ""

        latestTime := 0

        Loop, %logsFolder%\*.log

        {

            FileGetTime, modTime, %A_LoopFileLongPath%

            if (modTime > latestTime) {

                latestTime := modTime

                latestLog := A_LoopFileLongPath

            }

        }

        if (latestLog != "") {

            FileRead, logContent, %latestLog%

            debugInfo .= "Log file: " . latestLog . "`n"

            ; 로그에서 계정번호 패턴 찾기

            if (RegExMatch(logContent, "i)'(\d{6,12})'", logMatch)) {

                detectedAccount := logMatch1

            } else if (RegExMatch(logContent, "i)(account|login)\s*[:#=]?\s*(\d{6,12})", logMatch2)) {

                detectedAccount := logMatch2_2

            } else if (RegExMatch(logContent, "authorized\s+(\d{6,12})", logMatch3)) {

                detectedAccount := logMatch3_1

            }

        }

    }

    if (detectedAccount != "") {

        GuiControl,, AccountNumEdit, %detectedAccount%

        IniWrite, %detectedAccount%, %iniFile%, account, number

        msgTimeout := autoDetectBootMode ? 1 : 0
        MsgBox, 64, 감지 성공, 계정번호를 감지했습니다: %detectedAccount%, %msgTimeout%

    } else {

        msgTimeout := autoDetectBootMode ? 1 : 0
        MsgBox, 48, 감지 실패, MT4 터미널에서 계정번호를 자동으로 감지할 수 없습니다.`n`n디버그 정보:`n%debugInfo%`n`n다음 방법을 시도하세요:`n1. MT4 터미널 창 제목에 계정번호가 보이는지 확인`n2. 계정번호를 직접 입력 후 저장, %msgTimeout%

    }

return

; =====================================================

; 창 위치 고정 기능 (v3.6)

; =====================================================

ToggleWindowLock:

    global isWindowLocked, savedWinX, savedWinY, iniFile

    isWindowLocked := !isWindowLocked

    if (isWindowLocked) {

        ; 현재 위치 저장

        WinGetPos, curX, curY, , , A

        savedWinX := curX

        savedWinY := curY

        IniWrite, %savedWinX%, %iniFile%, window, pos_x

        IniWrite, %savedWinY%, %iniFile%, window, pos_y

        IniWrite, 1, %iniFile%, window, locked

        GuiControl,, BtnLock, 🔓 고정 해제

        SetTimer, EnforceWindowPosition, 100

    } else {

        IniWrite, 0, %iniFile%, window, locked

        GuiControl,, BtnLock, 🔒 위치 고정

        SetTimer, EnforceWindowPosition, Off
    }
return

ToggleAlwaysOnTop:
    global isAlwaysOnTop
    isAlwaysOnTop := !isAlwaysOnTop
    if (isAlwaysOnTop) {
        Gui, +AlwaysOnTop
        GuiControl,, ToggleAlwaysOnTop, 🔝 상단고정ON
    } else {
        Gui, -AlwaysOnTop
        GuiControl,, ToggleAlwaysOnTop, 🔝 상단고정OFF
    }
return

SaveWindowPos:

    global savedWinX, savedWinY, iniFile

    WinGetPos, curX, curY, , , A

    savedWinX := curX

    savedWinY := curY

    IniWrite, %savedWinX%, %iniFile%, window, pos_x

    IniWrite, %savedWinY%, %iniFile%, window, pos_y

    MsgBox, 64, 위치 저장, 현재 창 위치가 저장되었습니다.`n`nX: %savedWinX%`nY: %savedWinY%

return

; =====================================================

; v3.7: 창 크기 조정 기능

; =====================================================

SetWindowSmall:

    Gui, Show, w850 h900 ; Laptop/FHD Mode

    global windowHeight := 900

    SetScrollRange()

return

SetWindowMedium:

    Gui, Show, w850 h1600 ; 4K Window Mode

    global windowHeight := 1600

    SetScrollRange()

return

SetWindowLarge:

    Gui, Show, w850 h2150 ; 4K Full Height

    global windowHeight := 2150

    SetScrollRange()

return

EnforceWindowPosition:
    global savedWinX, savedWinY, isWindowLocked
    if (!isWindowLocked)
        return
    
    ; 현재 창의 핸들(ID)을 사용하여 보다 안정적으로 제어
    Gui, +LastFound
    this_id := WinExist()
    
    WinGetPos, curX, curY, , , ahk_id %this_id%
    if (curX != savedWinX || curY != savedWinY) {
        WinMove, ahk_id %this_id%, , %savedWinX%, %savedWinY%
    }
return

FixMT4Window:

    WinGet, wins, List

    mt4Found := 0

    Loop, %wins% {
        id := wins%A_Index%
        WinGet, proc, ProcessName, ahk_id %id%
        if (proc = "terminal.exe") {
            WinGetTitle, mt4Title, ahk_id %id%
            if (mt4Title != "" && !InStr(mt4Title, "Tester")) {
                WinMove, ahk_id %id%, , 0, 0, 960, 1036
                mt4Found := 1
                break
            }
        }
    }

    if (mt4Found)
        MsgBox, 64, 완료, MT4 창 크기를 고정했습니다.`n(0, 0) - 960x1036
    else
        MsgBox, 48, 오류, MT4 창을 찾을 수 없습니다.
return

return

GuiClose:

    ExitApp

return

; =====================================================

; 스크롤 핸들러 (WM_VSCROLL)

; =====================================================

OnVScroll(wParam, lParam, msg, hwnd) {

    global scrollY, scrollHeight, windowHeight, guiHwnd

    if (hwnd != guiHwnd)

        return

    scrollCode := wParam & 0xFFFF

    ; SB_LINEUP=0, SB_LINEDOWN=1, SB_PAGEUP=2, SB_PAGEDOWN=3, SB_THUMBTRACK=5

    step := 20

    page := windowHeight

    newY := scrollY

    if (scrollCode = 0) ; LINEUP

        newY -= step

    else if (scrollCode = 1) ; LINEDOWN

        newY += step

    else if (scrollCode = 2) ; PAGEUP

        newY -= page

    else if (scrollCode = 3) ; PAGEDOWN

        newY += page

    else if (scrollCode = 5) { ; THUMBTRACK

        newY := (wParam >> 16) & 0xFFFF

        ; 16비트 제한으로 인해 32비트 값 얻기 위해 GetScrollInfo 필요할 수 있음

    }

    UpdateScroll(newY)

    return 0

}

OnMouseWheel(wParam, lParam, msg, hwnd) {

    global scrollY

    delta := (wParam >> 16)

    ; 휠 올리면 delta > 0 -> 위로 스크롤 (Y 감소)

    ; 휠 내리면 delta < 0 -> 아래로 스크롤 (Y 증가)

    step := 40

    newY := scrollY - (delta / 120) * step

    UpdateScroll(newY)

    return 0

}

UpdateScroll(newPos) {

    global scrollY, scrollHeight, windowHeight, guiHwnd

    ; 범위 제한

    maxScroll := scrollHeight - windowHeight

    if (maxScroll < 0)

        maxScroll := 0

    if (newPos < 0)

        newPos := 0

    if (newPos > maxScroll)

        newPos := maxScroll

    if (newPos = scrollY)

        return

    deltaY := scrollY - newPos

    scrollY := newPos

    ; 스크롤바 위치 업데이트

    VarSetCapacity(si, 28, 0)

    NumPut(28, si, 0, "UInt") ; cbSize

    NumPut(0x4, si, 4, "UInt") ; fMask = SIF_POS

    NumPut(newPos, si, 20, "Int") ; nPos

    DllCall("SetScrollInfo", "Ptr", guiHwnd, "Int", 1, "Ptr", &si, "Int", 1) ; SB_VERT=1

    ; 윈도우 내용 스크롤 (ScrollWindow)

    DllCall("ScrollWindow", "Ptr", guiHwnd, "Int", 0, "Int", deltaY, "Ptr", 0, "Ptr", 0)

}

SetScrollRange() {

    global scrollHeight, windowHeight, guiHwnd

    ; 전체 높이 계산 (마지막 컨트롤 위치 기반)

    lastY := 0

    WinGet, ctrlList, ControlList, ahk_id %guiHwnd%

    Loop, Parse, ctrlList, `n

    {

        ControlGetPos, cx, cy, cw, ch, %A_LoopField%, ahk_id %guiHwnd%

        if (cy + ch > lastY)

            lastY := cy + ch

    }

    scrollHeight := lastY + 50 ; 여유 공간

    VarSetCapacity(si, 28, 0)

    NumPut(28, si, 0, "UInt") ; cbSize

    NumPut(0x1 | 0x2, si, 4, "UInt") ; fMask = SIF_RANGE | SIF_PAGE

    NumPut(0, si, 8, "Int") ; nMin

    NumPut(scrollHeight, si, 12, "Int") ; nMax

    NumPut(windowHeight, si, 16, "UInt") ; nPage

    DllCall("SetScrollInfo", "Ptr", guiHwnd, "Int", 1, "Ptr", &si, "Int", 1) ; SB_VERT=1

}

RestartApp:

    Reload

return

; =====================================================

; v2.7: EA 이동 함수 (129번 에러 방지 포함)

; =====================================================

MoveCurrentEA:

    FileAppend, [MoveCurrentEA] Attempting to move: %currentEAFile%`n, %logFile%

    ; 1. NOTRADELIVE 폴더 확인 및 생성

    notradeFolder := eaFolder . "\NOTRADELIVE"

    IfNotExist, %notradeFolder%

        FileCreateDir, %notradeFolder%

    ; 2. 원본 및 대상 경로 설정

    sourcePath := eaFolder . "\" . currentEAFile

    destPath := notradeFolder . "\" . currentEAFile

    ; 3. 파일 존재 확인

    IfNotExist, %sourcePath%

    {

        FileAppend, [MoveCurrentEA] Source file not found: %sourcePath%`n, %logFile%

        return

    }

    ; 4. 파일 이동 (FileMove)

    FileMove, %sourcePath%, %destPath%, 1 ; 1=Overwrite

    if (ErrorLevel) {

        FileAppend, [MoveCurrentEA] FileMove failed (ErrorLevel: %ErrorLevel%)`n, %logFile%

        

        ; 4-1. 실패 시 재시도 (잠시 대기 후)

        Sleep, 500

        FileMove, %sourcePath%, %destPath%, 1

        if (ErrorLevel) {

             FileAppend, [MoveCurrentEA] Retry failed.`n, %logFile%

        } else {

             FileAppend, [MoveCurrentEA] Moved successfully on retry.`n, %logFile%

        }

    } else {

        FileAppend, [MoveCurrentEA] Moved successfully.`n, %logFile%

    }

return

; =====================================================

; v3.9: 프리셋 목록 읽기 함수

; =====================================================

GetPresetList() {

    global configsFolder

    

    ; 기본 리스트

    baseList := "권장6개|권장8개"

    

    presetFile := configsFolder . "\date_presets.ini"

    

    ; 섹션 목록 읽기 (AHK v1.1+)

    IniRead, sections, %presetFile%

    

    if (sections != "ERROR" && sections != "") {

        Loop, Parse, sections, `n, `r

        {

            ; 기본값과 중복되지 않게 추가

            if (A_LoopField != "권장6개" && A_LoopField != "권장8개" && A_LoopField != "")

                baseList .= "|" . A_LoopField

        }

    }

    

    return baseList

}

#Include %A_ScriptDir%\scripts\SOLO_V36_MODULE_FINAL.ahk

; =====================================================
; [v8.0] Worker 서버 연동 핸들러
; =====================================================

StartWorkerSync:
    Gui, Submit, NoHide
    masterIP := MasterIPEdit
    workerID := WorkerIDEdit
    IniWrite, %masterIP%, %iniFile%, worker, master_ip
    IniWrite, %workerID%, %iniFile%, worker, worker_id
    workerScript := scriptsFolder . "\integrated_solo_worker_v7.1.py"
    if !FileExist(workerScript) {
        MsgBox, 16, 오류, integrated_solo_worker_v7.1.py를 찾을 수 없습니다.`n%workerScript%
        return
    }
    pcName := A_ComputerName
    serverURL := "http://" . masterIP . ":9001"
    Run, %pythonExePath% "%workerScript%" --worker-id %workerID% --worker-name "%pcName%" --server %serverURL% --max-iterations 100, , , workerPID
    if (workerPID > 0) {
        workerConnected := true
        Gui, Font, s14 cGreen Bold
        GuiControl, Font, WorkerStatusDot
        GuiControl,, WorkerStatusDot, ●
        Gui, Font, s9 cGreen Bold
        GuiControl, Font, WorkerStatusText
        GuiControl,, WorkerStatusText, 연동 중 (PID: %workerPID%)
        GuiControl, Font, OptLoopStatus
        GuiControl,, OptLoopStatus, ✅ Worker 연동 시작됨 - 서버: %serverURL%
        Gui, Font, s9 Normal cDefault
    }
return

StopWorkerSync:
    Gosub, ForceStopBacktest
    if (workerPID > 0) {
        Process, Close, %workerPID%
        workerPID := 0
    }
    workerConnected := false
    Gui, Font, s14 cRed Bold
    GuiControl, Font, WorkerStatusDot
    GuiControl,, WorkerStatusDot, ●
    Gui, Font, s9 cRed Bold
    GuiControl, Font, WorkerStatusText
    GuiControl,, WorkerStatusText, 연결 안됨
    Gui, Font, s9 Normal cDefault
    GuiControl,, OptLoopStatus, 🛑 백테스트 강제 중지됨
return

CheckServerStatus:
    Gui, Submit, NoHide
    masterIP := MasterIPEdit
    serverURL := "http://" . masterIP . ":9001/status"
    try {
        whr := ComObjCreate("WinHttp.WinHttpRequest.5.1")
        whr.Open("GET", serverURL, false)
        whr.SetTimeouts(3000, 3000, 3000, 3000)
        whr.Send()
        whrStatus := whr.Status
        whrBody := whr.ResponseText
        if (whrStatus = 200) {
            GuiControl,, WorkerStatusText, 서버 응답 OK
            GuiControl,, OptLoopStatus, 서버 연결 확인: %serverURL%
            MsgBox, 64, 서버 상태, 서버 연결 성공!`nURL: %serverURL%`n응답: %whrBody%, 3
        } else {
            MsgBox, 48, 서버 상태, 서버 응답 오류: %whrStatus%, 3
        }
    } catch e {
        eMsg := e.Message
        GuiControl,, WorkerStatusText, 서버 연결 실패
        MsgBox, 16, 서버 상태, 연결 실패`nURL: %serverURL%`n오류: %eMsg%
    }
return

StartOptLoop:
    Gui, Submit, NoHide
    masterIP := MasterIPEdit
    workerID := WorkerIDEdit
    workerScript := scriptsFolder . "\integrated_solo_worker_v7.1.py"
    if !FileExist(workerScript) {
        MsgBox, 16, 오류, integrated_solo_worker_v7.1.py를 찾을 수 없습니다.
        return
    }
    pcName := A_ComputerName
    serverURL := "http://" . masterIP . ":9001"
    Run, %pythonExePath% "%workerScript%" --worker-id %workerID% --worker-name "%pcName%" --server %serverURL% --max-iterations 9999, , , workerPID
    if (workerPID > 0) {
        workerConnected := true
        GuiControl,, WorkerStatusDot, ●
        GuiControl, +cGreen, WorkerStatusDot
        GuiControl,, WorkerStatusText, 최적화 루프 실행 중
        GuiControl,, OptLoopStatus, 🔄 최적화 무한 루프 실행 중
        GuiControl,, BtnOptLoop, 🔄 최적화 루프 실행 중...
        GuiControl, +Disabled, BtnOptLoop
    }
return

StopOptLoop:
    Gosub, ForceStopBacktest
    if (workerPID > 0) {
        Process, Close, %workerPID%
        workerPID := 0
    }
    workerConnected := false
    Gui, Font, s14 cRed Bold
    GuiControl, Font, WorkerStatusDot
    GuiControl,, WorkerStatusDot, ●
    Gui, Font, s9 cRed Bold
    GuiControl, Font, WorkerStatusText
    GuiControl,, WorkerStatusText, 연결 안됨
    Gui, Font, s9 Normal cDefault
    GuiControl,, OptLoopStatus, 🛑 백테스트 강제 중지됨
    GuiControl,, BtnOptLoop, 🔄 최적화 자동 루프 시작 (서버↔백테스트↔분석↔반복)
    GuiControl, -Disabled, BtnOptLoop
return

; =====================================================
; [v8.0] 백테스트 강제 중지 (CheckAutoTriggerCommand 정지 + AHK + MT4 중지)
; =====================================================
ForceStopBacktest:
    ; 1. IPC 타이머 OFF (새 command.json 처리 중단)
    SetTimer, CheckAutoTriggerCommand, Off

    ; 2. 실행 중인 SIMPLE_4STEPS AutoHotkey 프로세스 강제 종료
    RunWait, %ComSpec% /c "taskkill /IM AutoHotkey.exe /F >nul 2>&1",, Hide

    ; 3. command.json / command_processing.json 삭제 (대기 중인 명령 제거)
    FileDelete, %configsFolder%\command.json
    FileDelete, %configsFolder%\command_processing.json

    ; 4. MT4 Strategy Tester 중지 - Ctrl+R 제거 (v7.7)

    ; 5. status.json을 stopped로 업데이트
    statusFile := configsFolder . "\status.json"
    FormatTime, stopTime,, HH:mm:ss
    statusContent = {"status": "stopped", "message": "Force stopped by user", "timestamp": "%A_Now%"}
    FileDelete, %statusFile%
    FileAppend, %statusContent%, %statusFile%

    ; 6. IPC 타이머 재시작 (다음 명령 수신 대기)
    SetTimer, CheckAutoTriggerCommand, 1000

    GuiControl,, StatusText, 상태: 강제 중지됨 (대기 중)

    FormatTime, logTime,, HH:mm:ss
    FileAppend, [%logTime%] ForceStopBacktest executed by user`n, %scriptsFolder%\solo_remote_log.txt
return

; [v8.0] 스크롤 바로가기
ScrollToTop:
    UpdateScroll(0)
    ToolTip, 상단으로 이동했습니다!
    SetTimer, ClearToolTip, 1500
return

ScrollToBottom:
    UpdateScroll(999999)
    ToolTip, 하단으로 이동했습니다!
    SetTimer, ClearToolTip, 1500
return

ClearToolTip:
    ToolTip
    SetTimer, ClearToolTip, Off
return

; [v8.0] IP 자동 감지
DetectMyIP:
    try {
        RunWait, %ComSpec% /c "ipconfig > ""%A_Temp%\ipconfig_out.txt""", , Hide
        FileRead, output, %A_Temp%\ipconfig_out.txt
        if RegExMatch(output, "100\.\d+\.\d+\.\d+", virtualIP) {
            GuiControl,, MyIPText, 내 IP: %virtualIP% (Virtual)
        } else if RegExMatch(output, "192\.168\.\d+\.\d+", localIP) {
            GuiControl,, MyIPText, 내 IP: %localIP% (Local)
        } else {
            GuiControl,, MyIPText, 내 IP: 감지 실패
        }
    } catch {
        GuiControl,, MyIPText, 내 IP: 감지 실패
    }
return

; v3.9: 설정 즉시 버리기/불러오기 (Sync)

; (LoadAllSettings moved to SOLO_V36_MODULE.ahk)

ReloadSettingsV39:

    ; INI에서 다시 읽어오기

    Gosub, LoadAllSettings

    

    ; GUI 업데이트 (로드된 변수값 -> GUI 컨트롤)

    ; LoadAllSettings 내부에서 GUI Update를 하지 않는다면 여기서 해줘야 함.

    ; SOLO_ALL_IN_ONE 구조상 변수만 로드될 수 있음.

    

    ; 날짜 설정 체크박스 업데이트

    Loop, 24 {

        GuiControl,, TestDateChk%A_Index%, % testDateEnable%A_Index%

        GuiControl,, TestFromDT%A_Index%, % testFromDate%A_Index%

        GuiControl,, TestToDT%A_Index%, % testToDate%A_Index%

    }

    

    ; EA 선택 업데이트 (변수가 있다면)

    ; 보통 EA 선택은 LoadSelectedEAs 호출 시점에 로드됨.

    

    msgTimeout := autoDetectBootMode ? 1 : 0
    MsgBox, 64, 설정 로드, CONFIG 파일에서 설정을 새로 불러왔습니다., %msgTimeout%

return

; =====================================================

; [v1.5] 마지막 세션 환경 비교

; =====================================================

CheckLastSession:
    IniRead, _lastPC,     %iniFile%, last_session, pc_name,
    IniRead, _lastFolder, %iniFile%, last_session, work_folder,
    IniRead, _lastEA,     %iniFile%, last_session, ea_path,
    IniRead, _lastTerm,   %iniFile%, last_session, terminal_path,
    IniRead, _lastTime,   %iniFile%, last_session, saved_time,

    ; 저장된 세션 없으면 스킵
    if (_lastPC = "" || _lastPC = "ERROR")
        return

    ; 현재 환경과 비교
    IniRead, _curFolder,  %iniFile%, folders, work_folder,   %A_ScriptDir%
    IniRead, _curEA,      %iniFile%, folders, ea_path,
    IniRead, _curTerm,    %iniFile%, folders, terminal_path,

    samePC     := (_lastPC     = A_ComputerName)
    sameFolder := (_lastFolder = _curFolder)
    sameEA     := (_lastEA     = _curEA)
    sameTerm   := (_lastTerm   = _curTerm)

    if (samePC && sameFolder && sameEA && sameTerm) {
        ToolTip, ✓ 동일 환경 (%A_ComputerName%) — 마지막 세션: %_lastTime%, 0, 0
        SetTimer, _ClearSessionTip, -4000
        GuiControl,, OptLoopStatus, [OK] 동일 환경 (%A_ComputerName%) — 마지막 세션: %_lastTime%
    } else {
        diffMsg := ""
        if (!samePC)     diffMsg .= "PC: " . _lastPC . " → " . A_ComputerName . "`n"
        if (!sameFolder) diffMsg .= "작업폴더 변경`n"
        if (!sameEA)     diffMsg .= "EA 경로 변경`n"
        if (!sameTerm)   diffMsg .= "터미널 경로 변경`n"
        ToolTip, ⚠ 환경 변경 감지`n%diffMsg%마지막 저장: %_lastTime%, 0, 0
        SetTimer, _ClearSessionTip, -6000
        GuiControl,, OptLoopStatus, [!] 환경 변경 감지 — 경로 확인 권장 (마지막: %_lastTime%)
    }
return

_ClearSessionTip:
    ToolTip
return

; =====================================================

; Hotkey Subroutines

; =====================================================

F9::GoSub, RunCleanupManager

F10::GoSub, RunDualLauncher

RunCleanupManager:

    Run, "%A_ScriptDir%\RUN_Cleanup_Manager.bat"

return

RunDualLauncher:

    Run, "%A_ScriptDir%\RUN_MENU_v4.0.bat"

return

RunLoopV36Internal_v2:

    Gosub, SaveSettings

    Gosub, SaveDateSettings

    

    scriptPath := A_ScriptDir . "\scripts\SIMPLE_LOOP_v3_7.ahk"

    IfExist, %scriptPath%

        Run, "%A_AhkPath%" "%scriptPath%"

    else

        MsgBox, 48, 오류, v3.6 루프 스크립트를 찾을 수 없습니다:`n%scriptPath%

return

; =====================================================

; v3.8: 기간 프리셋 저장/불러오기 (10개)

; =====================================================

SaveDatePresetV38:

    GuiControlGet, presetName,, DatePresetSelect

    if (presetName = "") {

        MsgBox, 48, 오류, 프리셋을 선택하세요.

        return

    }

    presetFile := configsFolder . "\date_presets.ini"

    ; 현재 기간 설정 저장

    Loop, 24 {

        idx := A_Index

        GuiControlGet, chkVal,, TestDateChk%idx%

        GuiControlGet, fromVal,, TestFromDT%idx%

        GuiControlGet, toVal,, TestToDT%idx%

        FormatTime, fromStr, %fromVal%, yyyy.MM.dd

        FormatTime, toStr, %toVal%, yyyy.MM.dd

        IniWrite, %chkVal%, %presetFile%, %presetName%, enable%idx%

        IniWrite, %fromStr%, %presetFile%, %presetName%, from%idx%

        IniWrite, %toStr%, %presetFile%, %presetName%, to%idx%

    }

    MsgBox, 64, 저장 완료, "%presetName%"에 기간 설정을 저장했습니다.

    ; 리스트 갱신 (새로 추가된 항목 반영)

    newList := "|" . GetPresetList()

    GuiControl,, DatePresetSelect, %newList%

    GuiControl, ChooseString, DatePresetSelect, %presetName%

return

LoadDatePresetV38:

    GuiControlGet, presetName,, DatePresetSelect

    if (presetName = "") {

        MsgBox, 48, 오류, 프리셋을 선택하세요.

        return

    }

    ; ★★★ 권장6개 프리셋 (하드코딩) ★★★

    if (presetName = "권장6개") {

        Loop, 24 { GuiControl,, TestDateChk%A_Index%, 0 }

        GuiControl,, TestDateChk1, 1

        GuiControl,, TestFromDT1, 20200101

        GuiControl,, TestToDT1, 20251231

        GuiControl,, TestDateChk2, 1

        GuiControl,, TestFromDT2, 20250101

        GuiControl,, TestToDT1, 20251231

        GuiControl,, TestDateChk3, 1

        GuiControl,, TestFromDT3, 20250101

        GuiControl,, TestToDT1, 20250430

        GuiControl,, TestDateChk4, 1

        GuiControl,, TestFromDT4, 20240101

        GuiControl,, TestToDT1, 20241231

        GuiControl,, TestDateChk5, 1

        GuiControl,, TestFromDT5, 20200201

        GuiControl,, TestToDT1, 20200531

        GuiControl,, TestDateChk6, 1

        GuiControl,, TestFromDT6, 20220101

        GuiControl,, TestToDT1, 20221231

        Gosub, SaveDateSettings

        MsgBox, 64, 권장6개 로드, 외부 제출용 권장 6개 기간이 설정되었습니다.

        return

    }

    ; ★★★ 권장8개 프리셋 (하드코딩) ★★★

    if (presetName = "권장8개") {

        Loop, 24 { GuiControl,, TestDateChk%A_Index%, 0 }

        GuiControl,, TestDateChk1, 1

        GuiControl,, TestFromDT1, 20250101

        GuiControl,, TestToDT1, 20251231

        GuiControl,, TestDateChk2, 1

        GuiControl,, TestFromDT2, 20250101

        GuiControl,, TestToDT1, 20250630

        GuiControl,, TestDateChk3, 1

        GuiControl,, TestFromDT3, 20250701

        GuiControl,, TestToDT1, 20251231

        GuiControl,, TestDateChk4, 1

        GuiControl,, TestFromDT4, 20250101

        GuiControl,, TestToDT1, 20250331

        GuiControl,, TestDateChk5, 1

        GuiControl,, TestFromDT5, 20250401

        GuiControl,, TestToDT1, 20250630

        GuiControl,, TestDateChk6, 1

        GuiControl,, TestFromDT6, 20250701

        GuiControl,, TestToDT1, 20250930

        GuiControl,, TestDateChk7, 1

        GuiControl,, TestFromDT7, 20251001

        GuiControl,, TestToDT1, 20251231

        GuiControl,, TestDateChk8, 1

        GuiControl,, TestFromDT8, 20250301

        GuiControl,, TestToDT1, 20251231

        Gosub, SaveDateSettings

        MsgBox, 64, 권장8개 로드, 2025년 분기별 8개 기간이 설정되었습니다.

        return

    }

    presetFile := configsFolder . "\date_presets.ini"

    IfNotExist, %presetFile%

    {

        MsgBox, 48, 오류, 저장된 프리셋이 없습니다.

        return

    }

    loadedCount := 0

    Loop, 24 {

        idx := A_Index

        IniRead, chkVal, %presetFile%, %presetName%, enable%idx%,

        IniRead, fromStr, %presetFile%, %presetName%, from%idx%,

        IniRead, toStr, %presetFile%, %presetName%, to%idx%,

        if (chkVal != "" && chkVal != "ERROR") {

            GuiControl,, TestDateChk%idx%, %chkVal%

            fromDT := StrReplace(fromStr, ".", "")

            toDT := StrReplace(toStr, ".", "")

            if (fromDT != "" && StrLen(fromDT) = 8)

                GuiControl,, TestFromDT%idx%, %fromDT%

            if (toDT != "" && StrLen(toDT) = 8)

                GuiControl,, TestToDT%idx%, %toDT%

            loadedCount++

        }

    }

    if (loadedCount > 0) {

        Gosub, SaveDateSettings

        MsgBox, 64, 불러오기 완료, "%presetName%"에서 기간 설정을 불러왔습니다.

    } else {

        MsgBox, 48, 오류, "%presetName%"에 저장된 설정이 없습니다.

    }

return

LoopOrderChanged:
    Gui, Submit, NoHide
    if (InStr(LoopOrderSelect, "Option B")) {
        loopOrder := "B"
    } else {
        loopOrder := "A"
    }
    IniWrite, %loopOrder%, %iniFile%, settings, loop_order
return

HtmlThresholdUp:
    htmlCloseThreshold += htmlStepSize
    if (htmlCloseThreshold > 9999)
        htmlCloseThreshold := 9999
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
return

HtmlThresholdDown:
    htmlCloseThreshold -= htmlStepSize
    if (htmlCloseThreshold < 1)
        htmlCloseThreshold := 1
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
return

HtmlStep1:
    htmlStepSize := 1
    IniWrite, %htmlStepSize%, %iniFile%, settings, html_step_size
return

HtmlStep10:
    htmlStepSize := 10
    IniWrite, %htmlStepSize%, %iniFile%, settings, html_step_size
return

HtmlStep50:
    htmlStepSize := 50
    IniWrite, %htmlStepSize%, %iniFile%, settings, html_step_size
return

HtmlBrowserChanged:
    Gui, Submit, NoHide
    if (HtmlBrowserChrome)
        htmlBrowserTarget := "chrome"
    else if (HtmlBrowserEdge)
        htmlBrowserTarget := "edge"
    else
        htmlBrowserTarget := "both"
    IniWrite, %htmlBrowserTarget%, %iniFile%, settings, html_browser_target
return

; ─────────────────────────────────────────────────────
; [HTML 프리셋] 빠른 설정 버튼
; ─────────────────────────────────────────────────────
HtmlPreset1:
    htmlCloseThreshold := 1
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
    htmlNewCount := 0  ; 즉시 리셋
    GuiControl,, HtmlNewCountText, 0개
return
HtmlPreset10:
    htmlCloseThreshold := 10
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
return
HtmlPreset50:
    htmlCloseThreshold := 50
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
return
HtmlPreset100:
    htmlCloseThreshold := 100
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
return
HtmlPreset200:
    htmlCloseThreshold := 200
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
return
HtmlPreset500:
    htmlCloseThreshold := 500
    GuiControl,, HtmlThresholdText, %htmlCloseThreshold%
    IniWrite, %htmlCloseThreshold%, %iniFile%, settings, html_close_threshold
return

; ─────────────────────────────────────────────────────
; [중간분석 인터벌 프리셋]
; ─────────────────────────────────────────────────────
ResetSinceTimestamp:
    ; [nc2.3] 분석 since 타임스탬프 초기화 → 다음 분석 시 전체 재스캔
    IniDelete, %iniFile%, analysis, last_analysis_time
    ToolTip, [Since 리셋] 다음 분석 시 전체 파일 재스캔합니다., , , 3
    SetTimer, RemoveToolTip, -3000
    FileAppend, [SINCE RESET] last_analysis_time 삭제 → 다음 분석 전체 재스캔`n, %logFile%
return

AnalInterval0:
    analyzeInterval := 0
    analNewCount := 0
    GuiControl,, AnalIntervalText, (비활성)
    GuiControl,, AnalNewCountText, 0개
    IniWrite, 0, %iniFile%, settings, analyze_interval
return
AnalInterval5:
    analyzeInterval := 5
    analNewCount := 0
    GuiControl,, AnalIntervalText, [%analyzeInterval%개마다]
    GuiControl,, AnalNewCountText, 0개
    IniWrite, %analyzeInterval%, %iniFile%, settings, analyze_interval
return
AnalInterval50:
    analyzeInterval := 50
    analNewCount := 0
    GuiControl,, AnalIntervalText, [%analyzeInterval%개마다]
    GuiControl,, AnalNewCountText, 0개
    IniWrite, %analyzeInterval%, %iniFile%, settings, analyze_interval
return
AnalInterval100:
    analyzeInterval := 100
    analNewCount := 0
    GuiControl,, AnalIntervalText, [%analyzeInterval%개마다]
    GuiControl,, AnalNewCountText, 0개
    IniWrite, %analyzeInterval%, %iniFile%, settings, analyze_interval
return
AnalInterval200:
    analyzeInterval := 200
    analNewCount := 0
    GuiControl,, AnalIntervalText, [%analyzeInterval%개마다]
    GuiControl,, AnalNewCountText, 0개
    IniWrite, %analyzeInterval%, %iniFile%, settings, analyze_interval
return
AnalInterval300:
    analyzeInterval := 300
    analNewCount := 0
    GuiControl,, AnalIntervalText, [%analyzeInterval%개마다]
    GuiControl,, AnalNewCountText, 0개
    IniWrite, %analyzeInterval%, %iniFile%, settings, analyze_interval
return

; ─────────────────────────────────────────────────────
; [중간분석 실행] N개 완료마다 BacktestAnalyzer 실행
; ─────────────────────────────────────────────────────
RunIntervalAnalysis:
    ; [nc2.3] A_ScriptDir에서만 분석기 탐색 (v2_0 우선 - --since 지원)
    _riaScript := ""
    _riaCandidates := ["BacktestAnalyzer_v2_0.py", "BacktestAnalyzer_v1_9.py"
                     , "BacktestAnalyzer_v1.9.py", "BacktestAnalyzer_v1_8.py"
                     , "BacktestAnalyzer_v1.7.py", "BacktestAnalyzer.py"]
    for i, _riaName in _riaCandidates {
        _riaPath := A_ScriptDir . "\" . _riaName
        if FileExist(_riaPath) {
            _riaScript := _riaPath
            break
        }
    }
    if (_riaScript = "") {
        ToolTip, [분석오류] BacktestAnalyzer.py 를 A_ScriptDir에서 찾지 못함, , , 3
        SetTimer, RemoveToolTip, -5000
        FileAppend, [ANAL ERROR] BacktestAnalyzer not found in %A_ScriptDir%`n, %logFile%
        return
    }

    ; [nc2.3] ROOT 폴더 = html_save_path 에서 2단계 위 (reports 루트)
    ; 구조: reports/20260405/EA이름/ → 2단계 위 = reports/
    IniRead, _htmlPath, %iniFile%, folders, html_save_path, NOTSET
    StringReplace, _htmlPath, _htmlPath, /, \, All
    if (_htmlPath != "NOTSET" && _htmlPath != "") {
        SplitPath, _htmlPath,, _dateDir          ; EA폴더 제거 → date폴더
        SplitPath, _dateDir,, _rootReportsDir    ; date폴더 제거 → reports 루트
        if (_rootReportsDir != "" && FileExist(_rootReportsDir))
            _iBasePath := _rootReportsDir
        else if (_dateDir != "" && FileExist(_dateDir))
            _iBasePath := _dateDir
        else
            _iBasePath := _htmlPath
    } else {
        _iBasePath := A_ScriptDir
    }

    ; [nc2.3] --since 타임스탬프 로드 (직전 분석 이후 새 파일만 스캔)
    IniRead, _sinceTs, %iniFile%, analysis, last_analysis_time, NONE
    _sinceArg := ""
    if (_sinceTs != "NONE" && _sinceTs != "")
        _sinceArg := " --since " . _sinceTs

    FormatTime, _iTime,, HH:mm:ss
    FormatTime, _nowTs,, yyyyMMdd_HHmmss
    GuiControl,, StatusText, 상태: 중간분석 실행 중 (%testCounter%개 완료)...
    FileAppend, [%_iTime%] 중간분석 실행: %_riaScript%`n경로: %_iBasePath% / since: %_sinceTs%`n, %logFile%

    ; 실행: ROOT 폴더 + --since (중복분석 방지) + --auto
    Run, %pythonExePath% "%_riaScript%" --auto "%_iBasePath%"%_sinceArg%, %A_ScriptDir%

    ; [nc2.3] 현재 타임스탬프 저장 → 다음 분석 시 --since로 사용 (중복 방지)
    IniWrite, %_nowTs%, %iniFile%, analysis, last_analysis_time
    FileAppend, [%_iTime%] 중간분석 발사완료 / 다음 since: %_nowTs%`n, %logFile%

    htmlAnalCount++
    GuiControl,, HtmlAnalCountText, %htmlAnalCount%회
    GuiControl,, AnalDoneCountText, %htmlAnalCount%회

    ; [nc2.3] 분석 완료 후 3분 뒤 브라우저 창 전체 자동 닫기 (one-shot timer)
    SetTimer, DelayedCloseAfterAnalysis, -180000
return

; ─────────────────────────────────────────────────────
; [nc2.3] 분석 후 3분 타이머 - 브라우저 자동 닫기
; ─────────────────────────────────────────────────────
DelayedCloseAfterAnalysis:
    FormatTime, _dcaTime,, HH:mm:ss
    FileAppend, [3MIN TIMER] %_dcaTime% 분석 후 3분 경과 -> 전체 닫기 실행`n, %logFile%
    ToolTip, [3분 타이머] 백테스트 분석 파일 자동 닫기 실행 중..., , , 5
    SetTimer, RemoveToolTip, -4000
    Gosub, CloseHTMLWindows
return

; ─────────────────────────────────────────────────────
; [FindAnalyzerScript] 버전별 자동 탐색
; ─────────────────────────────────────────────────────
FindAnalyzerScript() {
    global scriptsFolder
    candidates := ["BacktestAnalyzer_v2_0.py", "BacktestAnalyzer_v2.0.py"
                 , "BacktestAnalyzer_v1_9.py", "BacktestAnalyzer_v1.9.py"
                 , "BacktestAnalyzer_v1_8.py", "BacktestAnalyzer_v1.8.py"
                 , "BacktestAnalyzer_v1_7.py", "BacktestAnalyzer_v1.7.py"
                 , "BacktestAnalyzer.py"]
    searchDirs := [A_ScriptDir, scriptsFolder, A_ScriptDir . "\scripts"]
    for i, name in candidates {
        for j, dir in searchDirs {
            p := dir . "\" . name
            if FileExist(p)
                return p
        }
    }
    return ""
}

; =====================================================
; [v8.0] AutoTrigger IPC: Python Worker → command.json → SOLO 7.0
; Python Worker가 command.json 생성 → SOLO 7.0이 읽어 백테스트 자동 실행
; =====================================================

CheckAutoTriggerCommand:
    commandFile := configsFolder . "\command.json"
    if FileExist(commandFile) {
        FileRead, jsonContent, %commandFile%
        if (jsonContent != "") {
            ; 파일 즉시 이름 변경 (중복 실행 방지)
            FileMove, %commandFile%, %configsFolder%\command_processing.json, 1

            ; JSON 파싱 및 설정 적용
            ParseAndApplyCommand(jsonContent)

            Sleep, 500

            GuiControl,, StatusText, 상태: 원격 명령 수신! 자동 시작 중...

            isAutoStart := true

            ; 로그 기록
            FormatTime, logTime,, HH:mm:ss
            FileAppend, [%logTime%] Remote Command Received: %jsonContent%`n, %scriptsFolder%\solo_remote_log.txt

            ; html_save_path 업데이트 (날짜 + EA이름) [v7.7]
            ; 기본값: [스크립트폴더]\reports (배포용 상대경로)
            ; 유저가 report_base_path 설정 시 해당 경로 사용
            FormatTime, todayDate,, yyyyMMdd
            IniRead, remoteBasePath, %iniFile%, folders, report_base_path, NOTSET
            if (remoteBasePath = "NOTSET" || remoteBasePath = "" || remoteBasePath = "ERROR") {
                ; [v1.5] 배포용: 스크립트 폴더 기준 상대 경로
                remoteBasePath := A_ScriptDir . "\reports"
            }
            StringReplace, remoteBasePath, remoteBasePath, /, \, All
            newHtmlPath := remoteBasePath . "\" . todayDate . "\" . cmdEA
            IniWrite, %newHtmlPath%, %iniFile%, folders, html_save_path
            htmlSaveFolder := newHtmlPath
            GuiControl,, HtmlSavePathEdit, %htmlSaveFolder%

            ; 백테스트 날짜 동기화 (기본: 항상 동기화 / 예외: 경고)
            if (cmdFromDate != "" && cmdToDate != "") {
                ; [기본] command.json 날짜 → current_config.ini + tester.ini 동기화
                IniWrite, 1, %iniFile%, test_date, enable
                IniWrite, %cmdFromDate%, %iniFile%, test_date, from_date
                IniWrite, %cmdToDate%, %iniFile%, test_date, to_date
                ; tester.ini 직접 동기화 (MT4가 GUI보다 ini 파일 우선 읽음)
                testerIniPath := terminalPath . "\tester\tester.ini"
                if FileExist(testerIniPath) {
                    IniWrite, %cmdFromDate%, %testerIniPath%, Tester, FromDate
                    IniWrite, %cmdToDate%, %testerIniPath%, Tester, ToDate
                    IniWrite, 1, %testerIniPath%, Tester, UseDate
                }
            } else {
                ; [예외] command.json에 날짜 없음 → current_config.ini 기존 날짜 유지 + 경고
                IniRead, _existFrom, %iniFile%, test_date, from_date,
                IniRead, _existTo, %iniFile%, test_date, to_date,
                FormatTime, _logTime,, HH:mm:ss
                FileAppend, [%_logTime%] WARNING: command.json에 날짜 없음 - 기존 날짜 사용 (%_existFrom% ~ %_existTo%)`n, %scriptsFolder%\solo_remote_log.txt
                GuiControl,, StatusText, [경고] 날짜 미지정 - 기존 설정(%_existFrom%~%_existTo%) 사용
                cmdFromDate := _existFrom
                cmdToDate := _existTo
            }

            ; [진행상태] [N/Total] EA|Symbol|TF|Period 형식
            if RegExMatch(jsonContent, """total_sets"":\s*(\d+)", tsMatch)
                cmdTotalSets := tsMatch1
            else
                cmdTotalSets := "?"
            if RegExMatch(jsonContent, """iteration"":\s*(\d+)", itMatch)
                cmdIterNum := itMatch1
            else
                cmdIterNum := 1

            progressText := "[" . cmdIterNum . "/" . cmdTotalSets . "] " . cmdEA . " | " . cmdSymbol . " | " . cmdTF
            if (cmdFromDate != "")
                progressText := progressText . " | " . SubStr(cmdFromDate,1,7)
            GuiControl,, CurrentText, %progressText%
            GuiControl,, StatusText, 상태: 백테스트 실행 중...

            runnerScript := scriptsFolder . "\SIMPLE_4STEPS_v4_0.ahk"
            if FileExist(runnerScript) {
                ; EA 이름 파일 기록
                eaNameFile := configsFolder . "\current_ea_name.txt"
                FileDelete, %eaNameFile%
                FileAppend, %cmdEA%, %eaNameFile%

                ; 이전 완료 플래그 삭제
                completionFlag := configsFolder . "\test_completed.flag"
                FileDelete, %completionFlag%

                if (cmdIter = "")
                    cmdIter := 1

                ; 서버에 BUSY 보고
                startUrl := "http://" . masterIP . ":9001/worker/" . workerID . "/start"
                pyCmd := "import requests; requests.post('" . startUrl . "', json={'ea_name': '" . cmdEA . "', 'iteration': " . cmdIter . "}, timeout=5)"
                Run, %pythonExePath% -c "%pyCmd%",, Hide

                statusFile := configsFolder . "\status.json"
                statusContent = {"status": "busy", "message": "Backtest Running: %cmdEA%", "timestamp": "%A_Now%", "ea": "%cmdEA%"}
                FileDelete, %statusFile%
                FileAppend, %statusContent%, %statusFile%

                ; MT4 새로고침
                refreshScript := scriptsFolder . "\REFRESH_MT4.ahk"
                if FileExist(refreshScript) {
                    RunWait, "%A_AhkPath%" "%refreshScript%"
                } else {
                    ; [NC2.0] MT4 새로고침 ControlSend 방식
                    WinGet, _ncmt4id, ID, ahk_class MetaQuotes::MetaTrader::4.00
                    if (_ncmt4id)
                        PostMessage, 0x111, 33276, 0,, ahk_id %_ncmt4id%
                    Sleep, 1000
                }

                ; SIMPLE_4STEPS 실행 (백테스트)
                backtestStart := A_TickCount
                RunWait, "%A_AhkPath%" "%runnerScript%" "%cmdEA%" "%cmdSymbol%" "%cmdTF%" "1", %A_ScriptDir%
                backtestElapsed := (A_TickCount - backtestStart) // 1000
                elapsedMin := backtestElapsed // 60
                elapsedSec := Mod(backtestElapsed, 60)

                ; 완료 상태 표시
                resultLine := progressText . " | " . elapsedMin . "분 " . elapsedSec . "초"
                GuiControl,, StatusText, %resultLine%

                statusContent = {"status": "completed", "message": "Test Finished", "timestamp": "%A_Now%", "ea": "%cmdEA%"}
                FileDelete, %statusFile%
                FileAppend, %statusContent%, %statusFile%

                ; 완료 플래그 생성 (Python 워커에게 알림)
                FileAppend, 1, %completionFlag%

                ; [★ FIX] 백테스트 완료 후 HTML 창 자동 닫기
                Gosub, CheckAndCloseOldHTML
                Gosub, CleanTesterHistory

            } else {
                GuiControl,, StatusText, [오류] SIMPLE_4STEPS_v4_0.ahk 없음 - scripts 폴더 확인
                FormatTime, logTime,, HH:mm:ss
                FileAppend, [%logTime%] ERR: SIMPLE_4STEPS_v4_0.ahk not found at %runnerScript%`n, %scriptsFolder%\solo_remote_log.txt
            }
        }
    } else {
        ; Heartbeat 업데이트 (완료 상태 덮어쓰기 방지)
        statusFile := configsFolder . "\status.json"
        FileRead, currentStatusInfo, %statusFile%
        if (!InStr(currentStatusInfo, """status"": ""completed""")) {
            statusContent = {"status": "%currentStepStatus%", "message": "%currentStatusMessage%", "timestamp": "%A_Now%"}
            FileDelete, %statusFile%
            FileAppend, %statusContent%, %statusFile%
        }
    }
return

; =====================================================
; [v8.0] 전체 완료 감지 타이머 (all_done.flag 감시, 3초 주기)
; Python 워커가 모든 SET 테스트 완료 시 생성 → 분석기 자동 실행
; =====================================================

CheckAllDone:
    allDoneFlag := configsFolder . "\all_done.flag"
    if FileExist(allDoneFlag) {
        FileRead, allDoneContent, %allDoneFlag%
        FileDelete, %allDoneFlag%

        ; JSON에서 정보 추출
        totalTested := 0
        bestScore := 0
        doneEA := ""
        if RegExMatch(allDoneContent, """total_tested"":\s*(\d+)", m)
            totalTested := m1
        if RegExMatch(allDoneContent, """best_score"":\s*([\d.]+)", m)
            bestScore := m1
        if RegExMatch(allDoneContent, """ea_name"":\s*""([^""]+)""", m)
            doneEA := m1

        GuiControl,, StatusText, 상태: 분석기 실행 중...

        FormatTime, logTime,, HH:mm:ss
        FileAppend, [%logTime%] ALL DONE: %doneEA% / tested=%totalTested%`n, %scriptsFolder%\solo_remote_log.txt

        ; BacktestAnalyzer 자동 실행
        analyzerScript := A_ScriptDir . "\BacktestAnalyzer_v1.7.py"
        IniRead, autoAnalyzePath, %iniFile%, folders, html_save_path, NOTSET
        StringReplace, autoAnalyzePath, autoAnalyzePath, /, \, All
        ; EA 폴더 → 날짜 폴더로 한 단계 올라가기
        SplitPath, autoAnalyzePath,, autoAnalyzePath

        if (FileExist(analyzerScript) && autoAnalyzePath != "NOTSET" && autoAnalyzePath != "") {
            Run, %pythonExePath% "%analyzerScript%" --auto "%autoAnalyzePath%" --email, %A_ScriptDir%, Hide
            FileAppend, [%logTime%] BacktestAnalyzer launched: %autoAnalyzePath%`n, %scriptsFolder%\solo_remote_log.txt

            Sleep, 5000
            summaryPath := autoAnalyzePath . "\SUMMARY"
            Loop, 5 {
                if FileExist(summaryPath) {
                    FileAppend, [%logTime%] SUMMARY folder detected: %summaryPath%`n, %scriptsFolder%\solo_remote_log.txt
                    uploadScript := scriptsFolder . "\upload_summary.py"
                    if FileExist(uploadScript) {
                        Run, %pythonExePath% "%uploadScript%" "%summaryPath%" "%doneEA%" %totalTested%, %A_ScriptDir%, Hide
                    }
                    break
                }
                Sleep, 5000
            }
        }

        MsgBox, 64, 백테스트 완료, 모든 테스트가 완료되었습니다!`n`n완료: %totalTested%회`nEA: %doneEA%, 3

        GuiControl,, StatusText, 상태: 완료 (대기 중)
    }
return

; =====================================================
; [v8.0] JSON 파싱 및 설정 적용 함수
; =====================================================

ParseAndApplyCommand(jsonStr) {
    global

    if RegExMatch(jsonStr, """ea_name"":\s*""([^""]+)""", match)
        cmdEA := match1
    if RegExMatch(jsonStr, """set_file"":\s*""([^""]+)""", match)
        cmdSetFile := match1
    if RegExMatch(jsonStr, """symbol"":\s*""([^""]+)""", match)
        cmdSymbol := match1
    if RegExMatch(jsonStr, """tf"":\s*""([^""]+)""", match)
        cmdTF := match1
    if RegExMatch(jsonStr, """iteration"":\s*(\d+)", match)
        cmdIter := match1
    if RegExMatch(jsonStr, """from_date"":\s*""([^""]+)""", match)
        cmdFromDate := match1
    if RegExMatch(jsonStr, """to_date"":\s*""([^""]+)""", match)
        cmdToDate := match1

    ; Symbol 설정
    if (cmdSymbol != "") {
        sym1 := cmdSymbol
        sym1Chk := 1
        sym2Chk := 0
        sym3Chk := 0
        sym4Chk := 0
        sym5Chk := 0
        GuiControl,, Sym1Edit, %sym1%
        GuiControl,, Sym1Chk, 1
        GuiControl,, Sym2Chk, 0
        GuiControl,, Sym3Chk, 0
    }

    ; TF 설정
    if (cmdTF != "") {
        tfM1 := 0
        tfM5 := 0
        tfM15 := 0
        tfM30 := 0
        tfH1 := 0
        tfH4 := 0

        if (cmdTF = "M1")
            tfM1 := 1
        else if (cmdTF = "M5")
            tfM5 := 1
        else if (cmdTF = "M15")
            tfM15 := 1
        else if (cmdTF = "M30")
            tfM30 := 1
        else if (cmdTF = "H1")
            tfH1 := 1
        else if (cmdTF = "H4")
            tfH4 := 1

        GuiControl,, TFM1Chk, %tfM1%
        GuiControl,, TFM5Chk, %tfM5%
        GuiControl,, TFM15Chk, %tfM15%
        GuiControl,, TFM30Chk, %tfM30%
        GuiControl,, TFH1Chk, %tfH1%
        GuiControl,, TFH4Chk, %tfH4%
    }

    ; 날짜 설정
    if (cmdFromDate != "" && cmdToDate != "") {
        testDateEnable1 := 1
        testFromDate1 := cmdFromDate
        testToDate1 := cmdToDate

        cleanFrom := StrReplace(cmdFromDate, ".", "")
        cleanTo := StrReplace(cmdToDate, ".", "")

        GuiControl,, TestDateChk1, 1
        GuiControl,, TestFromDT1, %cleanFrom%
        GuiControl,, TestToDT1, %cleanTo%

        Loop, 23 {
            idx := A_Index + 1
            testDateEnable%idx% := 0
            GuiControl,, TestDateChk%idx%, 0
        }
    }

    ; INI 저장
    Gosub, SaveSettings
    Gosub, SaveDateSettings

    ; SET 파일 정보
    if (cmdSetFile != "") {
        IniWrite, 1, %iniFile%, current_backtest, has_set
        IniWrite, %cmdSetFile%, %iniFile%, current_backtest, set_file_path
    } else {
        IniWrite, 0, %iniFile%, current_backtest, has_set
    }
    IniWrite, %cmdEA%, %iniFile%, current_backtest, ea_name
}

; =====================================================
; [v8.0] DETECT_STEP2_COORDS.ahk 변경 감지 (500ms 주기)
; =====================================================

MonitorConfigChanges:
    if (!FileExist(iniFile))
        return
    try {
        FileRead, coordsContent, %iniFile%
        if RegExMatch(coordsContent, "i)\[coords\](.*?)(\[|$)", coordsMatch) {
            coordsSection := coordsMatch1
            if (StrLen(coordsSection) != StrLen(lastConfigChecksum)) {
                lastConfigChecksum := coordsSection
                Gosub, RefreshSavedDisplay
                ToolTip, 좌표 설정이 업데이트되었습니다!
                SetTimer, ClearToolTip, 2000
            }
        }
    } catch e {
    }
return


