"""
G4v7 전략 — Python 포팅
EMA크로스 + ADX필터 + RSI필터 + ATR기반 SL/TP
"""
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def adx(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df['high'], df['low'], df['close']
    plus_dm  = (high - high.shift(1)).clip(lower=0)
    minus_dm = (low.shift(1) - low).clip(lower=0)
    plus_dm[plus_dm < minus_dm]  = 0
    minus_dm[minus_dm < plus_dm] = 0
    tr_s     = atr(df, period) * period
    plus_di  = 100 * plus_dm.ewm(span=period, adjust=False).mean() / (tr_s / period + 1e-9)
    minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / (tr_s / period + 1e-9)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    return dx.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    return 100 - 100 / (1 + rs)


class G4v7Strategy:
    """G4v7 전략 신호 생성기"""

    def __init__(self, params: dict):
        self.p = params
        self._cooldown_count = 0   # 쿨다운 카운터

    def calc_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """캔들 DataFrame → 지표 계산 후 반환"""
        p = self.p
        df = df.copy()
        df['fast_ema'] = ema(df['close'], p['InpFastMA'])
        df['slow_ema'] = ema(df['close'], p['InpSlowMA'])
        df['atr_val']  = atr(df, p['InpATRPeriod'])
        df['adx_val']  = adx(df, p['InpADXPeriod'])
        df['rsi_val']  = rsi(df['close'], p.get('InpRSIPeriod', 14))
        return df

    def get_signal(self, df: pd.DataFrame) -> dict:
        """
        마지막 완성된 캔들 기준으로 신호 반환
        반환: {'signal': 'BUY'/'SELL'/'HOLD', 'sl': float, 'tp': float, 'atr': float}
        """
        p = self.p
        df = self.calc_indicators(df)

        # 마지막 완성 캔들 (인덱스 -2, -1은 현재 미완성)
        cur = df.iloc[-2]
        prv = df.iloc[-3]

        atr_val  = cur['atr_val']
        adx_val  = cur['adx_val']
        rsi_val  = cur['rsi_val']
        fast_cur = cur['fast_ema']
        slow_cur = cur['slow_ema']
        fast_prv = prv['fast_ema']
        slow_prv = prv['slow_ema']
        price    = cur['close']

        result = {
            'signal': 'HOLD',
            'sl': 0.0,
            'tp': 0.0,
            'atr': atr_val,
            'adx': adx_val,
            'rsi': rsi_val,
            'fast_ema': fast_cur,
            'slow_ema': slow_cur,
            'price': price,
        }

        # 쿨다운 체크
        if self._cooldown_count > 0:
            self._cooldown_count -= 1
            return result

        # ADX 필터: 추세 강도 확인
        if adx_val < p['InpADXMin']:
            return result

        # RSI 필터: 과매수/과매도 구간 제외
        if not (p['InpRSILower'] <= rsi_val <= p['InpRSIUpper']):
            return result

        # EMA 크로스 매수 신호
        golden_cross = (fast_prv <= slow_prv) and (fast_cur > slow_cur)
        # EMA 크로스 매도 신호
        death_cross  = (fast_prv >= slow_prv) and (fast_cur < slow_cur)

        if golden_cross:
            sl = price - atr_val * p['InpSLMultiplier']
            tp = price + atr_val * p['InpTPMultiplier']
            result['signal'] = 'BUY'
            result['sl'] = round(sl, 2)
            result['tp'] = round(tp, 2)
            self._cooldown_count = p['InpCooldownBars']

        elif death_cross:
            sl = price + atr_val * p['InpSLMultiplier']
            tp = price - atr_val * p['InpTPMultiplier']
            result['signal'] = 'SELL'
            result['sl'] = round(sl, 2)
            result['tp'] = round(tp, 2)
            self._cooldown_count = p['InpCooldownBars']

        return result
