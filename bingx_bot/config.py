"""
BingX G4v7 Bot — 설정 파일
EA: G4v7_SC032_R7_SL065_TP0040_AT27_FM10_SM52_AX20_RL40_RH75_DD15_MP2_CD02
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ① API 키 설정 (BingX에서 발급받은 키 입력)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_KEY    = ""    # 예: "abc123def456..."
API_SECRET = ""    # 예: "xyz789..."

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ② 실행 모드 선택
#   DEMO_MODE = True  → BingX 데모 계좌 (가상 머니, 안전)
#   DEMO_MODE = False → 실제 계좌 (실제 돈)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEMO_MODE = True   # ← 처음엔 반드시 True !

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ③ 거래 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYMBOL     = "BTC/USDT:USDT"  # 비트코인 선물
TIMEFRAME  = "5m"              # 5분봉
LEVERAGE   = 3                 # 레버리지 배수 (처음엔 3배 이하 권장)
ORDER_SIZE = 20                # 1회 주문 금액 (USDT) — 데모는 자유

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ④ G4v7 전략 파라미터 (SC032_R7 최적화 결과)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARAMS = {
    "InpSLMultiplier":  0.65,
    "InpTPMultiplier":  4.0,
    "InpATRPeriod":     27,
    "InpFastMA":        10,
    "InpSlowMA":        52,
    "InpADXPeriod":     20,
    "InpADXMin":        40.0,
    "InpRSIPeriod":     14,
    "InpRSILower":      40.0,
    "InpRSIUpper":      75.0,
    "InpMaxDD":         15.0,
    "InpMaxPositions":  2,
    "InpCooldownBars":  2,
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⑤ 리스크 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_DAILY_LOSS_PCT  = 5.0   # 하루 최대 손실 % (초과 시 자동 중단)
MAX_OPEN_POSITIONS  = PARAMS["InpMaxPositions"]
