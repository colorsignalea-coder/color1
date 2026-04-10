"""
set_1combo.py — SOLO GUI에서 1-combo 설정 후 Gen→Run 클릭
Target: EA1(Survivor v2), Lot7(0.1), SL9(300), TP9(300), TF4(H1) = 1 combo total
"""
import ctypes
import ctypes.wintypes
import time
import sys

try:
    import win32gui
    import win32api
    import win32con
except ImportError:
    print("ERR: pywin32 not installed")
    sys.exit(1)

BM_SETCHECK   = 0x00F1
BM_GETCHECK   = 0x00F0
BM_CLICK      = 0x00F5
BST_CHECKED   = 1
BST_UNCHECKED = 0

# ── SOLO window ───────────────────────────────────────────────
SOLO_TITLE = "MT4 COMBO BACKTESTER 11.0"

def find_solo_window():
    hwnd = win32gui.FindWindow(None, SOLO_TITLE)
    if not hwnd:
        # partial match
        result = []
        def cb(h, _):
            t = win32gui.GetWindowText(h)
            if "COMBO BACKTESTER" in t:
                result.append(h)
            return True
        win32gui.EnumWindows(cb, None)
        if result:
            hwnd = result[0]
    return hwnd

# ── Enumerate Button children ──────────────────────────────────
def get_all_buttons(parent):
    """Returns list of (hwnd, text) for all Button-class children"""
    buttons = []
    def cb(hwnd, _):
        cls = win32gui.GetClassName(hwnd)
        if cls == "Button":
            txt = win32gui.GetWindowText(hwnd)
            buttons.append((hwnd, txt))
        return True
    win32gui.EnumChildWindows(parent, cb, None)
    return buttons

def set_check(hwnd, checked):
    current = win32api.SendMessage(hwnd, BM_GETCHECK, 0, 0)
    want = BST_CHECKED if checked else BST_UNCHECKED
    if current != want:
        win32api.SendMessage(hwnd, BM_CLICK, 0, 0)
        time.sleep(0.05)

def click_btn(hwnd):
    win32api.SendMessage(hwnd, BM_CLICK, 0, 0)
    time.sleep(0.1)

# ── 1-combo target ────────────────────────────────────────────
# checkbox text → keep checked (True) or uncheck (False)
# We identify by text label as shown in AHK code
EA_KEEP = {"Survivor v2 SLTP"}     # only EA1
LOT_KEEP = {"0.1"}                  # only BtLot7
SL_KEEP  = {"300"}                  # only BtSL9
TP_KEEP  = {"300"}                  # only BtTP9
TF_KEEP  = {"H1(1\uc2dc\uac04)", "H1"}  # TF4 — try both Korean and ASCII

def classify(text):
    """Return (category, keep) or None if not a combo checkbox"""
    # EA checkboxes
    ea_labels = [
        "Survivor v2 SLTP", "Survivor v3 SLTP", "TrendRange SLTP",
        "euraka v3.1", "AI TRIPLE", "BRaid SAR 3.2",
        "COLOR175", "COLORBB BTC", "COLORBB GOLD",
        "euraka v3.0", "tCL 6.0 Gold", "LRC_EA 3.0", "SupplyDemand"
    ]
    lot_labels = ["0.01","0.02","0.03","0.04","0.05","0.07","0.1","0.13","0.15","0.18","0.2","0.25","0.3","0.4","0.5"]
    sl_labels  = ["5","10","20","30","50","100","150","200","300","400","500","700","1000"]
    tp_labels  = ["5","10","20","30","50","100","150","200","300","400","500","700","900"]
    # TF labels may be encoded or partial
    tf_keywords = ["M5", "M15", "M30", "H1", "H4", "4h", "4\uc2dc", "1\uc2dc"]

    if text in ea_labels:
        return ("EA", text in EA_KEEP)
    if text in lot_labels:
        return ("Lot", text in LOT_KEEP)
    # SL and TP share same number labels — we need to process in order
    # We'll handle via index tracking in main
    return None

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Looking for SOLO window...")
    solo = None
    for attempt in range(10):
        solo = find_solo_window()
        if solo:
            break
        print(f"  waiting... ({attempt+1}/10)")
        time.sleep(2)

    if not solo:
        print(f"ERR: '{SOLO_TITLE}' window not found")
        sys.exit(1)

    title = win32gui.GetWindowText(solo)
    print(f"Found: hwnd={solo} title='{title}'")

    buttons = get_all_buttons(solo)
    print(f"Total Button controls: {len(buttons)}")

    # ── Group buttons by tracking sequence ────────────────────
    # We rely on the GUI definition order:
    # EA checkboxes first (13), then Lot (15+), then SL (13), then TP (13), then TF (5)
    # Gen button text contains "Gen", Run button contains "Run"

    ea_labels = [
        "Survivor v2 SLTP", "Survivor v3 SLTP", "TrendRange SLTP",
        "euraka v3.1", "AI TRIPLE", "BRaid SAR 3.2",
        "COLOR175", "COLORBB BTC", "COLORBB GOLD",
        "euraka v3.0", "tCL 6.0 Gold", "LRC_EA 3.0", "SupplyDemand"
    ]
    lot_labels = ["0.01","0.02","0.03","0.04","0.05","0.07","0.1","0.13","0.15","0.18","0.2","0.25","0.3","0.4","0.5"]

    ea_hwnds  = []
    lot_hwnds = []
    sl_hwnds  = []
    tp_hwnds  = []
    tf_hwnds  = []
    gen_hwnd  = None
    run_hwnd  = None
    stop_hwnd = None

    # Track state machine: after all lots, next 13 buttons are SL, then 13 are TP, then 5 are TF
    for hwnd, text in buttons:
        # Gen/Run/Stop buttons
        if "Gen" in text and "조합" in text:
            gen_hwnd = hwnd
            continue
        if "Run" in text and ("백테스트" in text or "Start" in text):
            run_hwnd = hwnd
            continue
        if text in ("Stop", "[Stop]", "정지"):
            stop_hwnd = hwnd
            continue

        if text in ea_labels:
            ea_hwnds.append((hwnd, text))
        elif text in lot_labels:
            lot_hwnds.append((hwnd, text))

    # Debug output
    print(f"EA checkboxes found: {len(ea_hwnds)}")
    print(f"Lot checkboxes found: {len(lot_hwnds)}")
    print(f"Gen button: {gen_hwnd}")
    print(f"Run button: {run_hwnd}")

    # Print all buttons for debugging if EA/Lot not found
    if not ea_hwnds or not lot_hwnds or not gen_hwnd:
        print("\nAll buttons (for debug):")
        for hwnd, text in buttons:
            print(f"  hwnd={hwnd} text='{text}'")
        sys.exit(1)

    # ── Find SL/TP/TF by position after Lot ───────────────────
    # SL/TP share same number texts as each other — identify by button index order
    # We enumerate ALL numeric buttons after the lot group
    num_labels_13 = ["5","10","20","30","50","100","150","200","300","400","500","700","1000"]
    num_labels_tp  = ["5","10","20","30","50","100","150","200","300","400","500","700","900"]

    # Collect buttons in order from the raw list
    all_hwnd_texts = [(h, t) for h, t in buttons]
    # Find lot end position
    lot_set = set(lot_labels)
    sl_set  = set(num_labels_13)
    tp_set  = set(num_labels_tp)

    # Build SL, TP, TF groups in sequence
    # Strategy: collect numeric-only buttons after lot group ends
    in_lots = False
    lots_done = False
    sl_done = False
    tp_done = False
    sl_count = 0
    tp_count = 0

    for hwnd, text in all_hwnd_texts:
        if text in ea_labels:
            continue
        if text in lot_set:
            in_lots = True
            continue
        # After lots are done:
        if in_lots and not lots_done:
            lots_done = True

        if lots_done and not sl_done:
            if text in sl_set:
                sl_hwnds.append((hwnd, text))
                sl_count += 1
                if sl_count >= 13:
                    sl_done = True
                continue

        if sl_done and not tp_done:
            if text in tp_set:
                tp_hwnds.append((hwnd, text))
                tp_count += 1
                if tp_count >= 13:
                    tp_done = True
                continue

        if tp_done:
            # TF buttons: M5, M15, M30, H1, H4 — text contains those keywords
            if any(kw in text for kw in ["M5", "M15", "M30", "H1", "H4", "시간", "4시", "1시"]):
                tf_hwnds.append((hwnd, text))

    print(f"SL checkboxes found: {len(sl_hwnds)} → {[t for _,t in sl_hwnds]}")
    print(f"TP checkboxes found: {len(tp_hwnds)} → {[t for _,t in tp_hwnds]}")
    print(f"TF checkboxes found: {len(tf_hwnds)} → {[t for _,t in tf_hwnds]}")

    # ── Stop if currently running ─────────────────────────────
    if stop_hwnd:
        print("\n[!] Clicking Stop first...")
        click_btn(stop_hwnd)
        time.sleep(1)

    # ── Set EA: only EA1 (Survivor v2 SLTP) ──────────────────
    print("\n[EA] Setting EA1 only...")
    for hwnd, text in ea_hwnds:
        want = (text == "Survivor v2 SLTP")
        set_check(hwnd, want)
        print(f"  EA '{text}': {'OK' if want else '--'}")

    # ── Set Lot: only 0.1 ─────────────────────────────────────
    print("\n[Lot] Setting 0.1 only...")
    for hwnd, text in lot_hwnds:
        want = (text == "0.1")
        set_check(hwnd, want)
        print(f"  Lot {text}: {'OK' if want else '--'}")

    # ── Set SL: only 300 ──────────────────────────────────────
    print("\n[SL] Setting 300 only...")
    for hwnd, text in sl_hwnds:
        want = (text == "300")
        set_check(hwnd, want)
        print(f"  SL {text}: {'OK' if want else '--'}")

    # ── Set TP: only 300 ──────────────────────────────────────
    print("\n[TP] Setting 300 only...")
    for hwnd, text in tp_hwnds:
        want = (text == "300")
        set_check(hwnd, want)
        print(f"  TP {text}: {'OK' if want else '--'}")

    # ── Set TF: only H1 ───────────────────────────────────────
    print("\n[TF] Setting H1 only...")
    for hwnd, text in tf_hwnds:
        want = ("H1" in text)
        set_check(hwnd, want)
        print(f"  TF '{text}': {'OK' if want else '--'}")

    time.sleep(0.5)

    # ── Click Gen ─────────────────────────────────────────────
    if gen_hwnd:
        print("\n[Gen] Clicking Gen button...")
        click_btn(gen_hwnd)
        time.sleep(2)
        print("  Gen clicked")
    else:
        print("ERR: Gen button not found")
        sys.exit(1)

    # ── Click Run ─────────────────────────────────────────────
    if run_hwnd:
        print("[Run] Clicking Run button...")
        click_btn(run_hwnd)
        time.sleep(1)
        print("  Run clicked → 1-combo backtest started!")
    else:
        print("ERR: Run button not found")
        sys.exit(1)

    print("\nDONE: 1-combo test started. Monitor log for '[BtCombo 완료]' entry.")

if __name__ == "__main__":
    main()
