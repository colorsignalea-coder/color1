"""
set_mt4_dates.py — MT4 Strategy Tester DateTimePicker 직접 설정
Usage: python set_mt4_dates.py YYYY.MM.DD YYYY.MM.DD
Sends DTM_SETSYSTEMTIME message to SysDateTimePick321/322 controls
"""
import sys
import ctypes
import ctypes.wintypes as wintypes
import win32gui
import win32con
import configparser
import os

# ── 설정 ─────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INI     = os.path.join(BASE, "configs", "current_config.ini")
LOG     = os.path.join(BASE, "scripts", "set_mt4_dates_log.txt")

DTM_FIRST         = 0x1000
DTM_SETSYSTEMTIME = DTM_FIRST + 2
GDT_VALID         = 0

class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ("wYear",         wintypes.WORD),
        ("wMonth",        wintypes.WORD),
        ("wDayOfWeek",    wintypes.WORD),
        ("wDay",          wintypes.WORD),
        ("wHour",         wintypes.WORD),
        ("wMinute",       wintypes.WORD),
        ("wSecond",       wintypes.WORD),
        ("wMilliseconds", wintypes.WORD),
    ]

def log(msg):
    print(msg)
    with open(LOG, "a", encoding="utf-8") as f:
        from datetime import datetime
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

def parse_date(s):
    """Parse YYYY.MM.DD → (year, month, day)"""
    parts = s.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid date format: {s}")
    return int(parts[0]), int(parts[1]), int(parts[2])

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_WRITE     = 0x0020
PROCESS_VM_READ      = 0x0010
MEM_COMMIT           = 0x1000
MEM_RELEASE          = 0x8000
PAGE_READWRITE       = 0x04

def set_datetime_picker(hwnd, year, month, day):
    """DTM_SETSYSTEMTIME 메시지로 DateTimePicker 직접 설정 (cross-process safe)"""
    st = SYSTEMTIME(
        wYear=year, wMonth=month, wDayOfWeek=0,
        wDay=day, wHour=0, wMinute=0, wSecond=0, wMilliseconds=0
    )

    # 대상 프로세스에 SYSTEMTIME 메모리 직접 주입
    pid = ctypes.c_ulong(0)
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h_proc = ctypes.windll.kernel32.OpenProcess(
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
        False, pid.value
    )
    if not h_proc:
        # fallback: local pointer (may fail cross-process)
        result = ctypes.windll.user32.SendMessageW(
            hwnd, DTM_SETSYSTEMTIME, GDT_VALID, ctypes.byref(st)
        )
        return result != 0

    buf_size = ctypes.sizeof(st)
    remote_buf = ctypes.windll.kernel32.VirtualAllocEx(
        h_proc, None, buf_size, MEM_COMMIT, PAGE_READWRITE
    )
    if not remote_buf:
        ctypes.windll.kernel32.CloseHandle(h_proc)
        return False

    written = ctypes.c_size_t(0)
    ctypes.windll.kernel32.WriteProcessMemory(
        h_proc, remote_buf, ctypes.byref(st), buf_size, ctypes.byref(written)
    )

    result = ctypes.windll.user32.SendMessageW(
        hwnd, DTM_SETSYSTEMTIME, GDT_VALID, remote_buf
    )

    ctypes.windll.kernel32.VirtualFreeEx(h_proc, remote_buf, 0, MEM_RELEASE)
    ctypes.windll.kernel32.CloseHandle(h_proc)
    return result != 0

BM_SETCHECK   = 0x00F1
BM_GETCHECK   = 0x00F0
BST_CHECKED   = 1
BST_UNCHECKED = 0

def find_child_by_class_name(parent_hwnd, class_name, index=1):
    """부모 hwnd에서 class_name으로 index번째 자식 컨트롤 탐색"""
    found = []
    def callback(hwnd, _):
        cls = win32gui.GetClassName(hwnd)
        if cls == class_name:
            found.append(hwnd)
        return True
    try:
        win32gui.EnumChildWindows(parent_hwnd, callback, None)
    except Exception:
        pass
    if index <= len(found):
        return found[index - 1]
    return None

def click_control(hwnd):
    """컨트롤에 실제 마우스 클릭 시뮬레이션 (WM_LBUTTONDOWN/UP)"""
    import win32con
    ctypes.windll.user32.PostMessageW(hwnd, win32con.WM_LBUTTONDOWN, 1, 0)
    ctypes.windll.user32.PostMessageW(hwnd, win32con.WM_LBUTTONUP,   0, 0)

def enable_use_date_checkbox(mt4_hwnd, button_index=9):
    """Use Date 체크박스 활성화 (Button9 = 9번째 Button 클래스 컨트롤)"""
    import configparser, os, time
    # INI에서 use_date_checkbox 컨트롤명 읽기
    cfg = configparser.RawConfigParser()
    cfg.read(INI, encoding="utf-8")
    try:
        cb_name = cfg.get("tester_controls", "use_date_checkbox").strip()  # e.g. "Button9"
        idx = int(''.join(filter(str.isdigit, cb_name)))
    except Exception:
        idx = 9

    btn_hwnd = find_child_by_class_name(mt4_hwnd, "Button", idx)
    if btn_hwnd:
        current = ctypes.windll.user32.SendMessageW(btn_hwnd, BM_GETCHECK, 0, 0)
        if current != BST_CHECKED:
            # 실제 클릭으로 체크 → MT4가 WM_COMMAND 처리해서 DateTimePicker 활성화
            click_control(btn_hwnd)
            log(f"Use Date checkbox clicked (Button{idx}, hwnd={btn_hwnd})")
        else:
            log(f"Use Date checkbox already checked (Button{idx})")
        time.sleep(0.2)
        return True
    else:
        log(f"WARN: Use Date checkbox (Button{idx}) not found")
        return False

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # INI에서 날짜 읽기 (기본값)
    cfg = configparser.RawConfigParser()
    cfg.read(INI, encoding="utf-8")
    try:
        from_str = cfg.get("test_date", "from_date").strip()
        to_str   = cfg.get("test_date", "to_date").strip()
    except Exception:
        from_str = "2025.01.01"
        to_str   = "2025.12.31"

    # 인수 우선
    if len(sys.argv) >= 3:
        from_str = sys.argv[1].strip()
        to_str   = sys.argv[2].strip()

    try:
        from_y, from_m, from_d = parse_date(from_str)
        to_y,   to_m,   to_d   = parse_date(to_str)
    except Exception as e:
        log(f"ERR: date parse failed: {e}")
        sys.exit(1)

    log(f"Setting dates: {from_str} ~ {to_str}")

    # MT4 창 찾기
    try:
        account = cfg.get("account", "number").strip()
    except Exception:
        account = ""

    mt4_hwnd = None
    def enum_cb(hwnd, _):
        nonlocal mt4_hwnd
        title = win32gui.GetWindowText(hwnd)
        cls   = win32gui.GetClassName(hwnd)
        if cls == "MetaQuotes::MetaTrader::4.00":
            if not account or account in title:
                mt4_hwnd = hwnd
                return False
        return True
    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass

    if not mt4_hwnd:
        log("ERR: MT4 창을 찾을 수 없음")
        sys.exit(1)

    log(f"MT4 hwnd={mt4_hwnd}")

    # Use Date 체크박스 먼저 활성화 (비활성화 상태면 DateTimePicker가 disabled)
    enable_use_date_checkbox(mt4_hwnd)
    import time
    time.sleep(0.15)

    # SysDateTimePick32 컨트롤 탐색 (1=From, 2=To)
    from_ctrl = find_child_by_class_name(mt4_hwnd, "SysDateTimePick32", 1)
    to_ctrl   = find_child_by_class_name(mt4_hwnd, "SysDateTimePick32", 2)

    if not from_ctrl:
        log("ERR: SysDateTimePick32 #1 (From) 컨트롤 없음")
        sys.exit(1)
    if not to_ctrl:
        log("ERR: SysDateTimePick32 #2 (To) 컨트롤 없음")
        sys.exit(1)

    log(f"From ctrl hwnd={from_ctrl}, To ctrl hwnd={to_ctrl}")

    ok1 = set_datetime_picker(from_ctrl, from_y, from_m, from_d)
    ok2 = set_datetime_picker(to_ctrl,   to_y,   to_m,   to_d)

    if ok1:
        log(f"From date SET: {from_str}")
    else:
        log(f"WARN: From date set failed (hwnd={from_ctrl})")

    if ok2:
        log(f"To date SET: {to_str}")
    else:
        log(f"WARN: To date set failed (hwnd={to_ctrl})")

    if ok1 and ok2:
        log("날짜 설정 완료")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
