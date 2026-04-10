"""
Bitget G4v7 Trading Bot
━━━━━━━━━━━━━━━━━━━━━━━
실행: python bot.py  또는  START_BOT.bat
DEMO_MODE=True  → Bitget 데모 계좌
DEMO_MODE=False → 실계좌
"""
import sys, os, time, logging
from datetime import datetime

_SITE = r'C:\Users\1\AppData\Roaming\Python\Python313\site-packages'
if _SITE not in sys.path:
    sys.path.insert(0, _SITE)

import ccxt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (API_KEY, API_SECRET, API_PASSPHRASE, SYMBOL, TIMEFRAME,
                    LEVERAGE, ORDER_SIZE, PARAMS, MAX_DAILY_LOSS_PCT,
                    MAX_OPEN_POSITIONS, DEMO_MODE)
from strategy import G4v7Strategy

log_file = os.path.join(os.path.dirname(__file__), 'bitget_bot.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
log = logging.getLogger('Bitget')


class BitgetBot:

    def __init__(self):
        self.exchange = ccxt.bitget({
            'apiKey':     API_KEY,
            'secret':     API_SECRET,
            'password':   API_PASSPHRASE,   # Bitget 전용
            'options': {
                'defaultType': 'swap',
                # 데모: Bitget은 별도 데모 URL 사용
                'urls': {
                    'api': {
                        'public':  'https://api.bitget.com',
                        'private': ('https://api.bitget.com' if not DEMO_MODE
                                    else 'https://api.bitget.com'),  # 동일 (데모=가상 잔고 운용)
                    }
                }
            },
        })
        self.strategy  = G4v7Strategy(PARAMS)
        self.positions = []
        self.trade_log = []
        self.start_bal = 0.0
        self.trade_cnt = 0

    def connect(self) -> bool:
        mode = "📋 데모(가상)" if DEMO_MODE else "💰 실계좌"
        log.info(f"{'='*50}")
        log.info(f" Bitget G4v7 Bot  [{mode}]")
        log.info(f" 심볼:{SYMBOL}  TF:{TIMEFRAME}  레버:{LEVERAGE}x")
        log.info(f"{'='*50}")

        if not API_KEY:
            log.warning("⚠️  API_KEY 없음 — 시세만 조회")
            self.start_bal = 50000.0
            return True
        try:
            bal = self.exchange.fetch_balance({'type': 'swap'})
            usdt = float(bal.get('USDT', {}).get('free', 0))
            self.start_bal = usdt
            log.info(f"✅ 연결 성공  잔고: ${usdt:,.2f} USDT")
            if not DEMO_MODE:
                self.exchange.set_leverage(LEVERAGE, SYMBOL,
                    params={'marginCoin': 'USDT', 'holdSide': 'long'})
                log.info(f"✅ 레버리지 {LEVERAGE}x 설정")
            return True
        except Exception as e:
            log.error(f"❌ 연결 실패: {e}")
            return False

    def get_candles(self) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=200,
                                         params={'productType': 'umcbl'})
        df = pd.DataFrame(raw, columns=['ts','open','high','low','close','vol'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        return df.set_index('ts')

    def pos_count(self) -> int:
        if not API_KEY or DEMO_MODE:
            return len(self.positions)
        try:
            pos = self.exchange.fetch_positions([SYMBOL],
                params={'productType': 'umcbl'})
            return sum(1 for p in pos if float(p.get('contracts', 0)) > 0)
        except Exception:
            return 0

    def order(self, side: str, price: float, sl: float, tp: float):
        amount = round(ORDER_SIZE * LEVERAGE / price, 4)
        ts_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        icon   = "🟢 BUY " if side == 'buy' else "🔴 SELL"
        log.info(f"{icon}  ${price:>10,.2f}  SL=${sl:,.2f}  TP=${tp:,.2f}")

        rec = {'time': ts_str, 'side': side, 'price': price,
               'sl': sl, 'tp': tp, 'amount': amount}
        self.trade_log.append(rec)
        self.trade_cnt += 1

        if not API_KEY or DEMO_MODE:
            self.positions.append(rec)
            return True

        try:
            hold = 'long' if side == 'buy' else 'short'
            self.exchange.create_order(
                SYMBOL, 'market', side, amount,
                params={'productType': 'umcbl', 'marginCoin': 'USDT',
                        'tradeSide': 'open', 'holdSide': hold})
            return True
        except Exception as e:
            log.error(f"주문 실패: {e}")
            return False

    def is_daily_loss_exceeded(self) -> bool:
        if not API_KEY or DEMO_MODE or self.start_bal == 0:
            return False
        try:
            bal  = self.exchange.fetch_balance({'type': 'swap'})
            now  = float(bal.get('USDT', {}).get('total', self.start_bal))
            loss = (self.start_bal - now) / self.start_bal * 100
            if loss >= MAX_DAILY_LOSS_PCT:
                log.error(f"🚨 일일 최대 손실 초과! {loss:.1f}%")
                return True
        except Exception:
            pass
        return False

    def run(self):
        if not self.connect():
            return

        log.info(f"⏱  30초마다 신호 확인  (Ctrl+C 종료)\n")

        while True:
            try:
                if self.is_daily_loss_exceeded():
                    break

                df  = self.get_candles()
                sig = self.strategy.get_signal(df)
                n   = self.pos_count()
                now = datetime.now().strftime('%H:%M:%S')

                log.info(f"[{now}] ${sig['price']:>9,.0f} | "
                         f"ADX={sig['adx']:5.1f} | RSI={sig['rsi']:5.1f} | "
                         f"Signal={sig['signal']:4s} | Pos={n}/{MAX_OPEN_POSITIONS}")

                if sig['signal'] in ('BUY','SELL') and n < MAX_OPEN_POSITIONS:
                    s = 'buy' if sig['signal'] == 'BUY' else 'sell'
                    self.order(s, sig['price'], sig['sl'], sig['tp'])

                time.sleep(30)

            except KeyboardInterrupt:
                log.info(f"\n종료  총 신호:{self.trade_cnt}회")
                break
            except Exception as e:
                log.error(f"오류: {e}")
                time.sleep(30)


if __name__ == '__main__':
    BitgetBot().run()
