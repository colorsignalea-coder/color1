"""
Bitget G4v7 Bot — 설정 파일
EA: G4v7_SC032_R7_SL065_TP0040_AT27_FM10_SM52_AX20_RL40_RH75_DD15_MP2_CD02
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ① API 키 (Bitget에서 발급)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_KEY        = ""
API_SECRET     = ""
API_PASSPHRASE = ""   # Bitget은 비밀번호(패스프레이즈)가 추가로 필요!

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ② 실행 모드
#   DEMO_MODE = True  → Bitget 데모 계좌
#   DEMO_MODE = False → 실계좌
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEMO_MODE = True

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ③ 거래 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYMBOL     = "BTCUSDT"          # Bitget 선물 심볼
TIMEFRAME  = "5m"
LEVERAGE   = 3
ORDER_SIZE = 20                 # USDT 기준

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ④ G4v7 전략 파라미터 (SC032_R7)
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

MAX_DAILY_LOSS_PCT = 5.0
MAX_OPEN_POSITIONS = PARAMS["InpMaxPositions"]
