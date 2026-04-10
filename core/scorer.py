"""
core/scorer.py — Stage 3: 다목적 스코어 엔진
==============================================
단순 수익/DD가 아닌 6개 목적함수로 "진짜 좋은 파라미터" 선별.

점수 구조 (합계 100점):
  30pt  수익성   (순이익 규모)
  20pt  안전성   (낙폭 낮을수록)
  20pt  안정성   (월별 수익 일관성)
  15pt  효율성   (수익팩터 PF)
  10pt  시장적합성 (추세/ranging 적합도 — HST 분석 연동)
   5pt  견고성   (다른 기간도 수익나는가)
"""


# ─────────────────────────────────────────────────────────────────────────────
# 1. 기본 스코어 (HTM 요약 통계 기반)
# ─────────────────────────────────────────────────────────────────────────────

def score_basic(result: dict,
                profit_target: float = 50_000,
                max_dd_limit: float  = 20.0) -> float:
    """
    HTM 요약 통계만으로 계산하는 빠른 스코어 (0~100).

    result 필수 키:
      profit, drawdown_pct, profit_factor, trades, win_rate(optional)
    """
    profit     = result.get('profit', 0)
    dd         = result.get('drawdown_pct', 100)
    pf         = result.get('profit_factor', 0)
    trades     = result.get('trades', 0)

    # 기본 필터
    if trades < 10:
        return 0.0
    if dd >= max_dd_limit:
        return 0.0

    # ── 수익성 (30pt) ─────────────────────────────────────────────
    profit_score = min(profit / profit_target * 30, 30)
    if profit <= 0:
        profit_score = 0.0

    # ── 안전성 (20pt): 낙폭 ──────────────────────────────────────
    dd_score = max(0, (max_dd_limit - dd) / max_dd_limit * 20)

    # ── 효율성 (15pt): 수익팩터 ──────────────────────────────────
    # PF 1.0 = 0pt, PF 3.0 = 15pt
    pf_score = min(max(pf - 1.0, 0) / 2.0 * 15, 15)

    # ── 거래 충분성 (10pt): 거래수 ──────────────────────────────
    trade_score = min(trades / 200 * 10, 10)

    # ── 안정성 (25pt): 수익 / 낙폭 균형 (Calmar-like) ────────────
    calmar = profit / max(dd, 0.1)
    stability_score = min(calmar / 5000 * 25, 25)

    total = profit_score + dd_score + pf_score + trade_score + stability_score
    return round(min(total, 100), 2)


# ─────────────────────────────────────────────────────────────────────────────
# 2. 확장 스코어 (시장분석 데이터 포함)
# ─────────────────────────────────────────────────────────────────────────────

def score_full(result: dict,
               market_analysis: dict = None,
               robustness: dict = None,
               profit_target: float = 50_000,
               max_dd_limit: float  = 25.0) -> dict:
    """
    6개 목적함수 전체 스코어.

    DD 6단계 티어 (안전성 20pt):
      ≤  5%: 20pt  (S등급 — 최고)
      ≤  8%: 18pt  (S등급 — 프롭펌 통과급)
      ≤ 10%: 15pt  (A등급 — 우수)
      ≤ 15%: 10pt  (B등급 — 양호)
      ≤ 20%:  5pt  (C등급 — 보통)
      ≤ 25%:  2pt  (D등급 — 주의)
       > 25%:  0pt  Hard cutoff — score_full 전체 0 반환

    market_analysis: core.market_analyzer.analyze_round() 반환값
    robustness:      다른 기간 백테스트 결과 {'profit': x, 'drawdown_pct': y}
    반환: {'total': float, 'breakdown': dict}
    """
    profit  = result.get('profit', 0)
    dd      = result.get('drawdown_pct', 100)
    pf      = result.get('profit_factor', 0)
    trades  = result.get('trades', 0)

    breakdown = {}

    # 기본 필터: DD > 25% 또는 거래 없음/손실
    if trades < 10 or dd > max_dd_limit or profit <= 0:
        return {'total': 0.0, 'breakdown': {k: 0.0 for k in
                ['profitability', 'safety', 'stability',
                 'efficiency', 'market_fit', 'robustness']}}

    # ── 1. 수익성 (30pt) ─────────────────────────────────────────
    breakdown['profitability'] = round(min(profit / profit_target * 30, 30), 2)

    # ── 2. 안전성 (20pt): DD 6단계 티어 ─────────────────────────
    if   dd <=  5.0: safety = 20.0
    elif dd <=  8.0: safety = 18.0
    elif dd <= 10.0: safety = 15.0
    elif dd <= 15.0: safety = 10.0
    elif dd <= 20.0: safety =  5.0
    else:            safety =  2.0   # 20 < dd <= 25
    breakdown['safety'] = safety

    # ── 3. 안정성 (20pt): Calmar 비율 기반 ──────────────────────
    calmar = profit / max(dd, 0.1)
    breakdown['stability'] = round(min(calmar / 5000 * 20, 20), 2)

    # ── 4. 효율성 (15pt): PF ────────────────────────────────────
    breakdown['efficiency'] = round(min(max(pf - 1.0, 0) / 2.0 * 15, 15), 2)

    # ── 5. 시장적합성 (10pt): HST 분석 연동 ─────────────────────
    if market_analysis and market_analysis.get('hst_available'):
        tp_pct     = market_analysis.get('tp_hit_pct', 0)
        trend_pct  = market_analysis.get('trend_aligned_pct', 50)
        reach_pct  = market_analysis.get('tp_reachable_pct', 0)

        # TP 도달률이 높을수록, 추세 방향 일치율 높을수록 좋음
        market_score = (
            tp_pct    / 100 * 4 +   # TP 도달률 (4pt)
            trend_pct / 100 * 4 +   # 추세 일치율 (4pt)
            reach_pct / 100 * 2     # TP 도달 가능성 (2pt)
        )
        breakdown['market_fit'] = round(market_score, 2)
    else:
        # HST 없으면 거래수 비례로 추정 (최대 5pt)
        breakdown['market_fit'] = round(min(trades / 500 * 5, 5), 2)

    # ── 6. 견고성 (5pt): 다른 기간 수익 여부 ────────────────────
    if robustness:
        rob_profit = robustness.get('profit', 0)
        rob_dd     = robustness.get('drawdown_pct', 100)
        if rob_profit > 0 and rob_dd < max_dd_limit:
            # 메인과 보조 기간 모두 수익: 만점
            breakdown['robustness'] = 5.0
        elif rob_profit > 0:
            breakdown['robustness'] = 2.5
        else:
            breakdown['robustness'] = 0.0
    else:
        breakdown['robustness'] = 0.0  # 데이터 없으면 0

    total = sum(breakdown.values())
    return {
        'total':     round(min(total, 100), 2),
        'breakdown': breakdown,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. 파레토 프론트 (다목적 최적화)
# ─────────────────────────────────────────────────────────────────────────────

def pareto_front(results: list, objectives: list = None) -> list:
    """
    다목적 최적화의 파레토 프론트 계산.
    어떤 결과도 "모든 목적에서 동시에 더 좋은" 다른 결과가 없는 것들.

    objectives: 최대화할 키 목록 (기본: profit, -drawdown_pct, profit_factor)
    반환: 파레토 프론트에 있는 결과들의 인덱스 목록
    """
    if objectives is None:
        objectives = ['profit', 'neg_dd', 'profit_factor']

    # neg_dd 계산
    for r in results:
        r['neg_dd'] = -r.get('drawdown_pct', 100)

    front = []
    for i, ri in enumerate(results):
        dominated = False
        for j, rj in enumerate(results):
            if i == j:
                continue
            # rj가 모든 목적에서 ri 이상이고 하나는 더 좋으면 ri는 지배됨
            if all(rj.get(obj, 0) >= ri.get(obj, 0) for obj in objectives) and \
               any(rj.get(obj, 0) >  ri.get(obj, 0) for obj in objectives):
                dominated = True
                break
        if not dominated:
            front.append(i)

    return front


# ─────────────────────────────────────────────────────────────────────────────
# 4. 점수 해석 텍스트
# ─────────────────────────────────────────────────────────────────────────────

def interpret_score(score_result: dict) -> str:
    """점수 분해를 사람이 읽기 쉬운 텍스트로 변환."""
    total = score_result.get('total', 0)
    bd    = score_result.get('breakdown', {})

    grade = (
        'S (최우수)' if total >= 85 else
        'A (우수)'   if total >= 70 else
        'B (양호)'   if total >= 55 else
        'C (보통)'   if total >= 40 else
        'D (미달)'
    )

    lines = [f"종합점수: {total:.1f}/100  등급: {grade}"]
    labels = {
        'profitability': f"수익성   ({bd.get('profitability',0):.1f}/30)",
        'safety':        f"안전성   ({bd.get('safety',0):.1f}/20)",
        'stability':     f"안정성   ({bd.get('stability',0):.1f}/20)",
        'efficiency':    f"효율성   ({bd.get('efficiency',0):.1f}/15)",
        'market_fit':    f"시장적합 ({bd.get('market_fit',0):.1f}/10)",
        'robustness':    f"견고성   ({bd.get('robustness',0):.1f}/5)",
    }
    for key, label in labels.items():
        bar_len = int(bd.get(key, 0) / 2)
        lines.append(f"  {label}  {'|' * bar_len}")

    return '\n'.join(lines)


if __name__ == '__main__':
    # 테스트
    sample_result = {
        'profit': 80000, 'drawdown_pct': 5.2,
        'profit_factor': 2.87, 'trades': 3985
    }
    basic = score_basic(sample_result)
    print(f"기본 스코어: {basic}")

    full = score_full(sample_result)
    print(interpret_score(full))
