"""
BTC_Gold_100 배치 백테스트 런처
- B_BTC_SP_* EA → BTCUSD × M5/M15/M30
- G4v7_*       EA → XAUUSD × M5/M15/M30
- 기간: 2025.04.01 ~ 2026.04.01 (1년)
"""
import os, sys, json, glob, shutil, time
from datetime import datetime

# ── 경로 설정 ─────────────────────────────────────────────────
SOLO_DIR    = os.path.dirname(os.path.abspath(__file__))
MT4_DIR     = r'C:\AG TO DO\MT4'
EXPERTS_DIR = os.path.join(MT4_DIR, r'MQL4\Experts')
BTC_GOLD    = os.path.join(EXPERTS_DIR, 'BTC_Gold_100')
CONFIGS_DIR = os.path.join(SOLO_DIR, 'configs')
CMD_JSON    = os.path.join(CONFIGS_DIR, 'command.json')
DONE_FLAG   = os.path.join(CONFIGS_DIR, 'test_completed.flag')
RESULTS_DIR = os.path.join(SOLO_DIR, 'g4_results')
REPORTS_BASE= os.path.join(SOLO_DIR, 'reports')
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── 설정 (UI 패치 파일 우선 읽기) ─────────────────────────────
FROM_DATE  = '2025.04.01'
TO_DATE    = '2026.04.01'
TIMEFRAMES = ['M5', 'M15', 'M30']
TIMEOUT    = 600   # 각 백테스트 최대 대기 (초)

_patch_path = os.environ.get('BTC_BATCH_PATCH',
              os.path.join(CONFIGS_DIR, '_btc_batch_patch.json'))
if os.path.exists(_patch_path):
    try:
        with open(_patch_path, encoding='utf-8') as _pf:
            _p = json.load(_pf)
        FROM_DATE  = _p.get('from_date', FROM_DATE)
        TO_DATE    = _p.get('to_date',   TO_DATE)
        TIMEFRAMES = _p.get('timeframes', TIMEFRAMES)
        _SYMS_OVERRIDE = _p.get('symbols', None)
        print(f"  [UI 패치] 기간={FROM_DATE}~{TO_DATE} TF={TIMEFRAMES}")
    except: _SYMS_OVERRIDE = None
else:
    _SYMS_OVERRIDE = None

print(f"\n{'='*60}")
print(f"  BTC_Gold_100 배치 런처")
print(f"  기간: {FROM_DATE} ~ {TO_DATE}")
print(f"  TF:   {' / '.join(TIMEFRAMES)}")
print(f"{'='*60}")

# ── EA 목록 수집 ──────────────────────────────────────────────
all_ex4 = sorted([f for f in os.listdir(BTC_GOLD) if f.endswith('.ex4')])
btc_eas  = sorted([f for f in all_ex4 if f.startswith('B_BTC')])
gold_eas = sorted([f for f in all_ex4 if f.startswith('G4v7')])

print(f"\nEA 목록:")
print(f"  BTC  전용 (B_BTC_SP): {len(btc_eas):3d}개")
print(f"  Gold 전용 (G4v7):     {len(gold_eas):3d}개")
print(f"  합계:                 {len(btc_eas)+len(gold_eas):3d}개")
print(f"  TF {len(TIMEFRAMES)}개 × = 총 {(len(btc_eas)+len(gold_eas))*len(TIMEFRAMES):3d}회 백테스트\n")

# ── EXPERTS 루트에 EA 복사 ─────────────────────────────────────
print("EXPERTS 루트로 EA 복사...")
for fname in all_ex4:
    src = os.path.join(BTC_GOLD, fname)
    dst = os.path.join(EXPERTS_DIR, fname)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
print(f"  복사 완료: {len(all_ex4)}개")

# ── IPC 헬퍼 ──────────────────────────────────────────────────
def send_command_and_wait(ea_name, symbol, tf, from_date, to_date,
                          sc_num, total, timeout=TIMEOUT):
    """command.json 작성 → test_completed.flag 대기."""
    # 이전 플래그 삭제
    for p in glob.glob(DONE_FLAG.replace('.flag', '*.flag')):
        try: os.remove(p)
        except: pass

    cmd = {
        'action':     'run_backtest',
        'ea_name':    ea_name, 'symbol': symbol, 'tf': tf,
        'from_date':  from_date, 'to_date': to_date,
        'iteration':  sc_num, 'total_sets': total,
        'timestamp':  datetime.now().strftime('%Y%m%d_%H%M%S'),
    }
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    with open(CMD_JSON, 'w', encoding='utf-8') as f:
        json.dump(cmd, f, ensure_ascii=False)
    print(f"  [{sc_num:3d}/{total}] {symbol} {tf:3s} → {ea_name[:55]}")

    t0 = time.time()
    while time.time() - t0 < timeout:
        flags = glob.glob(DONE_FLAG.replace('.flag', '*.flag'))
        if flags:
            return True
        stop = os.path.join(CONFIGS_DIR, 'runner_stop.signal')
        if os.path.exists(stop):
            print("  [STOP] 중지 신호 감지")
            return False
        elapsed = int(time.time() - t0)
        if elapsed % 120 == 0 and elapsed > 0:
            print(f"  [{sc_num}/{total}] 대기 {elapsed}s/{timeout}s ...")
        time.sleep(2)

    print(f"  [{sc_num}/{total}] ⚠️ 타임아웃 {timeout}s")
    return False

def find_latest_htm(ea_name_base, sym, tf):
    """최신 HTM 결과 파일 찾기"""
    pattern = os.path.join(REPORTS_BASE, '**', f'*{ea_name_base}*{sym}*{tf}*.htm')
    files   = glob.glob(pattern, recursive=True)
    pattern2= os.path.join(REPORTS_BASE, '**', f'*{ea_name_base}*.htm')
    files  += glob.glob(pattern2, recursive=True)
    if not files: return None
    # 타임스탬프 기준 최신
    import re
    def ts(p):
        m = re.search(r'_(\d{10})_', os.path.basename(p))
        return m.group(1) if m else '0000000000'
    return max(files, key=lambda p: (ts(p), os.path.getctime(p)))

def parse_htm(path):
    import re as _re
    try:
        with open(path, 'rb') as f: raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        nums = []
        for v in _re.findall(r'<td[^>]*align=right[^>]*>([-\d.,]+)</td>', text):
            try: nums.append(float(v.replace(',', '')))
            except: pass
        profit = pf = dd = trades = 0.0
        for i, n in enumerate(nums):
            if abs(n - 10000.0) < 0.1 and i + 4 < len(nums):
                profit = nums[i + 1]
                pf     = nums[i + 4]
                break
        m = _re.search(r'<td[^>]*align=right[^>]*>([\d.]+)%\s*\([\d.,]+\)</td>', text)
        dd = float(m.group(1)) if m else 0.0
        m2 = _re.search(r'<td[^>]*align=right[^>]*>(\d+)</td><td[^>]*>[^<]+(won|%)', text)
        trades = int(m2.group(1)) if m2 else 0
        return {'profit': profit, 'drawdown_pct': dd,
                'profit_factor': pf, 'trades': trades}
    except Exception as e:
        return {'profit': 0, 'drawdown_pct': 100, 'profit_factor': 0,
                'trades': 0, 'error': str(e)}

def calc_score(p):
    profit = p.get('profit', 0)
    dd     = p.get('drawdown_pct', 100)
    pf     = p.get('profit_factor', 0)
    trades = p.get('trades', 0)
    if dd >= 100 or profit <= 0: return 0.0
    s_profit = min(30, profit / 10000)
    s_safety = max(0, 20 - dd)
    s_stab   = min(20, trades / 300)
    s_eff    = min(15, pf * 5)
    s_fit    = 15 if trades >= 50 else trades / 50 * 15
    return round(s_profit + s_safety + s_stab + s_eff + s_fit, 2)

# ── 백테스트 실행 ─────────────────────────────────────────────
# EA × TF 조합 빌드 (BTC EA → BTCUSD, Gold EA → XAUUSD)
tasks = []
for ea in btc_eas:
    for tf in TIMEFRAMES:
        tasks.append((ea, 'BTCUSD', tf))
for ea in gold_eas:
    for tf in TIMEFRAMES:
        tasks.append((ea, 'XAUUSD', tf))

total = len(tasks)
print(f"\n총 {total}회 백테스트 시작\n")

all_results = []
t_start = time.time()

for idx, (ea_fname, symbol, tf) in enumerate(tasks):
    sc_num = idx + 1
    ea_base = ea_fname.replace('.ex4', '')

    ok = send_command_and_wait(
        ea_name=ea_fname, symbol=symbol, tf=tf,
        from_date=FROM_DATE, to_date=TO_DATE,
        sc_num=sc_num, total=total
    )

    if not ok:
        all_results.append({
            'ea_name': ea_fname, 'symbol': symbol, 'tf': tf,
            'profit': 0, 'drawdown_pct': 100, 'profit_factor': 0,
            'trades': 0, 'score': 0, 'status': 'timeout'
        })
        continue

    # HTM 파싱
    htm = find_latest_htm(ea_base[:20], symbol, tf)
    if htm:
        p = parse_htm(htm)
        p['score'] = calc_score(p)
        p['ea_name'] = ea_fname
        p['symbol']  = symbol
        p['tf']      = tf
        p['status']  = 'ok'
        all_results.append(p)
        print(f"    ↳ score={p['score']:.1f} profit=${p['profit']:,.0f} dd={p['drawdown_pct']:.1f}%")
    else:
        all_results.append({
            'ea_name': ea_fname, 'symbol': symbol, 'tf': tf,
            'profit': 0, 'drawdown_pct': 100, 'profit_factor': 0,
            'trades': 0, 'score': 0, 'status': 'no_htm'
        })

    # ── 실시간 부분 저장 (모니터 탭 연동) ──
    live_json = os.path.join(RESULTS_DIR, 'BTC_GOLD100_live.json')
    with open(live_json, 'w', encoding='utf-8') as f:
        json.dump({
            'round': 'BTC_GOLD100_LIVE',
            'from_date': FROM_DATE, 'to_date': TO_DATE,
            'progress': f'{sc_num}/{total}',
            'results': all_results,
            'timestamp': datetime.now().isoformat(),
        }, f, ensure_ascii=False)

    # 진행률 표시
    if sc_num % 30 == 0:
        elapsed = time.time() - t_start
        rate = sc_num / elapsed
        remain = (total - sc_num) / rate / 60
        done = [r for r in all_results if r.get('score',0)>0]
        avg_s = sum(r['score'] for r in done)/len(done) if done else 0
        print(f"\n  진행: {sc_num}/{total} | 평균score={avg_s:.1f} | ~{remain:.0f}분 남음\n")

# ── 결과 저장 ─────────────────────────────────────────────────
ts = datetime.now().strftime('%m%d_%H%M')
out_json = os.path.join(RESULTS_DIR, f'BTC_GOLD100_{ts}.json')

# 최종 결과: EA별 최고 점수
from collections import defaultdict
ea_best = defaultdict(lambda: {'score': -1})
for r in all_results:
    k = r['ea_name']
    if r.get('score', 0) > ea_best[k]['score']:
        ea_best[k] = r

final_results = sorted(ea_best.values(), key=lambda x: -x.get('score', 0))

out = {
    'round': 'BTC_GOLD_100',
    'from_date': FROM_DATE, 'to_date': TO_DATE,
    'timeframes': TIMEFRAMES,
    'btc_ea_count': len(btc_eas), 'gold_ea_count': len(gold_eas),
    'total_tests': total,
    'results': final_results,
    'timestamp': datetime.now().isoformat(),
}

with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# ── 최종 요약 ─────────────────────────────────────────────────
done = [r for r in final_results if r.get('score', 0) > 0]
btc_done  = [r for r in done if 'BTC' in r.get('symbol','')]
gold_done = [r for r in done if 'XAU' in r.get('symbol','')]

print(f"\n{'='*60}")
print(f"  BTC_Gold_100 백테스트 완료!")
print(f"  총 소요: {(time.time()-t_start)/60:.0f}분")
print(f"")
if btc_done:
    print(f"  [BTC]  완료={len(btc_done)} 평균score={sum(r['score'] for r in btc_done)/len(btc_done):.1f}")
    top3_btc = sorted(btc_done, key=lambda x:-x['score'])[:3]
    for r in top3_btc:
        print(f"    TOP: score={r['score']:.1f} {r['ea_name'][:45]}")
if gold_done:
    print(f"  [Gold] 완료={len(gold_done)} 평균score={sum(r['score'] for r in gold_done)/len(gold_done):.1f}")
    top3_gold = sorted(gold_done, key=lambda x:-x['score'])[:3]
    for r in top3_gold:
        print(f"    TOP: score={r['score']:.1f} {r['ea_name'][:45]}")
print(f"")
print(f"  결과 저장: {out_json}")
print(f"{'='*60}")

# all_done.flag 생성 (SOLO 알람)
with open(os.path.join(CONFIGS_DIR, 'all_done.flag'), 'w') as f:
    f.write(datetime.now().isoformat())
print("  all_done.flag 생성 완료 (SOLO 알람)")
