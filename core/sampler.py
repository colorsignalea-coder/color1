"""
core/sampler.py — Stage 2: 지능형 파라미터 샘플러
====================================================
Latin Hypercube Sampling (LHS) + Sobol 시퀀스로
파라미터 공간을 "균등하게" 커버하는 N개 샘플 생성.

핵심 원리 (비유):
  - 랜덤 샘플: 운동장에 씨를 무작위로 뿌림 → 겹치는 구역 있고 안 가는 구역 생김
  - LHS:       운동장을 격자로 나눠 각 행×열에 정확히 1개씩 → 빠짐없이 균등 커버

100개 샘플로 10억 조합을 "대표"할 수 있는 이유: LHS
"""
import random
import math
from core.param_space import ParamSpace


# ─────────────────────────────────────────────────────────────────────────────
# 1. Latin Hypercube Sampling
# ─────────────────────────────────────────────────────────────────────────────

def lhs_sample(param_space: ParamSpace, n: int, seed: int = 42) -> list:
    """
    Latin Hypercube Sampling으로 n개 파라미터 조합 생성.

    반환: list of dict  [{param_name: value, ...}, ...]
    각 dict는 param_space의 is_valid() 제약 조건을 만족함.
    """
    rng = random.Random(seed)
    specs = param_space.specs()

    # 최적화 대상 파라미터만 추출 (fixed 제외)
    active = {
        name: spec for name, spec in specs.items()
        if spec['fixed'] is None
    }
    fixed = {
        name: spec['fixed'] for name, spec in specs.items()
        if spec['fixed'] is not None
    }

    if not active:
        return [fixed.copy() for _ in range(n)]

    param_names = list(active.keys())
    k = len(param_names)

    # LHS 격자 생성: k차원 각각 0~1 범위를 n등분
    # 각 행에서 해당 차원 구간 내 균등 랜덤 샘플
    grid = []
    for _ in range(k):
        col = [(i + rng.random()) / n for i in range(n)]
        rng.shuffle(col)
        grid.append(col)
    # grid[dim][sample_idx] = 0~1 값

    samples = []
    attempts = 0
    max_attempts = n * 20

    i = 0
    while len(samples) < n and attempts < max_attempts:
        sample_idx = i % n
        candidate = dict(fixed)

        for dim, name in enumerate(param_names):
            u = grid[dim][sample_idx]
            candidate[name] = _unit_to_value(u, active[name], param_space)

        attempts += 1
        if param_space.is_valid({'params': candidate}):
            samples.append(candidate)
        else:
            # 제약 위반 시 해당 슬롯 재랜덤
            for dim in range(k):
                grid[dim][sample_idx] = rng.random()
            i -= 1  # 다시 시도

        i += 1

    # 부족하면 랜덤으로 채움
    while len(samples) < n:
        candidate = dict(fixed)
        for name, spec in active.items():
            u = rng.random()
            candidate[name] = _unit_to_value(u, spec, param_space)
        if param_space.is_valid({'params': candidate}):
            samples.append(candidate)

    return samples


def _unit_to_value(u, spec, param_space):
    """0~1 유닛값 → 파라미터 실제값 변환."""
    if spec['choices']:
        idx = min(int(u * len(spec['choices'])), len(spec['choices']) - 1)
        return spec['choices'][idx]

    lo = spec['min']
    hi = spec['max']
    raw = lo + u * (hi - lo)

    if spec['step']:
        steps = round((raw - lo) / spec['step'])
        raw = lo + steps * spec['step']

    raw = max(lo, min(hi, raw))

    if spec['type'] == 'int':
        return int(round(raw))
    return round(raw, 4)


# ─────────────────────────────────────────────────────────────────────────────
# 2. 유망 구역 집중 샘플 (Stage 2용)
# ─────────────────────────────────────────────────────────────────────────────

def focused_sample(param_space: ParamSpace, top_results: list,
                   n: int, noise_ratio: float = 0.2, seed: int = None) -> list:
    """
    상위 결과 주변 ±noise_ratio 범위에서 집중 샘플링.

    top_results: [{'params': {name: value}, 'score': float}, ...]
    noise_ratio: 파라미터 범위 대비 탐색 반경 (0.2 = ±20%)
    """
    rng = random.Random(seed)
    specs = param_space.specs()
    samples = []

    if not top_results:
        return lhs_sample(param_space, n, seed or 42)

    attempts = 0
    max_attempts = n * 30

    while len(samples) < n and attempts < max_attempts:
        attempts += 1
        # 상위 결과 중 하나를 기준점으로 선택 (점수 가중치 적용)
        scores = [max(r.get('score', 0), 0.001) for r in top_results]
        total  = sum(scores)
        probs  = [s / total for s in scores]
        base   = _weighted_choice(top_results, probs, rng)['params']

        candidate = {}
        for name, spec in specs.items():
            if spec['fixed'] is not None:
                candidate[name] = spec['fixed']
                continue

            base_val = base.get(name, (spec['min'] + spec['max']) / 2)
            if spec['choices']:
                # 이산값: 인접값으로 무작위 이동
                idx = spec['choices'].index(base_val) if base_val in spec['choices'] else 0
                delta = rng.choice([-1, 0, 0, 1])
                idx = max(0, min(len(spec['choices']) - 1, idx + delta))
                candidate[name] = spec['choices'][idx]
            else:
                lo, hi = spec['min'], spec['max']
                radius = (hi - lo) * noise_ratio
                raw = base_val + rng.uniform(-radius, radius)
                candidate[name] = param_space.clip(name, raw)

        if param_space.is_valid({'params': candidate}):
            samples.append(candidate)

    # 부족분 LHS로 보충
    if len(samples) < n:
        extra = lhs_sample(param_space, n - len(samples),
                           seed=(seed or 42) + 1)
        samples.extend(extra)

    return samples[:n]


def _weighted_choice(items, weights, rng):
    r = rng.random()
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


# ─────────────────────────────────────────────────────────────────────────────
# 3. 유전 알고리즘 교차·변이 (Stage 3용)
# ─────────────────────────────────────────────────────────────────────────────

def genetic_sample(param_space: ParamSpace, population: list,
                   n: int, mutation_rate: float = 0.1,
                   seed: int = None) -> list:
    """
    유전 알고리즘: 상위 파라미터들을 교배(crossover) + 돌연변이(mutation).

    population: [{'params': {name: value}, 'score': float}, ...]
    mutation_rate: 각 파라미터가 돌연변이될 확률
    """
    rng = random.Random(seed)
    specs = param_space.specs()
    offspring = []
    attempts  = 0
    max_att   = n * 30

    if len(population) < 2:
        return lhs_sample(param_space, n, seed or 42)

    scores = [max(r.get('score', 0), 0.001) for r in population]
    total  = sum(scores)
    probs  = [s / total for s in scores]

    while len(offspring) < n and attempts < max_att:
        attempts += 1

        # 부모 2개 선택
        p1 = _weighted_choice(population, probs, rng)['params']
        p2 = _weighted_choice(population, probs, rng)['params']
        if p1 is p2:
            continue

        child = {}
        for name, spec in specs.items():
            if spec['fixed'] is not None:
                child[name] = spec['fixed']
                continue

            # 교차: 각 파라미터를 p1 또는 p2에서 무작위 선택
            val = p1.get(name) if rng.random() < 0.5 else p2.get(name)

            # 돌연변이
            if rng.random() < mutation_rate:
                if spec['choices']:
                    val = rng.choice(spec['choices'])
                else:
                    lo, hi = spec['min'], spec['max']
                    # 전체 범위에서 균등 돌연변이
                    val = rng.uniform(lo, hi)
                val = param_space.clip(name, val)

            child[name] = val if val is not None else param_space.clip(name, 0)

        if param_space.is_valid({'params': child}):
            offspring.append(child)

    if len(offspring) < n:
        extra = lhs_sample(param_space, n - len(offspring),
                           seed=(seed or 42) + 99)
        offspring.extend(extra)

    return offspring[:n]


# ─────────────────────────────────────────────────────────────────────────────
# 4. 라운드별 샘플링 전략 자동 선택
# ─────────────────────────────────────────────────────────────────────────────

def get_samples_for_round(param_space: ParamSpace, round_num: int,
                          prev_results: list, n: int,
                          seed: int = None) -> list:
    """
    라운드에 따라 자동으로 샘플링 전략 선택.

    Round 1~2:  LHS (전체 공간 균등 탐색)
    Round 3~5:  focused_sample (상위 결과 주변 집중)
    Round 6+:   genetic_sample (교차 진화)
    """
    seed = seed or (42 + round_num * 7)

    if round_num <= 2 or not prev_results:
        strategy = 'LHS'
        samples  = lhs_sample(param_space, n, seed)
    elif round_num <= 5:
        strategy = 'FOCUSED'
        top = sorted(prev_results, key=lambda x: x.get('score', 0), reverse=True)[:10]
        samples = focused_sample(param_space, top, n,
                                 noise_ratio=0.25, seed=seed)
    else:
        strategy = 'GENETIC'
        top = sorted(prev_results, key=lambda x: x.get('score', 0), reverse=True)[:20]
        samples = genetic_sample(param_space, top, n,
                                 mutation_rate=0.15, seed=seed)

    print(f"  [SAMPLER] R{round_num} 전략={strategy}  {n}개 샘플 생성")
    return samples


if __name__ == '__main__':
    from core.param_space import make_g4_param_space

    ps = make_g4_param_space(extra_params=True)
    print(ps.summary())
    print()

    samples = lhs_sample(ps, 10)
    print("LHS 10개 샘플:")
    for i, s in enumerate(samples, 1):
        sl  = s.get('InpSLMultiplier', '?')
        tp  = s.get('InpTPMultiplier', '?')
        adx = s.get('InpADXMin', '?')
        mp  = s.get('InpMaxPositions', '?')
        print(f"  {i:2d}. SL={sl:.3f}  TP={tp:.1f}  ADXmin={adx}  MaxPos={mp}")
