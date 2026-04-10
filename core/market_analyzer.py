"""
core/market_analyzer.py — EA Auto Master v6.1
================================================
라운드별 백테스트 결과 × MT4 실제 시장 데이터 비교 분석.

HTM에서 개별 거래(진입/청산 시간·가격·방향·SL/TP·결과) 파싱 후
XAUUSD5.hst 시장 데이터와 대조해 "왜 실패했는지" 자동 진단.

출력 구조 (analyze_round 반환값):
  {
    "round": int,
    "ea_name": str,
    "total_trades": int,
    "tp_hit_pct": float,
    "sl_hit_pct": float,
    "trend_aligned_pct": float,   # 시장 추세 방향과 일치한 거래 %
    "avg_tp_dist": float,         # 평균 TP 거리
    "avg_sl_dist": float,         # 평균 SL 거리
    "avg_mfe": float,             # 평균 최대유리이동(MFE) — TP 대비
    "tp_reachable_pct": float,    # MFE >= TP거리 였던 비율 (TP가 잡힐 수 있었나)
    "failure_patterns": dict,     # 실패 원인별 분류
    "market_context": str,        # 요약 텍스트 (GUI 표시용)
    "recommendation": str,        # 파라미터 변경 제안
  }
"""
import os
import re
import struct
import glob
from datetime import datetime, timedelta


# ── MT4 HST 파일 탐색 경로 ────────────────────────────────────────────────
_HST_SEARCH_DIRS = [
    r"C:\AG TO DO\MT4\history\MonetaMarketsTrading-Demo",
    r"C:\MT4\history\MonetaMarketsTrading-Demo",
    r"D:\MT4\history\MonetaMarketsTrading-Demo",
    r"C:\AG TO DO\MT4\history\default",
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. HTM 개별 거래 파싱
# ─────────────────────────────────────────────────────────────────────────────

def parse_trades_from_htm(htm_path):
    """
    MT4 Strategy Tester HTM에서 모든 개별 거래 파싱.

    반환: list of dict
      {open_time, close_time, direction, entry, sl, tp,
       close_price, close_type('t/p'|'s/l'|'close'), profit}
    """
    try:
        with open(htm_path, 'rb') as f:
            raw = f.read()
        enc = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
        html = raw.decode(enc, errors='replace')
    except Exception:
        return []

    all_trs = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)

    trades = []
    i = 0
    while i < len(all_trs) - 1:
        open_cells = re.findall(r'<td[^>]*>(.*?)</td>', all_trs[i], re.S)
        # open row: cells[2] == 'buy' or 'sell'
        if (len(open_cells) >= 8
                and open_cells[2].strip().lower() in ('buy', 'sell')):
            close_cells = re.findall(r'<td[^>]*>(.*?)</td>', all_trs[i + 1], re.S)
            if len(close_cells) >= 9:
                close_type = close_cells[2].strip().lower()  # t/p, s/l, close
                try:
                    profit = float(close_cells[8].replace(',', '').strip())
                except Exception:
                    profit = 0.0
                try:
                    open_dt  = datetime.strptime(open_cells[1].strip(),  '%Y.%m.%d %H:%M')
                    close_dt = datetime.strptime(close_cells[1].strip(), '%Y.%m.%d %H:%M')
                    entry_p  = float(open_cells[5].replace(',', ''))
                    sl_p     = float(open_cells[6].replace(',', ''))
                    tp_p     = float(open_cells[7].replace(',', ''))
                    close_p  = float(close_cells[5].replace(',', ''))
                    direction = open_cells[2].strip().lower()
                    trades.append({
                        'open_time':   open_dt,
                        'close_time':  close_dt,
                        'direction':   direction,
                        'entry':       entry_p,
                        'sl':          sl_p,
                        'tp':          tp_p,
                        'close_price': close_p,
                        'close_type':  close_type,
                        'profit':      profit,
                    })
                except Exception:
                    pass
            i += 2
        else:
            i += 1

    return trades


# ─────────────────────────────────────────────────────────────────────────────
# 2. MT4 HST 파일 로드
# ─────────────────────────────────────────────────────────────────────────────

def load_hst(symbol='XAUUSD', tf_minutes=5):
    """
    MT4 .hst 파일 로드 → {timestamp: {'o':o,'h':h,'l':l,'c':c}} dict 반환.
    빠른 룩업을 위해 Unix timestamp 키 사용.
    """
    fname = f"{symbol.upper()}{tf_minutes}.hst"
    hst_path = None
    for d in _HST_SEARCH_DIRS:
        cand = os.path.join(d, fname)
        if os.path.exists(cand):
            hst_path = cand
            break
    if not hst_path:
        return None, None

    try:
        with open(hst_path, 'rb') as f:
            raw = f.read()

        header_size = 148
        rec = raw[header_size:]

        # 레코드 크기 자동 감지 (48, 60, 44 바이트)
        rec_size = None
        for rs in (60, 48, 44):
            if len(rec) % rs == 0 and len(rec) >= rs:
                ts_test = struct.unpack_from('<q', rec, 0)[0]
                if 0 < ts_test < 2_000_000_000:
                    rec_size = rs
                    break
        if rec_size is None:
            return None, None

        n = len(rec) // rec_size
        candles = {}          # ts → {o,h,l,c}
        ts_list = []          # 정렬된 ts 목록 (이진 탐색용)

        for idx in range(n):
            off = idx * rec_size
            ts = struct.unpack_from('<q', rec, off)[0]
            o, h, l, c = struct.unpack_from('<dddd', rec, off + 8)
            candles[ts] = {'o': o, 'h': h, 'l': l, 'c': c}
            ts_list.append(ts)

        ts_list.sort()
        return candles, ts_list

    except Exception as e:
        print(f"[HST] load error {fname}: {e}")
        return None, None


def _find_candle(candles, ts_list, dt, tf_minutes=5):
    """datetime에 가장 가까운 캔들 반환 (±tf_minutes×3 허용)."""
    if not ts_list:
        return None
    target = int(dt.timestamp())
    # 이진 탐색
    lo, hi = 0, len(ts_list) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if ts_list[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    # 전후 비교
    best_idx = lo
    if lo > 0 and abs(ts_list[lo - 1] - target) < abs(ts_list[lo] - target):
        best_idx = lo - 1
    if abs(ts_list[best_idx] - target) <= tf_minutes * 3 * 60:
        return candles[ts_list[best_idx]]
    return None


def _get_candles_range(candles, ts_list, start_dt, end_dt):
    """start_dt ~ end_dt 범위의 캔들 리스트 반환."""
    if not ts_list:
        return []
    t0 = int(start_dt.timestamp())
    t1 = int(end_dt.timestamp())
    return [candles[ts] for ts in ts_list if t0 <= ts <= t1]


# ─────────────────────────────────────────────────────────────────────────────
# 3. 시장 추세 판정
# ─────────────────────────────────────────────────────────────────────────────

def _market_trend_at(candles, ts_list, dt, lookback=20, tf_minutes=5):
    """
    dt 시점의 시장 방향 반환: 'up' | 'down' | 'ranging'
    lookback개 캔들의 단순 MA 기울기로 판단.
    """
    target = int(dt.timestamp())
    # lookback 개 앞 캔들 수집
    lo, hi = 0, len(ts_list) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if ts_list[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    end_idx = lo - 1
    if end_idx < lookback:
        return 'ranging'

    closes = [candles[ts_list[i]]['c'] for i in range(end_idx - lookback, end_idx)]
    if not closes:
        return 'ranging'

    ma_first = sum(closes[:5]) / 5
    ma_last  = sum(closes[-5:]) / 5
    slope = (ma_last - ma_first) / ma_first * 100  # % 변화

    if slope > 0.05:
        return 'up'
    elif slope < -0.05:
        return 'down'
    return 'ranging'


def _max_favorable_excursion(trade, candles, ts_list):
    """
    거래 기간 동안 진입가 대비 최대 유리 이동폭 (MFE) 계산.
    buy: 진입가 이후 최고가 - 진입가
    sell: 진입가 - 진입가 이후 최저가
    """
    range_candles = _get_candles_range(
        candles, ts_list,
        trade['open_time'],
        trade['close_time'] + timedelta(minutes=5)
    )
    if not range_candles:
        return 0.0

    if trade['direction'] == 'buy':
        peak = max(c['h'] for c in range_candles)
        return max(0.0, peak - trade['entry'])
    else:
        trough = min(c['l'] for c in range_candles)
        return max(0.0, trade['entry'] - trough)


# ─────────────────────────────────────────────────────────────────────────────
# 4. 라운드 전체 분석
# ─────────────────────────────────────────────────────────────────────────────

def analyze_round(htm_paths, round_num, ea_name=''):
    """
    하나 이상의 HTM 파일 목록을 분석해 라운드 전체 시장 분석 결과 반환.

    htm_paths: list of HTM 경로 (한 라운드의 여러 시나리오)
    """
    # HST 로드
    candles, ts_list = load_hst('XAUUSD', 5)
    hst_ok = candles is not None

    # 전체 거래 수집
    all_trades = []
    for p in htm_paths:
        all_trades.extend(parse_trades_from_htm(p))

    if not all_trades:
        return {
            'round': round_num, 'ea_name': ea_name,
            'total_trades': 0,
            'market_context': 'HTM 거래 데이터 없음',
            'recommendation': '',
        }

    total = len(all_trades)
    tp_hit  = sum(1 for t in all_trades if t['close_type'] == 't/p')
    sl_hit  = sum(1 for t in all_trades if t['close_type'] == 's/l')
    other   = total - tp_hit - sl_hit

    tp_pct = tp_hit / total * 100
    sl_pct = sl_hit / total * 100

    # SL/TP 거리 통계
    tp_dists = [abs(t['tp'] - t['entry']) for t in all_trades]
    sl_dists = [abs(t['sl'] - t['entry']) for t in all_trades]
    avg_tp = sum(tp_dists) / len(tp_dists) if tp_dists else 0
    avg_sl = sum(sl_dists) / len(sl_dists) if sl_dists else 0

    # MFE (실제 최대 유리이동) 분석
    mfe_list = []
    trend_aligned = 0
    tp_reachable  = 0

    failure_patterns = {
        'early_reversal':  0,   # SL 도달: 진입 직후 반전
        'trend_against':   0,   # 추세 역방향 진입
        'tp_too_far':      0,   # MFE < TP거리 (TP가 너무 멀었음)
        'ranging_market':  0,   # ranging 시장에서 손실
    }

    for t in all_trades:
        tp_dist = abs(t['tp'] - t['entry'])
        sl_dist = abs(t['sl'] - t['entry'])

        # MFE 계산 (HST 데이터 있을 때만)
        mfe = 0.0
        if hst_ok:
            mfe = _max_favorable_excursion(t, candles, ts_list)
        mfe_list.append(mfe)

        if mfe >= tp_dist:
            tp_reachable += 1

        # 시장 추세 방향
        if hst_ok:
            trend = _market_trend_at(candles, ts_list, t['open_time'])
        else:
            trend = 'ranging'

        trade_aligned = (
            (t['direction'] == 'buy'  and trend == 'up') or
            (t['direction'] == 'sell' and trend == 'down')
        )
        if trade_aligned:
            trend_aligned += 1

        # 실패 패턴 분류
        if t['close_type'] == 's/l':
            hold_time = (t['close_time'] - t['open_time']).total_seconds() / 60
            if hold_time < 30:
                failure_patterns['early_reversal'] += 1
            if not trade_aligned:
                failure_patterns['trend_against'] += 1
            if mfe < tp_dist * 0.5:
                failure_patterns['tp_too_far'] += 1
            if trend == 'ranging':
                failure_patterns['ranging_market'] += 1

    avg_mfe = sum(mfe_list) / len(mfe_list) if mfe_list else 0
    trend_aligned_pct  = trend_aligned / total * 100
    tp_reachable_pct   = tp_reachable  / total * 100

    # ── 시장 컨텍스트 텍스트 생성 ────────────────────────────────────────
    lines = []
    lines.append(f"■ R{round_num} 시장분석 — {ea_name}")
    lines.append(f"  총 거래: {total}개")
    lines.append(f"  TP 도달: {tp_hit}개 ({tp_pct:.1f}%)  "
                 f"SL 손절: {sl_hit}개 ({sl_pct:.1f}%)")
    lines.append(f"  평균 TP거리: {avg_tp:.2f}pt  평균 SL거리: {avg_sl:.2f}pt  "
                 f"RR비율: {avg_tp/avg_sl:.1f}x")
    lines.append("")
    if hst_ok:
        lines.append(f"  [시장추세] 추세 방향 일치: {trend_aligned_pct:.1f}%")
        lines.append(f"  [MFE] 평균 최대유리이동: {avg_mfe:.2f}pt  "
                     f"(TP거리의 {avg_mfe/avg_tp*100:.0f}%)" if avg_tp else "")
        lines.append(f"  [TP도달가능] MFE≥TP인 거래: {tp_reachable_pct:.1f}%  "
                     f"(가격은 갔으나 TP 못 잡은 비율)")
        lines.append("")
        lines.append("  [실패 원인 분류]")
        if sl_hit > 0:
            er_pct = failure_patterns['early_reversal'] / sl_hit * 100
            ta_pct = failure_patterns['trend_against']  / sl_hit * 100
            tf_pct = failure_patterns['tp_too_far']     / sl_hit * 100
            rm_pct = failure_patterns['ranging_market'] / sl_hit * 100
            lines.append(f"    진입 직후 반전 (30분내 손절): {er_pct:.0f}%")
            lines.append(f"    추세 역방향 진입:              {ta_pct:.0f}%")
            lines.append(f"    TP 너무 멀었음 (MFE<TP/2):    {tf_pct:.0f}%")
            lines.append(f"    Ranging 시장 손실:             {rm_pct:.0f}%")
    else:
        lines.append("  [주의] XAUUSD5.hst 파일 없어 추세분석 불가 (집계만)")

    # ── 파라미터 변경 제안 ────────────────────────────────────────────────
    rec_lines = []
    if hst_ok:
        if failure_patterns['tp_too_far'] / max(sl_hit, 1) > 0.5:
            rec_lines.append(f"→ TP 단축 권장: 현재 {avg_tp:.1f}pt → "
                             f"목표 {avg_mfe*0.8:.1f}pt (MFE 80%)")
        if failure_patterns['trend_against'] / max(sl_hit, 1) > 0.4:
            rec_lines.append("→ 추세필터 강화 권장 (ADX 임계값 상향 또는 MA 기울기 조건 추가)")
        if failure_patterns['early_reversal'] / max(sl_hit, 1) > 0.5:
            rec_lines.append("→ SL 타이트 의심: 진입 직후 손절 많음 → SL 범위 재검토")
        if tp_pct > 60:
            rec_lines.append(f"→ TP 설정 양호 ({tp_pct:.0f}% 도달) — 현 TP 유지 또는 소폭 확대 가능")
        if not rec_lines:
            rec_lines.append("→ 현 파라미터 구조 양호. 다음 라운드 정밀 탐색 진행.")

    recommendation = '\n'.join(rec_lines)

    return {
        'round':              round_num,
        'ea_name':            ea_name,
        'total_trades':       total,
        'tp_hit':             tp_hit,
        'sl_hit':             sl_hit,
        'tp_hit_pct':         round(tp_pct, 1),
        'sl_hit_pct':         round(sl_pct, 1),
        'trend_aligned_pct':  round(trend_aligned_pct, 1) if hst_ok else None,
        'avg_tp_dist':        round(avg_tp, 2),
        'avg_sl_dist':        round(avg_sl, 2),
        'avg_mfe':            round(avg_mfe, 2) if hst_ok else None,
        'tp_reachable_pct':   round(tp_reachable_pct, 1) if hst_ok else None,
        'failure_patterns':   failure_patterns,
        'market_context':     '\n'.join(lines),
        'recommendation':     recommendation,
        'hst_available':      hst_ok,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. 라운드 분석 메모 저장/로드
# ─────────────────────────────────────────────────────────────────────────────

def save_round_notes(notes_path, round_num, market_analysis, user_notes):
    """
    round_analysis_notes.json에 라운드별 메모 저장.
    market_analysis: analyze_round() 반환값
    user_notes: 사용자가 입력한 텍스트
    """
    import json
    try:
        with open(notes_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = {}

    data[str(round_num)] = {
        'saved_at':       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'market_context': market_analysis.get('market_context', ''),
        'recommendation': market_analysis.get('recommendation', ''),
        'user_notes':     user_notes,
        'stats': {
            'total_trades':      market_analysis.get('total_trades', 0),
            'tp_hit_pct':        market_analysis.get('tp_hit_pct', 0),
            'sl_hit_pct':        market_analysis.get('sl_hit_pct', 0),
            'trend_aligned_pct': market_analysis.get('trend_aligned_pct'),
            'avg_tp_dist':       market_analysis.get('avg_tp_dist', 0),
            'avg_sl_dist':       market_analysis.get('avg_sl_dist', 0),
            'avg_mfe':           market_analysis.get('avg_mfe'),
            'tp_reachable_pct':  market_analysis.get('tp_reachable_pct'),
        },
    }

    with open(notes_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_round_notes(notes_path, round_num=None):
    """notes_path에서 round_num (None이면 전체) 로드."""
    import json
    try:
        with open(notes_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return {}
    if round_num is not None:
        return data.get(str(round_num), {})
    return data
