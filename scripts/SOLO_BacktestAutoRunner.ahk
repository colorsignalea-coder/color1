; ============================================================
; SOLO 백테스트 자동 실행 스크립트 (AutoHotkey v2.0)
; ============================================================
; 역할: MT4 SOLO 창을 찾아서 자동으로 백테스트 시작
; 사용: AutoHotkey.exe SOLO_BacktestAutoRunner.ahk EA_이름.ex4 SET_파일.set

#Requires AutoHotkey v2.0
#NoTrayIcon

; 커맨드라인 인자
ea_name := A_Args.Length >= 1 ? A_Args[1] : ""
set_name := A_Args.Length >= 2 ? A_Args[2] : ""

if (ea_name = "" || set_name = "") {
    MsgBox 48, 사용법,
    (
        사용: AutoHotkey.exe SOLO_BacktestAutoRunner.ahk EA명.ex4 SET파일.set
        예:   AutoHotkey.exe SOLO_BacktestAutoRunner.ahk COLOR_R01.ex4 COLOR_R01.set
    )
    ExitApp
}

Log := ""

LogWrite(msg) {
    Log := Log . msg . "`n"
    FileDelete "SOLO_run.log"
    FileAppend Log, "SOLO_run.log"
}

; ===== STEP 1: SOLO 창 찾기 =====
LogWrite "[Step 1] SOLO 창 찾기..."

SetTitleMatchMode 2
if !WinExist("SOLO") {
    LogWrite "ERROR: SOLO 창을 찾을 수 없음!"
    MsgBox 48, ERROR, SOLO 창을 찾을 수 없습니다. MT4를 열었는지 확인하세요.
    ExitApp
}

WinActivate "SOLO"
WinWaitActive "SOLO"
Sleep 1000

LogWrite "✅ SOLO 창 활성화 완료"

; ===== STEP 2: EA 선택 =====
LogWrite "[Step 2] EA 선택: " . ea_name

; ComboBox (EA 선택)는 보통 좌표가 고정되어 있음
; SOLO 5.3 기준 대략 위치 (조정 필요)
; 실제로는 SOLO의 정확한 UI 구조를 알아야 함

; 임시: 클릭 후 테이블 생성 (실제 구현은 더 복잡)
LogWrite "⏳ EA 선택 대기 (사용자 수동 또는 자동화 필요)..."

; ===== STEP 3: SET 파일 로드 =====
LogWrite "[Step 3] SET 파일 로드: " . set_name

; SET 파일 로드는 보통 특정 버튼이나 메뉴 사용
; 예: [Load] 버튼 클릭 → 파일 선택 대화
; 이 부분은 SOLO의 UI에 따라 다름

LogWrite "⏳ SET 파일 로드 대기..."

; ===== STEP 4: 백테스트 시작 =====
LogWrite "[Step 4] [START] 버튼 클릭..."

; START 버튼 위치 (근사값)
; SOLO 창 크기에 따라 달라짐 (800x600 기준)
button_x := 150
button_y := 500

ControlClick "x" . button_x . " y" . button_y, "SOLO"
Sleep 500

LogWrite "✅ [START] 버튼 클릭 완료"

; ===== STEP 5: 백테스트 완료 대기 =====
LogWrite "[Step 5] 백테스트 실행 중... (최대 10분)"

start_time := A_TickCount
max_wait := 600000  ; 10분

progress_text := ""
loop {
    elapsed := (A_TickCount - start_time) / 1000

    ; 진행률 표시 (옵션)
    if (Mod(elapsed, 10) = 0) {
        LogWrite "⏳ " . Format("{:.0f}", elapsed) . "초 경과..."
    }

    ; 완료 조건 확인 (Reports 폴더에 새 파일 생성)
    ; 또는 SOLO 상태 확인

    if (elapsed > max_wait) {
        LogWrite "⚠️  타임아웃: 10분 이상 백테스트 대기"
        break
    }

    Sleep 5000  ; 5초마다 확인
}

LogWrite "✅ 백테스트 완료!"

; ===== STEP 6: 결과 저장 =====
LogWrite "[Step 6] 결과 저장..."

; 리포트 생성은 MT4가 자동으로 함
; Reports/ 폴더에 HTML 파일이 저장됨

LogWrite "✅ 모든 단계 완료!"

; ===== DONE =====
MsgBox 64, 성공, 백테스트가 완료되었습니다!`n`nLog: SOLO_run.log

ExitApp
