"""
r1_dashboard.py — R1 백테스트 실시간 모니터링 대시보드
자동 refresh, 에러 감지, 진행률 표시
"""

import os
import sys
import time
import glob
import subprocess
import configparser
from datetime import datetime, timedelta

# ── 경로 설정 ────────────────────────────────────────────────
BASE         = r"C:\NEWOPTIMISER\LOCAL_WORKER8.1"
INI_PATH     = os.path.join(BASE, "configs", "current_config.ini")
LOG_4STEPS   = os.path.join(BASE, "scripts", "simple_4steps_v2_log.txt")
LOG_SOLO     = os.path.join(BASE, "scripts", "solo_run_log.txt")
HTML_OUT     = r"D:\2026NEWOPTMIZER\OPT_ROUNDS\R01"
REPORT_BASE  = r"D:\2026NEWOPTMIZER"
TERMINAL_EXE = "terminal.exe"
REFRESH_SEC  = 5   # 갱신 주기

# ── ANSI 색상 ────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE  = "\033[44m"
    BG_DARK  = "\033[40m"

def clear():
    os.system("cls")

def ts():
    return datetime.now().strftime("%H:%M:%S")

def bar(pct, width=40):
    filled = int(width * pct / 100)
    b = "█" * filled + "░" * (width - filled)
    return f"[{b}] {pct:.1f}%"

def age_str(seconds):
    if seconds < 60:
        return f"{int(seconds)}초"
    elif seconds < 3600:
        return f"{int(seconds/60)}분 {int(seconds%60)}초"
    else:
        return f"{int(seconds/3600)}시간 {int((seconds%3600)/60)}분"

# ── INI 읽기 ─────────────────────────────────────────────────
def read_ini():
    cfg = configparser.RawConfigParser()
    cfg.read(INI_PATH, encoding="utf-8")
    return cfg

def get_combo_status(cfg):
    try:
        cur   = int(cfg.get("bt_combo", "current_index"))
        total = int(cfg.get("bt_combo", "total"))
        ea    = cfg.get("bt_combo", "ea_name").strip()
        lot   = cfg.get("bt_combo", "lot").strip()
        sl    = cfg.get("bt_combo", "sl").strip()
        tp    = cfg.get("bt_combo", "tp").strip()
        tf    = cfg.get("bt_combo", "tf").strip()
        return cur, total, ea, lot, sl, tp, tf
    except:
        return 0, 0, "N/A", "N/A", "N/A", "N/A", "N/A"

def get_symbol_period(cfg):
    try:
        sym = cfg.get("current_backtest", "symbol").strip()
        per = cfg.get("current_backtest", "period").strip()
        return sym, per
    except:
        return "N/A", "N/A"

def get_test_date(cfg):
    try:
        f = cfg.get("test_date", "from_date1").strip()
        t = cfg.get("test_date", "to_date1").strip()
        return f, t
    except:
        return "N/A", "N/A"

# ── HTML 리포트 탐색 ──────────────────────────────────────────
def find_latest_html():
    latest_time = 0
    latest_file = None
    count = 0
    for base in [HTML_OUT, REPORT_BASE]:
        if not base or not os.path.exists(base):
            continue
        for ext in ("*.htm", "*.html"):
            for f in glob.glob(os.path.join(base, "**", ext), recursive=True):
                count += 1
                try:
                    mt = os.path.getmtime(f)
                    if mt > latest_time:
                        latest_time = mt
                        latest_file = f
                except:
                    pass
    return latest_file, latest_time, count

# ── MT4 실행 확인 ─────────────────────────────────────────────
def is_mt4_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/fi", f"imagename eq {TERMINAL_EXE}"],
            stderr=subprocess.DEVNULL, encoding="cp949"
        )
        return TERMINAL_EXE.lower() in out.lower()
    except:
        return False

# ── 로그 파일 읽기 ────────────────────────────────────────────
def tail_file(path, n=15):
    if not os.path.exists(path):
        return [], 0
    try:
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-n:]], size
    except:
        return [], 0

def count_errors(path, tail=200):
    if not os.path.exists(path):
        return 0, []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-tail:]
        errors = [l.strip() for l in lines if "[ERROR]" in l or "ERROR:" in l]
        return len(errors), errors[-5:]
    except:
        return 0, []

# ── solo_run_log 에서 최신 Combo 줄 추출 ─────────────────────
def get_latest_combo_from_log():
    lines, _ = tail_file(LOG_SOLO, 50)
    for line in reversed(lines):
        if "Combo " in line and "/" in line:
            return line
    return None

# ── 플래그 상태 ───────────────────────────────────────────────
FLAG_PATH = os.path.join(BASE, "configs", "test_completed.flag")
def flag_age():
    if not os.path.exists(FLAG_PATH):
        return None
    return time.time() - os.path.getmtime(FLAG_PATH)

# ── 대시보드 출력 ─────────────────────────────────────────────
def draw(refresh_count):
    clear()
    now = datetime.now()
    cfg = read_ini()

    cur, total, ea, lot, sl, tp, tf = get_combo_status(cfg)
    sym, per = get_symbol_period(cfg)
    from_d, to_d = get_test_date(cfg)
    mt4 = is_mt4_running()
    latest_html, latest_time, html_count = find_latest_html()
    html_age = time.time() - latest_time if latest_time else 9999
    err_count, err_lines = count_errors(LOG_4STEPS)
    flag_sec = flag_age()
    latest_combo_log = get_latest_combo_from_log()
    solo_lines, solo_size = tail_file(LOG_SOLO, 8)
    steps_lines, steps_size = tail_file(LOG_4STEPS, 8)

    pct = (cur / total * 100) if total > 0 else 0

    # 상태 판정
    if not mt4:
        status_str = f"{C.BG_RED}{C.WHITE} ❌ MT4 미실행 {C.RESET}"
        status_col = C.RED
    elif html_age > 120:
        status_str = f"{C.YELLOW}⚠  HTML {age_str(html_age)} 미갱신{C.RESET}"
        status_col = C.YELLOW
    elif err_count > 0:
        status_str = f"{C.YELLOW}⚠  에러 {err_count}개 감지{C.RESET}"
        status_col = C.YELLOW
    else:
        status_str = f"{C.BG_GREEN}{C.WHITE} ✅ 정상 진행 중 {C.RESET}"
        status_col = C.GREEN

    # ═══════════════ 헤더 ═══════════════
    w = 76
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}" + "=" * w + C.RESET)
    title = "  R1 BackTest Monitor"
    right = f"Update: {now.strftime('%H:%M:%S')}  #{refresh_count}"
    pad = w - len(title) - len(right) - 2
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}{title}" + " " * pad + f"{right}  {C.RESET}")
    print(f"{C.BG_BLUE}{C.WHITE}" + "=" * w + C.RESET)

    # ═══════════════ 상태 & 진행률 ═══════════════
    print(f"\n  상태: {status_str}")
    print()

    if total > 0:
        progress_bar = bar(pct)
        print(f"  {C.BOLD}진행률{C.RESET}  {C.CYAN}{progress_bar}{C.RESET}")
        print(f"  {C.BOLD}콤보{C.RESET}    {C.WHITE}{cur} / {total}{C.RESET}  ({C.GRAY}완료 {cur-1}, 남음 {total-cur+1}{C.RESET})")
    else:
        print(f"  {C.GRAY}콤보 정보 없음 (아직 시작 안 됨){C.RESET}")

    # ═══════════════ 현재 테스트 정보 ═══════════════
    print()
    print(f"  {C.BOLD}{'─'*70}{C.RESET}")
    print(f"  {C.BOLD}현재 EA{C.RESET}  {C.YELLOW}{ea}{C.RESET}")
    print(f"  {C.BOLD}설정{C.RESET}     Symbol={C.CYAN}{sym}{C.RESET}  TF={C.CYAN}{tf}{C.RESET}  Lot={lot}  SL={sl}  TP={tp}")
    print(f"  {C.BOLD}기간{C.RESET}     {from_d} ~ {to_d}")

    if latest_combo_log:
        print(f"  {C.BOLD}로그{C.RESET}     {C.GRAY}{latest_combo_log}{C.RESET}")

    # ═══════════════ HTML 리포트 상태 ═══════════════
    print()
    print(f"  {C.BOLD}{'─'*70}{C.RESET}")
    html_col = C.GREEN if html_age < 120 else C.RED
    print(f"  {C.BOLD}HTML{C.RESET}    누적 {html_count}개  |  최종 생성 {html_col}{age_str(html_age)} 전{C.RESET}")
    if latest_html:
        fname = os.path.basename(latest_html)
        print(f"  {C.GRAY}        {fname}{C.RESET}")

    # ═══════════════ MT4 & 플래그 ═══════════════
    mt4_str = f"{C.GREEN}✅ 실행 중{C.RESET}" if mt4 else f"{C.RED}❌ 미실행{C.RESET}"
    flag_str = f"{C.GREEN}{age_str(flag_sec)} 전{C.RESET}" if flag_sec is not None else f"{C.GRAY}없음{C.RESET}"
    print(f"  {C.BOLD}MT4{C.RESET}     {mt4_str}   |   {C.BOLD}완료플래그{C.RESET} {flag_str}")

    # ═══════════════ 에러 감지 ═══════════════
    if err_count > 0:
        print()
        print(f"  {C.RED}{C.BOLD}⚠  에러 {err_count}개 감지 (최근 5개):{C.RESET}")
        for e in err_lines:
            print(f"  {C.RED}  ▸ {e}{C.RESET}")

    # ═══════════════ solo_run_log (최근 8줄) ═══════════════
    print()
    print(f"  {C.BOLD}{'─'*70}{C.RESET}")
    print(f"  {C.BOLD}SOLO 로그{C.RESET}  {C.GRAY}({solo_size//1024}KB){C.RESET}")
    for ln in solo_lines:
        col = C.RED if "ERROR" in ln or "ERR" in ln else C.GRAY
        print(f"  {col}{ln[:72]}{C.RESET}")

    # ═══════════════ 4steps 로그 (최근 8줄) ═══════════════
    print()
    print(f"  {C.BOLD}4STEPS 로그{C.RESET}  {C.GRAY}({steps_size//1024}KB){C.RESET}")
    for ln in steps_lines:
        col = C.RED if "[ERROR]" in ln or "ERROR:" in ln else C.GRAY
        print(f"  {col}{ln[:72]}{C.RESET}")

    # ═══════════════ 푸터 ═══════════════
    print()
    print(f"  {C.GRAY}{'─'*70}{C.RESET}")
    print(f"  {C.GRAY}출력경로: {HTML_OUT}{C.RESET}")
    print(f"  {C.GRAY}Ctrl+C 로 중단  |  갱신주기: {REFRESH_SEC}초{C.RESET}")
    print()

# ── 메인 루프 ─────────────────────────────────────────────────
def main():
    # Windows UTF-8 + ANSI 색상 활성화
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.system("color")

    count = 0
    print(f"R1 대시보드 시작 중...")
    time.sleep(0.5)

    try:
        while True:
            count += 1
            draw(count)
            time.sleep(REFRESH_SEC)
    except KeyboardInterrupt:
        clear()
        print(f"\n{C.CYAN}대시보드 종료됨.{C.RESET}\n")

if __name__ == "__main__":
    main()
