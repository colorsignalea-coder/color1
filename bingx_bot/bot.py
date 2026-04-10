"""
BingX G4v7 Trading Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
실행: python bot.py  또는  START_BOT.bat
DEMO_MODE=True  → BingX 데모 계좌 (가상 머니)
DEMO_MODE=False → 실계좌
"""
import sys, os, time, logging
from datetime import datetime

_SITE = r'C:\Users\1\AppData\Roaming\Python\Python313\site-packages'
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import ccxt
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (API_KEY, API_SECRET, SYMBOL, TIMEFRAME, LEVERAGE,
                    ORDER_SIZE, PARAMS, MAX_DAILY_LOSS_PCT,
                    MAX_OPEN_POSITIONS, DEMO_MODE)
from strategy import G4v7Strategy

# ── 로그 설정 ──────────────────────────────────────────────────
log_file = os.path.join(os.path.dirname(__file__), 'bingx_bot.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
log = logging.getLogger('BingX')


class BingXBot:

    def __init__(self):
        options = {'defaultType': 'swap'}
        self.exchange = ccxt.bingx({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'options': options,
        })
        if DEMO_MODE:
            self.exchange.set_sandbox_mode(True)  # BingX 데모 서버 사용

        self.strategy  = G4v7Strategy(PARAMS)
        self.positions = []   # 페이퍼/데모 포지션 목록
        self.trade_log = []   # 거래 기록
        self.start_bal = 0.0
        self.trade_cnt = 0

    # ── 연결 ───────────────────────────────────────────────────
    def connect(self) -> bool:
        mode = "📋 데모(가상)" if DEMO_MODE else "💰 실계좌"
        log.info(f"{'='*50}")
        log.info(f" BingX G4v7 Bot  [{mode}]")
        log.info(f" 심볼:{SYMBOL}  타임프레임:{TIMEFRAME}  레버리지:{LEVERAGE}x")
        log.info(f" 주문크기:${ORDER_SIZE}  최대포지션:{MAX_OPEN_POSITIONS}")
        log.info(f"{'='*50}")

        if not API_KEY:
            log.warning("⚠️  API_KEY 없음 — 시세 조회만 가능 (주문 불가)")
            self.start_bal = 50000.0  # 가상 잔고
            return True
        try:
            bal = self.exchange.fetch_balance()
            usdt = float(bal.get('USDT', {}).get('free', 0))
            self.start_bal = usdt
            log.info(f"✅ 연결 성공  잔고: ${usdt:,.2f} USDT")
            if not DEMO_MODE:
                self.exchange.set_leverage(LEVERAGE, SYMBOL)
                log.info(f"✅ 레버리지 {LEVERAGE}x 설정")
            return True
        except Exception as e:
            log.error(f"❌ 연결 실패: {e}")
            log.error("   → config.py 에서 API_KEY / API_SECRET 확인하세요")
            return False

    # ── 캔들 데이터 ────────────────────────────────────────────
    def get_candles(self) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=200)
        df = pd.DataFrame(raw, columns=['ts','open','high','low','close','vol'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        return df.set_index('ts')

    # ── 포지션 수 ──────────────────────────────────────────────
    def pos_count(self) -> int:
        if not API_KEY or DEMO_MODE:
            return len(self.positions)
        try:
            pos = self.exchange.fetch_positions([SYMBOL])
            return sum(1 for p in pos if float(p.get('contracts', 0)) > 0)
        except Exception:
            return 0

    # ── 주문 ───────────────────────────────────────────────────
    def order(self, side: str, price: float, sl: float, tp: float):
        amount = round(ORDER_SIZE * LEVERAGE / price, 4)
        ts_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        icon = "🟢 BUY " if side == 'buy' else "🔴 SELL"

        log.info(f"{icon}  ${price:>10,.2f}  SL=${sl:,.2f}  TP=${tp:,.2f}  {amount}BTC")

        record = {
            'time': ts_str, 'side': side, 'price': price,
            'sl': sl, 'tp': tp, 'amount': amount, 'status': 'OPEN'
        }
        self.trade_log.append(record)
        self.trade_cnt += 1

        if not API_KEY or DEMO_MODE:
            self.positions.append(record)
            return True

        try:
            self.exchange.create_order(SYMBOL, 'market', side, amount)
            opp = 'sell' if side == 'buy' else 'buy'
            self.exchange.create_order(SYMBOL, 'STOP_MARKET', opp, amount,
                params={'stopPrice': sl, 'reduceOnly': True})
            self.exchange.create_order(SYMBOL, 'TAKE_PROFIT_MARKET', opp, amount,
                params={'stopPrice': tp, 'reduceOnly': True})
            return True
        except Exception as e:
            log.error(f"주문 실패: {e}")
            return False

    # ── MaxDD 체크 ─────────────────────────────────────────────
    def is_daily_loss_exceeded(self) -> bool:
        if not API_KEY or DEMO_MODE or self.start_bal == 0:
            return False
        try:
            bal = self.exchange.fetch_balance()
            now = float(bal.get('USDT', {}).get('total', self.start_bal))
            loss = (self.start_bal - now) / self.start_bal * 100
            if loss >= MAX_DAILY_LOSS_PCT:
                log.error(f"🚨 일일 최대 손실 초과! {loss:.1f}% ≥ {MAX_DAILY_LOSS_PCT}%")
                return True
        except Exception:
            pass
        return False

    # ── 거래 요약 ──────────────────────────────────────────────
    def print_summary(self):
        log.info(f"\n{'─'*50}")
        log.info(f" 총 신호: {self.trade_cnt}회")
        if self.trade_log:
            log.info(f" 최근 5건:")
            for t in self.trade_log[-5:]:
                log.info(f"   {t['time']}  {t['side'].upper():4s}  ${t['price']:,.0f}")
        log.info(f"{'─'*50}\n")

    # ── 메인 루프 ──────────────────────────────────────────────
    def run(self):
        if not self.connect():
            return

        check_interval = 30   # 30초마다 신호 체크
        candle_mins    = int(TIMEFRAME.replace('m',''))
        log.info(f"⏱  {candle_mins}분봉 기준  {check_interval}초마다 확인")
        log.info("Ctrl+C 로 종료\n")

        while True:
            try:
                if self.is_daily_loss_exceeded():
                    log.info("오늘 거래 종료. 내일 다시 실행하세요.")
                    break

                df = self.get_candles()
                if len(df) < 100:
                    time.sleep(check_interval)
                    continue

                sig  = self.strategy.get_signal(df)
                n    = self.pos_count()
                now  = datetime.now().strftime('%H:%M:%S')

                # 상태 출력
                line = (f"[{now}] ${sig['price']:>9,.0f} | "
                        f"ADX={sig['adx']:5.1f} | RSI={sig['rsi']:5.1f} | "
                        f"Signal={sig['signal']:4s} | Pos={n}/{MAX_OPEN_POSITIONS}")
                log.info(line)

                # 신호 실행
                if sig['signal'] in ('BUY', 'SELL') and n < MAX_OPEN_POSITIONS:
                    s = 'buy' if sig['signal'] == 'BUY' else 'sell'
                    self.order(s, sig['price'], sig['sl'], sig['tp'])
                    self.print_summary()

                time.sleep(check_interval)

            except KeyboardInterrupt:
                log.info("\n사용자 중단")
                self.print_summary()
                break
            except ccxt.NetworkError as e:
                log.warning(f"네트워크 오류 (재시도): {e}")
                time.sleep(10)
            except Exception as e:
                log.error(f"오류: {e}")
                time.sleep(check_interval)


if __name__ == '__main__':
    BingXBot().run()
