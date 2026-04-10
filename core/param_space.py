"""
core/param_space.py — Stage 1: 파라미터 공간 정의 & MQ4 자동 파싱
===================================================================
어떤 EA든 .mq4 input 선언을 읽어 파라미터 공간 자동 생성.
사용자가 "범위·단계"만 지정하면 나머지는 자동.
"""
import re
import os


# ─────────────────────────────────────────────────────────────────────────────
# 1. MQ4 input 자동 파싱
# ─────────────────────────────────────────────────────────────────────────────

def parse_mq4_inputs(mq4_path):
    """
    .mq4 파일에서 input/extern 선언을 모두 파싱.

    반환: list of dict
      {name, type('double'|'int'|'bool'|'string'), default, comment}

    예:
      input double InpSLMultiplier = 0.3;  // SL 배율
      → {name:'InpSLMultiplier', type:'double', default:0.3, comment:'SL 배율'}
    """
    if not os.path.exists(mq4_path):
        return []

    try:
        with open(mq4_path, 'r', encoding='utf-8', errors='replace') as f:
            src = f.read()
    except Exception:
        return []

    pattern = re.compile(
        r'(?:input|extern)\s+'           # input 또는 extern
        r'(double|int|bool|string)\s+'   # 타입
        r'(\w+)\s*=\s*'                  # 변수명 =
        r'([^;]+);'                      # 기본값 (세미콜론까지)
        r'(?:\s*//\s*(.*))?',            # 선택적 주석
        re.MULTILINE
    )

    params = []
    for m in pattern.finditer(src):
        ptype   = m.group(1).strip()
        name    = m.group(2).strip()
        raw_val = m.group(3).strip()
        comment = (m.group(4) or '').strip()

        # 기본값 변환
        try:
            if ptype == 'double':
                default = float(raw_val)
            elif ptype == 'int':
                default = int(float(raw_val))
            elif ptype == 'bool':
                default = raw_val.lower() in ('true', '1')
            else:
                default = raw_val.strip('"\'')
        except Exception:
            default = raw_val

        params.append({
            'name':    name,
            'type':    ptype,
            'default': default,
            'comment': comment,
        })

    return params


# ─────────────────────────────────────────────────────────────────────────────
# 2. 파라미터 공간 정의
# ─────────────────────────────────────────────────────────────────────────────

class ParamSpace:
    """
    파라미터 공간 정의 + 유효성 검사.

    사용법:
        ps = ParamSpace()
        ps.add('InpSLMultiplier', ptype='double', min=0.1, max=1.0, step=0.05)
        ps.add('InpADXMin',       ptype='double', min=15,  max=35,  step=2.5)
        ps.add('InpMaxPositions', ptype='int',    min=1,   max=5,   step=1)

        # 전체 그리드 크기 (참고용 — 실제로는 LHS 사용)
        print(ps.grid_size())  # 20 × 9 × 5 = 900 → 전수탐색 가능
        # 변수 많아지면 → print(ps.grid_size())  # 10^12 → LHS 필요

        # 특정 조합이 유효한지 검사
        ps.add_constraint('InpFastMA < InpSlowMA')
    """

    def __init__(self):
        self._params = {}          # name → spec dict
        self._constraints = []     # 제약 조건 표현식 목록

    def add(self, name, ptype='double', min_val=None, max_val=None,
            step=None, choices=None, fixed=None, comment=''):
        """
        파라미터 추가.

        fixed:   고정값 (탐색 제외)
        choices: 이산 선택지 목록 [v1, v2, ...] — step 무시
        """
        spec = {
            'name':    name,
            'type':    ptype,
            'min':     min_val,
            'max':     max_val,
            'step':    step,
            'choices': choices,
            'fixed':   fixed,
            'comment': comment,
        }
        self._params[name] = spec

    def add_from_mq4(self, mq4_path, overrides=None):
        """
        .mq4 파싱 결과로 파라미터 공간 자동 구성.
        overrides: {param_name: {min, max, step}} — 범위 수동 지정
        """
        overrides = overrides or {}
        parsed = parse_mq4_inputs(mq4_path)
        for p in parsed:
            name = p['name']
            ov   = overrides.get(name, {})
            if p['type'] in ('double', 'int'):
                default = p['default']
                if isinstance(default, (int, float)):
                    # 기본 범위: default × 0.3 ~ default × 3.0
                    lo = ov.get('min', default * 0.3)
                    hi = ov.get('max', default * 3.0)
                    st = ov.get('step', (hi - lo) / 10)
                    self.add(name, ptype=p['type'],
                             min_val=round(lo, 4), max_val=round(hi, 4),
                             step=round(st, 4), comment=p['comment'])
                else:
                    self.add(name, ptype=p['type'], fixed=default,
                             comment=p['comment'])
            elif p['type'] == 'bool':
                self.add(name, ptype='bool', choices=[True, False],
                         comment=p['comment'])

    def add_constraint(self, expr):
        """
        파라미터 간 제약 조건 추가.
        expr: 'InpFastMA < InpSlowMA' 형식 문자열
        """
        self._constraints.append(expr)

    def is_valid(self, params_dict):
        """params_dict가 모든 제약 조건을 만족하는지 확인."""
        for expr in self._constraints:
            try:
                if not eval(expr, {}, params_dict):
                    return False
            except Exception:
                pass
        return True

    def grid_size(self):
        """전수탐색 시 총 조합 수 (참고용)."""
        total = 1
        for spec in self._params.values():
            if spec['fixed'] is not None:
                continue
            if spec['choices']:
                total *= len(spec['choices'])
            elif spec['min'] is not None and spec['max'] is not None and spec['step']:
                n = int((spec['max'] - spec['min']) / spec['step']) + 1
                total *= max(n, 1)
        return total

    def names(self):
        return list(self._params.keys())

    def specs(self):
        return dict(self._params)

    def clip(self, name, value):
        """값을 파라미터 범위 내로 클리핑."""
        spec = self._params.get(name)
        if not spec:
            return value
        if spec['fixed'] is not None:
            return spec['fixed']
        if spec['choices']:
            return min(spec['choices'], key=lambda x: abs(x - value))
        lo = spec['min'] if spec['min'] is not None else value
        hi = spec['max'] if spec['max'] is not None else value
        v  = max(lo, min(hi, value))
        if spec['type'] == 'int':
            v = int(round(v))
        elif spec['step']:
            steps = round((v - lo) / spec['step'])
            v = round(lo + steps * spec['step'], 6)
        return v

    def summary(self):
        """파라미터 공간 요약 출력 문자열."""
        lines = [f"파라미터 공간: {len(self._params)}개  "
                 f"전수탐색규모: {self.grid_size():,}"]
        for spec in self._params.values():
            if spec['fixed'] is not None:
                lines.append(f"  {spec['name']:30s} [고정={spec['fixed']}]")
            elif spec['choices']:
                lines.append(f"  {spec['name']:30s} choices={spec['choices']}")
            else:
                lines.append(
                    f"  {spec['name']:30s} "
                    f"{spec['min']} ~ {spec['max']}  step={spec['step']}  "
                    f"({'int' if spec['type']=='int' else 'float'})"
                    + (f"  # {spec['comment']}" if spec['comment'] else ""))
        if self._constraints:
            lines.append(f"  제약조건: {self._constraints}")
        return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 3. G4 EA 기본 파라미터 공간 (현재 EA 기반, 확장 가능)
# ─────────────────────────────────────────────────────────────────────────────

def make_g4_param_space(extra_params=False):
    """
    G4 Trend EA 파라미터 공간.
    extra_params=True: ADX·RSI·멀티포지션·쿨다운 포함 (확장형)
    """
    ps = ParamSpace()

    # ── 기본 파라미터 (현재 EA) ──────────────────────────────────────
    ps.add('InpSLMultiplier', 'double', min_val=0.10, max_val=0.80, step=0.025,
           comment='SL = ATR × 이 값')
    ps.add('InpTPMultiplier', 'double', min_val=4.0,  max_val=28.0, step=0.5,
           comment='TP = ATR × 이 값')
    ps.add('InpATRPeriod',    'int',    min_val=7,    max_val=28,   step=1,
           comment='ATR 계산 기간')
    ps.add('InpFastMA',       'int',    min_val=5,    max_val=20,   step=1,
           comment='빠른 EMA 기간')
    ps.add('InpSlowMA',       'int',    min_val=14,   max_val=55,   step=1,
           comment='느린 EMA 기간')

    # FastMA < SlowMA 제약
    ps.add_constraint('params["InpFastMA"] < params["InpSlowMA"]')

    if extra_params:
        # ── 확장 파라미터 (ADX · RSI · DD · 멀티포지션 · 쿨다운) ──────
        ps.add('InpADXPeriod',    'int',    min_val=10,   max_val=30,   step=2,
               comment='ADX 기간 (추세강도 필터)')
        ps.add('InpADXMin',       'double', min_val=15.0, max_val=35.0, step=2.5,
               comment='최소 ADX 값 (낮으면 추세약해 진입안함)')
        ps.add('InpRSIPeriod',    'int',    min_val=7,    max_val=21,   step=2,
               comment='RSI 기간')
        ps.add('InpRSILower',     'double', min_val=25.0, max_val=45.0, step=5.0,
               comment='RSI 하한 (매수 진입조건)')
        ps.add('InpRSIUpper',     'double', min_val=55.0, max_val=75.0, step=5.0,
               comment='RSI 상한 (매도 진입조건)')
        ps.add('InpMaxDD',        'double', min_val=5.0,  max_val=25.0, step=2.5,
               comment='최대 낙폭 % (초과 시 전체 청산)')
        ps.add('InpMaxPositions', 'int',    min_val=1,    max_val=5,    step=1,
               comment='동시 최대 포지션 수')
        ps.add('InpCooldownBars', 'int',    min_val=1,    max_val=10,   step=1,
               comment='청산 후 재진입 대기 봉 수')

        # RSI 범위 제약
        ps.add_constraint('params["InpRSILower"] < params["InpRSIUpper"]')

    return ps


if __name__ == '__main__':
    # 기본 파라미터 공간
    ps_basic = make_g4_param_space(extra_params=False)
    print("=== 기본 파라미터 공간 ===")
    print(ps_basic.summary())
    print()

    # 확장 파라미터 공간
    ps_full = make_g4_param_space(extra_params=True)
    print("=== 확장 파라미터 공간 ===")
    print(ps_full.summary())
    print()

    # MQ4 자동 파싱 예시
    mq4 = r"C:\AG TO DO\MT4\MQL4\Experts\_R3_ONLY\G4_TR_SC002_R3.mq4"
    if os.path.exists(mq4):
        print("=== MQ4 자동 파싱 ===")
        inputs = parse_mq4_inputs(mq4)
        for p in inputs:
            print(f"  {p['name']:25s} {p['type']:8s} default={p['default']}")
