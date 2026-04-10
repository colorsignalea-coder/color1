# coding: utf-8
"""
set_r7_8ea.py — R7 EA 자동 선택 + Gen + Run [TEST 1콤보]
#   AITRP1 7fc → AI_TRIPLE_3_1_GoldBTC_0323_7fc
#   BRaid2 7fc → BRaid_SAR_3_2_GoldBTC_0323_7fc
#   TRange 7fc → BTC_Gold_TrendRange_EA_0323_7fc
#   LRC0 7fc → LRC_EA_3_0_GoldBTC_0323_7fc
사용법:
  python set_r7_8ea.py          # 현재 R7 EA만 선택 후 Gen+Run
  python set_r7_8ea.py all       # 모든 EA 체크 ON (Gen+Run 안 함)
  python set_r7_8ea.py none      # 모든 EA 체크 OFF
"""
import sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    import win32gui, win32api
except ImportError:
    print("ERR: pywin32 없음"); sys.exit(1)

MODE = sys.argv[1].lower() if len(sys.argv) > 1 else "run"  # run | all | none

BM_SETCHECK=0x00F1; BM_GETCHECK=0x00F0; BST_CHECKED=1; BST_UNCHECKED=0
WM_COMMAND=0x0111; BN_CLICKED=0

def find_solo():
    r=[]
    def cb(h,_): (r.append(h) if "COMBO BACKTESTER" in win32gui.GetWindowText(h) else None); return True
    win32gui.EnumWindows(cb,None); return r[0] if r else None

def get_buttons(p):
    b=[]
    def cb(h,_): b.append((h,win32gui.GetWindowText(h))); return True
    win32gui.EnumChildWindows(p,cb,None); return b

def set_check(hwnd, want):
    cur=win32api.SendMessage(hwnd,BM_GETCHECK,0,0)
    tgt=BST_CHECKED if want else BST_UNCHECKED
    if cur!=tgt:
        win32api.SendMessage(hwnd,BM_SETCHECK,tgt,0)
        p=win32gui.GetParent(hwnd); cid=win32gui.GetDlgCtrlID(hwnd)
        win32api.PostMessage(p,WM_COMMAND,(BN_CLICKED<<16)|(cid&0xFFFF),hwnd)
        time.sleep(0.15)

def click(hwnd):
    p=win32gui.GetParent(hwnd); cid=win32gui.GetDlgCtrlID(hwnd)
    win32api.PostMessage(p,WM_COMMAND,(BN_CLICKED<<16)|(cid&0xFFFF),hwnd)
    time.sleep(0.2)

# 대기
solo=None
for _ in range(15):
    solo=find_solo()
    if solo: break
    print(f"  SOLO 창 대기... ({_+1}/15)"); time.sleep(2)
if not solo: print("ERR: SOLO 없음"); sys.exit(1)

buttons = get_buttons(solo)

ALL_EA_LABELS = set(['AITRP1 3fc', 'AITRP1 4fc', 'AITRP1 5fc', 'AITRP1 6fc', 'AITRP1 7fc', 'AI_TRIPLE', 'AI_TRIPLE 2fc', 'BRaid2 3fc', 'BRaid2 4fc', 'BRaid2 5fc', 'BRaid2 6fc', 'BRaid2 7fc', 'BRaid_SAR', 'BRaid_SAR 2fc', 'B_DFT2', 'B_FB5', 'COLOR175', 'COLORBB B', 'COLORBB G', 'FB5_2Sma', 'LRC0 3fc', 'LRC0 4fc', 'LRC0 5fc', 'LRC0 6fc', 'LRC0 7fc', 'LRC_EA', 'LRC_EA 2fc', 'SupplyDem', 'SupplyDemand 2fc', 'Survivor 2fc', 'Survivor v2', 'TRange 3fc', 'TRange 4fc', 'TRange 5fc', 'TRange 6fc', 'TRange 7fc', 'TrendRange', 'TrendRange 2fc', 'euraka'])
R_EA_KEEP     = set(['AITRP1 7fc'])
LOT_L = {"0.01","0.02","0.03","0.04","0.05","0.07","0.1","0.13","0.15","0.18","0.2","0.25","0.3","0.4","0.5"}
SL_L  = {"5","10","20","30","50","100","150","200","300","400","500","700","1000"}
TP_L  = {"5","10","20","30","50","100","150","200","300","400","500","700","900"}

ea_h=[]; lot_h=[]; sl_h=[]; tp_h=[]; tf_h=[]; gen_hwnd=run_hwnd=stop_hwnd=None
for hwnd,text in buttons:
    t=text.strip()
    if "[Gen]" in t or ("Gen" in t and "조합" in t): gen_hwnd=hwnd
    elif "[Run]" in t or ("Run" in t and "백테스트" in t) or "백테스트 시작" in t: run_hwnd=hwnd
    elif "[Stop]" in t or "정지" in t: stop_hwnd=hwnd
    elif t in ALL_EA_LABELS: ea_h.append((hwnd,t))
    elif t in LOT_L: lot_h.append((hwnd,t))

in_lots=lots_done=sl_done=tp_done=False; sl_c=tp_c=0
for hwnd,text in buttons:
    t=text.strip()
    if t in ALL_EA_LABELS: continue
    if t in LOT_L: in_lots=True; continue
    if in_lots and not lots_done: lots_done=True
    if lots_done and not sl_done:
        if t in SL_L: sl_h.append((hwnd,t)); sl_c+=1
        if sl_c>=13: sl_done=True
        continue
    if sl_done and not tp_done:
        if t in TP_L: tp_h.append((hwnd,t)); tp_c+=1
        if tp_c>=13: tp_done=True
        continue
    if tp_done:
        if any(k in t for k in ["M5","M15","M30","H1","H4","시간","4시","1시"]): tf_h.append((hwnd,t))

print(f"EA={len(ea_h)} Lot={len(lot_h)} SL={len(sl_h)} TP={len(tp_h)} TF={len(tf_h)}")
print(f"Gen={gen_hwnd} Run={run_hwnd}  MODE={MODE}")

if not gen_hwnd or not run_hwnd:
    print("버튼 전체 목록:")
    for h,t in buttons: print(f"  {h}: '{t}'")
    sys.exit(1)

# ── 전체 선택 ─────────────────────────────────────────────────────
if MODE == "all":
    print("\n[EA] 전체 선택:")
    for hwnd,text in ea_h:
        set_check(hwnd, True)
        print(f"  ✅ {text}: ON")
    print("\n완료: 모든 EA 선택됨 (Gen/Run 미실행)")
    sys.exit(0)

# ── 전체 해제 ─────────────────────────────────────────────────────
if MODE == "none":
    print("\n[EA] 전체 해제:")
    for hwnd,text in ea_h:
        set_check(hwnd, False)
        print(f"  ⬜ {text}: off")
    print("\n완료: 모든 EA 선택 해제됨")
    sys.exit(0)

# ── 일반 실행 (run) ───────────────────────────────────────────────
if stop_hwnd:
    print("[Stop]..."); click(stop_hwnd); time.sleep(1)

print(f"\n[EA] R7 EA 선택:")
for hwnd,text in ea_h:
    want = text in R_EA_KEEP
    set_check(hwnd,want)
    print(f"  {'[R7] ' if want else '       '}{text}: {'ON ✅' if want else 'off'}")

for hwnd,text in lot_h: set_check(hwnd, text=="0.1")
for hwnd,text in sl_h:  set_check(hwnd, text in {"300"})
for hwnd,text in tp_h:  set_check(hwnd, text in {"300"})
for hwnd,text in tf_h:  set_check(hwnd, "H1" in text)

time.sleep(0.5)
print("\n[Gen] 조합 생성..."); click(gen_hwnd); time.sleep(2)
print("[Run] 백테스트 시작!"); click(run_hwnd); time.sleep(1)
print(f"\nDONE: R7 백테스트 시작! (1EA x 1SL x 1TP = 1콤보 [TEST])")
