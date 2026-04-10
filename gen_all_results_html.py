"""
gen_all_results_html.py
=======================
諛깊뀒?ㅽ듃 HTM ?뚯씪 ?꾩껜 ?뚯떛 ???듯빀 ?깃낵 HTML ?앹꽦 ??釉뚮씪?곗? ?ㅽ뵂
"""
import json, re, glob, os
from collections import Counter, defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))

# ?? HTM ?뚯꽌 ????????????????????????????????????????????????????????
def parse_htm(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except:
        return None
    m_profit = re.search(r"10000\.00</td>.*?align=right>([\-\d,\.]+)</td>", txt, re.DOTALL)
    m_pf     = re.search(r"align=right>([\d\.]+)</td><td>[^<]*</td><td align=right>[\d\.]+</td><td></td><td align=right></td></tr>", txt)
    m_dd     = re.search(r"([\d\.]+)%\s*\([\d\.]+\)</td></tr>", txt)
    tds      = re.findall(r"<td[^>]*>\s*([\-\d,\.]+)\s*</td>", txt)
    profit   = float(m_profit.group(1).replace(",","")) if m_profit else 0.0
    pf       = float(m_pf.group(1)) if m_pf else 0.0
    dd_pct   = float(m_dd.group(1)) if m_dd else 0.0
    trades   = 0
    try:
        idx = tds.index("10000.00")
        for i in range(idx+5, min(idx+15, len(tds))):
            v = tds[i]
            if "." not in v and int(v.replace(",","")) > 100:
                trades = int(v.replace(",",""))
                break
    except:
        pass
    return {"profit": profit, "pf": pf, "dd_pct": dd_pct, "trades": trades}


# ?? HTM ?꾩껜 ?섏쭛 ?????????????????????????????????????????????????????
def load_all():
    htm_files = list(set(
        glob.glob(os.path.join(BASE,"reports","**","*.htm"), recursive=True) +
        glob.glob(os.path.join(BASE,"reports","*.htm"))
    ))
    rows = []
    for path in htm_files:
        fn    = os.path.basename(path)
        m_sc  = re.search(r"SC(\d+)", fn)
        m_rnd = re.search(r"_R(\d+)_", fn)
        m_sym = re.search(r"_(XAUUSD|BTCUSD|EURUSD|GBPUSD|USDJPY|GBPJPY)_", fn)
        m_tf  = re.search(r"_(M\d+|H\d+)_", fn)
        if not m_sc or not m_sym:
            continue
        p = parse_htm(path)
        if not p:
            continue
        sym = m_sym.group(1)
        rnd = m_rnd.group(1) if m_rnd else "?"
        sc  = int(m_sc.group(1))
        ea  = fn[:fn.find("_"+sym)]
        rows.append({
            "sc": sc, "round": rnd, "sym": sym,
            "tf": m_tf.group(1) if m_tf else "M5",
            "ea": ea,
            "profit":  p["profit"],
            "dd_pct":  p["dd_pct"],
            "pf":      p["pf"],
            "trades":  p["trades"],
            "path":    path
        })
    return rows


# ?? HTML 鍮뚮뜑 ?????????????????????????????????????????????????????????
COLOR = {
    "XAUUSD": ("#6366f1","#f0f4ff"),
    "BTCUSD": ("#f59e0b","#fffbeb"),
    "EURUSD": ("#16a34a","#f0fdf4"),
    "GBPUSD": ("#0369a1","#eff6ff"),
    "USDJPY": ("#dc2626","#fff1f2"),
    "GBPJPY": ("#7c3aed","#faf5ff"),
}

def avg(data, key):
    return sum(r[key] for r in data) / len(data) if data else 0.0

def sym_card(sym, data):
    bc, bg = COLOR.get(sym, ("#64748b","#f8fafc"))
    top1   = max(data, key=lambda x: x["profit"])
    pos    = sum(1 for r in data if r["profit"] > 0)
    return f"""
    <div class="card" style="border-color:{bc};background:{bg}">
      <div class="card-title" style="color:{bc}">{sym}</div>
      <div class="card-grid">
        <div><span class="lbl">?뚯뒪?몄닔</span><b class="val">{len(data):,}</b></div>
        <div><span class="lbl">?묒옄鍮꾩쑉</span><b class="val">{pos/len(data)*100:.0f}%</b></div>
        <div><span class="lbl">?됯퇏?섏씡</span><b class="val">${avg(data,'profit'):,.0f}</b></div>
        <div><span class="lbl">理쒕??섏씡</span><b class="val">${max(r['profit'] for r in data):,.0f}</b></div>
        <div><span class="lbl">?됯퇏DD</span><b class="val">{avg(data,'dd_pct'):.1f}%</b></div>
        <div><span class="lbl">?됯퇏PF</span><b class="val">{avg(data,'pf'):.2f}</b></div>
        <div><span class="lbl">理쒓퀬EA</span><b class="val" style="font-size:10px">SC{top1['sc']:03d} R{top1['round']}</b></div>
        <div><span class="lbl">理쒓퀬?섏씡EA</span><b class="val" style="font-size:10px">${top1['profit']:,.0f}</b></div>
      </div>
    </div>"""

def round_table(rows, syms, rounds):
    html = """
    <table class="data"><thead><tr>
      <th>Round</th><th>?щ낵</th><th>?뚯뒪?몄닔</th>
      <th>?됯퇏?섏씡</th><th>理쒕??섏씡</th><th>理쒖냼?섏씡</th><th>?됯퇏DD%</th><th>?됯퇏PF</th><th>?묒옄??/th>
    </tr></thead><tbody>"""
    for rnd in rounds:
        for sym in syms:
            data = [r for r in rows if r["round"]==rnd and r["sym"]==sym]
            if not data: continue
            bc, bg = COLOR.get(sym, ("#64748b","#f8fafc"))
            pos = sum(1 for r in data if r["profit"]>0)
            html += f"""
    <tr>
      <td align="center"><b>R{rnd}</b></td>
      <td align="center"><span class="badge" style="background:{bc}22;color:{bc}">{sym}</span></td>
      <td align="center">{len(data):,}</td>
      <td align="right">${avg(data,'profit'):,.0f}</td>
      <td align="right" style="color:#16a34a"><b>${max(r['profit'] for r in data):,.0f}</b></td>
      <td align="right" style="color:#dc2626">${min(r['profit'] for r in data):,.0f}</td>
      <td align="right">{avg(data,'dd_pct'):.1f}%</td>
      <td align="right">{avg(data,'pf'):.2f}</td>
      <td align="right">{pos/len(data)*100:.0f}%</td>
    </tr>"""
    html += "</tbody></table>"
    return html

def sc_compare_table(rows):
    btc_map = {}
    gld_map = {}
    for r in rows:
        k = (r["sc"], r["round"])
        if r["sym"] == "BTCUSD":
            if k not in btc_map or r["profit"] > btc_map[k]["profit"]:
                btc_map[k] = r
        elif r["sym"] == "XAUUSD":
            if k not in gld_map or r["profit"] > gld_map[k]["profit"]:
                gld_map[k] = r
    keys = sorted(set(btc_map) & set(gld_map), key=lambda x: -(btc_map[x]["profit"]+gld_map[x]["profit"]))
    if not keys:
        return "<p style='color:#94a3b8'>怨듯넻 SC횞Round ?놁쓬</p>"
    html = """
    <table class="data"><thead><tr>
      <th>SC</th><th>Round</th>
      <th>BTC ?섏씡</th><th>BTC DD</th><th>BTC PF</th>
      <th>GOLD ?섏씡</th><th>GOLD DD</th><th>GOLD PF</th>
      <th>李⑥씠</th><th>?곗쐞</th>
    </tr></thead><tbody>"""
    for k in keys[:150]:
        b = btc_map[k]; g = gld_map[k]
        diff   = b["profit"] - g["profit"]
        winner = "BTC" if diff > 0 else "GOLD"
        wcol   = "#f59e0b" if winner=="BTC" else "#6366f1"
        html += f"""
    <tr>
      <td align="center"><b>SC{k[0]:03d}</b></td>
      <td align="center">R{k[1]}</td>
      <td align="right" style="color:#b45309">${b['profit']:,.0f}</td>
      <td align="right">{b['dd_pct']:.1f}%</td>
      <td align="right">{b['pf']:.2f}</td>
      <td align="right" style="color:#6366f1">${g['profit']:,.0f}</td>
      <td align="right">{g['dd_pct']:.1f}%</td>
      <td align="right">{g['pf']:.2f}</td>
      <td align="right">${abs(diff):,.0f}</td>
      <td align="center"><b style="color:{wcol}">{winner}</b></td>
    </tr>"""
    html += "</tbody></table>"
    return html

def top_table(rows, n=300):
    top = sorted(rows, key=lambda x: -x["profit"])[:n]
    html = f"""
    <div style="margin-bottom:10px">
        <select id="topSort" onchange="sortTop()" style="padding:4px;font-size:12px">
            <option value="high">최고수익순</option>
            <option value="low">최저수익순</option>
        </select>
    </div>
    <table class="data" id="topTable"><thead><tr>
      <th>#</th><th>SC</th><th>Round</th><th>심볼</th><th>TF</th>
      <th>수익($)</th><th>DD(%)</th><th>PF</th><th>거래</th>
      <th>파일/리포트</th>
    </tr></thead><tbody id="topBody">"""
    for i, r in enumerate(top, 1):
        bc, bg = COLOR.get(r["sym"], ("#64748b","#f8fafc"))
        pcolor = "#16a34a" if r["profit"] > 0 else "#dc2626"
        fpath = r.get("path","")
        folder_url = fpath.replace("\\", "/").rsplit("/", 1)[0] if fpath else ""
        btn_html = f"""<a href="file:///{folder_url}" target="_blank" style="text-decoration:none;background:#2563eb;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px;margin-right:2px">📂 폴더</a>
                       <a href="file:///{fpath.replace('\\','/')}" target="_blank" style="text-decoration:none;background:#16a34a;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">📄 리포트</a>""" if fpath else "—"
        
        html += f"""
    <tr data-profit="{r['profit']}">
      <td align="center" style="color:#94a3b8;font-size:11px">{i}</td>
      <td align="center"><b>SC{r['sc']:03d}</b></td>
      <td align="center">R{r['round']}</td>
      <td align="center"><span class="badge" style="background:{bc}22;color:{bc}">{r['sym']}</span></td>
      <td align="center">{r['tf']}</td>
      <td align="right" style="color:{pcolor}"><b>${r['profit']:,.0f}</b></td>
      <td align="right">{r['dd_pct']:.1f}%</td>
      <td align="right">{r['pf']:.2f}</td>
      <td align="right">{r['trades']:,}</td>
      <td align="center">{btn_html}</td>
    </tr>"""
    html += "</tbody></table>"
    return html


def build_html(rows):
    syms   = sorted(set(r["sym"] for r in rows))
    rounds = sorted(set(r["round"] for r in rows),
                    key=lambda x: f"{int(x):04d}" if x.isdigit() else x)
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ?щ낵蹂?移대뱶
    cards_html = "".join(sym_card(s, [r for r in rows if r["sym"]==s]) for s in syms)

    # 차트 데이터
    rnd_labels, rnd_btc, rnd_gold = [], [], []
    for rnd in [r for r in rounds if r.isdigit()]:
        b = [r["profit"] for r in rows if r["round"]==rnd and r["sym"]=="BTCUSD"]
        g = [r["profit"] for r in rows if r["round"]==rnd and r["sym"]=="XAUUSD"]
        if b or g:
            rnd_labels.append(f"R{rnd}")
            rnd_btc.append(round(avg([{"profit":x} for x in b],"profit"),0) if b else 0)
            rnd_gold.append(round(avg([{"profit":x} for x in g],"profit"),0) if g else 0)

    sc_top = sorted(rows, key=lambda x: -x["profit"])[:25]
    sc_labels  = [f"SC{x['sc']:03d} R{x['round']} {x['sym'][:3]}" for x in sc_top]
    sc_profits = [x["profit"] for x in sc_top]
    sc_colors  = ['"#f59e0b"' if x["sym"]=="BTCUSD" else '"#6366f1"' for x in sc_top]
    all_profits = [r["profit"] for r in rows]

    total    = len(rows)
    pos_cnt  = sum(1 for r in rows if r["profit"] > 0)
    max_prof = max(r["profit"] for r in rows)
    avg_prof = avg(rows, "profit")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EA 諛깊뀒?ㅽ듃 ?꾩껜 ?깃낵 由ы룷????{now[:10]}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Malgun Gothic',Arial,sans-serif;background:#f0f9ff;color:#0f172a}}
header{{background:linear-gradient(135deg,#0369a1,#0284c7);color:#fff;padding:20px 30px}}
header h1{{font-size:22px;margin-bottom:6px}}
header p{{font-size:13px;opacity:.85}}
.container{{max-width:1400px;margin:0 auto;padding:20px 24px}}
.section{{background:#fff;border-radius:10px;padding:20px;margin-bottom:20px;box-shadow:0 2px 8px rgba(3,105,161,.1)}}
.section h2{{font-size:15px;color:#0369a1;border-bottom:2px solid #bae6fd;padding-bottom:8px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}}
.card{{flex:1;min-width:180px;border:2px solid;border-radius:8px;padding:14px}}
.card-title{{font-size:14px;font-weight:bold;margin-bottom:10px}}
.card-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5px}}
.lbl{{font-size:10px;color:#64748b;display:block}}
.val{{font-size:12px;font-weight:bold;display:block}}
table.data{{width:100%;border-collapse:collapse;font-size:12.5px}}
table.data th{{background:#0369a1;color:#fff;padding:8px 10px;position:sticky;top:0}}
table.data td{{padding:6px 10px;border-bottom:1px solid #e2e8f0}}
table.data tr:hover td{{background:#f1f5f9}}
.badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold}}
.chart-wrap{{position:relative;height:300px}}
.tabs{{display:flex;gap:4px;margin-bottom:12px;flex-wrap:wrap}}
.tab{{padding:7px 16px;border-radius:6px 6px 0 0;cursor:pointer;font-size:12px;background:#e2e8f0;color:#475569;border:none;transition:.15s}}
.tab.active{{background:#0369a1;color:#fff}}
.tab-content{{display:none}}
.tab-content.active{{display:block}}
.stat-bar{{display:flex;gap:24px;flex-wrap:wrap;padding:8px 0}}
.stat-num{{font-size:26px;font-weight:bold;color:#0369a1}}
.stat-lbl{{font-size:11px;color:#64748b;margin-top:2px}}
.tbl-scroll{{overflow-x:auto;max-height:500px;overflow-y:auto}}
</style>
</head>
<body>
<header>
  <h1>EA 諛깊뀒?ㅽ듃 ?꾩껜 ?깃낵 由ы룷??/h1>
  <p>?앹꽦: {now} &nbsp;|&nbsp; 珥?<b>{total:,}</b>媛?&nbsp;|&nbsp; ?щ낵: {", ".join(syms)} &nbsp;|&nbsp; ?쇱슫?? {", ".join("R"+r for r in rounds if r.isdigit())}</p>
</header>
<div class="container">

<div class="section">
  <h2>?꾩껜 ?붿빟</h2>
  <div class="stat-bar">
    <div><div class="stat-num">{total:,}</div><div class="stat-lbl">珥??뚯뒪??/div></div>
    <div><div class="stat-num">{len(set(r['sc'] for r in rows))}</div><div class="stat-lbl">EA 醫낅쪟(SC)</div></div>
    <div><div class="stat-num">{len(rounds)}</div><div class="stat-lbl">?쇱슫??/div></div>
    <div><div class="stat-num">{len(syms)}</div><div class="stat-lbl">?듯솕??/div></div>
    <div><div class="stat-num">${max_prof:,.0f}</div><div class="stat-lbl">理쒕? ?섏씡</div></div>
    <div><div class="stat-num">${avg_prof:,.0f}</div><div class="stat-lbl">?됯퇏 ?섏씡</div></div>
    <div><div class="stat-num">{pos_cnt:,}</div><div class="stat-lbl">?묒옄 EA</div></div>
    <div><div class="stat-num">{total-pos_cnt:,}</div><div class="stat-lbl">?곸옄 EA</div></div>
  </div>
</div>

<div class="section">
  <h2>?듯솕?띾퀎 ?붿빟</h2>
  <div class="cards">{cards_html}</div>
</div>

<div class="section">
  <h2>?깃낵 李⑦듃</h2>
  <div class="tabs">
    <button class="tab active" onclick="showTab('t1',this)">?쇱슫?쒕퀎 ?됯퇏?섏씡</button>
    <button class="tab" onclick="showTab('t2',this)">?곸쐞 25 EA</button>
    <button class="tab" onclick="showTab('t3',this)">?섏씡 遺꾪룷</button>
  </div>
  <div id="t1" class="tab-content active">
    <div class="chart-wrap"><canvas id="chart1"></canvas></div>
  </div>
  <div id="t2" class="tab-content">
    <div class="chart-wrap" style="height:420px"><canvas id="chart2"></canvas></div>
  </div>
  <div id="t3" class="tab-content">
    <div class="chart-wrap"><canvas id="chart3"></canvas></div>
  </div>
</div>

<div class="section">
  <h2>?쇱슫??횞 ?듯솕???곸꽭</h2>
  <div class="tbl-scroll">{round_table(rows,syms,rounds)}</div>
</div>

<div class="section">
  <h2>BTC vs GOLD ???숈씪 SC 鍮꾧탳</h2>
  <div class="tbl-scroll">{sc_compare_table(rows)}</div>
</div>

<div class="section">
  <h2>?섏씡 ?곸쐞 300 ?꾩껜 紐⑸줉</h2>
  <div class="tbl-scroll">{top_table(rows,300)}</div>
</div>

<div style="color:#94a3b8;font-size:11px;text-align:right;padding:12px 0">
  EA Auto Master v8.0 ???먮룞 ?앹꽦 &nbsp;|&nbsp; {now}
</div>
</div>

<script>
function showTab(id,btn){{
  document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}
new Chart(document.getElementById('chart1'),{{
  type:'bar',
  data:{{labels:{rnd_labels},datasets:[
    {{label:'BTCUSD',data:{rnd_btc},backgroundColor:'#f59e0b',borderRadius:4}},
    {{label:'XAUUSD',data:{rnd_gold},backgroundColor:'#6366f1',borderRadius:4}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top',labels:{{font:{{size:12}}}}}},
             title:{{display:true,text:'?쇱슫?쒕퀎 BTC/GOLD ?됯퇏?섏씡'}}}},
    scales:{{y:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}
  }}
}});
new Chart(document.getElementById('chart2'),{{
  type:'bar',
  data:{{labels:{sc_labels},datasets:[{{
    label:'?섏씡($)',data:{sc_profits},
    backgroundColor:[{",".join(sc_colors)}],borderRadius:4
  }}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},title:{{display:true,text:'?곸쐞 25 EA ?섏씡'}}}},
    scales:{{x:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}
  }}
}});
const profits={all_profits};
const bins=[-100000,0,10000,30000,60000,100000,150000,200000,300000,500000];
const lbls=bins.slice(0,-1).map((b,i)=>
  (b<0?'?먯떎':'$'+Math.round(b/1000)+'k')+'~'+(bins[i+1]<=0?'0':'$'+Math.round(bins[i+1]/1000)+'k'));
const cnts=bins.slice(0,-1).map((_,i)=>profits.filter(p=>p>=bins[i]&&p<bins[i+1]).length);
new Chart(document.getElementById('chart3'),{{
  type:'bar',
  data:{{labels:lbls,datasets:[{{label:'EA??,data:cnts,backgroundColor:'#0284c7',borderRadius:4}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{title:{{display:true,text:'수익 구간별 EA 분포'}}}},
    scales:{{y:{{beginAtZero:true}}}}
  }}
}});

function sortTop(){{
  const val = document.getElementById('topSort').value;
  const tbody = document.getElementById('topBody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  
  rows.sort((a,b)=>{{
    const pA = parseFloat(a.getAttribute('data-profit'));
    const pB = parseFloat(b.getAttribute('data-profit'));
    return val==='high' ? pB - pA : pA - pB;
  }});
  
  rows.forEach((r,i)=>{{
    r.querySelector('td').innerText = i+1;
    tbody.appendChild(r);
  }});
}}
</script>
</body>
</html>"""


# ?? 硫붿씤 ?ㅽ뻾 ?????????????????????????????????????????????????????????
if __name__ == "__main__":
    print("?곗씠??濡쒕뵫 以?..")
    rows = load_all()
    print(f"珥?{len(rows):,}媛?濡쒕뱶 ?꾨즺")

    syms   = sorted(set(r["sym"] for r in rows))
    rounds = sorted(set(r["round"] for r in rows),
                    key=lambda x: f"{int(x):04d}" if x.isdigit() else x)
    print(f"?щ낵: {syms}")
    print(f"?쇱슫?? {rounds}")

    html = build_html(rows)

    out_dir = os.path.join(BASE, "reports", "performance")
    os.makedirs(out_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"all_results_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(path)
    print(f"??? {path}")
    print(f"?ш린: {size:,} bytes")

    # 釉뚮씪?곗? ?ㅽ뵂
    import subprocess
    subprocess.Popen(["cmd", "/c", "start", "", path],
                     creationflags=subprocess.CREATE_NO_WINDOW)
    print("釉뚮씪?곗? ?ㅽ뵂 ?꾨즺")

