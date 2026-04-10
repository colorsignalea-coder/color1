"""
post_r10_validation.py
======================
R10 완료 후 자동 실행되는 종합 검증 스크립트.

동작:
  1. R10 완료 감지 (all_done.flag 또는 g4_results 확인)
  2. 전체 라운드(R4~R10)에서 상위 13개 고유 파라미터 추출
  3. 100개 GENETIC 샘플 생성 (모든 이전 결과 기반)
  4. GOLD+BTC × M5+M30 = 4콤보 × 100시나리오 = 400 백테스트
  5. 결과 → g4_results/V7_POST_R10_{ts}.json 저장
  6. HTML 리포트 자동 생성

실행:
  python post_r10_validation.py
  또는 START_POST_R10.bat (R10 완료 감지 자동 대기)
"""
import os, sys, json, glob, shutil, time
from datetime import datetime

# ── 경로 ─────────────────────────────────────────────────────────────────
SOLO_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(SOLO_DIR, 'configs')
RESULTS_DIR = os.path.join(SOLO_DIR, 'g4_results')
REPORTS_BASE= os.path.join(SOLO_DIR, 'reports')
CMD_JSON    = os.path.join(CONFIGS_DIR, 'command.json')
DONE_FLAG   = os.path.join(CONFIGS_DIR, 'test_completed.flag')

sys.path.insert(0, SOLO_DIR)

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8',
                                  errors='replace', line_buffering=True)

# ── 설정 ─────────────────────────────────────────────────────────────────
SYMBOLS        = ['XAUUSD', 'BTCUSD']   # GOLD + BTC
TIMEFRAMES     = ['M5', 'M30']           # 5분 + 30분
SAMPLES        = 100                     # 시나리오 수 (100×4콤보=400 백테스트)
FROM_DATE      = '2025.04.01'
TO_DATE        = '2026.04.01'
MAX_WAIT_HOURS = 12                      # R10 완료 최대 대기 시간
BATCH_SIZE     = 100                     # 배치당 시나리오 수 (100씩 4배치)

# ── MT4 경로 ─────────────────────────────────────────────────────────────
def _find_mt4():
    for p in [r'C:\AG TO DO\MT4', r'C:\MT4', r'D:\MT4',
              r'C:\Program Files\MetaTrader 4']:
        if os.path.exists(os.path.join(p, 'terminal.exe')):
            return p
    return r'C:\AG TO DO\MT4'

MT4_DIR     = _find_mt4()
EXPERTS_DIR = os.path.join(MT4_DIR, r'MQL4\Experts')
ME_EXE      = os.path.join(MT4_DIR, 'metaeditor.exe')
READY_DIR   = os.path.join(REPORTS_BASE, 'READY_FOR_TEST')
AFTER_DIR   = os.path.join(REPORTS_BASE, 'AFTER_FOR_TEST')

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(READY_DIR,   exist_ok=True)
os.makedirs(AFTER_DIR,   exist_ok=True)


# ═════════════════════════════════════════════════════════════════════════
# 1. R10 완료 대기
# ═════════════════════════════════════════════════════════════════════════

def wait_for_r10():
    """R10이 완료될 때까지 대기. 이미 완료된 경우 즉시 반환."""
    print(f"\n{'='*60}")
    print(f"  R10 완료 대기 중...")
    print(f"{'='*60}")

    deadline = time.time() + MAX_WAIT_HOURS * 3600

    while time.time() < deadline:
        # 방법1: g4_results에서 R10 결과 파일 확인 (50개 이상 완료)
        r10_files = sorted(glob.glob(os.path.join(RESULTS_DIR, 'V7_R10*.json')))
        for rf in r10_files:
            try:
                with open(rf, encoding='utf-8') as f:
                    d = json.load(f)
                n_done = len([r for r in d.get('results', []) if r.get('score', 0) > 0
                               or r.get('trades', 0) > 0])
                if n_done >= 40:   # 80% 이상 완료 = 충분
                    print(f"  [OK] R10 결과 감지: {rf} ({n_done}개 완료)")
                    return True
            except Exception:
                pass

        # 방법2: all_done.flag 확인
        all_done = os.path.join(CONFIGS_DIR, 'all_done.flag')
        if os.path.exists(all_done):
            try:
                with open(all_done, encoding='utf-8') as f:
                    d = json.load(f)
                if d.get('round', 0) >= 10:
                    print(f"  [OK] all_done.flag 감지: R{d['round']} 완료")
                    return True
            except Exception:
                pass

        # 방법3: status.json 확인
        sts = os.path.join(CONFIGS_DIR, 'status.json')
        if os.path.exists(sts):
            try:
                with open(sts, encoding='utf-8') as f:
                    d = json.load(f)
                if d.get('status') == 'done' and d.get('round', 0) >= 10:
                    print(f"  [OK] status.json: R{d['round']} done")
                    return True
            except Exception:
                pass

        # 30초 대기 후 재확인
        remaining = int((deadline - time.time()) / 60)
        print(f"  R10 진행 중... (잔여 최대대기 {remaining}분)", end='\r')
        time.sleep(30)

    print(f"\n  [WARN] {MAX_WAIT_HOURS}시간 대기 초과 — 강제 시작")
    return True   # 타임아웃 후에도 진행


# ═════════════════════════════════════════════════════════════════════════
# 2. 전체 결과에서 상위 13개 파라미터 추출
# ═════════════════════════════════════════════════════════════════════════

def load_all_results():
    """g4_results에서 전체 이전 결과 로드."""
    all_res = []
    for rf in sorted(glob.glob(os.path.join(RESULTS_DIR, 'V7_R*.json'))):
        try:
            with open(rf, encoding='utf-8') as f:
                d = json.load(f)
            for r in d.get('results', []):
                if r.get('score', 0) > 0:
                    all_res.append({'params': r.get('params', {}),
                                    'score':  r.get('score', 0),
                                    'ea_name': r.get('ea_name', ''),
                                    'round': r.get('round', 0)})
        except Exception as e:
            print(f"  [WARN] 결과 로드 실패: {rf}: {e}")
    return all_res


def get_top13(all_results):
    """전체 결과에서 파라미터 중복 제거 후 상위 13개 반환."""
    seen = set()
    top13 = []
    for r in sorted(all_results, key=lambda x: x['score'], reverse=True):
        p = r['params']
        # 파라미터 조합으로 중복 감지
        key = (
            round(p.get('InpSLMultiplier', 0), 2),
            round(p.get('InpTPMultiplier', 0), 1),
            int(p.get('InpATRPeriod', 0)),
            int(p.get('InpFastMA', 0)),
            int(p.get('InpSlowMA', 0)),
        )
        if key not in seen:
            seen.add(key)
            top13.append(r)
        if len(top13) >= 13:
            break
    return top13


# ═════════════════════════════════════════════════════════════════════════
# 3. 시나리오 생성 (GENETIC 100개 + 상위 13개 포함)
# ═════════════════════════════════════════════════════════════════════════

def generate_scenarios(all_results, n=100):
    """
    GENETIC 샘플링으로 100개 생성.
    상위 13개는 반드시 포함 (검증용).
    """
    from core.param_space import make_g4_param_space
    from core.sampler     import get_samples_for_round

    param_space = make_g4_param_space(extra_params=True)

    # R11 기준 GENETIC 샘플링
    samples = get_samples_for_round(
        param_space, round_num=11, prev_results=all_results,
        n=n, seed=1100)

    return samples


# ═════════════════════════════════════════════════════════════════════════
# 4. MQ4 컴파일
# ═════════════════════════════════════════════════════════════════════════

def compile_mq4(mq4_path):
    import subprocess
    if not os.path.exists(ME_EXE):
        print(f"  [WARN] MetaEditor not found: {ME_EXE}")
        return False
    log_path = mq4_path.replace('.mq4', '.log')
    ex4_path = mq4_path.replace('.mq4', '.ex4')
    if os.path.exists(ex4_path):
        try: os.remove(ex4_path)
        except: pass
    try:
        cmd = f'"{ME_EXE}" /compile:"{mq4_path}" /log:"{log_path}" /portable'
        subprocess.run(cmd, shell=True, timeout=30, cwd=os.path.dirname(ME_EXE),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        return os.path.exists(ex4_path)
    except Exception as e:
        print(f"  [ERR] 컴파일 오류: {e}")
        return False


def generate_round_files(samples, round_label='POST10'):
    from core.ea_template_v7 import generate_mq4_v7, make_ea_filename
    staging = os.path.join(EXPERTS_DIR, f'_staging_v7_{round_label}')
    os.makedirs(staging, exist_ok=True)

    scenarios_map = {}
    for sc_id, params in enumerate(samples, 1):
        base     = make_ea_filename(sc_id, round_label, params)
        mq4_path = os.path.join(EXPERTS_DIR, base + '.mq4')
        ex4_path = os.path.join(EXPERTS_DIR, base + '.ex4')

        src = generate_mq4_v7(sc_id, round_label, params)
        with open(mq4_path, 'w', encoding='ascii', errors='replace') as f:
            f.write(src)
        shutil.copy2(mq4_path, os.path.join(staging, base + '.mq4'))

        ok = compile_mq4(mq4_path)
        if ok:
            scenarios_map[sc_id] = {'params': params, 'fname': base + '.ex4'}
            # READY_FOR_TEST 복사
            try: shutil.copy2(ex4_path, os.path.join(READY_DIR, base + '.ex4'))
            except: pass
        else:
            print(f"  [FAIL] SC{sc_id:03d} 컴파일 실패")

    print(f"  컴파일: {len(scenarios_map)} OK / {len(samples)-len(scenarios_map)} FAIL")
    return scenarios_map


# ═════════════════════════════════════════════════════════════════════════
# 5. 백테스트 실행 (4배치: GOLD×M5, GOLD×M30, BTC×M5, BTC×M30)
# ═════════════════════════════════════════════════════════════════════════

def _write_status(round_num, sc_num, total, ea_name, sym, tf):
    status = {
        'status':  'busy',
        'round':   f'POST_R10_{sym}_{tf}',
        'current': sc_num,
        'total':   total,
        'ea':      ea_name,
        'message': f'POST_R10 [{sc_num}/{total}] {sym} {tf} {ea_name}',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    }
    try:
        with open(os.path.join(CONFIGS_DIR, 'status.json'), 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False)
    except Exception:
        pass


def send_command_and_wait(ea_name, symbol, tf, sc_num, total, timeout=600):
    for p in glob.glob(DONE_FLAG.replace('.flag', '*.flag')):
        try: os.remove(p)
        except: pass

    cmd = {
        'action':     'run_backtest',
        'ea_name':    ea_name,
        'symbol':     symbol,
        'tf':         tf,
        'from_date':  FROM_DATE,
        'to_date':    TO_DATE,
        'iteration':  sc_num,
        'total_sets': total,
        'timestamp':  datetime.now().strftime('%Y%m%d_%H%M%S'),
    }
    with open(CMD_JSON, 'w', encoding='utf-8') as f:
        json.dump(cmd, f, ensure_ascii=False)
    print(f"  [{sc_num}/{total}] {symbol} {tf} → {ea_name}")

    t0 = time.time()
    while time.time() - t0 < timeout:
        flags = glob.glob(DONE_FLAG.replace('.flag', '*.flag'))
        if flags:
            print(f"  [{sc_num}/{total}] 완료 ({int(time.time()-t0)}s)")
            return True
        stop = os.path.join(CONFIGS_DIR, 'runner_stop.signal')
        if os.path.exists(stop):
            print("  [STOP] 중지 신호")
            return False
        elapsed = int(time.time() - t0)
        if elapsed % 60 == 0 and elapsed > 0:
            print(f"  [{sc_num}/{total}] 대기 {elapsed}s...")
        time.sleep(2)

    print(f"  [{sc_num}/{total}] 타임아웃 ({timeout}s)")
    return False


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


def find_latest_htm(ea_name, newer_than=None):
    import re as _re
    today = datetime.now().strftime('%Y%m%d')
    base  = os.path.splitext(ea_name)[0]

    def _ftime(fpath):
        m = _re.search(r'_(\d{10})_', os.path.basename(fpath))
        if m:
            ts = m.group(1)
            try:
                now = datetime.now()
                return datetime(now.year, int(ts[0:2]), int(ts[2:4]),
                                int(ts[4:6]), int(ts[6:8]), int(ts[8:10])).timestamp()
            except: pass
        try: return os.path.getctime(fpath)
        except: return 0.0

    for pattern in [
        os.path.join(REPORTS_BASE, today, ea_name, '*.htm'),
        os.path.join(REPORTS_BASE, today, ea_name, '*.ht'),
        os.path.join(REPORTS_BASE, '**', base + '*.htm'),
        os.path.join(REPORTS_BASE, '**', base + '*.ht'),
    ]:
        files = glob.glob(pattern, recursive=True)
        if newer_than is not None:
            files = [f for f in files if _ftime(f) > newer_than]
        if files:
            return max(files, key=_ftime)
    return None


def run_validation_batch(scenarios_map):
    """
    4배치 실행:
      배치1: 100 SC × GOLD × M5
      배치2: 100 SC × GOLD × M30
      배치3: 100 SC × BTC  × M5
      배치4: 100 SC × BTC  × M30
    각 SC별 4콤보 결과를 합산해 최종 score 산출.
    """
    from core.scorer import score_full

    items     = sorted(scenarios_map.items())
    n_items   = len(items)
    n_combos  = len(SYMBOLS) * len(TIMEFRAMES)
    total_bts = n_items * n_combos   # 예: 100 × 4 = 400

    print(f"\n{'='*60}")
    print(f"  POST-R10 검증  |  {n_items}개 시나리오")
    print(f"  심볼: {'+'.join(SYMBOLS)}  TF: {'+'.join(TIMEFRAMES)}")
    print(f"  총 {total_bts}회 백테스트 (4배치 × {n_items})")
    print(f"  기간: {FROM_DATE} ~ {TO_DATE}")
    print(f"{'='*60}")

    # sc_id → combo_results 누적
    combo_acc = {sc_id: [] for sc_id, _ in items}

    global_bt_num = 0
    error_count   = 0

    # 4배치: GOLD_M5, GOLD_M30, BTC_M5, BTC_M30
    for batch_idx, (sym, tf) in enumerate(
            [(s, t) for s in SYMBOLS for t in TIMEFRAMES], 1):

        print(f"\n  ── 배치 {batch_idx}/4: {sym} {tf} ({n_items}개) ──")

        for sc_id, sc in items:
            ea_name = sc['fname']
            params  = sc['params']

            global_bt_num += 1
            t_before = time.time()
            _write_status('POST10', global_bt_num, total_bts, ea_name, sym, tf)

            ok = send_command_and_wait(
                ea_name, sym, tf,
                sc_num=global_bt_num, total=total_bts)

            if not ok:
                error_count += 1
                if error_count >= 15:
                    print("  [ABORT] 에러 15회 이상 — 중단")
                    break
                combo_acc[sc_id].append({
                    'sym': sym, 'tf': tf,
                    'htm_data':  {'profit': 0, 'drawdown_pct': 100,
                                  'profit_factor': 0, 'trades': 0},
                    'score_res': score_full({'profit': 0, 'drawdown_pct': 100,
                                            'profit_factor': 0, 'trades': 0}),
                })
                continue

            # HTM 탐색
            htm = find_latest_htm(ea_name, newer_than=t_before)
            if not htm:
                t0 = time.time()
                while time.time() - t0 < 120:
                    time.sleep(10)
                    htm = find_latest_htm(ea_name, newer_than=t_before)
                    if htm: break

            c_htm  = parse_htm(htm) if htm else {
                'profit': 0, 'drawdown_pct': 100,
                'profit_factor': 0, 'trades': 0}
            c_score = score_full(c_htm)
            combo_acc[sc_id].append({
                'sym': sym, 'tf': tf,
                'htm_data': c_htm,
                'score_res': c_score,
            })
            print(f"  │  SC{sc_id:03d} {sym} {tf}: "
                  f"${c_htm['profit']:,.0f}  DD={c_htm['drawdown_pct']:.1f}%  "
                  f"score={c_score['total']:.1f}")
        else:
            continue
        break  # inner error abort propagated

    # ── 집계 ──────────────────────────────────────────────────────────
    results = []
    for sc_id, sc in items:
        combos = combo_acc.get(sc_id, [])
        if combos:
            sc_total  = sum(c['score_res']['total'] for c in combos) / len(combos)
            htm_avg   = {
                'profit':       sum(c['htm_data']['profit']       for c in combos) / len(combos),
                'drawdown_pct': max(c['htm_data']['drawdown_pct'] for c in combos),
                'profit_factor':sum(c['htm_data']['profit_factor']for c in combos) / len(combos),
                'trades':       sum(c['htm_data']['trades']       for c in combos),
            }
            bd = combos[0]['score_res']['breakdown']
        else:
            sc_total = 0
            htm_avg  = {'profit': 0, 'drawdown_pct': 100,
                        'profit_factor': 0, 'trades': 0}
            bd       = {}

        entry = {
            'sc_id':    sc_id,
            'ea_name':  sc['fname'],
            'params':   sc['params'],
            'round':    'POST_R10',
            **htm_avg,
            'score':        sc_total,
            'score_detail': bd,
            'combos': [{'sym': c['sym'], 'tf': c['tf'],
                        'score': c['score_res']['total'],
                        'profit': c['htm_data']['profit'],
                        'dd':    c['htm_data']['drawdown_pct']}
                       for c in combos],
        }
        results.append(entry)

        grade = 'S' if sc_total>=85 else 'A' if sc_total>=70 else 'B' if sc_total>=55 else 'C'
        print(f"  SC{sc_id:03d} 최종: score={sc_total:.1f}[{grade}] "
              f"avg_profit=${htm_avg['profit']:,.0f}  worst_DD={htm_avg['drawdown_pct']:.1f}%")

    return results


# ═════════════════════════════════════════════════════════════════════════
# 6. 결과 저장 + HTML 리포트
# ═════════════════════════════════════════════════════════════════════════

def save_results(results):
    ts    = datetime.now().strftime('%H%M')
    rfile = os.path.join(RESULTS_DIR, f'V7_POST_R10_{ts}.json')
    with open(rfile, 'w', encoding='utf-8') as f:
        json.dump({
            'round':      'POST_R10',
            'symbols':    SYMBOLS,
            'timeframes': TIMEFRAMES,
            'from_date':  FROM_DATE,
            'to_date':    TO_DATE,
            'n_scenarios':len(results),
            'results':    results,
            'timestamp':  datetime.now().isoformat(),
        }, f, indent=2, ensure_ascii=False)
    print(f"\n  결과 저장: {os.path.basename(rfile)}")
    return rfile


def print_top_report(results, n=13):
    top = sorted(results, key=lambda x: x['score'], reverse=True)[:n]
    print(f"\n  {'='*60}")
    print(f"  POST-R10 TOP {n} 최종 검증 결과")
    print(f"  {'='*60}")
    for i, e in enumerate(top, 1):
        nm    = e['ea_name'].replace('.ex4', '')[-45:]
        grade = 'S' if e['score']>=85 else 'A' if e['score']>=70 else 'B' if e['score']>=55 else 'C'
        print(f"  {i:2d}. [{grade}] score={e['score']:.1f}  "
              f"avg_profit=${e['profit']:,.0f}  worst_DD={e['drawdown_pct']:.1f}%")
        print(f"      {nm}")
        # 4콤보 breakdown
        for c in e.get('combos', []):
            print(f"         {c['sym']:8s} {c['tf']:4s}: "
                  f"${c['profit']:>10,.0f}  DD={c['dd']:.1f}%  score={c['score']:.1f}")
    print(f"  {'='*60}")


# ═════════════════════════════════════════════════════════════════════════
# 7. MAIN
# ═════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'#'*60}")
    print(f"  POST-R10 종합 검증")
    print(f"  {'+'.join(SYMBOLS)} × {'+'.join(TIMEFRAMES)}")
    print(f"  {SAMPLES}개 시나리오 × 4콤보 = {SAMPLES*len(SYMBOLS)*len(TIMEFRAMES)}회 백테스트")
    print(f"  기간: {FROM_DATE} ~ {TO_DATE}")
    print(f"{'#'*60}\n")

    # 1. R10 완료 대기 (--no-wait 옵션으로 스킵 가능)
    if '--no-wait' not in sys.argv:
        wait_for_r10()

    # 2. 전체 이전 결과 로드
    print("\n  이전 결과 로드 중...")
    all_results = load_all_results()
    print(f"  총 {len(all_results)}개 결과 로드")

    if not all_results:
        print("  [ERROR] 이전 결과 없음 — 중단")
        return

    # 상위 13개 출력
    top13 = get_top13(all_results)
    print(f"\n  상위 13개 고유 파라미터:")
    for i, r in enumerate(top13, 1):
        p = r['params']
        print(f"  {i:2d}. score={r['score']:.1f} "
              f"SL={p.get('InpSLMultiplier',0):.2f} "
              f"TP={p.get('InpTPMultiplier',0):.1f} "
              f"ATR={p.get('InpATRPeriod',0)} "
              f"MA={p.get('InpFastMA',0)}/{p.get('InpSlowMA',0)}")

    # 3. 100개 시나리오 생성 (GENETIC + top13 포함)
    print(f"\n  {SAMPLES}개 시나리오 생성 중 (GENETIC + 상위13 포함)...")
    samples = generate_scenarios(all_results, n=SAMPLES)
    print(f"  {len(samples)}개 샘플 생성 완료")

    # 4. MQ4 컴파일
    print(f"\n  MQ4 컴파일 중...")
    scenarios_map = generate_round_files(samples, round_label='POST10')
    if not scenarios_map:
        print("  [ERROR] 컴파일 실패 — 중단")
        return

    # 5. 4배치 백테스트 실행
    results = run_validation_batch(scenarios_map)

    if not results:
        print("  [ERROR] 백테스트 결과 없음")
        return

    # 6. 결과 저장
    rfile = save_results(results)

    # 7. TOP 리포트 출력
    print_top_report(results, n=13)

    # 8. HTML 리포트 생성
    try:
        sys.argv_backup = sys.argv[:]
        sys.argv = [rfile]
        import gen_ea_detail_html
        out_html = rfile.replace('.json', '.html')
        print(f"\n  HTML 리포트: {out_html}")
    except Exception as e:
        print(f"  [WARN] HTML 생성 스킵: {e}")

    # 9. 완료 플래그
    try:
        with open(os.path.join(CONFIGS_DIR, 'post_r10_done.flag'), 'w', encoding='utf-8') as f:
            json.dump({'timestamp': datetime.now().isoformat(),
                       'n_results': len(results),
                       'result_file': rfile}, f)
    except Exception:
        pass

    print(f"\n{'#'*60}")
    print(f"  POST-R10 검증 완료!")
    print(f"  결과: {rfile}")
    print(f"{'#'*60}\n")


if __name__ == '__main__':
    main()
