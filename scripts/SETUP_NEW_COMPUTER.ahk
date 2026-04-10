#NoEnv
#SingleInstance Force

; =====================================================
; MT4 백테스트 자동화 - 새 컴퓨터 설정 도구 v3.4
; 컴퓨터 변경 시 이 스크립트만 실행하면 모든 경로 자동 업데이트
; v3.4: SET 파일 선택사항 (없어도 진행 가능)
; v3.4.1: 윈도우 크기 조정 추가, 경로 문제 수정
; =====================================================

; v3.4: 상위 폴더의 configs 사용 (A_ScriptDir = scripts 폴더)
parentFolder := A_ScriptDir "\.."
configsFolder := parentFolder "\configs"

; configs 폴더 없으면 생성
IfNotExist, %configsFolder%
    FileCreateDir, %configsFolder%

iniFile := configsFolder "\current_config.ini"

; =====================================================
; 기존 설정 읽기
; =====================================================
IniRead, existingTermPath, %iniFile%, folders, terminal_path, NONE
IniRead, existingEAPath, %iniFile%, folders, ea_path, NONE
IniRead, existingSetPath, %iniFile%, folders, setfiles_path, NONE
IniRead, existingHtmlPath, %iniFile%, folders, html_save_path, NONE

; 기존 설정이 있는지 확인
hasExistingConfig := (existingTermPath != "NONE" and existingTermPath != "" and existingTermPath != "ERROR")

; 기존 설정이 있으면 먼저 보여주기
if (hasExistingConfig) {
    MsgBox, 36, 기존 설정 발견,
    (
    이미 설정된 내용을 발견했습니다:

    터미널: %existingTermPath%
    EA 폴더: %existingEAPath%
    SET 파일: %existingSetPath%
    HTML 저장: %existingHtmlPath%

    이 설정을 그대로 사용하시겠습니까?
    Yes = 기존 설정 유지
    No = 새로 설정
    )
    IfMsgBox Yes
    {
        MsgBox, 64, 설정 유지, 기존 설정을 그대로 유지합니다.
        ExitApp
    }
}

MsgBox, 64, 새 컴퓨터 설정 v3.4,
(
MT4 백테스트 자동화 - 새 컴퓨터 설정

이 도구는 다음을 설정합니다:
1. MT4 터미널 경로 (필수)
2. EA 폴더 경로 (필수)
3. SET 파일 경로 (선택 - 없어도 OK)
4. HTML 저장 경로 (필수)

계속하려면 OK를 클릭하세요.
)

; =====================================================
; STEP 1: MT4 터미널 폴더 선택
; =====================================================
FileSelectFolder, terminalPath, C:\Users\%A_UserName%\AppData\Roaming\MetaQuotes\Terminal, 3, MT4 터미널 폴더를 선택하세요 (예: 43C02898...)

if (ErrorLevel or terminalPath = "") {
    MsgBox, 16, 오류, 터미널 폴더가 선택되지 않았습니다.`n`n설정을 취소합니다.
    ExitApp
}

; 터미널 ID 추출 (마지막 폴더 이름)
SplitPath, terminalPath, terminalID

; 경로를 슬래시로 변환
StringReplace, terminalPathSlash, terminalPath, \, /, All

; =====================================================
; STEP 2: EA 폴더 자동 감지 (필수)
; =====================================================
eaPath := terminalPath "\MQL4\Experts"
eaCount := 0

IfExist, %eaPath%
{
    Loop, %eaPath%\*.ex4
        eaCount++
}

if (eaCount > 0) {
    MsgBox, 36, EA 폴더 확인,
    (
    EA 폴더를 찾았습니다:
    %eaPath%

    EA 파일: %eaCount%개

    이 경로를 사용하시겠습니까?
    )
    IfMsgBox No
    {
        FileSelectFolder, eaPath, %terminalPath%, 3, EA 파일(*.ex4)이 있는 폴더를 선택하세요:
        if (ErrorLevel or eaPath = "") {
            MsgBox, 16, 오류, EA 폴더가 선택되지 않았습니다.
            ExitApp
        }
    }
} else {
    MsgBox, 48, EA 폴더 선택,
    (
    기본 경로에서 EA 파일을 찾을 수 없습니다.

    EA 파일(*.ex4)이 있는 폴더를 선택해주세요.
    )
    FileSelectFolder, eaPath, %terminalPath%, 3, EA 파일(*.ex4)이 있는 폴더를 선택하세요:
    if (ErrorLevel or eaPath = "") {
        MsgBox, 16, 오류, EA 폴더가 선택되지 않았습니다.
        ExitApp
    }
}

StringReplace, eaPathSlash, eaPath, \, /, All

; =====================================================
; STEP 3: SET 파일 폴더 (선택사항)
; =====================================================
MsgBox, 36, SET 파일 폴더,
(
SET 파일을 사용하시겠습니까?

Yes = SET 파일 폴더 선택
No = SET 파일 없이 진행 (EA 기본설정 사용)

※ SET 파일 없이도 백테스트 가능합니다.
)

IfMsgBox Yes
{
    ; SET 파일 폴더 찾기
    possiblePaths := []
    possiblePaths.Push(terminalPath "\MQL4\Files\BY_STRATEGY")
    possiblePaths.Push(terminalPath "\tester")

    foundPath := ""
    foundCount := 0

    Loop, % possiblePaths.Length()
    {
        testPath := possiblePaths[A_Index]
        IfExist, %testPath%
        {
            Loop, %testPath%\*.set
                foundCount++
            if (foundCount > 0) {
                foundPath := testPath
                break
            }
            foundCount := 0
        }
    }

    if (foundPath != "" and foundCount > 0) {
        MsgBox, 36, SET 파일 발견,
        (
        SET 파일을 찾았습니다:
        %foundPath%

        SET 파일: %foundCount%개

        이 경로를 사용하시겠습니까?
        )
        IfMsgBox Yes
            setfilesPath := foundPath
        Else
        {
            FileSelectFolder, setfilesPath, %terminalPath%, 3, SET 파일 폴더 선택:
            if (ErrorLevel or setfilesPath = "")
                setfilesPath := ""
        }
    } else {
        FileSelectFolder, setfilesPath, %terminalPath%, 3, SET 파일 폴더 선택 (없으면 취소):
        if (ErrorLevel or setfilesPath = "")
            setfilesPath := ""
    }
}
Else
{
    setfilesPath := ""
}

if (setfilesPath != "")
    StringReplace, setfilesPathSlash, setfilesPath, \, /, All
else
    setfilesPathSlash := ""

; =====================================================
; STEP 4: HTML 저장 경로 (templates 폴더)
; =====================================================
htmlSavePath := terminalPath "\templates"

IfNotExist, %htmlSavePath%
    FileCreateDir, %htmlSavePath%

; =====================================================
; STEP 5: INI 파일 업데이트
; =====================================================
IniWrite, %terminalPathSlash%, %iniFile%, folders, terminal_path
IniWrite, %eaPathSlash%, %iniFile%, folders, ea_path
IniWrite, %setfilesPathSlash%, %iniFile%, folders, setfiles_path
IniWrite, %htmlSavePath%, %iniFile%, folders, html_save_path
IniWrite, %terminalID%, %iniFile%, folders, terminal_id

; SET 파일 사용 여부 설정
if (setfilesPath = "")
    IniWrite, 0, %iniFile%, selection, useSetFiles
else
    IniWrite, 1, %iniFile%, selection, useSetFiles

; =====================================================
; STEP 6: MT4 윈도우 크기 조정
; =====================================================
MsgBox, 36, 윈도우 크기 조정,
(
MT4 Strategy Tester 창 크기를 설정하시겠습니까?

Yes = 지금 설정 (MT4가 열려있어야 함)
No = 나중에 설정

※ 창 크기가 올바르지 않으면 좌표 클릭이
   정확하지 않을 수 있습니다.
)

IfMsgBox Yes
{
    ; MT4 창 찾기
    WinGet, mt4List, List, ahk_class MetaQuotes::MetaTrader::4.00

    if (mt4List = 0) {
        MsgBox, 48, MT4 없음, MT4 터미널이 실행되지 않았습니다.`n`nMT4를 실행한 후 MENU에서 "2단계: 좌표 설정"을 실행하세요.
    } else {
        ; 첫 번째 MT4 창 활성화
        mt4ID := mt4List1
        WinActivate, ahk_id %mt4ID%
        WinWait, ahk_id %mt4ID%,, 3

        ; 창 크기 조정 (960x1036 - v3.2 기준)
        MsgBox, 36, 창 크기 선택,
        (
        MT4 창 크기를 선택하세요:

        Yes = 960x1036 (좌측 절반 - 권장)
        No = 현재 크기 유지
        )

        IfMsgBox Yes
        {
            WinMove, ahk_id %mt4ID%,, 0, 0, 960, 1036
            Sleep, 500

            WinGetPos, x, y, w, h, ahk_id %mt4ID%
            MsgBox, 64, 창 크기 조정 완료, MT4 창 크기가 조정되었습니다.`n`n위치: %x%, %y%`n크기: %w% x %h%`n`n(v3.2 기준: 960 x 1036)
        }
    }
}

; =====================================================
; 완료 메시지
; =====================================================
setStatus := (setfilesPath != "") ? setfilesPathSlash : "(사용 안함 - EA 기본설정)"

MsgBox, 64, 설정 완료,
(
새 컴퓨터 설정이 완료되었습니다!

터미널 ID: %terminalID%
EA 폴더: %eaPathSlash%
SET 파일: %setStatus%
HTML 저장: %htmlSavePath%

※ 다음 단계:
1. MENU_v3.4.ahk 실행
2. "1단계: 컨트롤 감지" 실행
3. "2단계: 좌표 설정" 실행
4. "3단계: Symbol 읽기" 실행
)

ExitApp
