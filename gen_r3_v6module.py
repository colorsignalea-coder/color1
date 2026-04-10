# -*- coding: utf-8 -*-
"""
gen_r3_v6module.py
v6.0 紐⑤뱢(ParamAnalyzer, gen_round_sets_v2, gen_bottom_fix_sets)濡?R1 寃곌낵 遺꾩꽍 -> R3 ?쒕굹由ъ삤 ?앹꽦 -> .mq4 ?앹꽦 + MetaEditor 而댄뙆??湲곕컲 ?대뜑: C:/AG TO DO//EA_AUTO_MASTER_v6.0/
"""
import os, sys, json, glob, subprocess, shutil, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from datetime import datetime

# ?? 寃쎈줈 ?ㅼ젙 (V6.1 湲곕컲) ????????????????????????????????????????????????
HERE       = os.path.dirname(os.path.abspath(__file__))
RESULTS    = os.path.join(HERE, "g4_results")
MT4_DIR    = os.path.abspath(os.path.join(HERE, "..", "MT4"))
EXPERTS    = os.path.join(MT4_DIR, r"MQL4\Experts")
BACKUP_ROOT= os.path.join(MT4_DIR, r"MQL4\_EXPERTS_BACKUP_0404")
ME_EXE     = os.path.join(MT4_DIR, "metaeditor.exe")
R3_DIR     = os.path.join(EXPERTS, "_R3_ONLY")

# v6.0 紐⑤뱢? 媛숈? ?대뜑 ?덉뿉 ?덉쓬
sys.path.insert(0, HERE)

print("=" * 60)
print("  R3 ?쒕굹由ъ삤 ?앹꽦 - v6.0 紐⑤뱢 ?ъ슜")
print(f"  BASE: {HERE}")
print("=" * 60)

# ?? v6.0 紐⑤뱢 import ??????????????????????????????????????????????????????
try:
    from core.round_optimizer import ParamAnalyzer, RoundDirector
    from core.round_engine import gen_round_sets_v2, gen_bottom_fix_sets
    print("[OK] v6.0 紐⑤뱢 import ?깃났")
except Exception as e:
    print(f"[FAIL] v6.0 紐⑤뱢 import ?ㅽ뙣: {e}")
    sys.exit(1)

# ?? R1 寃곌낵 濡쒕뱶 ?????????????????????????????????????????????????????????
r1_file = os.path.join(RESULTS, "R01_recovered_1640.json")
if not os.path.exists(r1_file):
    print(f"[FAIL] R1 寃곌낵 ?뚯씪 ?놁쓬: {r1_file}")
    sys.exit(1)

with open(r1_file, encoding="utf-8") as f:
    r1_raw = json.load(f)
r1_results = r1_raw.get("results", [])
print(f"[OK] R1 寃곌낵 濡쒕뱶: {len(r1_results)}媛?)

# R1 寃곌낵 -> ParamAnalyzer ?뺤떇 蹂??r1_for_analyzer = []
for r in r1_results:
    if r.get("score", 0) <= 0:
        continue  # score=0 ?쒖쇅 (SC005 誘몄셿猷?
    params = {
        "sl": str(r.get("sl", 0.3)),
        "tp": str(r.get("tp", 11.0)),
    }
    htm = {
        "profit":        r.get("profit", 0),
        "profit_factor": r.get("profit_factor", 0),
        "drawdown_pct":  r.get("drawdown_pct", 100),
        "trades":        r.get("trades", 0),
        "score":         r.get("score", 0),
    }
    r1_for_analyzer.append({"params": params, "htm": htm})

print(f"  ?좏슚 R1 寃곌낵: {len(r1_for_analyzer)}媛?(score>0)")

# ?? ParamAnalyzer 遺꾩꽍 ????????????????????????????????????????????????????
analyzer = ParamAnalyzer()
analyzer.add_results(r1_for_analyzer)

sweet_spots = analyzer.find_sweet_spots(
    results=[(e["params"], e["htm"]) for e in r1_for_analyzer],
    top_ratio=0.375
)
raw_correlations = analyzer.rank_param_impact(
    results=[(e["params"], e["htm"]) for e in r1_for_analyzer]
)
print(f"\n[v6.0 ParamAnalyzer] ?먯떆 ?곴??? {raw_correlations}")
print(f"  Sweet Spots: {sweet_spots}")

# ?? 媛뺥솕???ㅼ쐵?ㅽ뙚 (R1 8媛??곗씠??遺議?蹂댁셿) ?????????????????????????????
# R1 ?ㅼ젣 ?곗씠?곗뿉??吏곸젒 踰붿쐞 怨꾩궛
sl_vals = [float(r["params"]["sl"]) for r in r1_for_analyzer]
tp_vals = [float(r["params"]["tp"]) for r in r1_for_analyzer]
top_3 = sorted(r1_for_analyzer, key=lambda x: x["htm"]["score"], reverse=True)[:3]
top_sl = [float(r["params"]["sl"]) for r in top_3]
top_tp = [float(r["params"]["tp"]) for r in top_3]

forced_sweet_spots = {
    "sl": {
        "center": round(sum(top_sl)/len(top_sl), 4),
        "low":    min(sl_vals),
        "high":   max(sl_vals),
        "direction": "decrease" if sum(top_sl)/len(top_sl) < sum(sl_vals)/len(sl_vals) else "increase",
    },
    "tp": {
        "center": round(sum(top_tp)/len(top_tp), 4),
        "low":    min(tp_vals),
        "high":   max(tp_vals),
        "direction": "increase" if sum(top_tp)/len(top_tp) > sum(tp_vals)/len(tp_vals) else "decrease",
    },
}
# ?곴???媛뺤젣 ?ㅼ젙 (?곗씠??8媛쒕줈????쾶 ?섏삤誘濡?遺꾩꽍 湲곕컲 理쒖냼媛?蹂댁옣)
forced_correlations = {
    "sl": max(abs(raw_correlations.get("sl", 0)), 0.35),
    "tp": max(abs(raw_correlations.get("tp", 0)), 0.30),
}

print(f"\n[媛뺥솕 ?ㅼ쐵?ㅽ뙚]")
for p, s in forced_sweet_spots.items():
    print(f"  {p}: center={s['center']:.4f}  low={s['low']:.4f}  high={s['high']:.4f}  dir={s['direction']}")
print(f"[媛뺥솕 ?곴??? {forced_correlations}")

# ?? gen_round_sets_v2 ?ㅽ뻾 ?????????????????????????????????????????????????
best = sorted(r1_for_analyzer, key=lambda x: x["htm"]["score"], reverse=True)[0]["params"]
base_params = {"sl": best["sl"], "tp": best["tp"]}
print(f"\n[base_params] sl={base_params['sl']}  tp={base_params['tp']} (R1 1??湲곕컲)")

v2_sets = gen_round_sets_v2(
    base_params=base_params,
    round_num=3,
    sweet_spots=forced_sweet_spots,
    correlations=forced_correlations,
    max_vary=2,
    n_steps=5,
    step=0.20,
)
print(f"\n[gen_round_sets_v2] ?앹꽦: {len(v2_sets)}媛?)
for i, s in enumerate(v2_sets):
    print(f"  [{i+1}] sl={s.get('sl')}  tp={s.get('tp')}")

# ?? gen_bottom_fix_sets ????????????????????????????????????????????????????
sorted_r1 = sorted(r1_for_analyzer, key=lambda x: x["htm"]["score"], reverse=True)
top_n = max(3, len(sorted_r1) // 3)
bot_n = max(2, len(sorted_r1) // 3)
top_results = sorted_r1[:top_n]
bot_results  = sorted_r1[-bot_n:]

top_comparison = {}
for param in ["sl", "tp"]:
    top_vals = [float(r["params"][param]) for r in top_results]
    bot_vals  = [float(r["params"][param]) for r in bot_results]
    top_avg = sum(top_vals) / len(top_vals)
    bot_avg  = sum(bot_vals) / len(bot_vals)
    direction = "decrease" if top_avg < bot_avg - 0.01 else ("increase" if top_avg > bot_avg + 0.01 else "same")
    top_comparison[param] = {"top_avg": top_avg, "direction": direction}

fix_sets = gen_bottom_fix_sets(
    bottom_results=bot_results,
    top_comparison=top_comparison,
    base_params=base_params,
)
print(f"\n[gen_bottom_fix_sets] ?앹꽦: {len(fix_sets)}媛?)
for i, s in enumerate(fix_sets):
    print(f"  [{i+1}] sl={s.get('sl')}  tp={s.get('tp')}")

# ?? 異붽? ?섎룞 寃⑹옄 (v6.0 寃곌낵 蹂댁셿 ??15媛?梨꾩슦湲? ?????????????????????????
# R1 Top3 以묒떖?쇰줈 짹20% 寃⑹옄 ?앹꽦
grid_params = []
for r in top_results:
    sl0 = float(r["params"]["sl"])
    tp0 = float(r["params"]["tp"])
    for sl_mult in [0.85, 1.0, 1.15]:
        for tp_mult in [0.85, 1.0, 1.15]:
            sl = round(sl0 * sl_mult, 4)
            tp = round(tp0 * tp_mult, 4)
            if sl > 0 and tp > 0:
                grid_params.append({"sl": sl, "tp": tp, "source": "grid"})

# ?? ?꾩껜 ?쒕굹由ъ삤 ?⑹튂湲???????????????????????????????????????????????????
all_scenarios = []
for s in v2_sets:
    try:
        sl = round(float(s.get("sl", base_params["sl"])), 4)
        tp = round(float(s.get("tp", base_params["tp"])), 4)
        if sl > 0 and tp > 0:
            all_scenarios.append({"sl": sl, "tp": tp, "source": "v6_v2"})
    except Exception: pass

for s in fix_sets:
    try:
        sl = round(float(s.get("sl", base_params["sl"])), 4)
        tp = round(float(s.get("tp", base_params["tp"])), 4)
        if sl > 0 and tp > 0:
            all_scenarios.append({"sl": sl, "tp": tp, "source": "v6_fix"})
    except Exception: pass

for s in grid_params:
    all_scenarios.append(s)

# 以묐났 ?쒓굅
seen = set()
unique = []
for s in all_scenarios:
    key = (s["sl"], s["tp"])
    if key not in seen:
        seen.add(key)
        unique.append(s)

# score 湲곕컲 ?뺣젹 (v6 寃곌낵 ?곗꽑, grid 蹂댁셿)
final_scenarios = unique[:15]

# 15媛?誘몃떖?대㈃ Top3 짹10% 異붽?
if len(final_scenarios) < 15:
    for r in top_results:
        sl0 = float(r["params"]["sl"])
        tp0 = float(r["params"]["tp"])
        for sl_d, tp_d in [(-0.05, 0), (0.05, 0), (0, -1.5), (0, 1.5), (-0.05, -1.5)]:
            sl = round(sl0 + sl_d, 4)
            tp = round(tp0 + tp_d, 4)
            key = (sl, tp)
            if sl > 0 and tp > 0 and key not in seen:
                seen.add(key)
                final_scenarios.append({"sl": sl, "tp": tp, "source": "top3_adj"})
            if len(final_scenarios) >= 15:
                break
        if len(final_scenarios) >= 15:
            break

final_scenarios = final_scenarios[:15]
print(f"\n[理쒖쥌 ?쒕굹由ъ삤] {len(final_scenarios)}媛?")
for i, s in enumerate(final_scenarios, 1):
    print(f"  SC{i:03d}: sl={s['sl']:.4f}  tp={s['tp']:.4f}  [{s['source']}]")

# ?? .mq4 ?뚯씪 ?앹꽦 ????????????????????????????????????????????????????????
MQ4_TEMPLATE = '''\
//+------------------------------------------------------------------+
//| G4 Trend EA - Round 3 Scenario {n:03d}  [v6.0 module generated]
//| sl={sl_val}  tp={tp_val}  magic={magic}
//+------------------------------------------------------------------+
#property strict

input double InpLotSize      = 0.1;
input int    InpMagicNumber  = {magic};
input double InpSLMultiplier = {sl_val};
input double InpTPMultiplier = {tp_val};
input int    InpATRPeriod    = 14;

void OnTick() {{
   if (Bars < InpATRPeriod + 2) return;
   double atr = iATR(NULL, 0, InpATRPeriod, 1);
   if (atr <= 0) return;
   double sl = atr * InpSLMultiplier;
   double tp = atr * InpTPMultiplier;
   if (CountOrders() > 0) return;
   double ask = MarketInfo(Symbol(), MODE_ASK);
   double bid = MarketInfo(Symbol(), MODE_BID);
   double mf = iMA(NULL, 0, 8,  0, MODE_EMA, PRICE_CLOSE, 1);
   double ms = iMA(NULL, 0, 21, 0, MODE_EMA, PRICE_CLOSE, 1);
   if (mf > ms) OrderSend(Symbol(), OP_BUY,  InpLotSize, ask, 3, ask-sl, ask+tp, "G4_R3_{n:03d}", InpMagicNumber, 0, clrBlue);
   else if (mf < ms) OrderSend(Symbol(), OP_SELL, InpLotSize, bid, 3, bid+sl, bid-tp, "G4_R3_{n:03d}", InpMagicNumber, 0, clrRed);
}}

int OnInit() {{ return INIT_SUCCEEDED; }}
int CountOrders() {{
   int c=0;
   for (int i=OrdersTotal()-1; i>=0; i--)
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         if (OrderSymbol()==Symbol() && OrderMagicNumber()==InpMagicNumber) c++;
   return c;
}}
'''

os.makedirs(R3_DIR, exist_ok=True)
print(f"\n[.mq4 ?앹꽦] {R3_DIR}")

mq4_files = []
for n, sc in enumerate(final_scenarios, 1):
    magic = 130000 + n
    fname = f"G4_TR_SC{n:03d}_R3"
    content = MQ4_TEMPLATE.format(n=n, sl_val=sc["sl"], tp_val=sc["tp"], magic=magic)
    mq4_path = os.path.join(R3_DIR, fname + ".mq4")
    with open(mq4_path, "w", encoding="utf-8") as f:
        f.write(content)
    mq4_files.append((mq4_path, fname, sc))
    print(f"  [GEN] {fname}.mq4  sl={sc['sl']}  tp={sc['tp']}")

# ?? MetaEditor 而댄뙆???????????????????????????????????????????????????????
print(f"\n[而댄뙆?? MetaEditor {len(mq4_files)}媛?..")
if not os.path.exists(ME_EXE):
    print(f"  [ERROR] metaeditor.exe ?놁쓬: {ME_EXE}")
    sys.exit(1)

# 湲곗〈 R3 .ex4 諛깆뾽
existing_r3 = glob.glob(os.path.join(EXPERTS, "G4_TR_SC*_R3.ex4"))
if existing_r3:
    ts = datetime.now().strftime("%H%M")
    bak = os.path.join(BACKUP_ROOT, f"R3_ex4_bak_{ts}")
    os.makedirs(bak, exist_ok=True)
    for f in existing_r3:
        shutil.move(f, os.path.join(bak, os.path.basename(f)))
    print(f"  湲곗〈 R3 .ex4 {len(existing_r3)}媛?諛깆뾽 ?꾨즺")

ok = 0; fail = 0
compiled = []
for mq4_path, fname, sc in mq4_files:
    log_path = mq4_path.replace(".mq4", ".log")
    cmd = f'"{ME_EXE}" /compile:"{mq4_path}" /log:"{log_path}" /portable'
    subprocess.run(cmd, shell=True, cwd=MT4_DIR, capture_output=True, timeout=30)
    ex4_src = mq4_path.replace(".mq4", ".ex4")
    ex4_dst = os.path.join(EXPERTS, fname + ".ex4")
    if os.path.exists(ex4_src):
        shutil.copy2(ex4_src, ex4_dst)
        ok += 1
        print(f"  [OK] {fname}.ex4")
        compiled.append({"sc_id": f"SC{ok:03d}", "file": fname + ".ex4",
                         "magic": 130000 + ok,
                         "sl": sc["sl"], "tp": sc["tp"], "source": sc["source"]})
    else:
        fail += 1
        print(f"  [FAIL] {fname}.mq4")

print(f"\n而댄뙆?? {ok} OK / {fail} FAIL")

# ?? R3 遺꾩꽍 ?뚯씪 ?낅뜲?댄듃 ?????????????????????????????????????????????????
r3_analysis = {
    "round": 3,
    "symbol": "XAUUSD",
    "tf": "M5",
    "from_date": "2025.01.01",
    "to_date": "2026.06.30",
    "generated_by": "v6.0 modules (ParamAnalyzer + gen_round_sets_v2 + gen_bottom_fix_sets + grid)",
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "base_folder": HERE,
    "note": "R2(USDJPY M30) ?꾨? ?먯떎 -> XAUUSD M5 蹂듦?, v6.0 紐⑤뱢濡?R1 ?ㅼ쐵?ㅽ뙚 湲곕컲 ?뺣? ?먯깋",
    "sweet_spots_raw":    {k: {kk: round(vv, 6) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in sweet_spots.items()},
    "sweet_spots_forced": forced_sweet_spots,
    "correlations_raw":   raw_correlations,
    "correlations_forced":forced_correlations,
    "top_comparison":     top_comparison,
    "r1_best": [
        {"rank": i+1, "sl": float(r["params"]["sl"]), "tp": float(r["params"]["tp"]),
         "profit": r["htm"].get("profit", 0), "score": r["htm"].get("score", 0)}
        for i, r in enumerate(sorted_r1[:3])
    ],
    "r2_result": "ALL NEGATIVE on USDJPY M30",
    "scenarios": compiled,
    "compiled_ok": ok,
    "compiled_fail": fail,
}

out_file = os.path.join(RESULTS, "R3_prep_analysis.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(r3_analysis, f, indent=2, ensure_ascii=False)
print(f"\n[??? {out_file}")

# ?? 理쒖쥌 蹂닿퀬 ?????????????????????????????????????????????????????????????
r3_ex4 = glob.glob(os.path.join(EXPERTS, "G4_TR_SC*_R3.ex4"))
subdirs = [d for d in os.listdir(EXPERTS) if os.path.isdir(os.path.join(EXPERTS, d)) and d != "mqlcache"]
print("\n" + "=" * 60)
print(f"  R3 ?앹꽦 ?꾨즺 - v6.0 紐⑤뱢 ?ъ슜")
print(f"  而댄뙆?? {ok}/{len(final_scenarios)} OK")
print(f"  諛⑸쾿: gen_round_sets_v2 + gen_bottom_fix_sets + grid")
print(f"  ??? XAUUSD M5")
print(f"  .ex4: Experts 猷⑦듃 {len(r3_ex4)}媛?)
print(f"  ?쒕툕?대뜑: {subdirs}")
if len(subdirs) > 1:
    print(f"  [WARNING] 1?대뜑 洹쒖튃 ?꾨컲 {len(subdirs)}媛?")
print("=" * 60)

