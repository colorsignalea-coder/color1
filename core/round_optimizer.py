"""
core/round_optimizer.py — EA Auto Master v6.0
===============================================
AI형 라운드 최적화 엔진.

기존 calc_adjusted_params()의 맹목적 +5% 조정을 완전 교체.
실제 HTM 데이터 기반 상관분석 + 상위/하위 비교 + 방향검증 + 롤백.

3개 클래스:
  ParamAnalyzer  — 파라미터<->성적 상관분석, 최적구간 추출
  RoundDirector  — 상위20/하위10 비교, 방향결정, 롤백
  StrategyMixer  — EA코드 분석, 전략 모듈 믹스
"""
import math
import os
import re
import json
import datetime
from collections import defaultdict

from core.scoring import calc_score_grade


# ================================================================
# ParamAnalyzer — 데이터 기반 파라미터 분석
# ================================================================

class ParamAnalyzer:
    """파라미터 변화 vs 성적 변화 상관분석.
    비유: 다트를 던진 모든 위치와 점수를 기록하고,
    어느 방향이 높은 점수 영역인지 지도를 그리는 것.
    """

    # 변동 제외 파라미터
    EXCLUDE = frozenset({
        "magicnumber", "magic", "slippage", "lotsize", "lot", "maxlot",
        "fixedlot", "comment", "maxpositions", "maxorders",
    })

    def __init__(self):
        self._history = []  # [(params_dict, htm_data_with_score), ...]

    def add_results(self, results):
        """라운드 결과 추가. results: [{"params": {k:v}, "htm": {htm_data}}]"""
        for r in results:
            params = r.get("params", {})
            htm = r.get("htm", {})
            sc, grade, rec = calc_score_grade(htm)
            entry = {**htm, "score": sc, "grade": grade, "recommendation": rec}
            self._history.append((params, entry))

    def get_history(self):
        return list(self._history)

    @staticmethod
    def _pearson(xs, ys):
        """피어슨 상관계수. 데이터 부족 시 0.0 반환."""
        n = len(xs)
        if n < 3:
            return 0.0
        mx = sum(xs) / n
        my = sum(ys) / n
        sx = sum((x - mx) ** 2 for x in xs)
        sy = sum((y - my) ** 2 for y in ys)
        if sx == 0 or sy == 0:
            return 0.0
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        return sxy / math.sqrt(sx * sy)

    def rank_param_impact(self, results=None):
        """각 파라미터의 변화량 vs 스코어 상관계수 계산.
        Returns: {param_name: correlation} 내림차순 정렬.
        """
        data = results or self._history
        if len(data) < 3:
            return {}

        scores = [entry.get("score", 0) for _, entry in data]

        # 파라미터별 값 수집
        param_vals = defaultdict(list)
        for params, _ in data:
            for k, v in params.items():
                if k.lower() in self.EXCLUDE:
                    continue
                try:
                    param_vals[k].append(float(v))
                except (ValueError, TypeError):
                    pass

        correlations = {}
        for k, vals in param_vals.items():
            if len(vals) != len(scores):
                continue
            # 값이 모두 동일하면 스킵
            if len(set(vals)) < 2:
                continue
            corr = self._pearson(vals, scores)
            correlations[k] = round(corr, 4)

        return dict(sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True))

    def find_sweet_spots(self, results=None, top_ratio=0.3):
        """상위 결과들의 파라미터 분포에서 최적 구간 추출.
        Returns: {param: {"center": float, "low": float, "high": float, "direction": str}}
        """
        data = results or self._history
        if len(data) < 3:
            return {}

        # 스코어 순 정렬
        sorted_data = sorted(data, key=lambda x: x[1].get("score", 0), reverse=True)
        top_n = max(2, int(len(sorted_data) * top_ratio))
        top_data = sorted_data[:top_n]
        bottom_data = sorted_data[-max(2, int(len(sorted_data) * 0.2)):]

        spots = {}
        for k in top_data[0][0].keys():
            if k.lower() in self.EXCLUDE:
                continue
            top_vals = []
            bottom_vals = []
            for params, _ in top_data:
                try:
                    top_vals.append(float(params.get(k, 0)))
                except (ValueError, TypeError):
                    pass
            for params, _ in bottom_data:
                try:
                    bottom_vals.append(float(params.get(k, 0)))
                except (ValueError, TypeError):
                    pass

            if not top_vals or len(set(top_vals)) < 1:
                continue

            top_avg = sum(top_vals) / len(top_vals)
            top_low = min(top_vals)
            top_high = max(top_vals)
            bot_avg = sum(bottom_vals) / len(bottom_vals) if bottom_vals else top_avg

            # 방향 결정: 상위 평균이 하위 평균보다 높으면 "increase"
            if abs(top_avg - bot_avg) < 1e-8:
                direction = "neutral"
            elif top_avg > bot_avg:
                direction = "increase"
            else:
                direction = "decrease"

            spots[k] = {
                "center": round(top_avg, 5),
                "low": round(top_low, 5),
                "high": round(top_high, 5),
                "direction": direction,
                "top_avg": round(top_avg, 5),
                "bottom_avg": round(bot_avg, 5),
            }
        return spots

    def calc_adjusted_params_v2(self, current_params, round_results):
        """v2 파라미터 조정 — 기존 맹목 +5%를 완전 교체.

        로직:
        1. 상관분석으로 영향력 높은 파라미터 식별
        2. sweet_spot에서 상위 구간 방향으로 조정
        3. 상관 낮은 파라미터는 고정 (불필요한 noise 제거)
        """
        correlations = self.rank_param_impact(round_results)
        sweet_spots = self.find_sweet_spots(round_results)

        adjusted = {}
        adjustments_log = []

        for k, v in current_params.items():
            kl = k.lower()
            if kl in self.EXCLUDE:
                adjusted[k] = v
                continue
            try:
                fv = float(v)
            except (ValueError, TypeError):
                adjusted[k] = v
                continue

            corr = correlations.get(k, 0.0)
            spot = sweet_spots.get(k)

            # 상관계수 < 0.15: 무의미 → 고정
            if abs(corr) < 0.15:
                adjusted[k] = v
                adjustments_log.append(f"  {k}: 고정 (상관={corr:.2f}, 무의미)")
                continue

            # sweet_spot이 있으면 상위 평균 방향으로 이동
            if spot:
                target = spot["center"]
                # 현재값에서 target까지 거리의 30%만 이동 (급격한 변화 방지)
                step_ratio = min(0.3, abs(corr) * 0.4)
                new_val = fv + (target - fv) * step_ratio

                # 정수형 파라미터 유지
                is_int = isinstance(v, int) or (isinstance(v, str) and "." not in str(v))
                if is_int:
                    new_val = int(round(new_val))
                else:
                    new_val = round(new_val, 5)

                adjusted[k] = new_val
                adjustments_log.append(
                    f"  {k}: {v} -> {new_val} (상관={corr:.2f}, "
                    f"방향={spot['direction']}, target={target})")
            else:
                # sweet_spot 없지만 상관 있음 → 상관 방향으로 소폭 조정
                mult = 1.0 + (0.05 * (1 if corr > 0 else -1))
                new_val = round(fv * mult, 5)
                is_int = isinstance(v, int) or (isinstance(v, str) and "." not in str(v))
                adjusted[k] = int(round(new_val)) if is_int else new_val
                adjustments_log.append(
                    f"  {k}: {v} -> {adjusted[k]} (상관={corr:.2f}, 소폭 조정)")

        return adjusted, adjustments_log


# ================================================================
# RoundDirector — 상위/하위 비교 + 방향 검증 + 롤백
# ================================================================

class RoundDirector:
    """매 라운드 결과 분석, 방향 판단, 롤백 결정.
    비유: 탐험대 대장이 매 교차로에서 "이 방향이 맞나?"를 확인하고,
    길을 잘못 들었으면 마지막 좋았던 지점으로 되돌아가는 것.
    """

    def __init__(self):
        self._round_history = []  # [{"round": n, "results": [...], "best": {...}, "analysis": {...}}]
        self._best_ever = None    # 역대 최고 라운드 정보
        self._decline_streak = 0  # 연속 악화 카운터
        self._analyzer = ParamAnalyzer()

    @property
    def analyzer(self):
        return self._analyzer

    def analyze_round(self, round_num, results):
        """라운드 결과 전체 분석.
        results: [{"params": {}, "htm": {htm_data}}]
        Returns: analysis dict
        """
        if not results:
            return {"error": "결과 없음"}

        # 스코어 계산
        scored = []
        for r in results:
            htm = r.get("htm", {})
            sc, grade, rec = calc_score_grade(htm)
            scored.append({
                **r,
                "score": sc, "grade": grade, "recommendation": rec,
                "profit": htm.get("net_profit", 0),
                "pf": htm.get("profit_factor", 0),
                "win_rate": htm.get("win_rate", 0),
                "mdd": htm.get("max_drawdown_pct", 0),
            })

        # 스코어 순 정렬
        scored.sort(key=lambda x: x["score"], reverse=True)

        # 상위/하위 분류
        n = len(scored)
        top_n = max(1, int(n * 0.3))  # 상위 30%
        bottom_n = max(1, int(n * 0.2))  # 하위 20%
        top_group = scored[:top_n]
        bottom_group = scored[-bottom_n:]
        best = scored[0]

        # 상위/하위 파라미터 비교
        comparison = self._compare_top_bottom(top_group, bottom_group)

        # 전체 통계
        all_scores = [s["score"] for s in scored]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        bottom_avg_score = sum(s["score"] for s in bottom_group) / len(bottom_group)

        analysis = {
            "round": round_num,
            "total_sets": n,
            "best": best,
            "best_score": best["score"],
            "avg_score": round(avg_score, 1),
            "bottom_avg_score": round(bottom_avg_score, 1),
            "top_group": top_group,
            "bottom_group": bottom_group,
            "comparison": comparison,
            "scored_results": scored,
        }

        # 히스토리에 추가
        self._analyzer.add_results(results)
        self._round_history.append(analysis)

        return analysis

    def _compare_top_bottom(self, top_group, bottom_group):
        """상위 vs 하위 파라미터 차이 추출.
        Returns: {param: {"top_avg": float, "bottom_avg": float, "diff": float, "direction": str}}
        """
        comparison = {}
        if not top_group or not bottom_group:
            return comparison

        # 파라미터 키 수집
        all_keys = set()
        for item in top_group + bottom_group:
            all_keys.update(item.get("params", {}).keys())

        for k in all_keys:
            if k.lower() in ParamAnalyzer.EXCLUDE:
                continue
            top_vals = []
            bot_vals = []
            for item in top_group:
                try:
                    top_vals.append(float(item.get("params", {}).get(k, 0)))
                except (ValueError, TypeError):
                    pass
            for item in bottom_group:
                try:
                    bot_vals.append(float(item.get("params", {}).get(k, 0)))
                except (ValueError, TypeError):
                    pass

            if not top_vals or not bot_vals:
                continue

            top_avg = sum(top_vals) / len(top_vals)
            bot_avg = sum(bot_vals) / len(bot_vals)
            diff = top_avg - bot_avg

            if abs(diff) < 1e-8:
                direction = "same"
            elif diff > 0:
                direction = "top_higher"
            else:
                direction = "top_lower"

            comparison[k] = {
                "top_avg": round(top_avg, 4),
                "bottom_avg": round(bot_avg, 4),
                "diff": round(diff, 4),
                "direction": direction,
            }

        return comparison

    def check_direction(self):
        """이전 라운드 대비 방향 검증.
        Returns: {"status": "improving"|"declining"|"stagnant",
                  "should_rollback": bool, "rollback_to": int|None, "details": str}
        """
        if len(self._round_history) < 2:
            return {"status": "first_round", "should_rollback": False,
                    "rollback_to": None, "details": "첫 라운드 — 비교 불가"}

        curr = self._round_history[-1]
        prev = self._round_history[-2]

        # 3가지 지표 비교
        best_delta = curr["best_score"] - prev["best_score"]
        avg_delta = curr["avg_score"] - prev["avg_score"]
        bottom_delta = curr["bottom_avg_score"] - prev["bottom_avg_score"]

        # 종합 판단 (가중 평균: BEST 50%, 평균 30%, 하위 20%)
        direction_score = best_delta * 0.5 + avg_delta * 0.3 + bottom_delta * 0.2

        if direction_score > 1:
            status = "improving"
            self._decline_streak = 0
        elif direction_score < -2:
            status = "declining"
            self._decline_streak += 1
        else:
            status = "stagnant"
            # 정체도 약간의 악화로 카운트 (3연속 정체 = 방향 전환 필요)
            if self._decline_streak > 0:
                self._decline_streak += 1

        # 역대 최고 업데이트
        if self._best_ever is None or curr["best_score"] > self._best_ever["best_score"]:
            self._best_ever = curr
            self._decline_streak = 0  # 신기록이면 리셋

        # 롤백 판단: 2라운드 연속 악화
        should_rollback = self._decline_streak >= 2
        rollback_to = None
        if should_rollback and self._best_ever:
            rollback_to = self._best_ever["round"]

        details = (
            f"BEST: {prev['best_score']} -> {curr['best_score']} ({best_delta:+.0f}) | "
            f"AVG: {prev['avg_score']:.1f} -> {curr['avg_score']:.1f} ({avg_delta:+.1f}) | "
            f"하위: {prev['bottom_avg_score']:.1f} -> {curr['bottom_avg_score']:.1f} ({bottom_delta:+.1f}) | "
            f"연속악화: {self._decline_streak}회"
        )

        return {
            "status": status,
            "should_rollback": should_rollback,
            "rollback_to": rollback_to,
            "details": details,
            "best_delta": best_delta,
            "avg_delta": avg_delta,
        }

    def get_rollback_params(self):
        """롤백 시 사용할 파라미터 (역대 최고 라운드의 BEST params)."""
        if self._best_ever and self._best_ever.get("best"):
            self._decline_streak = 0  # 롤백 후 카운터 리셋
            return self._best_ever["best"].get("params", {})
        return {}

    def decide_next_params(self, current_params):
        """모든 분석을 종합하여 다음 라운드 base_params 결정.
        Returns: (params_dict, decision_log: list[str])
        """
        log = []

        # 1) 방향 검증
        direction = self.check_direction()
        log.append(f"[방향] {direction['status']} — {direction['details']}")

        # 2) 롤백 필요?
        if direction["should_rollback"]:
            rollback_params = self.get_rollback_params()
            if rollback_params:
                log.append(f"[롤백] R{direction['rollback_to']}로 복원 (2라운드 연속 악화)")
                return rollback_params, log
            else:
                log.append("[롤백] 복원 대상 없음 — 현재 params 유지")

        # 3) 상관분석 기반 조정
        if len(self._round_history) > 0:
            latest = self._round_history[-1]
            results_for_analysis = [
                {"params": item.get("params", {}), "htm": item.get("htm", item)}
                for item in latest.get("scored_results", [])
            ]
            if results_for_analysis:
                adjusted, adj_log = self._analyzer.calc_adjusted_params_v2(
                    current_params, results_for_analysis)
                log.extend(adj_log)
                return adjusted, log

        log.append("[조정] 데이터 부족 — 현재 params 유지")
        return current_params, log

    def get_round_summary(self):
        """전체 라운드 히스토리 요약."""
        summary = []
        for rh in self._round_history:
            summary.append({
                "round": rh["round"],
                "best_score": rh["best_score"],
                "avg_score": rh["avg_score"],
                "total_sets": rh["total_sets"],
                "best_profit": rh["best"].get("profit", 0),
                "best_grade": rh["best"].get("grade", "?"),
            })
        return summary

    def generate_report(self):
        """최종 보고서 (10라운드 완료 후)."""
        lines = ["=" * 60]
        lines.append("EA Auto Master v6.0 — 라운드 최적화 보고서")
        lines.append(f"생성: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)

        if not self._round_history:
            lines.append("결과 없음")
            return "\n".join(lines)

        # 라운드별 요약
        lines.append("\n[라운드별 진행]")
        for rh in self._round_history:
            best = rh["best"]
            lines.append(
                f"  R{rh['round']:02d}: BEST={rh['best_score']}pts "
                f"({best.get('grade', '?')}) "
                f"Profit=${best.get('profit', 0):.2f} "
                f"PF={best.get('pf', 0):.2f} "
                f"AVG={rh['avg_score']:.1f} "
                f"Sets={rh['total_sets']}")

        # 최적 경로
        if self._best_ever:
            lines.append(f"\n[역대 최고] R{self._best_ever['round']} — "
                         f"{self._best_ever['best_score']}pts")
            best_params = self._best_ever["best"].get("params", {})
            if best_params:
                lines.append("[최적 파라미터]")
                for k, v in sorted(best_params.items()):
                    lines.append(f"  {k} = {v}")

        # 파라미터 영향력 분석
        correlations = self._analyzer.rank_param_impact()
        if correlations:
            lines.append("\n[파라미터 영향력 (상관계수)]")
            for k, corr in list(correlations.items())[:10]:
                bar = "+" * int(abs(corr) * 20)
                sign = "+" if corr > 0 else "-"
                lines.append(f"  {k:30s} {sign}{abs(corr):.3f} {bar}")

        return "\n".join(lines)


# ================================================================
# StrategyMixer — EA 코드 분석 + 전략 믹스
# ================================================================

class StrategyMixer:
    """성적 좋은 EA의 전략을 나쁜 EA에 주입.
    비유: 우승팀의 전술을 분석해서 하위팀에 적용하는 감독.
    """

    # 전략 시그널 패턴
    SIGNAL_PATTERNS = {
        "EMA_CROSS":    r'\biMA\s*\(.*?,\s*(\d+)\s*\).*?iMA\s*\(.*?,\s*(\d+)\s*\)',
        "RSI":          r'\biRSI\s*\(',
        "MACD":         r'\biMACD\s*\(',
        "BB":           r'\biBands\s*\(|Bollinger',
        "ATR":          r'\biATR\s*\(',
        "STOCH":        r'\biStochastic\s*\(',
        "CCI":          r'\biCCI\s*\(',
        "ADX":          r'\biADX\s*\(',
        "ICHIMOKU":     r'\biIchimoku\s*\(',
        "SAR":          r'\biSAR\s*\(',
        "CUSTOM_IND":   r'\biCustom\s*\(',
        "TRAIL_STOP":   r'TrailingStop|trailing|trail',
        "GRID":         r'grid|Grid|GRID',
        "MARTINGALE":   r'martingale|Martingale|lotMulti',
        "HEDGE":        r'hedge|Hedge|HEDGE',
        "TIME_FILTER":  r'TimeFilter|StartHour|EndHour|InpUseTimeFilter',
        "NEWS_FILTER":  r'NewsFilter|news_filter|skipNews',
        "CRASH_GUARD":  r'CrashGuard|crash_guard|InpUseCrashGuard',
    }

    def analyze_ea_code(self, mq4_content):
        """MQ4 소스에서 전략 구성요소 추출.
        Returns: {"signals": [...], "params": {...}, "functions": [...]}
        """
        signals = []
        for name, pattern in self.SIGNAL_PATTERNS.items():
            if re.search(pattern, mq4_content, re.IGNORECASE):
                signals.append(name)

        # extern/input 파라미터 추출
        params = {}
        for m in re.finditer(
                r'^\s*(?:extern|input)\s+(\w+)\s+(\w+)\s*=\s*([^;/\r\n]+)',
                mq4_content, re.MULTILINE):
            ptype, pname, pval = m.group(1), m.group(2), m.group(3).strip()
            params[pname] = {"type": ptype, "val": pval}

        # 함수 목록
        functions = re.findall(
            r'^(?:void|double|int|bool|string)\s+(\w+)\s*\(',
            mq4_content, re.MULTILINE)

        return {
            "signals": signals,
            "params": params,
            "functions": functions,
            "has_ontick": "OnTick" in mq4_content,
            "has_onstart": "OnStart" in mq4_content,
        }

    def compare_strategies(self, top_ea_analysis, bottom_ea_analysis):
        """상위 EA vs 하위 EA의 전략 구성 차이.
        Returns: {"only_in_top": [...], "only_in_bottom": [...], "common": [...], "suggestions": [...]}
        """
        top_signals = set(top_ea_analysis.get("signals", []))
        bot_signals = set(bottom_ea_analysis.get("signals", []))

        only_top = top_signals - bot_signals
        only_bot = bot_signals - top_signals
        common = top_signals & bot_signals

        suggestions = []
        # 상위에만 있는 시그널 → 하위에 추가 권장
        for sig in only_top:
            suggestions.append(f"ADD: {sig} (상위 EA에서 사용, 하위에 없음)")

        # 하위에만 있는 시그널 → 제거 또는 파라미터 조정 권장
        for sig in only_bot:
            if sig in ("MARTINGALE", "GRID"):
                suggestions.append(f"REMOVE: {sig} (하위 EA에서만 사용, 위험 전략)")
            else:
                suggestions.append(f"CHECK: {sig} (하위 EA에서만 사용, 파라미터 확인)")

        # 공통 시그널 중 파라미터 차이
        top_params = top_ea_analysis.get("params", {})
        bot_params = bottom_ea_analysis.get("params", {})
        for k in top_params:
            if k in bot_params:
                try:
                    tv = float(top_params[k]["val"])
                    bv = float(bot_params[k]["val"])
                    if abs(tv - bv) / max(abs(tv), 1) > 0.3:
                        suggestions.append(
                            f"ADJUST: {k} = {bv} -> {tv} "
                            f"(상위 EA 값으로 변경, 차이 {abs(tv-bv):.2f})")
                except (ValueError, TypeError):
                    pass

        return {
            "only_in_top": sorted(only_top),
            "only_in_bottom": sorted(only_bot),
            "common": sorted(common),
            "suggestions": suggestions,
        }

    def suggest_mix(self, top_ea_code, bottom_ea_code):
        """하위 EA에 주입할 상위 EA의 함수/모듈 제안.
        Returns: list of {"function": name, "reason": str, "code": str}
        """
        top_analysis = self.analyze_ea_code(top_ea_code)
        bot_analysis = self.analyze_ea_code(bottom_ea_code)
        comparison = self.compare_strategies(top_analysis, bot_analysis)

        from core.mql4_merger import parse_mq4_blocks

        top_blocks = parse_mq4_blocks(top_ea_code)
        suggestions = []

        # 상위에만 있는 함수 중 전략 관련 함수 추출
        top_funcs = set(top_blocks.get("funcs", {}).keys())
        bot_funcs_raw = re.findall(
            r'^(?:void|double|int|bool|string)\s+(\w+)\s*\(',
            bottom_ea_code, re.MULTILINE)
        bot_funcs = set(bot_funcs_raw)

        # 기본 함수 제외
        skip_funcs = {"OnInit", "OnTick", "OnDeinit", "OnStart", "OnTimer",
                       "init", "start", "deinit"}

        for fn in top_funcs - bot_funcs - skip_funcs:
            code = top_blocks["funcs"].get(fn, "")
            if not code:
                continue
            # 전략 관련 함수만 (Filter, Signal, Check, Calculate 등)
            if any(kw in fn.lower() for kw in
                   ["filter", "signal", "check", "calc", "trail", "guard",
                    "risk", "lot", "close", "modify"]):
                suggestions.append({
                    "function": fn,
                    "reason": f"상위 EA 전용 함수 (하위에 없음)",
                    "code": code,
                })

        return suggestions
