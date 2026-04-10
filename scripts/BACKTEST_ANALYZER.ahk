; =====================================================
; MT4 백테스트 분석기 v1.5
; - templates 폴더의 HTML 리포트 자동 분석
; - 거래 유무, 수익/손실, 드로다운 분석
; - 개선점 제안 및 상세 리포트 생성
; - Statement 타입과 Backtest Report 타입 모두 지원
; - v1.5: 실제 리포트 파일 카운트 표시 추가
; =====================================================
#NoEnv
#SingleInstance Force
SetWorkingDir, %A_ScriptDir%
SetBatchLines, -1

global configsFolder := A_ScriptDir "\..\configs"
global iniFile := configsFolder "\current_config.ini"
global reportsArray := []
global totalFiles := 0
global analyzedFiles := 0
global additionalFolders := []  ; 추가 분석 폴더 목록
global lvLastCol := 0
global lvSortOrder := "Asc"
global filePathMap := {}  ; 파일 경로 매핑

; 터미널 경로 읽기
IniRead, terminalPath, %iniFile%, folders, terminal_path, NOTSET
StringReplace, terminalPath, terminalPath, /, \, All

if (terminalPath = "NOTSET" || terminalPath = "") {
    MsgBox, 48, 오류, 터미널 경로가 설정되지 않았습니다.`n먼저 MENU에서 터미널 경로를 설정해주세요.
    ExitApp
}

templatesPath := terminalPath "\templates"

; html_save_path 읽기 (D:\2026NEWOPTMIZER 등)
IniRead, htmlSavePath, %iniFile%, folders, html_save_path, NOTSET
StringReplace, htmlSavePath, htmlSavePath, /, \, All

IfNotExist, %templatesPath%
{
    MsgBox, 48, 오류, templates 폴더를 찾을 수 없습니다:`n%templatesPath%
    ExitApp
}

; =====================================================
; GUI 생성
; =====================================================
Gui, +Resize +MinSize800x600
Gui, Margin, 10, 10
Gui, Color, F5F5F5

; 제목
Gui, Font, s14 Bold cNavy
Gui, Add, Text, x10 y10 w780, 📊 MT4 백테스트 분석기 v1.5

Gui, Font, s9 Normal c666666
Gui, Add, Text, x10 y+5 w780, 분석 경로: %templatesPath%

Gui, Add, Text, x10 w780 y+10 0x10 ; 구분선

; 버튼 영역
Gui, Font, s9 Normal
Gui, Add, Button, gStartAnalysis x10 w150 h30 y+10, 🔍 분석 시작
Gui, Add, Button, gRefreshList x+10 yp w150 h30, 🔄 새로고침
Gui, Add, Button, gExportReport x+10 yp w150 h30, 📄 리포트 저장
Gui, Add, Button, gOpenFolder x+10 yp w150 h30, 📁 폴더 열기
Gui, Add, Button, gAddFolder x+10 yp w150 h30, ➕ 폴더 추가

; 상태 표시
Gui, Add, Text, vStatusText x10 w480 y+10 c0066CC, 📋 분석 대기 중...

; 실제 리포트 카운트 (신규)
actualReportCount := 0
Loop, %templatesPath%\*.htm
    actualReportCount++
Loop, %templatesPath%\*.html
    actualReportCount++

Gui, Font, s9 Bold cGreen
Gui, Add, Text, vActualReportText x500 yp w280, 📊 실제 리포트 파일: %actualReportCount%개

Gui, Font, s9 Normal

Gui, Add, Text, x10 w780 y+5 0x10

; 결과 리스트뷰
Gui, Font, s8 Normal
Gui, Add, ListView, vResultLV gResultLV x10 y+10 w1200 h300 Grid, #|폴더|파일명|EA|심볼|TF|테스트기간|거래수|총수익|총손실|순이익|승률|드로다운|상태|문제점

; 컬럼 너비 설정
LV_ModifyCol(1, 30)   ; #
LV_ModifyCol(2, 50)   ; 폴더
LV_ModifyCol(3, 130)  ; 파일명
LV_ModifyCol(4, 80)   ; EA
LV_ModifyCol(5, 50)   ; 심볼
LV_ModifyCol(6, 35)   ; TF
LV_ModifyCol(7, 130)  ; 테스트기간 (80 -> 130)
LV_ModifyCol(8, 45)   ; 거래수
LV_ModifyCol(9, 65)   ; 총수익
LV_ModifyCol(10, 65)  ; 총손실
LV_ModifyCol(11, 65)  ; 순이익
LV_ModifyCol(12, 45)  ; 승률
LV_ModifyCol(13, 55)  ; 드로다운
LV_ModifyCol(14, 40)  ; 상태
LV_ModifyCol(15, 120) ; 문제점

Gui, Add, Text, x10 w780 y+10 0x10

; 요약 영역
Gui, Font, s10 Bold
Gui, Add, Text, x10 y+10 w780, 📈 분석 요약

Gui, Font, s9 Normal
Gui, Add, Text, vSummaryText x10 y+5 w780 h150, (분석 후 결과가 표시됩니다)

; GUI 표시 (화면 중앙에 배치)
Gui, Show, w800 h650 Center, MT4 백테스트 분석기

; 5분 후 자동 닫기 타이머 (300,000ms = 5분)
SetTimer, AutoCloseAnalyzer, 300000

; 자동 분석 시작
Gosub, StartAnalysis
return

; =====================================================
; 분석 시작
; =====================================================
StartAnalysis:
    LV_Delete()
    reportsArray := []
    filePathMap := {}
    totalFiles := 0
    analyzedFiles := 0

    ; 통계 변수
    global noTradeCount := 0
    global profitCount := 0
    global lossCount := 0
    global totalProfit := 0
    global maxDrawdown := 0
    global highDDCount := 0

    GuiControl,, StatusText, 🔍 HTML 파일 검색 중...

    ; 기본 templates 폴더 검색
    ScanFolder(templatesPath, "기본")

    ; Menu3 폴더 검색
    menu3Path := terminalPath "\MQL4\Files\Menu3"
    if (FileExist(menu3Path)) {
        ScanFolder(menu3Path, "Menu3")
    }

    ; Menu5 폴더 검색
    menu5Path := terminalPath "\MQL4\Files\Menu5"
    if (FileExist(menu5Path)) {
        ScanFolder(menu5Path, "Menu5")
    }

    ; html_save_path 하위 날짜 폴더 자동 스캔 (D:\2026NEWOPTMIZER\YYYYMMDD\)
    if (htmlSavePath != "NOTSET" && htmlSavePath != "" && FileExist(htmlSavePath)) {
        ; 오늘 날짜 폴더 우선 스캔
        FormatTime, todayStr,, yyyyMMdd
        todayFolder := htmlSavePath "\" todayStr
        if (FileExist(todayFolder)) {
            ScanFolderRecursive(todayFolder, "오늘(" . todayStr . ")")
        }
        ; 최근 7일 날짜 폴더도 스캔
        Loop, %htmlSavePath%\20*, 2  ; 폴더만
        {
            folderName := A_LoopFileName
            if (folderName != todayStr) {
                ScanFolderRecursive(A_LoopFileLongPath, folderName)
            }
        }
    }

    ; 추가 폴더들 검색
    for index, folder in additionalFolders {
        if (FileExist(folder)) {
            ScanFolder(folder, "추가" . index)
        }
    }

    ; 결과 없으면
    if (totalFiles = 0) {
        GuiControl,, StatusText, ⚠️ HTML 리포트 파일이 없습니다.
        GuiControl,, SummaryText, templates 폴더에 백테스트 결과 파일(.htm, .html)이 없습니다.`n`n백테스트를 먼저 실행하거나, Strategy Tester에서 Report 탭 우클릭 → "Save as Report"로 저장해주세요.
        return
    }
    
    ; 요약 생성
    GenerateSummary()
    
    GuiControl,, StatusText, ✅ 분석 완료! (총 %totalFiles%개 파일)
return

; =====================================================
; 폴더 스캔 함수
; =====================================================
ScanFolder(folderPath, folderLabel) {
    global totalFiles

    ; .htm 파일 검색
    Loop, %folderPath%\*.htm
    {
        totalFiles++
        filePath := A_LoopFileLongPath
        fileName := A_LoopFileName

        ; 파일 분석
        AnalyzeReport(filePath, fileName, totalFiles, folderLabel)
    }

    ; .html 파일 검색
    Loop, %folderPath%\*.html
    {
        totalFiles++
        filePath := A_LoopFileLongPath
        fileName := A_LoopFileName

        ; 파일 분석
        AnalyzeReport(filePath, fileName, totalFiles, folderLabel)
    }
}

; =====================================================
; 하위 폴더 재귀 스캔 (D:\2026NEWOPTMIZER\날짜\ 구조용)
; =====================================================
ScanFolderRecursive(rootPath, rootLabel) {
    global totalFiles

    ; 루트의 직접 .htm/.html 파일 먼저
    ScanFolder(rootPath, rootLabel)

    ; 1단계 하위 폴더 순회
    Loop, %rootPath%\*, 2  ; 폴더만
    {
        subPath  := A_LoopFileLongPath
        subLabel := rootLabel . "\" . A_LoopFileName
        ScanFolder(subPath, subLabel)
    }
}

; =====================================================
; 리포트 파일 분석
; =====================================================
AnalyzeReport(filePath, fileName, idx, folderLabel := "") {
    global reportsArray, noTradeCount, profitCount, lossCount, totalProfit, maxDrawdown, highDDCount

    ; 파일 읽기
    FileRead, content, %filePath%
    if (ErrorLevel) {
        LV_Add("", idx, folderLabel, fileName, "?", "?", "?", "?", "?", "?", "?", "❌", "파일 읽기 실패")
        return
    }

    ; 기본값 초기화
    ea := "Unknown"
    symbol := "?"
    tf := "?"
    testPeriod := "?"
    trades := 0
    totalGrossProfit := 0
    totalGrossLoss := 0
    profit := 0
    winRate := "?"
    drawdown := 0
    status := "?"
    issue := ""
    isStatement := false

    ; 파일 타입 확인 (Statement vs Backtest Report)
    ; Statement는 title에 "Statement:"가 있으면 Statement 타입
    if (InStr(content, "<title>Statement:")) {
        isStatement := true
    }

    ; Statement 타입인 경우 파일명에서 정보 추출
    if (isStatement) {
        ; 파일명 형식: C_892662277_XAU_H1_AI_BRAID_MASTER_05m_v6.0_PRO_0920_20250926_211856.htm
        if (RegExMatch(fileName, "i)C_\d+_([A-Z0-9]+)_(M\d+|H\d+|D\d+|W\d+|MN)_(.+?)_\d{8}_\d{6}", fMatch)) {
            symbol := fMatch1
            tf := fMatch2
            ea := fMatch3
        } else if (RegExMatch(fileName, "i)([A-Z]{3,}USD|NAS\d+|US\d+)", symMatch)) {
            symbol := symMatch1
        }
    } else {
        ; 기존 방식: EA 이름 추출 (title 태그에서)
        if (RegExMatch(content, "i)<title>.*?:\s*(.+?)</title>", match)) {
            ea := Trim(match1)
            ; EA 이름에서 심볼 추출 시도
            if (InStr(ea, "BTCUSD") || InStr(ea, "btcusd"))
                symbol := "BTCUSD"
            else if (InStr(ea, "XAUUSD") || InStr(ea, "xauusd") || InStr(ea, "Gold"))
                symbol := "XAUUSD"
            else if (InStr(ea, "NAS100") || InStr(ea, "USTEC") || InStr(ea, "US100"))
                symbol := "NAS100"
        }
    }
    
    ; 심볼 추출 (테이블에서)
    if (RegExMatch(content, "i)>\s*(BTCUSD|XAUUSD|EURUSD|GBPUSD|USDJPY|NAS100|US100|USTEC|Gold)[^<]*<", symMatch)) {
        symbol := symMatch1
    }
    
    ; 타임프레임 추출
    if (InStr(content, "M1") || InStr(content, "1 Minute"))
        tf := "M1"
    else if (InStr(content, "M5") || InStr(content, "5 Minute"))
        tf := "M5"
    else if (InStr(content, "M15") || InStr(content, "15 Minute"))
        tf := "M15"
    else if (InStr(content, "M30") || InStr(content, "30 Minute"))
        tf := "M30"
    else if (InStr(content, "H1") || InStr(content, "1 Hour") || InStr(content, "Hourly"))
        tf := "H1"
    else if (InStr(content, "H4") || InStr(content, "4 Hour"))
        tf := "H4"
    else if (InStr(content, "D1") || InStr(content, "Daily"))
        tf := "D1"
    
    ; Statement 타입인 경우 거래 내역에서 통계 계산
    if (isStatement) {
        tradeCount := 0
        winCount := 0
        totalProfitCalc := 0
        grossProfit := 0
        grossLoss := 0
        maxBalance := 2500.00
        minBalance := 2500.00
        currentBalance := 2500.00
        firstTradeDate := ""
        lastTradeDate := ""

        ; balance 행 찾기 (초기 잔액)
        if (RegExMatch(content, "i)<td[^>]*>balance</td>.*?class=mspt>(-?[\d,\.]+)</td>", balMatch)) {
            initBalance := StrReplace(balMatch1, ",", "")
            initBalance := StrReplace(initBalance, " ", "")
            currentBalance := initBalance + 0
            maxBalance := currentBalance
            minBalance := currentBalance
        }

        ; 모든 buy/sell 거래 찾기 - HTML 테이블 구조에 맞춘 파싱
        ; 거래 행 형식: <tr ...><td>...</td><td>buy/sell</td><td>Size</td>...<td>Profit</td></tr>
        pos := 1
        Loop {
            ; buy 또는 sell 찾기
            foundPos := RegExMatch(content, "i)<td>(buy|sell)</td>", typeMatch, pos)
            if (!foundPos)
                break

            ; 해당 <tr> 시작 위치 찾기 (역방향으로 찾기)
            trStartPos := foundPos
            Loop, 1000 {
                trStartPos--
                if (trStartPos <= 0)
                    break
                if (SubStr(content, trStartPos, 3) = "<tr")
                    break
            }

            ; </tr> 종료 위치 찾기
            trEndPos := InStr(content, "</tr>", false, foundPos)
            if (!trEndPos) {
                pos := foundPos + 1
                continue
            }

            ; 전체 <tr>...</tr> 추출
            tradeLine := SubStr(content, trStartPos, trEndPos - trStartPos + 5)

            ; 날짜 추출 (class=msdate)
            if (RegExMatch(tradeLine, "class=msdate[^>]*>([^<]+)</td>", dateMatch)) {
                tradeDate := Trim(dateMatch1)
                if (firstTradeDate = "")
                    firstTradeDate := tradeDate
                lastTradeDate := tradeDate
            }

            ; mspt 클래스 값들 추출
            profitValues := []
            tPos := 1
            Loop {
                matchPos := RegExMatch(tradeLine, "class=mspt>(-?[\d,\.]+)</td>", pMatch, tPos)
                if (!matchPos)
                    break

                val := StrReplace(pMatch1, ",", "")
                val := StrReplace(val, " ", "")
                profitValues.Push(val + 0)
                tPos := matchPos + StrLen(pMatch)
            }

            ; 거래 데이터 검증: 최소 5개 값 필요
            ; [Size, Price, S/L, T/P, ClosePrice, Commission, Taxes, Swap, Profit]
            if (profitValues.Length() >= 5) {
                profit_value := profitValues[profitValues.Length()]

                tradeCount++
                totalProfitCalc += profit_value
                currentBalance += profit_value

                if (profit_value > 0) {
                    winCount++
                    grossProfit += profit_value
                } else {
                    grossLoss += profit_value
                }

                if (currentBalance > maxBalance)
                    maxBalance := currentBalance
                if (currentBalance < minBalance)
                    minBalance := currentBalance
            }

            pos := trEndPos
        }

        trades := tradeCount
        profit := totalProfitCalc
        totalGrossProfit := grossProfit
        totalGrossLoss := grossLoss

        ; 테스트 기간 설정
        if (firstTradeDate != "" && lastTradeDate != "") {
            ; 날짜 형식: 2025.09.05 13:22:28 -> 2025.09.05로 변환
            RegExMatch(firstTradeDate, "(\d{4}\.\d{2}\.\d{2})", fDate)
            RegExMatch(lastTradeDate, "(\d{4}\.\d{2}\.\d{2})", lDate)
            if (fDate1 != "" && lDate1 != "") {
                testPeriod := fDate1 . "~" . lDate1
            }
        }

        if (tradeCount > 0) {
            winRate := Format("{:.1f}", (winCount / tradeCount * 100)) . "%"
        }

        ; 드로다운 계산
        if (maxBalance > minBalance) {
            drawdown := Format("{:.2f}", ((maxBalance - minBalance) / maxBalance * 100))
        }
    } else {
        ; 기존 백테스트 리포트 타입 처리
        ; 테스트 기간 추출 (인코딩 문제 대응: 날짜 패턴 직접 찾기)
        if (RegExMatch(content, "(\d{4}\.\d{2}\.\d{2})\s+\d{2}:\d{2}\s*-\s*(\d{4}\.\d{2}\.\d{2})\s+\d{2}:\d{2}", periodMatch)) {
            testPeriod := periodMatch1 . "~" . periodMatch2
        } else if (RegExMatch(content, "i)Period.*?(\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})", periodMatch)) {
            testPeriod := periodMatch1 . "~" . periodMatch2
        }
    }

    ; 파일명에서 테스트 기간 추출 (HTML 추출 실패 시 대체 수단)
    ; 파일명 패턴: YYYYMMDD-YYYYMMDD -> YYYY.MM.DD~YYYY.MM.DD로 변환
    if (testPeriod = "?" && RegExMatch(fileName, "(\d{8})-(\d{8})", fnMatch)) {
        fDate := SubStr(fnMatch1, 1, 4) . "." . SubStr(fnMatch1, 5, 2) . "." . SubStr(fnMatch1, 7, 2)
        lDate := SubStr(fnMatch2, 1, 4) . "." . SubStr(fnMatch2, 5, 2) . "." . SubStr(fnMatch2, 7, 2)
        testPeriod := fDate . "~" . lDate
    }

    if (!isStatement) {

        ; 총 거래수 추출 (한국어 HTML 대응)
        ; 패턴: <td>총 매매횟수</td><td align=right>166</td>
        if (RegExMatch(content, "align=right>(\d+)</td><td[^>]*>.*?won\s*%", trMatch)) {
            trades := trMatch1
        } else if (RegExMatch(content, "i)Total\s*Trades.*?align=right>(\d+)</td>", trMatch2)) {
            trades := trMatch2_1
        } else if (RegExMatch(content, "i)Total.*?deals.*?(\d+)", trMatch3)) {
            trades := trMatch3_1
        } else if (RegExMatch(content, "<td[^>]*>.*?</td><td[^>]*align=right>(\d+)</td><td[^>]*>.*?won", trMatch4)) {
            trades := trMatch4_1
        }

        ; 총수익 (Gross Profit) 추출 - 개선된 패턴
        if (RegExMatch(content, "i)Gross\s*Profit.*?align=right>(-?[\d,\.]+)</td>", gpMatch)) {
            totalGrossProfit := StrReplace(gpMatch1, ",", "")
            totalGrossProfit := StrReplace(totalGrossProfit, " ", "")
        } else if (RegExMatch(content, "i)>.*?<td[^>]*align=right>(-?[\d,\.]+)</td><td[^>]*>.*?<td[^>]*align=right>-[\d,\.]+</td>", gpMatch2)) {
            ; 패턴: <td>순이익</td><td>556.70</td><td>수익</td><td>6266.03</td><td>손실</td><td>-5709.33</td>
            ; 중간 값이 총수익
            if (RegExMatch(content, "align=right>(-?[\d,\.]+)</td><td[^>]*>.*?align=right>(-?[\d,\.]+)</td>", multiMatch)) {
                totalGrossProfit := StrReplace(multiMatch2, ",", "")
                totalGrossProfit := StrReplace(totalGrossProfit, " ", "")
            }
        }

        ; 총손실 (Gross Loss) 추출 - 개선된 패턴
        if (RegExMatch(content, "i)Gross\s*Loss.*?align=right>(-?[\d,\.]+)</td>", glMatch)) {
            totalGrossLoss := StrReplace(glMatch1, ",", "")
            totalGrossLoss := StrReplace(totalGrossLoss, " ", "")
        } else if (RegExMatch(content, "align=right>(-?[\d,\.]+)</td><td[^>]*>.*?align=right>-?([\d,\.]+)</td></tr>", lossMatch)) {
            ; 마지막 값이 총손실 (음수)
            lossVal := StrReplace(lossMatch2, ",", "")
            lossVal := StrReplace(lossVal, " ", "")
            if (lossVal + 0 > 0)
                totalGrossLoss := "-" . lossVal
            else
                totalGrossLoss := lossVal
        }

        ; 순이익, 총수익, 총손실을 한 번에 추출 (한국어 HTML 대응)
        ; 패턴: <td>총 순이익</td><td align=right>556.70</td><td>총수익</td><td align=right>6266.03</td><td>총손실</td><td align=right>-5709.33</td>
        if (RegExMatch(content, "<tr[^>]*><td[^>]*>.*?</td><td[^>]*align=right>(-?[\d,\.]+)</td><td[^>]*>.*?</td><td[^>]*align=right>(-?[\d,\.]+)</td><td[^>]*>.*?</td><td[^>]*align=right>(-?[\d,\.]+)</td></tr>", allMatch)) {
            ; 첫 번째: 순이익, 두 번째: 총수익, 세 번째: 총손실
            profit := StrReplace(allMatch1, ",", "")
            profit := StrReplace(profit, " ", "")

            if (totalGrossProfit = 0 || totalGrossProfit = "") {
                totalGrossProfit := StrReplace(allMatch2, ",", "")
                totalGrossProfit := StrReplace(totalGrossProfit, " ", "")
            }
            if (totalGrossLoss = 0 || totalGrossLoss = "") {
                totalGrossLoss := StrReplace(allMatch3, ",", "")
                totalGrossLoss := StrReplace(totalGrossLoss, " ", "")
            }
        } else if (RegExMatch(content, "i)Total\s*Net\s*Profit.*?align=right>(-?[\d,\.]+)</td>", profMatch)) {
            profit := StrReplace(profMatch1, ",", "")
            profit := StrReplace(profit, " ", "")
        } else if (RegExMatch(content, "i)Closed\s*P/L.*?(-?[\d,\.]+)", profMatch2)) {
            profit := StrReplace(profMatch2_1, ",", "")
        }

        ; 승률 추출 (한국어 HTML 대응)
        ; 패턴: <td>총 거래이익(won %)</td><td align=right>83 (71.08%)</td>
        if (RegExMatch(content, "won\s*%\)</td><td[^>]*align=right>\d+\s*\((\d+\.?\d*)%\)", winMatch)) {
            winRate := winMatch1 . "%"
        } else if (RegExMatch(content, "i)Profit\s*Trades.*?\((\d+\.?\d*)%\)", winMatch2)) {
            winRate := winMatch2_1 . "%"
        } else if (RegExMatch(content, "align=right>\d+\s*\((\d+\.?\d*)%\)</td><td[^>]*>", winMatch3)) {
            ; 숫자 (퍼센트%) 패턴
            winRate := winMatch3_1 . "%"
        }

        ; 최대 드로다운 추출 (한국어 HTML 대응)
        ; 패턴: <td>최대 상대 드로다운</td><td align=right>25.73% (2680.14)</td>
        if (RegExMatch(content, "align=right>(\d+\.?\d*)%\s*\([\d,\.]+\)</td></tr>", ddMatch)) {
            drawdown := ddMatch1
        } else if (RegExMatch(content, "i)Maximal\s*Drawdown.*?(\d+\.?\d*)\s*\((\d+\.?\d*)%\)", ddMatch2)) {
            drawdown := ddMatch2_2
        } else if (RegExMatch(content, "i)Relative\s*Drawdown.*?(\d+\.?\d*)%", ddMatch3)) {
            drawdown := ddMatch3_1
        } else if (RegExMatch(content, "align=right>(\d+\.?\d*)%", ddMatch4)) {
            ; 일반적인 % 패턴 (마지막 수단)
            drawdown := ddMatch4_1
        }
    }
    
    ; 상태 및 문제점 판단
    if (trades = 0 || trades = "") {
        status := "❌"
        issue := "거래 없음 - 진입조건 확인 필요"
        noTradeCount++
    } else if (profit + 0 > 0) {
        status := "✅"
        profitCount++
        totalProfit += profit
        
        if (drawdown + 0 > 20) {
            issue := "드로다운 " . drawdown . "% (위험)"
            highDDCount++
        } else if (drawdown + 0 > 10) {
            issue := "드로다운 " . drawdown . "% (주의)"
        } else {
            issue := "양호"
        }
    } else if (profit + 0 < 0) {
        status := "⚠️"
        issue := "손실 발생 - TP/SL 비율 확인"
        lossCount++
        totalProfit += profit
    } else {
        status := "➖"
        issue := "수익 없음"
    }
    
    ; 드로다운 최대값 갱신
    if (drawdown + 0 > maxDrawdown)
        maxDrawdown := drawdown
    
    ; 리스트에 추가
    profitStr := (profit != 0 && profit != "") ? Format("{:+.2f}", profit) : "0.00"
    grossProfitStr := (totalGrossProfit != 0 && totalGrossProfit != "") ? Format("{:+.2f}", totalGrossProfit) : "0.00"
    grossLossStr := (totalGrossLoss != 0 && totalGrossLoss != "") ? Format("{:+.2f}", totalGrossLoss) : "0.00"
    ddStr := (drawdown != 0 && drawdown != "") ? drawdown . "%" : "?"

    LV_Add("", idx, folderLabel, fileName, ea, symbol, tf, testPeriod, trades, grossProfitStr, grossLossStr, profitStr, winRate, ddStr, status, issue)

    ; 파일 경로 매핑 저장
    global filePathMap
    filePathMap[idx] := filePath

    ; 배열에 저장
    report := {}
    report.folder := folderLabel
    report.file := fileName
    report.filePath := filePath
    report.ea := ea
    report.symbol := symbol
    report.tf := tf
    report.testPeriod := testPeriod
    report.trades := trades
    report.grossProfit := totalGrossProfit
    report.grossLoss := totalGrossLoss
    report.profit := profit
    report.winRate := winRate
    report.drawdown := drawdown
    report.status := status
    report.issue := issue
    reportsArray.Push(report)
}

; =====================================================
; 리스트뷰 소팅
; =====================================================
ResultLV:
    global lvLastCol, lvSortOrder, filePathMap

    if (A_GuiEvent = "ColClick") {
        col := A_EventInfo

        ; 같은 컬럼을 다시 클릭하면 정렬 순서 반대로
        if (col = lvLastCol) {
            lvSortOrder := (lvSortOrder = "Asc") ? "Desc" : "Asc"
        } else {
            lvSortOrder := "Asc"
            lvLastCol := col
        }

        ; 숫자 컬럼: 8(거래수), 9(총수익), 10(총손실), 11(순이익), 13(드로다운)
        if (col = 8 || col = 9 || col = 10 || col = 11 || col = 13) {
            LV_ModifyCol(col, "Sort" . lvSortOrder . " Float")
        } else {
            ; 텍스트 컬럼
            LV_ModifyCol(col, "Sort" . lvSortOrder)
        }
    }

    ; 더블클릭 - 파일 열기
    else if (A_GuiEvent = "DoubleClick") {
        rowNum := A_EventInfo
        if (rowNum > 0) {
            LV_GetText(fileIdx, rowNum, 1)  ; # 컬럼에서 인덱스 가져오기
            if (filePathMap.HasKey(fileIdx)) {
                filePath := filePathMap[fileIdx]
                Run, %filePath%
            }
        }
    }

    ; 우클릭 - 컨텍스트 메뉴
    else if (A_GuiEvent = "RightClick") {
        rowNum := A_EventInfo
        if (rowNum > 0) {
            LV_GetText(fileIdx, rowNum, 1)  ; # 컬럼
            LV_GetText(fileName, rowNum, 3)  ; 파일명 컬럼

            Menu, ContextMenu, Add, 파일 열기, OpenFile
            Menu, ContextMenu, Add, 파일명 복사, CopyFileName
            Menu, ContextMenu, Add, 전체 경로 복사, CopyFilePath
            Menu, ContextMenu, Add
            Menu, ContextMenu, Add, 폴더에서 열기, OpenInFolder
            Menu, ContextMenu, Show
            Menu, ContextMenu, DeleteAll
        }
    }
return

; =====================================================
; 요약 생성
; =====================================================
GenerateSummary() {
    global totalFiles, noTradeCount, profitCount, lossCount, totalProfit, maxDrawdown, highDDCount
    
    summary := ""
    summary .= "📊 총 분석 파일: " . totalFiles . "개`n`n"
    
    summary .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n"
    summary .= "📈 수익 발생: " . profitCount . "개`n"
    summary .= "📉 손실 발생: " . lossCount . "개`n"
    summary .= "❌ 거래 없음: " . noTradeCount . "개`n"
    summary .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n`n"
    
    if (profitCount > 0 || lossCount > 0) {
        totalProfitStr := Format("{:+.2f}", totalProfit)
        summary .= "💰 총 순이익: $" . totalProfitStr . "`n"
        summary .= "📊 최대 드로다운: " . maxDrawdown . "%`n"
    }
    
    if (highDDCount > 0)
        summary .= "⚠️ 고위험 드로다운(>20%): " . highDDCount . "개`n"
    
    summary .= "`n"
    
    ; 권장사항
    summary .= "💡 권장사항:`n"
    
    if (noTradeCount > 0)
        summary .= "  • 거래 없는 EA: 진입조건/필터 완화 필요`n"
    
    if (highDDCount > 0)
        summary .= "  • 고위험 EA: 로트 축소, 마틴게일 레벨 감소`n"
    
    if (lossCount > profitCount && (profitCount + lossCount) > 0)
        summary .= "  • 손실 EA가 많음: TP/SL 비율 2:1 이상으로 조정`n"
    
    GuiControl,, SummaryText, %summary%
}

; =====================================================
; 리포트 저장
; =====================================================
ExportReport:
    if (totalFiles = 0) {
        MsgBox, 48, 알림, 분석된 데이터가 없습니다.
        return
    }
    
    FormatTime, timestamp, , yyyyMMdd_HHmmss
    reportPath := A_ScriptDir "\..\backtest_analysis_" . timestamp . ".txt"
    
    report := "═══════════════════════════════════════════════════════════════`n"
    report .= "           MT4 백테스트 분석 리포트 v1.1`n"
    report .= "           생성일시: " . A_Now . "`n"
    report .= "═══════════════════════════════════════════════════════════════`n`n"
    
    ; 요약
    GuiControlGet, summaryContent,, SummaryText
    report .= summaryContent . "`n`n"
    
    ; 상세 결과
    report .= "═══════════════════════════════════════════════════════════════`n"
    report .= "상세 분석 결과`n"
    report .= "═══════════════════════════════════════════════════════════════`n`n"
    
    for idx, r in reportsArray {
        report .= "──────────────────────────────────────────`n"
        report .= "[" . idx . "] " . r.file
        if (r.folder != "")
            report .= " (" . r.folder . ")"
        report .= "`n"
        report .= "──────────────────────────────────────────`n"
        report .= "  EA: " . r.ea . "`n"
        report .= "  심볼: " . r.symbol . " | TF: " . r.tf . "`n"
        report .= "  거래수: " . r.trades . "`n"
        report .= "  순이익: $" . r.profit . "`n"
        report .= "  승률: " . r.winRate . "`n"
        report .= "  드로다운: " . r.drawdown . "%`n"
        report .= "  상태: " . r.status . " " . r.issue . "`n"
        report .= "`n"
        
        ; 문제별 상세 분석
        if (r.trades = 0 || r.trades = "") {
            report .= "  ⚠️ [거래 없음 원인 분석]`n"
            report .= "    1. 진입 조건이 너무 엄격 (RSI/트렌드/패턴 필터 완화)`n"
            report .= "    2. 나스닥 연동 필터 확인 (UseNasdaqDirection=false)`n"
            report .= "    3. TradingTimeframe 설정 확인`n"
            report .= "    4. 히스토리 데이터 부족 확인`n"
            report .= "`n"
        } else if (r.profit + 0 < 0) {
            report .= "  ⚠️ [손실 원인 분석]`n"
            report .= "    1. TP/SL 비율 확인 (2:1 이상 권장)`n"
            report .= "    2. 마틴게일 레벨 축소 (2단계 이하)`n"
            report .= "    3. 로트 크기 감소`n"
            report .= "    4. 트렌드 필터 활성화 고려`n"
            report .= "`n"
        }
        
        if (r.drawdown + 0 > 20) {
            report .= "  ⚠️ [고위험 드로다운 해결책]`n"
            report .= "    1. RiskPerTrade 감소 (1% 이하)`n"
            report .= "    2. MaxPositions 감소 (3개 이하)`n"
            report .= "    3. MaxDrawdownPercent=10 설정`n"
            report .= "    4. 마틴게일 비활성화 고려`n"
            report .= "`n"
        }
    }
    
    ; 종합 권장사항
    report .= "═══════════════════════════════════════════════════════════════`n"
    report .= "종합 권장사항`n"
    report .= "═══════════════════════════════════════════════════════════════`n`n"
    
    if (noTradeCount > 0) {
        report .= "📌 거래 없음 해결:`n"
        report .= "  - UseNasdaqDirection=false (나스닥 필터 비활성화)`n"
        report .= "  - RSI_Oversold=30, RSI_Overbought=70 (범위 확장)`n"
        report .= "  - UseTrendFilter=false (테스트용)`n"
        report .= "`n"
    }
    
    if (lossCount > 0) {
        report .= "📌 손실 개선:`n"
        report .= "  - TP/SL 비율 2:1 이상 (예: TP200, SL100)`n"
        report .= "  - QuickProfitTarget 조정`n"
        report .= "  - MaxMartingaleLevels=2 이하`n"
        report .= "`n"
    }
    
    if (highDDCount > 0) {
        report .= "📌 드로다운 감소:`n"
        report .= "  - RiskPerTrade=1 (2%→1%)`n"
        report .= "  - MaxPositions=3 (5→3)`n"
        report .= "  - MaxFloatingLoss=300`n"
        report .= "`n"
    }
    
    report .= "`n═══════════════════════════════════════════════════════════════`n"
    report .= "분석 도구: MT4 백테스트 분석기 v1.1`n"
    report .= "═══════════════════════════════════════════════════════════════`n"
    
    ; 파일 저장
    FileDelete, %reportPath%
    FileAppend, %report%, %reportPath%, UTF-8
    
    if (ErrorLevel) {
        MsgBox, 48, 오류, 리포트 저장 실패
    } else {
        MsgBox, 64, 완료, 리포트가 저장되었습니다:`n%reportPath%
        Run, notepad.exe "%reportPath%"
    }
return

; =====================================================
; 새로고침
; =====================================================
RefreshList:
    Gosub, StartAnalysis
return

; =====================================================
; 폴더 열기
; =====================================================
OpenFolder:
    ; Templates 폴더 열기 (기본)
    Run, explorer.exe "%templatesPath%"
return

; =====================================================
; 컨텍스트 메뉴 - 파일 열기
; =====================================================
OpenFile:
    global filePathMap
    rowNum := LV_GetNext(0, "Focused")
    if (rowNum > 0) {
        LV_GetText(fileIdx, rowNum, 1)
        if (filePathMap.HasKey(fileIdx)) {
            filePath := filePathMap[fileIdx]
            Run, %filePath%
        }
    }
return

; =====================================================
; 컨텍스트 메뉴 - 파일명 복사
; =====================================================
CopyFileName:
    rowNum := LV_GetNext(0, "Focused")
    if (rowNum > 0) {
        LV_GetText(fileName, rowNum, 3)
        Clipboard := fileName
        ToolTip, 파일명 복사됨: %fileName%
        SetTimer, RemoveToolTip, 1500
    }
return

; =====================================================
; 컨텍스트 메뉴 - 전체 경로 복사
; =====================================================
CopyFilePath:
    global filePathMap
    rowNum := LV_GetNext(0, "Focused")
    if (rowNum > 0) {
        LV_GetText(fileIdx, rowNum, 1)
        if (filePathMap.HasKey(fileIdx)) {
            filePath := filePathMap[fileIdx]
            Clipboard := filePath
            ToolTip, 전체 경로 복사됨: %filePath%
            SetTimer, RemoveToolTip, 1500
        }
    }
return

; =====================================================
; 컨텍스트 메뉴 - 폴더에서 열기
; =====================================================
OpenInFolder:
    global filePathMap
    rowNum := LV_GetNext(0, "Focused")
    if (rowNum > 0) {
        LV_GetText(fileIdx, rowNum, 1)
        if (filePathMap.HasKey(fileIdx)) {
            filePath := filePathMap[fileIdx]
            Run, explorer.exe /select`,"%filePath%"
        }
    }
return

; =====================================================
; 툴팁 제거
; =====================================================
RemoveToolTip:
    SetTimer, RemoveToolTip, Off
    ToolTip
return

; =====================================================
; 5분 후 자동 닫기 (v8.0 추가)
; =====================================================
AutoCloseAnalyzer:
    SetTimer, AutoCloseAnalyzer, Off
    Gui, Destroy
    ExitApp
return

; =====================================================
; 폴더 추가
; =====================================================
AddFolder:
    FileSelectFolder, selectedFolder, , 3, 분석할 HTML 파일이 있는 폴더를 선택하세요

    if (ErrorLevel) {
        return  ; 사용자가 취소함
    }

    if (!FileExist(selectedFolder)) {
        MsgBox, 48, 오류, 선택한 폴더가 존재하지 않습니다.
        return
    }

    ; 중복 확인
    for index, folder in additionalFolders {
        if (folder = selectedFolder) {
            MsgBox, 48, 알림, 이미 추가된 폴더입니다.
            return
        }
    }

    ; 폴더 추가
    additionalFolders.Push(selectedFolder)
    MsgBox, 64, 완료, 폴더가 추가되었습니다:`n%selectedFolder%`n`n자동으로 분석을 시작합니다.

    ; 자동 분석 시작
    Gosub, StartAnalysis
return

; =====================================================
; GUI 이벤트
; =====================================================
GuiClose:
    ExitApp
return

GuiEscape:
    ExitApp
return

GuiSize:
    if (A_EventInfo = 1)
        return
    
    ; 창 크기에 맞게 리스트뷰 조정
    newWidth := A_GuiWidth - 20
    newHeight := A_GuiHeight - 350
    if (newHeight < 100)
        newHeight := 100
    
    GuiControl, Move, ResultLV, w%newWidth% h%newHeight%
return
