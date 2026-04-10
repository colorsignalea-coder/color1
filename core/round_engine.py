"""
core/round_engine.py — EA Auto Master v6.0
===========================================
SET 파일 파싱 + 라운드별 파라미터 변동 생성.
R1~R10 자동 라운드의 핵심 데이터 로직.
"""
import itertools
import re

from core.encoding import read_mq4


SKIP_KW = [
    "magic", "comment", "slip", "lot", "enable", "filter", "hedge",
    "mode", "type", "signal", "alert", "print", "debug", "email", "push"
]


def parse_set_file(path):
    """MT4 .set 파일 -> {param: value}"""
    params = {}
    try:
        content, _ = read_mq4(path)
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(";") or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                v = v.split("||")[0].strip()
                params[k.strip()] = v
    except Exception:
        pass
    return params


def parse_ea_params(mq4_path):
    """MQL4 파일에서 extern/input 파라미터 추출."""
    try:
        content, _ = read_mq4(mq4_path)
        params = {}
        for m in re.finditer(
                r'^\s*(?:extern|input)\s+(\w+)\s+(\w+)\s*=\s*([^;/\r\n]+)',
                content, re.MULTILINE):
            ptype, pname, pval = m.group(1), m.group(2), m.group(3).strip()
            params[pname] = {"type": ptype, "val": pval}
        return params
    except Exception:
        return {}


def smart_vary(name, val_str, step=0.15, n_steps=3):
    """파라미터 스마트 변동값 생성."""
    try:
        n = name.lower()
        if any(k in n for k in SKIP_KW):
            return [val_str]
        if val_str.strip().lower() in ("true", "false"):
            return [val_str]

        center = float(val_str)

        if any(k in n for k in ["period", "bar", "length", "lookback", "shift"]):
            s = max(1, int(center * 0.12))
            vals = sorted(set(max(1, int(center + s * i))
                              for i in range(-n_steps // 2, n_steps // 2 + 1)))
        elif any(k in n for k in ["sl", "tp", "stop", "pip", "point", "spread"]):
            vals = [round(center * (1 + step * (i - (n_steps - 1) / 2)), 1) for i in range(n_steps)]
        else:
            vals = [round(center * (1 + step * (i - (n_steps - 1) / 2)), 4) for i in range(n_steps)]

        result = sorted(set([center] + vals))
        return [str(v) for v in result]
    except Exception:
        return [val_str]


def gen_round_sets(base_params, round_num, max_vary=3, n_steps=3, step=0.15,
                   step_override=None):
    """라운드별 파라미터 SET 조합 생성.
    step_override: {param_key: absolute_delta}
    round_num: 라운드 진행에 따라 step 수렴 (R1=100%, R2=87%, ... 최소 20%)
    """
    effective_step = step * max(0.2, 1.0 - (round_num - 1) * 0.13)
    vary_candidates = []
    for k, v in base_params.items():
        if step_override and k in step_override:
            delta = step_override[k] * max(0.2, 1.0 - (round_num - 1) * 0.13)
            try:
                center = float(v)
                is_int = "." not in str(v)
                raw = [center + delta * i for i in range(-(n_steps // 2), n_steps // 2 + 1)]
                if is_int:
                    vals = sorted(set(str(max(0, int(round(x)))) for x in raw))
                else:
                    vals = sorted(set(str(round(x, 4)) for x in raw))
                if len(vals) > 1:
                    vary_candidates.append((k, vals))
                    continue
            except Exception:
                pass
        vals = smart_vary(k, str(v), effective_step, n_steps)
        if len(vals) > 1:
            vary_candidates.append((k, vals))

    vary_candidates = vary_candidates[:max_vary]
    if not vary_candidates:
        return [dict(base_params)]

    combos = list(itertools.product(*[v for _, v in vary_candidates]))
    sets = []
    for combo in combos:
        new_params = dict(base_params)
        for (k, _), v in zip(vary_candidates, combo):
            new_params[k] = v
        sets.append(new_params)
    return sets


def gen_round_sets_v2(base_params, round_num, sweet_spots=None, correlations=None,
                      max_vary=4, n_steps=5, step=0.15):
    """v2 비균등 탐색 — ParamAnalyzer의 분석 결과를 반영.

    sweet_spots: {param: {"center", "low", "high", "direction"}} from ParamAnalyzer
    correlations: {param: float} from ParamAnalyzer.rank_param_impact()

    로직:
    - 상관 높은 파라미터: sweet_spot 구간에 집중 (5개 값 중 3개가 상위 구간)
    - 상관 낮은 파라미터: 고정 또는 2개 값만 탐색
    - 역상관 파라미터: 반대 방향 탐색
    """
    sweet_spots = sweet_spots or {}
    correlations = correlations or {}

    effective_step = step * max(0.2, 1.0 - (round_num - 1) * 0.13)
    vary_candidates = []

    # 상관계수 기준 내림차순 정렬 → 영향력 큰 파라미터 우선
    sorted_keys = sorted(
        base_params.keys(),
        key=lambda k: abs(correlations.get(k, 0)),
        reverse=True)

    for k in sorted_keys:
        v = base_params[k]
        kl = k.lower()
        if kl in SKIP_KW:
            continue
        try:
            center = float(v)
        except (ValueError, TypeError):
            continue
        if str(v).strip().lower() in ("true", "false"):
            continue

        corr = abs(correlations.get(k, 0))
        spot = sweet_spots.get(k)

        # 상관 < 0.15: 무의미 → 고정
        if corr < 0.15 and not spot:
            continue

        # 상관 높음 + sweet_spot 있음: 상위 구간에 집중
        if spot and corr >= 0.3:
            low = spot["low"]
            high = spot["high"]
            target = spot["center"]
            span = max(abs(high - low), abs(center) * effective_step)

            # 5개 값: target 중심 + 상위 구간 집중 (비균등)
            vals = set()
            vals.add(round(target, 5))
            vals.add(round(center, 5))  # 현재값도 포함
            # target 방향으로 3개 추가
            for i in range(1, 4):
                offset = span * 0.25 * i
                if spot["direction"] == "increase":
                    vals.add(round(target + offset * 0.3, 5))
                elif spot["direction"] == "decrease":
                    vals.add(round(target - offset * 0.3, 5))
                else:
                    vals.add(round(target + offset * 0.2, 5))
                    vals.add(round(target - offset * 0.2, 5))

            # 정수형 처리
            is_int = "." not in str(v)
            if is_int:
                vals = sorted(set(str(max(0, int(round(x)))) for x in vals))
            else:
                vals = sorted(set(str(round(x, 4)) for x in vals))

            if len(vals) > 1:
                vary_candidates.append((k, vals[:n_steps]))
                continue

        # 상관 있지만 spot 없음: 일반 smart_vary (좁은 범위)
        if corr >= 0.15:
            adj_step = effective_step * min(1.0, corr * 2)
            vals = smart_vary(k, str(v), adj_step, min(n_steps, 3))
            if len(vals) > 1:
                vary_candidates.append((k, vals))

    vary_candidates = vary_candidates[:max_vary]
    if not vary_candidates:
        return [dict(base_params)]

    combos = list(itertools.product(*[v for _, v in vary_candidates]))
    sets = []
    for combo in combos:
        new_params = dict(base_params)
        for (k, _), v in zip(vary_candidates, combo):
            new_params[k] = v
        sets.append(new_params)
    return sets


def gen_bottom_fix_sets(bottom_results, top_comparison, base_params):
    """하위 결과의 파라미터를 상위 방향으로 수정한 SET 생성.

    bottom_results: 하위 결과 리스트 [{"params": {}, ...}]
    top_comparison: RoundDirector.compare_top_bottom() 결과
    base_params: 현재 base 파라미터

    Returns: list of param dicts (수정된 하위 SET들)
    """
    fix_sets = []
    for br in bottom_results:
        fixed = dict(br.get("params", base_params))
        for k, comp in top_comparison.items():
            if k not in fixed:
                continue
            if comp["direction"] == "same":
                continue
            try:
                current = float(fixed[k])
                top_avg = comp["top_avg"]
                # 현재값에서 상위 평균 방향으로 50% 이동
                new_val = current + (top_avg - current) * 0.5
                is_int = "." not in str(fixed[k])
                fixed[k] = str(int(round(new_val))) if is_int else str(round(new_val, 4))
            except (ValueError, TypeError):
                pass
        fix_sets.append(fixed)
    return fix_sets
