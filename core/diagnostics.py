"""
core/diagnostics.py — EA Auto Master v6.0
==========================================
거래 0건 원인 자동 진단. MT4 오류 코드 기반.
"""
import re


ERROR_MAP = {
    "131": "ERR_INVALID_TRADE_VOLUME -- LotSize 줄이기",
    "130": "ERR_INVALID_STOPS -- StopLoss/TakeProfit 간격 늘리기",
    "132": "ERR_MARKET_CLOSED -- 테스트 기간 또는 심볼 변경",
    "133": "ERR_TRADE_DISABLED -- EA 자동매매 활성화 확인",
    "4051": "ERR_INVALID_FUNCTION_PARAMVALUE -- 파라미터 범위 확인",
}


def diagnose_zero_trades(htm_path):
    """거래 0건 원인 자동 진단. 오류 코드 기반."""
    result = []
    try:
        content = ""
        for enc in ("utf-8", "cp949", "latin-1"):
            try:
                with open(htm_path, encoding=enc, errors="replace") as f:
                    content = f.read()
                break
            except Exception:
                content = ""
        for code, msg in ERROR_MAP.items():
            if code in content:
                result.append(f"[오류 {code}] {msg}")
        m = re.search(r'lotsize[^>]*>\s*([\d.]+)', content, re.I)
        if m and float(m.group(1)) < 0.01:
            result.append("[LotSize<0.01] 최소 거래량 미달 -- LotSize 0.01 이상으로 수정")
        if re.search(r'expir', content, re.I):
            result.append("[Expiry] EA 만료일 설정 감지 -- 만료 조건 확인")
    except Exception:
        pass
    return result if result else ["진단 불가 -- HTM 내 오류 코드 없음"]
