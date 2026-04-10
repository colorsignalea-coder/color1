"""
core/scoring.py — EA Auto Master v6.0
======================================
100점 스코어링 + S/A/B/C/D 등급 + 성과 기반 파라미터 자동 조정.
"""


def calc_score_grade(data):
    """100점 스코어 + S/A/B/C/D 등급 계산.
    Returns (score, grade, recommendation)
    """
    pf = data.get("profit_factor", 0)
    wr = data.get("win_rate", 0)
    mdd = data.get("max_drawdown_pct", 100)
    tot = data.get("total_trades", 0)
    rf = data.get("recovery_factor", 0)
    rr = data.get("rr_ratio", 0)

    sc = 0
    # PF (25)
    if pf >= 2.0:     sc += 25
    elif pf >= 1.7:   sc += 20
    elif pf >= 1.5:   sc += 15
    elif pf >= 1.3:   sc += 10
    elif pf >= 1.1:   sc += 5
    # WinRate (20)
    if wr >= 65:      sc += 20
    elif wr >= 55:    sc += 15
    elif wr >= 45:    sc += 10
    elif wr >= 35:    sc += 5
    # MDD (20)
    if mdd <= 5:      sc += 20
    elif mdd <= 10:   sc += 15
    elif mdd <= 15:   sc += 10
    elif mdd <= 25:   sc += 5
    # Recovery Factor (15)
    if rf >= 5:       sc += 15
    elif rf >= 3:     sc += 10
    elif rf >= 1.5:   sc += 5
    # Trade Count (10)
    if tot >= 500:    sc += 10
    elif tot >= 200:  sc += 7
    elif tot >= 100:  sc += 4
    elif tot >= 50:   sc += 2
    # R/R Ratio (10)
    if rr >= 2.0:     sc += 10
    elif rr >= 1.5:   sc += 7
    elif rr >= 1.0:   sc += 4

    if sc >= 85:     grade = "S"
    elif sc >= 70:   grade = "A"
    elif sc >= 55:   grade = "B"
    elif sc >= 40:   grade = "C"
    else:            grade = "D"

    rec_map = {
        "S": "LIVE_READY" if mdd <= 20 else "OPTIMIZE_MDD",
        "A": "LIVE_CANDIDATE",
        "B": "OPTIMIZE_PF" if pf < 1.5 else ("OPTIMIZE_WR" if wr < 50 else "CONTINUE_TEST"),
        "C": "NEED_IMPROVEMENT",
        "D": "NOT_RECOMMENDED",
    }
    return sc, grade, rec_map.get(grade, "CONTINUE_TEST")


def calc_multi_score(data):
    """6개 지표별 분리 점수 반환.
    Returns dict: {"pf": int, "wr": int, "mdd": int, "rf": int, "trades": int, "rr": int, "total": int}
    """
    pf = data.get("profit_factor", 0)
    wr = data.get("win_rate", 0)
    mdd = data.get("max_drawdown_pct", 100)
    tot = data.get("total_trades", 0)
    rf = data.get("recovery_factor", 0)
    rr = data.get("rr_ratio", 0)

    scores = {}
    # PF (25)
    if pf >= 2.0:     scores["pf"] = 25
    elif pf >= 1.7:   scores["pf"] = 20
    elif pf >= 1.5:   scores["pf"] = 15
    elif pf >= 1.3:   scores["pf"] = 10
    elif pf >= 1.1:   scores["pf"] = 5
    else:             scores["pf"] = 0
    # WinRate (20)
    if wr >= 65:      scores["wr"] = 20
    elif wr >= 55:    scores["wr"] = 15
    elif wr >= 45:    scores["wr"] = 10
    elif wr >= 35:    scores["wr"] = 5
    else:             scores["wr"] = 0
    # MDD (20)
    if mdd <= 5:      scores["mdd"] = 20
    elif mdd <= 10:   scores["mdd"] = 15
    elif mdd <= 15:   scores["mdd"] = 10
    elif mdd <= 25:   scores["mdd"] = 5
    else:             scores["mdd"] = 0
    # Recovery Factor (15)
    if rf >= 5:       scores["rf"] = 15
    elif rf >= 3:     scores["rf"] = 10
    elif rf >= 1.5:   scores["rf"] = 5
    else:             scores["rf"] = 0
    # Trade Count (10)
    if tot >= 500:    scores["trades"] = 10
    elif tot >= 200:  scores["trades"] = 7
    elif tot >= 100:  scores["trades"] = 4
    elif tot >= 50:   scores["trades"] = 2
    else:             scores["trades"] = 0
    # R/R Ratio (10)
    if rr >= 2.0:     scores["rr"] = 10
    elif rr >= 1.5:   scores["rr"] = 7
    elif rr >= 1.0:   scores["rr"] = 4
    else:             scores["rr"] = 0

    scores["total"] = sum(scores.values())

    # 가장 약한 지표 식별 (최대 점수 대비 비율)
    max_map = {"pf": 25, "wr": 20, "mdd": 20, "rf": 15, "trades": 10, "rr": 10}
    weakest = min(max_map, key=lambda k: scores[k] / max_map[k])
    scores["weakest"] = weakest
    scores["weakest_ratio"] = round(scores[weakest] / max_map[weakest], 2)

    return scores


def calc_adjusted_params(data, params):
    """[LEGACY] 기존 맹목 비율 조정 — v6.0에서는 ParamAnalyzer.calc_adjusted_params_v2() 사용 권장.
    PF<1.2 -> TP +15%, MDD>25% -> SL -15%, WinRate<45% -> Period -10%
    Returns dict of adjusted params.
    """
    EXCLUDE = {"magicnumber", "magic", "slippage", "lotsize", "lot", "maxlot",
               "fixedlot", "comment", "maxpositions", "maxorders"}
    TP_KEYS = {"tp", "takeprofit", "inptrendtp", "inptp", "tpamount"}
    SL_KEYS = {"sl", "stoploss", "inptrendsl", "inpsl", "slfixedamount"}
    PER_KEYS = {"period", "fast", "slow", "inpbbperiod", "inpsqueezeminbars",
                "inpatrsmoooth", "inpatrperiod"}

    pf = data.get("profit_factor", 1.0)
    mdd = data.get("max_drawdown_pct", 0)
    wr = data.get("win_rate", 50)

    adjusted = {}
    for k, v in params.items():
        kl = k.lower()
        if kl in EXCLUDE:
            adjusted[k] = v
            continue
        try:
            fv = float(v)
        except (ValueError, TypeError):
            adjusted[k] = v
            continue

        mult = 1.0
        if pf < 1.2 and any(tp in kl for tp in TP_KEYS):
            mult = 1.15
        elif mdd > 25 and any(sl in kl for sl in SL_KEYS):
            mult = 0.85
        elif wr < 45 and any(pr in kl for pr in PER_KEYS):
            mult = 0.90
        else:
            mult = 1.05

        nv = round(fv * mult, 5)
        adjusted[k] = int(nv) if isinstance(v, int) or (isinstance(v, str) and "." not in str(v)) else nv

    return adjusted
