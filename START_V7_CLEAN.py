"""
START_V7_CLEAN.py - Start all V7 components cleanly
Kills old instances first, then starts: MT4 -> SOLO -> EA Master -> Watcher -> WATCHDOG -> Optimizer
"""
import os, subprocess, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))

AHK_PATHS = [
    r'C:\Program Files\AutoHotkey\AutoHotkey.exe',
    r'C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe',
]
MT4_PATHS = [r'C:\AG TO DO\MT4', r'C:\NEWOPTMISER\MT4', r'C:\MT4', r'D:\MT4']


def kill_all():
    for name in ['terminal.exe', 'AutoHotkey.exe']:
        subprocess.run(['taskkill', '/F', '/IM', name, '/T'],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    # Kill python processes except this one
    try:
        import psutil
        me = os.getpid()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if p.info['name'] == 'python.exe' and p.info['pid'] != me:
                    p.kill()
            except Exception:
                pass
    except ImportError:
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/T'],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(2)


def find_ahk():
    for p in AHK_PATHS:
        if os.path.exists(p):
            return p
    return None


def find_mt4():
    for p in MT4_PATHS:
        if os.path.exists(os.path.join(p, 'terminal.exe')):
            return p
    return None


def run(args, cwd=None, minimized=False):
    flags = subprocess.CREATE_NEW_CONSOLE
    if minimized:
        flags |= subprocess.SW_HIDE if hasattr(subprocess, 'SW_HIDE') else 0
    subprocess.Popen(args, cwd=cwd or HERE,
                     creationflags=flags)


print("=" * 55)
print("  V7 CLEAN START")
print("=" * 55)

# Delete stop signal
sig = os.path.join(HERE, 'configs', 'runner_stop.signal')
if os.path.exists(sig):
    os.remove(sig)
for f in glob.glob(os.path.join(HERE, 'configs', 'test_completed*.flag')):
    try: os.remove(f)
    except: pass

print("[0] Killing old instances...")
kill_all()

mt4 = find_mt4()
ahk = find_ahk()

print(f"[1] MT4 start ({mt4})...")
if mt4:
    bat = os.path.join(mt4, 'Start_Portable.bat')
    if os.path.exists(bat):
        subprocess.Popen(['cmd', '/c', bat], cwd=mt4,
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen([os.path.join(mt4, 'terminal.exe'), '/portable'],
                         cwd=mt4)
time.sleep(8)

print("[2] SOLO start...")
solo_ahk = os.path.join(HERE, 'SOLO_nc2.3.ahk')
if ahk and os.path.exists(solo_ahk):
    subprocess.Popen([ahk, solo_ahk], cwd=HERE,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
time.sleep(3)

print("[3] EA Master GUI start...")
master = os.path.join(HERE, 'ea_master.py')
if os.path.exists(master):
    subprocess.Popen([sys.executable, master], cwd=HERE,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)

print("[4] SOLO Watcher start...")
watcher = os.path.join(HERE, 'SOLO_WATCHER.py')
if os.path.exists(watcher):
    subprocess.Popen([sys.executable, '-u', watcher], cwd=HERE,
                     creationflags=subprocess.CREATE_NO_WINDOW)

print("[5] WATCHDOG start...")
wd = os.path.join(HERE, 'WATCHDOG_V7.py')
if os.path.exists(wd):
    subprocess.Popen([sys.executable, '-u', wd], cwd=HERE,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
time.sleep(3)

print("[6] Optimizer start...")
opt = os.path.join(HERE, 'ea_optimizer_v7.py')
if os.path.exists(opt):
    subprocess.Popen([sys.executable, '-u', opt], cwd=HERE,
                     creationflags=subprocess.CREATE_NEW_CONSOLE)

print()
print("  All components started.")
print("  MT4 -> SOLO -> EA Master -> SOLO Watcher -> WATCHDOG -> Optimizer")
print("=" * 55)
