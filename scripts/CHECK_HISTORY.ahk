#NoEnv
#SingleInstance Force
SetWorkingDir, %A_ScriptDir%\..

; =====================================================
; MT4 히스토리 데이터 확인 (CHECK_HISTORY)
; - .hst 파일을 읽어 데이터 시작일/종료일 확인
; =====================================================

iniFile := A_WorkingDir "\configs\current_config.ini"

; 터미널 경로 읽기
IniRead, terminalPath, %iniFile%, folders, terminal_path, NOTSET

historyPath := ""
if (terminalPath != "NOTSET" && terminalPath != "") {
    StringReplace, terminalPathWin, terminalPath, /, \, All
    historyPath := terminalPathWin "\history"
}

; GUI 생성
Gui, Margin, 10, 10
Gui, Font, s11 Bold
Gui, Add, Text, w500 Center, 📅 MT4 히스토리 데이터 점검

Gui, Font, s9 Normal
Gui, Add, Text, w500 y+10, 1. 터미널의 history 폴더를 선택하세요. (서버 폴더)
Gui, Add, Edit, vHistoryFolderEdit w400 h25 ReadOnly, %historyPath%
Gui, Add, Button, gSelectHistoryFolder x+5 yp w90 h25, 📂 폴더 선택

Gui, Add, Text, x10 w500 y+10, 2. 파일(.hst)을 선택하면 기간을 확인합니다.
Gui, Font, s9
Gui, Add, ListView, vHSTList gOnHSTSelect w500 h300 Grid, 파일명|크기|시작일 (Oldest)|종료일 (Newest)|데이터(Bar) 수

Gui, Font, s9 Bold
Gui, Add, Text, vFileInfoText w500 y+10 cBlue, 파일을 선택해주세요.

Gui, Font, s9 Normal
Gui, Add, Text, w500 y+10 cGray, * 날짜가 1970년으로 나오면 데이터가 손상되었거나 형식이 다를 수 있습니다.

Gui, Add, Button, gExitApp x10 w500 h30 y+10, 닫기

; 초기 자동 로드 시도
if (historyPath != "" && InStr(FileExist(historyPath), "D")) {
    ; history 폴더 안에 하위 폴더(서버명)가 있는지 확인
    foundSub := false
    Loop, %historyPath%\*, 2
    {
        ; 첫 번째 발견된 서버 폴더 자동 선택
        historyPath := A_LoopFileFullPath
        foundSub := true
        break
    }
    
    if (foundSub) {
        GuiControl,, HistoryFolderEdit, %historyPath%
        Gosub, LoadHSTFiles
    }
}

Gui, Show, , 히스토리 데이터 확인
return

; =====================================================
; 폴더 선택
; =====================================================
SelectHistoryFolder:
    FileSelectFolder, sel, *%historyPath%, 3, history 내의 서버 폴더 선택 (예: history\DemoServer)
    if (sel != "") {
        historyPath := sel
        GuiControl,, HistoryFolderEdit, %historyPath%
        Gosub, LoadHSTFiles
    }
return

; =====================================================
; HST 파일 목록 로드
; =====================================================
LoadHSTFiles:
    LV_Delete()
    GuiControl, -Redraw, HSTList
    
    Loop, %historyPath%\*.hst
    {
        ; 파일 크기 (KB)
        sizeKB := Round(A_LoopFileSize / 1024)
        
        ; 미리 파싱하여 리스트에 바로 표시
        res := ParseHST(A_LoopFileFullPath)
        
        if (IsObject(res)) {
            LV_Add("", A_LoopFileName, sizeKB . " KB", res.startDT, res.endDT, res.count)
        } else {
            LV_Add("", A_LoopFileName, sizeKB . " KB", "?", "?", "0")
        }
    }
    
    ; 컬럼 너비 및 정렬 설정 (타이틀 유지하도록 옵션만 수정)
    LV_ModifyCol(1, 150) ; 파일명
    LV_ModifyCol(2, "60 Integer") ; 크기 (Size=60, Sort=Integer)
    LV_ModifyCol(3, 110) ; 시작일
    LV_ModifyCol(4, 110) ; 종료일
    LV_ModifyCol(5, "80 Integer") ; 개수 (Size=80, Sort=Integer)
    
    GuiControl, +Redraw, HSTList
return

; =====================================================
; HST 파일 선택 시 상세 분석
; =====================================================
OnHSTSelect:
    if (A_GuiEvent != "Normal" && A_GuiEvent != "K")
        return
        
    LV_GetText(fileName, A_EventInfo, 1)
    if (fileName = "")
        return
        
    fullPath := historyPath "\" fileName
    
    ; 파일 분석
    res := ParseHST(fullPath)
    
    ; 리스트 업데이트
    if (IsObject(res)) {
        LV_Modify(A_EventInfo, "Col3", res.startDT)
        LV_Modify(A_EventInfo, "Col4", res.endDT)
        LV_Modify(A_EventInfo, "Col5", res.count)
        
        GuiControl,, FileInfoText, % fileName . ": " . res.count . "개 바 (`n" . res.startDT . " ~ " . res.endDT . ")"
    } else {
         GuiControl,, FileInfoText, 파일 분석 실패
    }
return

; =====================================================
; HST 파싱 함수 (MT4 Build 600+)
; =====================================================
ParseHST(filePath) {
    result := {startDT: "?", endDT: "?", count: 0}
    
    file := FileOpen(filePath, "r")
    if !file
        return result
    
    ; 버전 확인 (첫 4바이트)
    file.Seek(0, 0)
    version := file.ReadInt()
    
    headerSize := 148
    recordSize := 60 ; Build 600+ (Version 401)
    isOldVersion := false
    
    if (version < 401) {
        recordSize := 44 ; Old format (Version 400)
        isOldVersion := true
    }
    
    file.Seek(0, 2) ; End
    fileSize := file.Pos
    
    if (fileSize < headerSize) {
        file.Close()
        return result
    }
    
    totalRecords := (fileSize - headerSize) // recordSize
    
    if (totalRecords <= 0) {
        file.Close()
        return result
    }
    
    result.count := totalRecords
    
    ; 첫 번째 레코드 (가장 오래된 날짜)
    file.Seek(headerSize, 0)
    if (isOldVersion)
        firstTime := file.ReadUInt()  ; Old: 4byte time
    else
        firstTime := file.ReadInt64() ; New: 8byte time
    
    ; 마지막 레코드 (가장 최근 날짜)
    file.Seek(headerSize + (totalRecords - 1) * recordSize, 0)
    if (isOldVersion)
        lastTime := file.ReadUInt()
    else
        lastTime := file.ReadInt64()
    
    file.Close()
    
    ; Unix Time -> YYYY.MM.DD
    result.startDT := UnixToDate(firstTime)
    result.endDT := UnixToDate(lastTime)
    
    return result
}

UnixToDate(unixTime) {
    if (unixTime = 0)
        return "N/A"
        
    time := 19700101000000
    time += unixTime, s
    FormatTime, res, %time%, yyyy.MM.dd
    return res
}

ExitApp:
GuiClose:
    ExitApp
return
