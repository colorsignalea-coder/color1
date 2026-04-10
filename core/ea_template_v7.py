"""
core/ea_template_v7.py - Stage 1+2: EA MQ4 Code Generator
===========================================================
G4 Trend EA v7 - Multi-parameter version
Parameters: SL, TP, ATR, FastMA, SlowMA, ADX, RSI, MaxDD, MaxPos, CooldownBars (13 total)

Generates .mq4 source string -> compile with MetaEditor -> .ex4 -> backtest
NOTE: Template must be ASCII-only (no Korean/Unicode) for MetaEditor to compile.
"""

_MQ4_TEMPLATE_V7 = """\
//+------------------------------------------------------------------+
//| G4 Trend EA v7 - SC{sc_id:03d} R{round_num}
//| EA_AUTO_MASTER v7.0
//| SL={sl}  TP={tp}  ATR={atr}  FastMA={fast}  SlowMA={slow}
//| ADXPeriod={adx_period}  ADXMin={adx_min}
//| RSIPeriod={rsi_period}  RSILow={rsi_low}  RSIHigh={rsi_high}
//| MaxDD={max_dd}pct  MaxPos={max_pos}  Cooldown={cooldown}bars
//+------------------------------------------------------------------+
#property strict

input double InpLotSize       = 0.1;
input int    InpMagicNumber   = {magic};
input double InpSLMultiplier  = {sl};
input double InpTPMultiplier  = {tp};
input int    InpATRPeriod     = {atr};
input int    InpFastMA        = {fast};
input int    InpSlowMA        = {slow};
input int    InpADXPeriod     = {adx_period};
input double InpADXMin        = {adx_min};
input int    InpRSIPeriod     = {rsi_period};
input double InpRSILower      = {rsi_low};
input double InpRSIUpper      = {rsi_high};
input double InpMaxDD         = {max_dd};
input int    InpMaxPositions  = {max_pos};
input int    InpCooldownBars  = {cooldown};

static datetime g_last_close_time = 0;

int OnInit() {{
   Print("G4v7 SC{sc_id:03d}_R{round_num} Init SL={sl} TP={tp} ADX={adx_min}");
   return INIT_SUCCEEDED;
}}

void OnTick() {{
   static datetime prev_time = 0;
   if (Time[0] == prev_time) return;
   prev_time = Time[0];
   if (Bars < MathMax(InpSlowMA, InpATRPeriod) + 5) return;

   if (InpMaxDD > 0) {{
      double bal = AccountBalance();
      double eq  = AccountEquity();
      if (bal > 0 && (bal - eq) / bal * 100.0 >= InpMaxDD) {{
         CloseAllOrders();
         Print("MaxDD hit");
         return;
      }}
   }}

   if (InpCooldownBars > 0 && g_last_close_time > 0) {{
      int bp = Bars - iBarShift(Symbol(), 0, g_last_close_time, false);
      if (bp < InpCooldownBars) return;
   }}

   if (CountOrders() >= InpMaxPositions) return;

   double atr = iATR(NULL, 0, InpATRPeriod, 1);
   if (atr <= 0) return;

   double mf  = iMA(NULL, 0, InpFastMA, 0, MODE_EMA, PRICE_CLOSE, 1);
   double ms  = iMA(NULL, 0, InpSlowMA, 0, MODE_EMA, PRICE_CLOSE, 1);
   double adx = iADX(NULL, 0, InpADXPeriod, PRICE_CLOSE, MODE_MAIN, 1);
   double rsi = iRSI(NULL, 0, InpRSIPeriod, PRICE_CLOSE, 1);

   bool adx_ok  = (InpADXMin <= 0) || (adx >= InpADXMin);
   bool rsi_buy = (rsi > InpRSILower && rsi < InpRSIUpper);
   bool rsi_sel = (rsi < InpRSIUpper && rsi > InpRSILower);
   double sl_d  = atr * InpSLMultiplier;
   double tp_d  = atr * InpTPMultiplier;

   if (mf > ms && adx_ok && rsi_buy) {{
      double ask = MarketInfo(Symbol(), MODE_ASK);
      OrderSend(Symbol(), OP_BUY,  InpLotSize, ask, 3,
                ask-sl_d, ask+tp_d, "G4v7_{sc_id:03d}", InpMagicNumber, 0, clrBlue);
   }} else if (mf < ms && adx_ok && rsi_sel) {{
      double bid = MarketInfo(Symbol(), MODE_BID);
      OrderSend(Symbol(), OP_SELL, InpLotSize, bid, 3,
                bid+sl_d, bid-tp_d, "G4v7_{sc_id:03d}", InpMagicNumber, 0, clrRed);
   }}
}}

int CountOrders() {{
   int c = 0;
   for (int i = OrdersTotal()-1; i >= 0; i--)
      if (OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         if (OrderSymbol()==Symbol() && OrderMagicNumber()==InpMagicNumber) c++;
   return c;
}}

void CloseAllOrders() {{
   for (int i = OrdersTotal()-1; i >= 0; i--) {{
      if (!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if (OrderSymbol()!=Symbol() || OrderMagicNumber()!=InpMagicNumber) continue;
      if (OrderType()==OP_BUY)  OrderClose(OrderTicket(), OrderLots(), Bid, 3, clrRed);
      if (OrderType()==OP_SELL) OrderClose(OrderTicket(), OrderLots(), Ask, 3, clrBlue);
   }}
   g_last_close_time = Time[0];
}}
"""


def generate_mq4_v7(sc_id: int, round_num: int, params: dict) -> str:
    """
    Generate v7 EA mq4 source from parameter dictionary.

    params keys (defaults used if missing):
      InpSLMultiplier, InpTPMultiplier, InpATRPeriod,
      InpFastMA, InpSlowMA, InpADXPeriod, InpADXMin,
      InpRSIPeriod, InpRSILower, InpRSIUpper,
      InpMaxDD, InpMaxPositions, InpCooldownBars
    """
    magic = 170000 + round_num * 1000 + sc_id

    return _MQ4_TEMPLATE_V7.format(
        sc_id      = sc_id,
        round_num  = round_num,
        magic      = magic,
        sl         = round(params.get('InpSLMultiplier', 0.30),  4),
        tp         = round(params.get('InpTPMultiplier', 10.0),  4),
        atr        = int(params.get('InpATRPeriod',   14)),
        fast       = int(params.get('InpFastMA',       8)),
        slow       = int(params.get('InpSlowMA',      21)),
        adx_period = int(params.get('InpADXPeriod',  14)),
        adx_min    = round(params.get('InpADXMin',   20.0), 1),
        rsi_period = int(params.get('InpRSIPeriod',  14)),
        rsi_low    = round(params.get('InpRSILower', 40.0), 1),
        rsi_high   = round(params.get('InpRSIUpper', 60.0), 1),
        max_dd     = round(params.get('InpMaxDD',    15.0), 1),
        max_pos    = int(params.get('InpMaxPositions', 1)),
        cooldown   = int(params.get('InpCooldownBars', 3)),
    )


def make_ea_filename(sc_id: int, round_num: int, params: dict) -> str:
    """
    Generate EA filename with ALL parameters visible.
    Example: G4v7_SC001_R4_SL024_TP0110_AT14_FM08_SM21_AX20_RL40_RH60_DD15_MP1_CD3
      SL  = InpSLMultiplier x100  (024 = 0.24)
      TP  = InpTPMultiplier x10   (0110 = 11.0)
      AT  = InpATRPeriod
      FM  = InpFastMA
      SM  = InpSlowMA
      AX  = InpADXMin             (integer)
      RL  = InpRSILower           (integer)
      RH  = InpRSIUpper           (integer)
      DD  = InpMaxDD              (integer)
      MP  = InpMaxPositions
      CD  = InpCooldownBars
    """
    sl  = int(round(params.get('InpSLMultiplier', 0.3)  * 100))
    tp  = int(round(params.get('InpTPMultiplier', 10.0) * 10))
    at  = int(params.get('InpATRPeriod',    14))
    fm  = int(params.get('InpFastMA',        8))
    sm  = int(params.get('InpSlowMA',       21))
    ax  = int(round(params.get('InpADXMin', 20.0)))
    rl  = int(round(params.get('InpRSILower', 40.0)))
    rh  = int(round(params.get('InpRSIUpper', 60.0)))
    dd  = int(round(params.get('InpMaxDD',   15.0)))
    mp  = int(params.get('InpMaxPositions',   1))
    cd  = int(params.get('InpCooldownBars',   3))
    return (f"G4v7_SC{sc_id:03d}_R{round_num}"
            f"_SL{sl:03d}_TP{tp:04d}"
            f"_AT{at:02d}_FM{fm:02d}_SM{sm:02d}"
            f"_AX{ax:02d}_RL{rl:02d}_RH{rh:02d}"
            f"_DD{dd:02d}_MP{mp}_CD{cd:02d}")


if __name__ == '__main__':
    test_params = {
        'InpSLMultiplier': 0.2425, 'InpTPMultiplier': 11.9,
        'InpATRPeriod': 14, 'InpFastMA': 8, 'InpSlowMA': 21,
        'InpADXPeriod': 14, 'InpADXMin': 20.0,
        'InpRSIPeriod': 14, 'InpRSILower': 40.0, 'InpRSIUpper': 60.0,
        'InpMaxDD': 15.0, 'InpMaxPositions': 1, 'InpCooldownBars': 3,
    }
    src = generate_mq4_v7(sc_id=1, round_num=1, params=test_params)
    print(src[:500], "...")
    print()
    print("Filename:", make_ea_filename(1, 1, test_params) + ".ex4")
