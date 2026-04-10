"""
gen_ea_detail_html.py
=====================
EA(SC)별 라운드 진행 + 파라미터 변화 + 수익 변화 인터랙티브 HTML 생성
  - 좌측 패널: EA 목록 (SC001~SC050)
  - 우측 패널: 선택한 EA의 BTC/GOLD 라운드별 수익 추이
             + SL/TP 변화 그래프
             + 전체 파라미터 테이블
"""
import json, re, glob, os, subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))


# ── 파서 ─────────────────────────────────────────────────────────────
def parse_htm(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except:
        return None
    m_p  = re.search(r"10000\.00</td>.*?align=right>([\-\d,\.]+)</td>", txt, re.DOTALL)
    m_pf = re.search(r"align=right>([\d\.]+)</td><td>[^<]*</td><td align=right>[\d\.]+</td><td></td><td align=right></td></tr>", txt)
    m_dd = re.search(r"([\d\.]+)%\s*\([\d\.]+\)</td></tr>", txt)
    tds  = re.findall(r"<td[^>]*>\s*([\-\d,\.]+)\s*</td>", txt)
    profit = float(m_p.group(1).replace(",","")) if m_p else 0.0
    pf     = float(m_pf.group(1)) if m_pf else 0.0
    dd_pct = float(m_dd.group(1)) if m_dd else 0.0
    trades = 0
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


def parse_fname(fn):
    def gi(pat, default=0):
        m = re.search(pat, fn)
        return int(m.group(1)) if m else default
    m_sym = re.search(r"_(XAUUSD|BTCUSD|EURUSD|GBPUSD|USDJPY|GBPJPY)_", fn)
    m_rnd = re.search(r"_R(\d+)_", fn)
    if not re.search(r"SC(\d+)", fn) or not m_sym or not m_rnd:
        return None
    return {
        "sc":    gi(r"SC(\d+)"),
        "round": gi(r"_R(\d+)_"),
        "sym":   m_sym.group(1),
        "tf":    re.search(r"_(M\d+|H\d+)_", fn).group(1) if re.search(r"_(M\d+|H\d+)_", fn) else "M5",
        "sl":    gi(r"_SL(\d+)_"),
        "tp":    gi(r"_TP(\d+)_"),
        "atr":   gi(r"_AT(\d+)_"),
        "fm":    gi(r"_FM(\d+)_"),
        "sm":    gi(r"_SM(\d+)_"),
        "adx":   gi(r"_AX(\d+)_"),
        "rl":    gi(r"_RL(\d+)_"),
        "rh":    gi(r"_RH(\d+)_"),
        "dd":    gi(r"_DD(\d+)_"),
        "mp":    gi(r"_MP(\d+)_"),
        "cd":    gi(r"_CD(\d+)_"),
    }


def load_all():
    htm_files = list(set(
        glob.glob(os.path.join(BASE,"reports","**","*.htm"), recursive=True) +
        glob.glob(os.path.join(BASE,"reports","*.htm"))
    ))
    rows = []
    for path in htm_files:
        fn = os.path.basename(path)
        info = parse_fname(fn)
        if not info:
            continue
        p = parse_htm(path)
        if not p:
            continue
        rows.append({**info, **p, "path": path, "fname": fn})
    return rows


# ── HTML 생성 ─────────────────────────────────────────────────────────
def build_html(rows):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # SC별 데이터 구성
    from collections import defaultdict
    sc_data = defaultdict(list)
    for r in rows:
        sc_data[r["sc"]].append(r)

    all_scs  = sorted(sc_data.keys())
    all_rounds = sorted(set(r["round"] for r in rows))

    # JS에 넘길 전체 데이터
    js_data = {}
    for sc, rlist in sc_data.items():
        # 심볼별 분리, 라운드 정렬
        btc  = sorted([r for r in rlist if r["sym"]=="BTCUSD"], key=lambda x: x["round"])
        gold = sorted([r for r in rlist if r["sym"]=="XAUUSD"], key=lambda x: x["round"])
        # 최고수익 (라운드별 최고)
        def best_per_round(lst):
            from collections import defaultdict
            best = {}
            for r in lst:
                k = r["round"]
                if k not in best or r["profit"] > best[k]["profit"]:
                    best[k] = r
            return [best[k] for k in sorted(best.keys())]

        btc_best  = best_per_round(btc)
        gold_best = best_per_round(gold)

        js_data[sc] = {
            "sc": sc,
            "btc":  [{"round":r["round"],"profit":r["profit"],"dd":r["dd_pct"],
                      "pf":r["pf"],"trades":r["trades"],
                      "sl":r["sl"],"tp":r["tp"],"atr":r["atr"],
                      "fm":r["fm"],"sm":r["sm"],"adx":r["adx"],
                      "rl":r["rl"],"rh":r["rh"],"dd_p":r["dd"],"mp":r["mp"],"cd":r["cd"],
                      "path":r.get("path",""), "fname":r.get("fname","")}
                     for r in btc_best],
            "gold": [{"round":r["round"],"profit":r["profit"],"dd":r["dd_pct"],
                      "pf":r["pf"],"trades":r["trades"],
                      "sl":r["sl"],"tp":r["tp"],"atr":r["atr"],
                      "fm":r["fm"],"sm":r["sm"],"adx":r["adx"],
                      "rl":r["rl"],"rh":r["rh"],"dd_p":r["dd"],"mp":r["mp"],"cd":r["cd"],
                      "path":r.get("path",""), "fname":r.get("fname","")}
                     for r in gold_best],
            "all":  [{"round":r["round"],"sym":r["sym"],"profit":r["profit"],
                      "dd":r["dd_pct"],"pf":r["pf"],"trades":r["trades"],
                      "sl":r["sl"],"tp":r["tp"],"atr":r["atr"],"fm":r["fm"],
                      "sm":r["sm"],"adx":r["adx"],"rl":r["rl"],"rh":r["rh"],
                      "dd_p":r["dd"],"mp":r["mp"],"cd":r["cd"],
                      "path":r.get("path",""), "fname":r.get("fname","")}
                     for r in sorted(rlist, key=lambda x: (x["round"],x["sym"]))],
        }

    # SC 목록 사이드바 데이터
    sc_summary = []
    for sc in all_scs:
        rlist = sc_data[sc]
        max_p = max(r["profit"] for r in rlist)
        n_rnd = len(set(r["round"] for r in rlist))
        syms  = sorted(set(r["sym"] for r in rlist))
        sc_summary.append({"sc":sc,"max_profit":max_p,"n_rounds":n_rnd,"syms":syms})

    JS_DATA = json.dumps(js_data, ensure_ascii=False)
    SC_LIST = json.dumps(sc_summary, ensure_ascii=False)
    TOTAL   = len(rows)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>EA별 라운드 성과 분석</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Malgun Gothic',Arial,sans-serif;background:#f0f9ff;color:#0f172a;display:flex;flex-direction:column;height:100vh}}
header{{background:linear-gradient(135deg,#0369a1,#0284c7);color:#fff;padding:14px 20px;flex-shrink:0}}
header h1{{font-size:17px}}
header p{{font-size:11px;opacity:.8;margin-top:3px}}
.main{{display:flex;flex:1;overflow:hidden}}
/* 사이드바 */
.sidebar{{width:200px;background:#1e293b;flex-shrink:0;overflow-y:auto;padding:8px 0}}
.sidebar-title{{color:#94a3b8;font-size:10px;padding:6px 12px;letter-spacing:1px;text-transform:uppercase}}
.sc-item{{padding:7px 12px;cursor:pointer;border-left:3px solid transparent;transition:.1s}}
.sc-item:hover{{background:#334155;color:#e2e8f0}}
.sc-item.active{{background:#0369a1;border-left-color:#7dd3fc;color:#fff}}
.sc-name{{font-size:12px;font-weight:bold}}
.sc-meta{{font-size:10px;color:#94a3b8;margin-top:1px}}
.sc-item.active .sc-meta{{color:#bae6fd}}
/* 메인 패널 */
.panel{{flex:1;overflow-y:auto;padding:16px 20px;display:flex;flex-direction:column;gap:14px}}
.card{{background:#fff;border-radius:8px;padding:16px;box-shadow:0 2px 6px rgba(3,105,161,.1)}}
.card h3{{font-size:13px;color:#0369a1;border-bottom:2px solid #bae6fd;padding-bottom:6px;margin-bottom:12px}}
/* 상단 요약 */
.summary-bar{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:4px}}
.s-item{{background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;padding:8px 14px;min-width:110px}}
.s-num{{font-size:18px;font-weight:bold;color:#0369a1}}
.s-lbl{{font-size:10px;color:#64748b;margin-top:2px}}
/* 차트 행 */
.chart-row{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.chart-box{{position:relative;height:220px}}
.chart-box.tall{{height:260px}}
/* 파라미터 테이블 */
table{{width:100%;border-collapse:collapse;font-size:11.5px}}
thead th{{background:#0369a1;color:#fff;padding:6px 8px;text-align:center;position:sticky;top:0}}
tbody td{{padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center}}
tbody tr:hover td{{background:#f1f5f9}}
.badge{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:bold}}
.btc{{background:#fef3c7;color:#b45309}}
.gold{{background:#ede9fe;color:#5b21b6}}
.pos{{color:#16a34a;font-weight:bold}}
.neg{{color:#dc2626}}
.empty{{color:#94a3b8;text-align:center;padding:40px;font-size:13px}}
/* 파라미터 변화 그리드 */
.param-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin-top:8px}}
.param-card{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:8px}}
.param-name{{font-size:10px;color:#64748b;margin-bottom:4px}}
.param-chart{{position:relative;height:60px}}
</style>
</head>
<body>
<header>
  <h1>EA별 라운드 성과 분석 — 파라미터 변화 추적</h1>
  <p>총 {TOTAL:,}개 백테스트 | SC001~SC{max(all_scs):03d} | 라운드: {', '.join('R'+str(r) for r in all_rounds)}</p>
</header>
<div class="main">

<!-- 사이드바 -->
<div class="sidebar">
  <div class="sidebar-title">EA 목록</div>
  <select id="sortSel" onchange="sortSC()" style="width:calc(100% - 24px);margin:0 12px 8px;padding:4px;background:#334155;color:white;border:none;border-radius:4px;font-size:11px">
    <option value="max_p">최고수익순</option>
    <option value="min_p">최저수익순</option>
    <option value="sc">SC번호순</option>
  </select>
  <div id="sc-list"></div>
</div>

<!-- 메인 패널 -->
<div class="panel" id="panel">
  <div class="empty">← 좌측에서 EA(SC)를 선택하세요</div>
</div>

</div>

<script>
const DATA = {JS_DATA};
let SC_LIST = {SC_LIST};

// 사이드바 렌더링
function renderList(){{
  const el = document.getElementById('sc-list');
  el.innerHTML = '';
  SC_LIST.forEach(sc => {{
    const div = document.createElement('div');
    div.className = 'sc-item';
    div.id = 'sc-'+sc.sc;
    const symsStr = sc.syms.map(s=>s==='XAUUSD'?'GOLD':'BTC').join('/');
    const profStr = sc.max_profit >= 0
      ? '+$'+sc.max_profit.toLocaleString('ko',{{maximumFractionDigits:0}})
      : '-$'+Math.abs(sc.max_profit).toLocaleString('ko',{{maximumFractionDigits:0}});
    div.innerHTML = `<div class="sc-name">SC${{String(sc.sc).padStart(3,'0')}}</div>
      <div class="sc-meta">R${{sc.n_rounds}} | ${{symsStr}}</div>
      <div class="sc-meta" style="color:#${{sc.max_profit>50000?'4ade80':sc.max_profit>0?'fbbf24':'f87171'}}">${{profStr}}</div>`;
    div.onclick = () => selectSC(sc.sc);
    el.appendChild(div);
  }});
}}

// 정렬
function sortSC(){{
  const val = document.getElementById('sortSel').value;
  if(val==='max_p') SC_LIST.sort((a,b)=>b.max_profit - a.max_profit);
  else if(val==='min_p') SC_LIST.sort((a,b)=>a.max_profit - b.max_profit);
  else SC_LIST.sort((a,b)=>a.sc - b.sc);
  renderList();
}}

// 초기화
sortSC();

let charts = [];
function destroyCharts(){{
  charts.forEach(c=>c.destroy());
  charts=[];
}}

function selectSC(sc){{

  // 사이드바 활성화
  document.querySelectorAll('.sc-item').forEach(e=>e.classList.remove('active'));
  const item = document.getElementById('sc-'+sc);
  if(item){{ item.classList.add('active'); item.scrollIntoView({{block:'nearest'}}); }}

  const d = DATA[sc];
  if(!d){{ document.getElementById('panel').innerHTML='<div class="empty">데이터 없음</div>'; return; }}

  destroyCharts();
  const btc  = d.btc  || [];
  const gold = d.gold || [];
  const all  = d.all  || [];

  // 공통 라운드
  const rndSet = [...new Set(all.map(r=>r.round))].sort((a,b)=>a-b);

  // 수익 요약
  const maxBTC  = btc.length  ? Math.max(...btc.map(r=>r.profit))  : null;
  const maxGOLD = gold.length ? Math.max(...gold.map(r=>r.profit)) : null;
  const lastBTC  = btc.length  ? btc[btc.length-1]  : null;
  const lastGOLD = gold.length ? gold[gold.length-1] : null;

  function fmt(n){{ return n==null?'N/A':'$'+n.toLocaleString('ko',{{maximumFractionDigits:0}}); }}

  const panel = document.getElementById('panel');
  panel.innerHTML = `
  <!-- 요약 -->
  <div class="card">
    <h3>SC${{String(sc).padStart(3,'0')}} — 전체 요약</h3>
    <div class="summary-bar">
      <div class="s-item"><div class="s-num">${{rndSet.length}}</div><div class="s-lbl">라운드수</div></div>
      <div class="s-item"><div class="s-num">${{all.length}}</div><div class="s-lbl">총 테스트</div></div>
      <div class="s-item" style="background:#fffbeb;border-color:#fcd34d">
        <div class="s-num" style="color:#b45309">${{fmt(maxBTC)}}</div><div class="s-lbl">BTC 최고수익</div></div>
      <div class="s-item" style="background:#f0f4ff;border-color:#c7d2fe">
        <div class="s-num" style="color:#6366f1">${{fmt(maxGOLD)}}</div><div class="s-lbl">GOLD 최고수익</div></div>
      <div class="s-item"><div class="s-num">${{lastBTC?lastBTC.sl:'N/A'}}</div><div class="s-lbl">최신 SL</div></div>
      <div class="s-item"><div class="s-num">${{lastBTC?lastBTC.tp:'N/A'}}</div><div class="s-lbl">최신 TP</div></div>
    </div>
  </div>

  <!-- 수익 추이 차트 -->
  <div class="card">
    <h3>라운드별 수익 추이 (BTC vs GOLD)</h3>
    <div class="chart-box tall"><canvas id="cProfit"></canvas></div>
  </div>

  <!-- SL/TP 변화 + 수익 상관 -->
  <div class="card">
    <h3>파라미터 변화 — SL / TP / ATR</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="cSLTP"></canvas></div>
      <div class="chart-box"><canvas id="cSlProfit"></canvas></div>
    </div>
  </div>

  <!-- FastMA/SlowMA/ADX 변화 -->
  <div class="card">
    <h3>파라미터 변화 — EMA / ADX / RSI</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="cEMA"></canvas></div>
      <div class="chart-box"><canvas id="cADX"></canvas></div>
    </div>
  </div>

  <!-- DD/PF 변화 -->
  <div class="card">
    <h3>리스크 지표 — DD% / PF</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="cDD"></canvas></div>
      <div class="chart-box"><canvas id="cPF"></canvas></div>
    </div>
  </div>

  <!-- 전체 파라미터 테이블 -->
  <div class="card">
    <h3>전체 파라미터 × 수익 테이블</h3>
    <div style="overflow-x:auto;max-height:400px;overflow-y:auto">
      <table id="tParams"></table>
    </div>
  </div>
  `;

  // ── 차트 생성 ─────────────────────────────────────────────────────
  const btcRnds  = btc.map(r=>'R'+r.round);
  const goldRnds = gold.map(r=>'R'+r.round);

  // 공통 라운드 레이블
  const allRndLabels = [...new Set([...btcRnds,...goldRnds])].sort();

  function getVal(arr, rnd, key){{
    const r = arr.find(x=>'R'+x.round===rnd);
    return r ? r[key] : null;
  }}

  // Chart 1: 수익 추이
  charts.push(new Chart(document.getElementById('cProfit'),{{
    type:'line',
    data:{{
      labels: allRndLabels,
      datasets:[
        {{label:'BTCUSD 수익', data:allRndLabels.map(l=>getVal(btc,l,'profit')),
          borderColor:'#f59e0b',backgroundColor:'#f59e0b22',
          tension:.3,pointRadius:5,pointHoverRadius:7,fill:true}},
        {{label:'XAUUSD 수익', data:allRndLabels.map(l=>getVal(gold,l,'profit')),
          borderColor:'#6366f1',backgroundColor:'#6366f122',
          tension:.3,pointRadius:5,pointHoverRadius:7,fill:true}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},tooltip:{{callbacks:{{label:ctx=>'$'+ctx.raw?.toLocaleString('ko',{{maximumFractionDigits:0}})||'N/A'}}}}}},
      scales:{{y:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}
    }}
  }}));

  // Chart 2: SL/TP 변화 (BTC 기준)
  const src = btc.length ? btc : gold;
  const srcSym = btc.length ? 'BTC' : 'GOLD';
  charts.push(new Chart(document.getElementById('cSLTP'),{{
    type:'line',
    data:{{
      labels: src.map(r=>'R'+r.round),
      datasets:[
        {{label:'SL (×0.01)', data:src.map(r=>r.sl), borderColor:'#ef4444',tension:.3,pointRadius:4,yAxisID:'y'}},
        {{label:'TP (×0.01)', data:src.map(r=>r.tp), borderColor:'#3b82f6',tension:.3,pointRadius:4,yAxisID:'y'}},
        {{label:'ATR기간', data:src.map(r=>r.atr), borderColor:'#10b981',tension:.3,pointRadius:4,yAxisID:'y2',borderDash:[4,3]}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top',labels:{{font:{{size:10}}}}}},title:{{display:true,text:'SL/TP/ATR 파라미터 (${{srcSym}} 기준)'}}}},
      scales:{{y:{{position:'left',title:{{display:true,text:'SL / TP'}}}},
               y2:{{position:'right',title:{{display:true,text:'ATR기간'}},grid:{{display:false}}}}}}
    }}
  }}));

  // Chart 3: SL vs 수익 산점도
  const scatterData = all.map(r=>{{
    return {{x:r.sl, y:r.profit, sym:r.sym, rnd:r.round, tp:r.tp}};
  }});
  charts.push(new Chart(document.getElementById('cSlProfit'),{{
    type:'scatter',
    data:{{
      datasets:[
        {{label:'BTCUSD', data:scatterData.filter(r=>r.sym==='BTCUSD').map(r=>{{return{{x:r.x,y:r.y,tp:r.tp,rnd:r.rnd}}}}) ,
          backgroundColor:'#f59e0baa',pointRadius:5}},
        {{label:'XAUUSD', data:scatterData.filter(r=>r.sym==='XAUUSD').map(r=>{{return{{x:r.x,y:r.y,tp:r.tp,rnd:r.rnd}}}}) ,
          backgroundColor:'#6366f1aa',pointRadius:5}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top',labels:{{font:{{size:10}}}}}},title:{{display:true,text:'SL값 vs 수익 (산점도)'}},
               tooltip:{{callbacks:{{label:ctx=>['SL='+ctx.raw.x,'TP='+ctx.raw.tp,'R'+ctx.raw.rnd,'$'+ctx.raw.y?.toLocaleString()]}}}}}},
      scales:{{x:{{title:{{display:true,text:'SL 값'}}}},y:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}
    }}
  }}));

  // Chart 4: EMA Fast/Slow 변화
  charts.push(new Chart(document.getElementById('cEMA'),{{
    type:'line',
    data:{{
      labels: src.map(r=>'R'+r.round),
      datasets:[
        {{label:'Fast EMA', data:src.map(r=>r.fm), borderColor:'#f59e0b',tension:.3,pointRadius:4}},
        {{label:'Slow EMA', data:src.map(r=>r.sm), borderColor:'#6366f1',tension:.3,pointRadius:4}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top',labels:{{font:{{size:10}}}}}},title:{{display:true,text:'EMA 기간 변화'}}}},
    }}
  }}));

  // Chart 5: ADX Min + RSI 범위 변화
  charts.push(new Chart(document.getElementById('cADX'),{{
    type:'line',
    data:{{
      labels: src.map(r=>'R'+r.round),
      datasets:[
        {{label:'ADX Min', data:src.map(r=>r.adx), borderColor:'#ef4444',tension:.3,pointRadius:4}},
        {{label:'RSI Lower', data:src.map(r=>r.rl), borderColor:'#10b981',tension:.3,pointRadius:4,borderDash:[4,3]}},
        {{label:'RSI Upper', data:src.map(r=>r.rh), borderColor:'#8b5cf6',tension:.3,pointRadius:4,borderDash:[4,3]}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top',labels:{{font:{{size:10}}}}}},title:{{display:true,text:'ADX / RSI 기준 변화'}}}},
    }}
  }}));

  // Chart 6: DD% 추이
  charts.push(new Chart(document.getElementById('cDD'),{{
    type:'line',
    data:{{
      labels: allRndLabels,
      datasets:[
        {{label:'BTC DD%', data:allRndLabels.map(l=>getVal(btc,l,'dd')),
          borderColor:'#f59e0b',backgroundColor:'#f59e0b22',tension:.3,pointRadius:4,fill:true}},
        {{label:'GOLD DD%', data:allRndLabels.map(l=>getVal(gold,l,'dd')),
          borderColor:'#6366f1',backgroundColor:'#6366f122',tension:.3,pointRadius:4,fill:true}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top',labels:{{font:{{size:10}}}}}},title:{{display:true,text:'최대 낙폭(DD%) 변화'}}}},
      scales:{{y:{{ticks:{{callback:v=>v+'%'}}}}}}
    }}
  }}));

  // Chart 7: PF 추이
  charts.push(new Chart(document.getElementById('cPF'),{{
    type:'line',
    data:{{
      labels: allRndLabels,
      datasets:[
        {{label:'BTC PF', data:allRndLabels.map(l=>getVal(btc,l,'pf')),
          borderColor:'#f59e0b',tension:.3,pointRadius:4}},
        {{label:'GOLD PF', data:allRndLabels.map(l=>getVal(gold,l,'pf')),
          borderColor:'#6366f1',tension:.3,pointRadius:4}}
      ]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top',labels:{{font:{{size:10}}}}}},title:{{display:true,text:'이익계수(PF) 변화'}}}},
    }}
  }}));

  const tbl = document.getElementById('tParams');
  tbl.innerHTML = `<thead><tr>
    <th>Round</th><th>심볼</th><th>수익($)</th><th>DD%</th><th>PF</th><th>거래</th>
    <th>SL</th><th>TP</th><th>TP/SL</th><th>ATR</th><th>FastEMA</th><th>SlowEMA</th>
    <th>ADX</th><th>RSI-L</th><th>RSI-H</th><th>MaxDD</th><th>MaxPos</th><th>CD</th>
    <th>파일/리포트</th>
  </tr></thead>`;
  const tbody = document.createElement('tbody');
  all.sort((a,b)=>a.round-b.round||(a.sym>b.sym?1:-1)).forEach(r=>{{
    const tr = document.createElement('tr');
    const pc = r.profit>=0?'pos':'neg';
    const sc2 = r.sym==='BTCUSD'?'btc':'gold';
    const ratio = r.sl>0?(r.tp/r.sl).toFixed(2):'N/A';
    
    let fpath = r.path || "";
    let folderUrl = fpath ? "file:///" + fpath.replace(/\\\\/g, "/").split("/").slice(0,-1).join("/") : "";
    let fileUrl = fpath ? "file:///" + fpath.replace(/\\\\/g, "/") : "";
    let btnHtml = fpath ? `<a href="${{folderUrl}}" target="_blank" style="text-decoration:none;background:#2563eb;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px;margin-right:2px">📂 폴더열기</a>
                           <a href="${{fileUrl}}" target="_blank" style="text-decoration:none;background:#16a34a;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">📄 리포트열기</a>` : '—';
    
    tr.innerHTML = `
      <td>R${{r.round}}</td>
      <td><span class="badge ${{sc2}}">${{r.sym}}</span></td>
      <td class="${{pc}}"><b>$${{r.profit.toLocaleString('ko',{{maximumFractionDigits:0}})}}</b></td>
      <td>${{r.dd.toFixed(1)}}%</td><td>${{r.pf.toFixed(2)}}</td><td>${{r.trades.toLocaleString()}}</td>
      <td><b>${{r.sl}}</b></td><td><b>${{r.tp}}</b></td><td>${{ratio}}</td>
      <td>${{r.atr}}</td><td>${{r.fm}}</td><td>${{r.sm}}</td>
      <td>${{r.adx}}</td><td>${{r.rl}}</td><td>${{r.rh}}</td>
      <td>${{r.dd_p}}</td><td>${{r.mp}}</td><td>${{r.cd}}</td>
      <td>${{btnHtml}}</td>`;
    tbody.appendChild(tr);
  }});
  tbl.appendChild(tbody);
}}

// 처음 SC001 자동 선택
if(SC_LIST.length>0) selectSC(SC_LIST[0].sc);
</script>
</body>
</html>"""


# ── 메인 실행 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("데이터 로딩 중...")
    rows = load_all()
    print(f"총 {len(rows):,}개 로드")

    html = build_html(rows)

    out_dir = os.path.join(BASE, "reports", "performance")
    os.makedirs(out_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"ea_detail_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    sz = os.path.getsize(path)
    print(f"저장: {path}")
    print(f"크기: {sz:,} bytes")

    subprocess.Popen(["cmd", "/c", "start", "", path],
                     creationflags=subprocess.CREATE_NO_WINDOW)
    print("브라우저 오픈 완료")
