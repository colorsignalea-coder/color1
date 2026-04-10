"""
core/mt4_control.py — EA Auto Master v6.0
==========================================
MT4 프로세스 관리: 종료, 재시작, 상태 확인.
UI 무관 -- 콜백 패턴으로 상태 전달.
"""
import os
import subprocess
import time

from core.encoding import read_ini


def kill_mt4():
    """MT4 (terminal.exe) 강제 종료."""
    subprocess.run(
        ["taskkill", "/F", "/IM", "terminal.exe"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(3)


def find_terminal_path(ini_path="", ea_path=""):
    """terminal.exe 경로 탐색. INI -> ea_path 상위 -> 동적 탐색."""
    terminal_path = ""
    if ini_path and os.path.exists(ini_path):
        cp = read_ini(ini_path)
        terminal_path = cp.get("folders", "terminal_path", fallback="").strip()
    if terminal_path and os.path.isdir(terminal_path):
        return terminal_path

    if ea_path:
        p = ea_path
        for _ in range(5):
            p = os.path.dirname(p)
            if not p:
                break
            if os.path.exists(os.path.join(p, "terminal.exe")):
                return p
    return ""


def start_mt4(terminal_path):
    """MT4 재시작. Start_Portable.bat 우선, 없으면 terminal.exe /portable.
    Returns True if started.
    """
    start_bat = os.path.join(terminal_path, "Start_Portable.bat")
    term_exe = os.path.join(terminal_path, "terminal.exe")
    if os.path.exists(start_bat):
        subprocess.Popen(
            ["cmd", "/c", start_bat],
            cwd=terminal_path,
            creationflags=subprocess.CREATE_NEW_CONSOLE)
        return True
    elif os.path.exists(term_exe):
        subprocess.Popen(
            [term_exe, "/portable"],
            cwd=terminal_path)
        return True
    return False


def restart_mt4(ini_path="", ea_path="", wait_seconds=20,
                on_status=None, should_stop=None):
    """MT4 종료 + 재시작 + 로딩 대기.
    on_status: callable(msg: str) -- 상태 전달 콜백.
    should_stop: callable() -> bool -- 중지 여부.
    Returns True if restart successful.
    """
    kill_mt4()
    terminal_path = find_terminal_path(ini_path, ea_path)
    if not terminal_path:
        if on_status:
            on_status("MT4 경로 없음")
        return False

    if not start_mt4(terminal_path):
        if on_status:
            on_status("terminal.exe 없음 -- 수동 재시작 필요")
        return False

    for i in range(wait_seconds, 0, -1):
        if should_stop and should_stop():
            return False
        if on_status:
            on_status(f"MT4 로딩 대기 ({i}초)...")
        time.sleep(1)
    return True


def is_mt4_running():
    """MT4 프로세스 실행 여부 확인."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq terminal.exe"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return "terminal.exe" in result.stdout
    except Exception:
        return False


def get_solo_paths(solo_dir, ini_path=""):
    """SOLO 경로 구조 반환 -- NC2.3 우선, 기존 AHK 폴백.
    Returns dict: solo, ini, ahk, flag, ahk_exe, ea_path, mt4_files
    """
    ini = os.path.join(solo_dir, "configs", "current_config.ini") if not ini_path else ini_path
    ahk = ""
    for name in ("SIMPLE_4STEPS_NC23.ahk", "SIMPLE_4STEPS_v5.3.ahk", "SIMPLE_4STEPS_v4_0.ahk"):
        cand = os.path.join(solo_dir, "scripts", name)
        if os.path.exists(cand):
            ahk = cand
            break
        cand = os.path.join(solo_dir, name)
        if os.path.exists(cand):
            ahk = cand
            break
    if not ahk:
        ahk = os.path.join(solo_dir, "scripts", "SIMPLE_4STEPS_NC23.ahk")
    flag = os.path.join(solo_dir, "configs", "test_completed.flag")
    ahk_exe = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
    if not os.path.exists(ahk_exe):
        ahk_exe = r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"

    ea_path = ""
    mt4_files = ""
    if os.path.exists(ini):
        cp = read_ini(ini)
        ea_path = cp.get("folders", "ea_path", fallback="").strip()
        mt4_files = cp.get("folders", "setfiles_path", fallback="").strip()
        if not mt4_files:
            tp = cp.get("folders", "terminal_path", fallback="").strip()
            if tp:
                mt4_files = os.path.join(tp, "MQL4", "Files")

    return {
        "solo": solo_dir, "ini": ini, "ahk": ahk, "flag": flag,
        "ahk_exe": ahk_exe, "ea_path": ea_path, "mt4_files": mt4_files,
    }
