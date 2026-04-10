"""
core/htm_parser.py — EA Auto Master v6.0
=========================================
HTM 백테스트 리포트 파싱. 한글/영문 멀티 레이블 대응.
"""
import re


def parse_htm_report(path):
    """HTM 백테스트 리포트 파싱.
    Returns dict: net_profit, profit_factor, max_drawdown, total_trades,
                  win_rate, return_pct, recovery_factor, rr_ratio
    """
    data = {}
    html = ""
    for enc in ("utf-8", "cp949", "euc-kr", "latin-1"):
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                html = f.read()
            break
        except Exception:
            html = ""
    if not html:
        return data

    label_map = {
        "net_profit":      ["순이익", "Net profit", "Total Net Profit"],
        "profit_factor":   ["손익요인", "Profit factor", "Profit Factor"],
        "max_drawdown":    ["최대하락폭", "Maximal drawdown", "Max drawdown"],
        "total_trades":    ["총 거래수", "Total trades", "Total Trades"],
        "initial_deposit": ["초기자금", "Initial deposit"],
        "win_trades":      ["이익 거래", "Profit trades"],
        "loss_trades":     ["손실 거래", "Loss trades"],
        "avg_profit":      ["평균 이익 거래", "Average profit trade"],
        "avg_loss":        ["평균 손실 거래", "Average loss trade"],
    }

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S | re.I)
    for key, labels in label_map.items():
        for row in rows:
            stripped = re.sub(r'<[^>]+>', ' ', row)
            if any(lb.lower() in stripped.lower() for lb in labels):
                nums = re.findall(r'[-]?\d[\d\s]*[.,]?\d*', stripped)
                for n in nums:
                    try:
                        val = float(n.replace(' ', '').replace(',', '.'))
                        data[key] = val
                        break
                    except ValueError:
                        continue
                if key in data:
                    break

    dep = data.get("initial_deposit", 10000) or 10000
    np_ = data.get("net_profit", 0)
    mdd = data.get("max_drawdown", 0)
    tot = data.get("total_trades", 0)
    win = data.get("win_trades", 0)
    ap = data.get("avg_profit", 0)
    al = abs(data.get("avg_loss", 1) or 1)

    data["return_pct"] = np_ / dep * 100
    data["max_drawdown_pct"] = mdd / dep * 100 if dep else 0
    data["win_rate"] = win / tot * 100 if tot else 0
    data["rr_ratio"] = ap / al if al else 0
    data["recovery_factor"] = np_ / mdd if mdd else 0
    return data
