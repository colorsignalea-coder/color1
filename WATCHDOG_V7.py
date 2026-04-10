"""
WATCHDOG_V7.py - EA Auto Master v8.0 Process Watchdog
======================================================
Watch targets:
  1. ea_optimizer_v7.py  - auto restart if dead
  2. terminal.exe (MT4)  - restart if optimizer running but MT4 dead
  NOTE: SOLO (AHK) is NOT restarted - it is stable and self-managing

Anti-duplicate safeguards:
  - MIN_RESTART_INTERVAL: do not restart within 120s of last start
  - kill_duplicate_optimizers(): kill all but one instance before starting

Usage: python WATCHDOG_V7.py  (auto-launched by START_ALL_v7.bat)
"""
import os
import subprocess
import time
import glob

HERE      = os.path.dirname(os.path.abspath(__file__))
CONFIGS   = os.path.join(HERE, 'configs')
STOP_FILE = os.path.join(CONFIGS, 'runner_stop.signal')

# Minimum seconds between optimizer restarts (prevents duplicate spawning)
MIN_RESTART_INTERVAL = 120

# AHK paths
AHK_PATHS = [
    r'C:\Program Files\AutoHotkey\AutoHotkey.exe',
    r'C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe',
]
SOLO_AHK = os.path.join(HERE, 'SOLO_nc2.3.ahk')

# MT4 search paths
MT4_PATHS = [
    r'C:\AG TO DO\MT4',
    r'C:\NEWOPTMISER\MT4',
    r'C:\MT4',
    r'D:\MT4',
]


def _find_ahk():
    for p in AHK_PATHS:
        if os.path.exists(p):
            return p
    return None


def _solo_running():
    """Return True if SOLO_nc2.3.ahk AHK process is alive."""
    try:
        r = subprocess.run(
            ['wmic', 'process', 'where', 'name="AutoHotkey.exe"',
             'get', 'commandline'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return 'solo_nc2.3' in r.stdout.decode('utf-8', 'replace').lower()
    except Exception:
        return False


def start_solo():
    """Start SOLO_nc2.3.ahk if AHK and script are present."""
    ahk = _find_ahk()
    if not ahk or not os.path.exists(SOLO_AHK):
        print("[WATCHDOG] SOLO AHK not found -skip")
        return False
    print("[WATCHDOG] Restarting SOLO_nc2.3.ahk ...")
    subprocess.Popen([ahk, SOLO_AHK], cwd=HERE,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(5)
    return True


def _find_mt4():
    for p in MT4_PATHS:
        if os.path.exists(os.path.join(p, 'terminal.exe')):
            return p
    return None


def _proc_running(name):
    try:
        r = subprocess.run(
            ['tasklist'], capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return name.lower() in r.stdout.decode('cp949', 'replace').lower()
    except Exception:
        return False


def _optimizer_running():
    """Return True if at least one ea_optimizer_v7 python process is alive."""
    try:
        r = subprocess.run(
            ['wmic', 'process', 'where', 'name="python.exe"',
             'get', 'commandline'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        lines = r.stdout.decode('utf-8', 'replace').splitlines()
        count = sum(1 for l in lines if 'ea_optimizer_v7' in l.lower())
        return count > 0
    except Exception:
        return False


def _optimizer_count():
    """Return number of running ea_optimizer_v7 instances."""
    try:
        r = subprocess.run(
            ['wmic', 'process', 'where', 'name="python.exe"',
             'get', 'commandline'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        lines = r.stdout.decode('utf-8', 'replace').splitlines()
        return sum(1 for l in lines if 'ea_optimizer_v7' in l.lower())
    except Exception:
        return 0


def kill_all_optimizers():
    """Kill ALL ea_optimizer_v7 instances (used when starting fresh)."""
    try:
        r = subprocess.run(
            ['wmic', 'process', 'where', 'name="python.exe"',
             'get', 'processid,commandline'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        lines = r.stdout.decode('utf-8', 'replace').splitlines()
        for line in lines:
            if 'ea_optimizer_v7' in line.lower():
                parts = line.strip().rsplit(None, 1)
                if parts:
                    pid = parts[-1].strip()
                    if pid.isdigit():
                        subprocess.run(['taskkill', '/F', '/PID', pid],
                                       capture_output=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                        print(f"[WATCHDOG] Killed optimizer PID {pid}")
    except Exception as e:
        print(f"[WATCHDOG] kill_all error: {e}")


def kill_extra_optimizers():
    """Keep the OLDEST optimizer (lowest PID), kill all newer duplicates."""
    try:
        r = subprocess.run(
            ['wmic', 'process', 'where', 'name="python.exe"',
             'get', 'processid,commandline'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        lines = r.stdout.decode('utf-8', 'replace').splitlines()
        pids = []
        for line in lines:
            if 'ea_optimizer_v7' in line.lower():
                parts = line.strip().rsplit(None, 1)
                if parts:
                    pid = parts[-1].strip()
                    if pid.isdigit():
                        pids.append(int(pid))
        if len(pids) <= 1:
            return
        pids.sort()
        keep = pids[0]
        print(f"[WATCHDOG] Keeping oldest optimizer PID {keep}, killing: {pids[1:]}")
        for pid in pids[1:]:
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                           capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"[WATCHDOG] kill_extra error: {e}")


def _should_run():
    if os.path.exists(STOP_FILE):
        return False
    mt4 = _find_mt4()
    if not mt4:
        return False
    experts = os.path.join(mt4, r'MQL4\Experts')
    has_v7 = bool(glob.glob(os.path.join(experts, 'G4v7_*.ex4')))
    return has_v7


def start_optimizer():
    """Kill all existing optimizers, then start one clean instance."""
    cnt = _optimizer_count()
    if cnt > 0:
        print(f"[WATCHDOG] {cnt} stale optimizer(s) found -killing first")
        kill_all_optimizers()
        time.sleep(3)
    print("[WATCHDOG] Starting ea_optimizer_v7.py ...")
    subprocess.Popen(
        ['python', '-u', os.path.join(HERE, 'ea_optimizer_v7.py')],
        cwd=HERE,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def start_mt4():
    mt4 = _find_mt4()
    if not mt4:
        print("[WATCHDOG] MT4 not found -skip")
        return
    print("[WATCHDOG] Restarting MT4 ...")
    bat = os.path.join(mt4, 'Start_Portable.bat')
    exe = os.path.join(mt4, 'terminal.exe')
    if os.path.exists(bat):
        subprocess.Popen(['cmd', '/c', bat], cwd=mt4,
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
    elif os.path.exists(exe):
        subprocess.Popen([exe, '/portable'], cwd=mt4)
    time.sleep(8)


def main():
    print("=" * 55)
    print("  WATCHDOG V7 - Process Auto-Restart Monitor")
    print("  Watch: Optimizer + MT4  (SOLO excluded)")
    print(f"  Min restart interval: {MIN_RESTART_INTERVAL}s  |  Check: 30s")
    print("=" * 55)

    # Kill extras on startup (keep oldest if any running)
    cnt = _optimizer_count()
    if cnt > 1:
        print(f"[WATCHDOG] Startup: {cnt} optimizers found -keeping oldest, killing extras")
        kill_extra_optimizers()
        time.sleep(3)

    # Wait before first active check
    time.sleep(15)

    # Initialize to now so WATCHDOG doesn't immediately restart on first wake
    last_opt_start  = time.time()  # pretend optimizer was just started
    last_solo_start = time.time()
    solo_dead_since = 0.0

    while True:
        try:
            if os.path.exists(STOP_FILE):
                print("[WATCHDOG] Stop signal -exit")
                break

            if not _should_run():
                time.sleep(30)
                continue

            opt_alive = _optimizer_running()
            mt4_alive = _proc_running('terminal.exe')
            solo_alive = _solo_running()
            now = time.time()

            # SOLO dead ??restart only if optimizer is running + dead for > 180s
            if not solo_alive:
                if solo_dead_since == 0.0:
                    solo_dead_since = now
                    print("[WATCHDOG] SOLO dead -monitoring...")
                elif opt_alive and (now - solo_dead_since) > 180:
                    elapsed_solo = int(now - last_solo_start)
                    if elapsed_solo >= 180:
                        print(f"[WATCHDOG] SOLO dead {int(now-solo_dead_since)}s + optimizer busy -restarting")
                        if start_solo():
                            last_solo_start = time.time()
                            solo_dead_since = 0.0
            else:
                solo_dead_since = 0.0  # reset dead timer when alive

            # MT4 dead ??restart
            if not mt4_alive:
                print("[WATCHDOG] MT4 dead -restarting")
                start_mt4()
                time.sleep(5)

            # Optimizer dead ??restart only if enough time has passed
            if not opt_alive:
                elapsed_since_start = now - last_opt_start
                if elapsed_since_start < MIN_RESTART_INTERVAL:
                    wait = int(MIN_RESTART_INTERVAL - elapsed_since_start)
                    print(f"[WATCHDOG] Optimizer dead but started {int(elapsed_since_start)}s ago -wait {wait}s")
                    time.sleep(min(wait, 30))
                    continue

                # Remove stale flags before restart
                for f in glob.glob(os.path.join(CONFIGS, 'test_completed*.flag')):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

                start_optimizer()
                last_opt_start = time.time()
                print("[WATCHDOG] Optimizer started -waiting 60s before next check")
                time.sleep(60)
            else:
                # Optimizer alive ??kill extras if > 1 (keep oldest)
                cnt = _optimizer_count()
                if cnt > 1:
                    print(f"[WATCHDOG] {cnt} optimizer instances -killing extras, keeping oldest")
                    kill_extra_optimizers()
                time.sleep(30)

        except KeyboardInterrupt:
            print("\n[WATCHDOG] Stopped by user")
            break
        except Exception as e:
            print(f"[WATCHDOG] Error: {e}")
            time.sleep(30)


if __name__ == '__main__':
    main()

