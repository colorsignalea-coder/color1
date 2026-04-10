"""
core/ipc.py — EA Auto Master v6.0
===================================
v5.4 <-> SOLO_nc2.3 IPC 통신 프로토콜 (command.json 기반).
UI 무관 -- 콜백 패턴으로 진행 전달.
"""
import os
import json
import time
import subprocess

from core.encoding import read_ini, write_ini


def send_command(configs_dir, ea_name, symbol, timeframe,
                 iteration=1, total_sets=1, from_date="", to_date=""):
    """command.json 생성 -> SOLO_nc2.3 AutoTrigger 폴링 대기.
    Returns cmd_path (str)
    """
    cmd_path = os.path.join(configs_dir, "command.json")
    proc_path = os.path.join(configs_dir, "command_processing.json")
    flag_path = os.path.join(configs_dir, "test_completed.flag")

    # 기존 플래그/처리중 파일 삭제
    for fp in (flag_path, proc_path):
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError:
                pass

    cmd_data = {
        "ea_name": ea_name,
        "symbol": symbol,
        "timeframe": timeframe,
        "iteration": iteration,
        "total_sets": total_sets,
        "from_date": from_date,
        "to_date": to_date,
    }
    with open(cmd_path, "w", encoding="utf-8") as f:
        json.dump(cmd_data, f, ensure_ascii=False)
    return cmd_path


def wait_solo_detection(configs_dir, timeout=10):
    """SOLO_nc2.3 AutoTrigger 감지 대기.
    command.json이 사라지거나 command_processing.json이 생기면 감지됨.
    Returns True if SOLO detected, False if timeout.
    """
    cmd_path = os.path.join(configs_dir, "command.json")
    proc_path = os.path.join(configs_dir, "command_processing.json")
    for _ in range(timeout):
        if os.path.exists(proc_path) or not os.path.exists(cmd_path):
            return True
        time.sleep(1)
    return False


def wait_completion(configs_dir, timeout=300, poll_interval=2, should_stop=None):
    """test_completed.flag 대기.
    Returns True if backtest completed, False if timeout/stopped.
    """
    flag_path = os.path.join(configs_dir, "test_completed.flag")
    start = time.time()
    while time.time() - start < timeout:
        if should_stop and should_stop():
            return False
        if os.path.exists(flag_path):
            try:
                txt = open(flag_path, "r").read().strip()
                if txt in ("DONE", "1"):
                    return True
            except Exception:
                pass
        time.sleep(poll_interval)
    return False


def fallback_ahk(ahk_exe, ahk_script, ea_name, symbol, period, test_num, configs_dir):
    """SOLO_nc2.3 미실행 시 직접 AHK 실행으로 폴백."""
    cmd_path = os.path.join(configs_dir, "command.json")
    if os.path.exists(cmd_path):
        try:
            os.remove(cmd_path)
        except OSError:
            pass
    if ahk_script and os.path.exists(ahk_script):
        cmd = [ahk_exe, ahk_script, ea_name, symbol, period, str(test_num)]
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)


def update_ini(ini_path, ea_name, symbol, period, from_date, to_date, set_file_path=""):
    """current_config.ini [current_backtest] + [test_date] 섹션 업데이트."""
    cp = read_ini(ini_path)
    if not cp.has_section("current_backtest"):
        cp.add_section("current_backtest")
    cp.set("current_backtest", "ea_name", ea_name)
    cp.set("current_backtest", "symbol", symbol)
    cp.set("current_backtest", "period", period)
    cp.set("current_backtest", "from_date", from_date)
    cp.set("current_backtest", "to_date", to_date)
    cp.set("current_backtest", "set_file_path", set_file_path)
    cp.set("current_backtest", "has_set", "1" if set_file_path else "0")
    if not cp.has_section("test_date"):
        cp.add_section("test_date")
    cp.set("test_date", "enable", "1")
    cp.set("test_date", "from_date", from_date)
    cp.set("test_date", "to_date", to_date)
    write_ini(cp, ini_path)
    # current_ea_name.txt 갱신 (AHK 인코딩 우회용)
    ea_txt = os.path.join(os.path.dirname(ini_path), "current_ea_name.txt")
    with open(ea_txt, "w", encoding="utf-8") as f:
        f.write(ea_name + ".ex4\n")


def sync_ini_to_gui(ini_path):
    """INI -> dict (Phase1: INI -> GUI 방향 동기화).
    Returns dict of gui-relevant values.
    """
    result = {}
    if not os.path.exists(ini_path):
        return result
    cp = read_ini(ini_path)
    for sec in cp.sections():
        for key, val in cp.items(sec):
            result[f"{sec}.{key}"] = val
    return result


def sync_gui_to_ini(ini_path, gui_state):
    """dict -> INI (Phase2: GUI -> INI 방향 동기화, UTF-8 BOM)."""
    cp = read_ini(ini_path)
    for dotkey, val in gui_state.items():
        parts = dotkey.split(".", 1)
        if len(parts) != 2:
            continue
        sec, key = parts
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, key, str(val))
    write_ini(cp, ini_path)
