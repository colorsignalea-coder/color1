# coding: utf-8
"""
set_r3_ea.py — R3 4개 EA SOLO GUI 자동 설정 + Gen → Run
대상: BtComboEA20~23 (3fc EA들만 선택)
설정: Lot=0.1, SL=300/500, TP=300/500, TF=H1
"""
import sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import win32gui, win32api, win32con
except ImportError:
    print("ERR: pywin32 not installed")
    sys.exit(1)

BM_SETCHECK = 0x00F1
BM_GETCHECK = 0x00F0
BST_CHECKED   = 1
BST_UNCHECKED = 0
WM_COMMAND = 0x0111
BN_CLICKED = 0

def find_solo():
    result = []
    def cb(h, _):
        if "COMBO BACKTESTER" in win32gui.GetWindowText(h):
            result.append(h)
        return True
    win32gui.EnumWindows(cb, None)
    return result[0] if result else None

def get_buttons(parent):
    btns = []
    def cb(h, _):
        if win32gui.GetClassName(h) == "Button":
            btns.append((h, win32gui.GetWindowText(h)))
        return True
    win32gui.EnumChildWindows(parent, cb, None)
    return btns

def notify_click(hwnd):
    parent = win32gui.GetParent(hwnd)
    ctrl_id = win32gui.GetDlgCtrlID(hwnd)
    wparam = (BN_CLICKED << 16) | (ctrl_id & 0xFFFF)
    win32api.PostMessage(parent, WM_COMMAND, wparam, hwnd)
    time.sleep(0.15)

def set_check(hwnd, want):
    cur = win32api.SendMessage(hwnd, BM_GETCHECK, 0, 0)
    target = BST_CHECKED if want else BST_UNCHECKED
    if cur != target:
        win32api.SendMessage(hwnd, BM_SETCHECK, target, 0)
        notify_click(hwnd)

def click(hwnd):
    notify_click(hwnd)
    time.sleep(0.05)

# R3 EA 레이블 (SOLO_12_0.ahk BtComboEA20~23)
R3_EA_LABELS = {
    "TRange 3fc", "BRaid2 3fc", "AITRP1 3fc", "LRC0 3fc",
}

# 모든 EA 레이블 (R1+R2+R3)
ALL_EA_LABELS = {
    # R1
    "Survivor v2", "TrendRange", "AI_TRIPLE", "BRaid_SAR", "LRC_EA",
    "COLOR175", "COLORBB B", "COLORBB G", "euraka", "B_DFT2",
    "B_FB5", "FB5_2Sma", "SupplyDem",
    # R2 (2fc)
    "Survivor 2fc", "TrendRange 2fc", "AI_TRIPLE 2fc",
    "BRaid_SAR 2fc", "LRC_EA 2fc", "SupplyDemand 2fc",
    # R3 (3fc)
    "TRange 3fc", "BRaid2 3fc", "AITRP1 3fc", "LRC0 3fc",
}

LOT_LABELS = {"0.01","0.05","0.1","0.15","0.2","0.3","0.5","1.0"}
SL_LABELS  = {"100","150","200","250","300","350","400","450","500","600","700","800","1000"}
TP_LABELS  = {"100","150","200","250","300","350","400","450","500","600","700","800","1000"}

print("=== R3 EA 설정 시작 ===")
solo = find_solo()
if not solo:
    print("ERR: COMBO BACKTESTER 창 없음")
    sys.exit(1)
print(f"SOLO 창: {solo}")

buttons = get_buttons(solo)
ea_hwnds = []; lot_hwnds = []; sl_hwnds = []; tp_hwnds = []; tf_hwnds = []
gen_hwnd = run_hwnd = stop_hwnd = None

for hwnd, text in buttons:
    if "Gen" in text and "Combo" not in text: gen_hwnd = hwnd
    elif "[Run]" in text or "백테스트 시작" in text: run_hwnd = hwnd
    elif "[Stop]" in text or "정지" in text: stop_hwnd = hwnd
    elif text in ALL_EA_LABELS: ea_hwnds.append((hwnd, text))
    elif text in LOT_LABELS: lot_hwnds.append((hwnd, text))

in_lots = lots_done = sl_done = tp_done = False
sl_count = tp_count = 0
lot_set = LOT_LABELS; sl_set = SL_LABELS; tp_set = TP_LABELS

for hwnd, text in buttons:
    if text in ALL_EA_LABELS: continue
    if text in lot_set:
        in_lots = True; continue
    if in_lots and not lots_done: lots_done = True
    if lots_done and not sl_done:
        if text in sl_set:
            sl_hwnds.append((hwnd, text)); sl_count += 1
            if sl_count >= 13: sl_done = True
        continue
    if sl_done and not tp_done:
        if text in tp_set:
            tp_hwnds.append((hwnd, text)); tp_count += 1
            if tp_count >= 13: tp_done = True
        continue
    if tp_done:
        if any(kw in text for kw in ["M5","M15","M30","H1","H4","시간","4시","1시"]):
            tf_hwnds.append((hwnd, text))

print(f"EA={len(ea_hwnds)} Lot={len(lot_hwnds)} SL={len(sl_hwnds)} TP={len(tp_hwnds)} TF={len(tf_hwnds)}")
print(f"Gen={gen_hwnd} Run={run_hwnd}")

if not gen_hwnd or not run_hwnd:
    print("버튼 목록:")
    for h, t in buttons: print(f"  {h}: '{t}'")
    sys.exit(1)

# Stop 먼저
if stop_hwnd:
    print("\n[Stop] 정지...")
    click(stop_hwnd); time.sleep(1)

# EA: R3 3fc EA만 ON, 나머지 OFF
print("\n[EA] R3 4개 3fc EA만 선택...")
for hwnd, text in ea_hwnds:
    want = text in R3_EA_LABELS
    set_check(hwnd, want)
    print(f"  '{text}': {'ON' if want else 'off'}")

# Lot: 0.1만
print("\n[Lot] 0.1만...")
for hwnd, text in lot_hwnds:
    set_check(hwnd, text == "0.1")

# SL: 300, 500
print("\n[SL] 300, 500...")
for hwnd, text in sl_hwnds:
    set_check(hwnd, text in {"300","500"})
    if text in {"300","500"}: print(f"  SL {text}: ON")

# TP: 300, 500
print("\n[TP] 300, 500...")
for hwnd, text in tp_hwnds:
    set_check(hwnd, text in {"300","500"})
    if text in {"300","500"}: print(f"  TP {text}: ON")

# TF: H1만
print("\n[TF] H1만...")
for hwnd, text in tf_hwnds:
    want = "H1" in text
    set_check(hwnd, want)
    if want: print(f"  TF '{text}': ON")

time.sleep(0.5)

# Gen
print("\n[Gen] 조합 생성...")
click(gen_hwnd); time.sleep(2)

# Run
print("[Run] 백테스트 시작!")
click(run_hwnd); time.sleep(1)

print("\nDONE: R3 4개 EA 백테스트 시작!")
print("조합: 4EA x 2SL x 2TP = 16회")
print("모니터: bt-monitor 스킬 사용")
