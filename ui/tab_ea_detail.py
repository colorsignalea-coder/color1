"""
ui/tab_ea_detail.py — EA Auto Master v7.0
==========================================
EA별 라운드 성과 + 파라미터 변화 추적 탭
  - 좌측: SC 목록 (최고수익 기준 정렬)
  - 우측: 선택 EA의 BTC/GOLD 수익 추이 + SL/TP/EMA/ADX 변화 차트
  - HTML 내보내기 → reports/performance/ea_detail_YYYYMMDD.html
"""

import base64
import glob
import io
import json
import os
import re
import subprocess
import threading
import tkinter as tk
from collections import defaultdict
from datetime import datetime
from tkinter import messagebox, ttk

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from ui.theme import BG, FG, PANEL, PANEL2, BLUE, GREEN, TEAL, AMBER, RED, B, LBL, TITLE, MONO

_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(_BASE, "reports", "performance")


# ── HTM 파서 ─────────────────────────────────────────────────────────
def _parse_htm(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except Exception:
        return None
    m_p  = re.search(r"10000\.00</td>.*?align=right>([\-\d,\.]+)</td>", txt, re.DOTALL)
    m_pf = re.search(r"align=right>([\d\.]+)</td><td>[^<]*</td><td align=right>[\d\.]+</td><td></td><td align=right></td></tr>", txt)
    m_dd = re.search(r"([\d\.]+)%\s*\([\d\.]+\)</td></tr>", txt)
    tds  = re.findall(r"<td[^>]*>\s*([\-\d,\.]+)\s*</td>", txt)
    profit = float(m_p.group(1).replace(",", "")) if m_p else 0.0
    pf     = float(m_pf.group(1)) if m_pf else 0.0
    dd_pct = float(m_dd.group(1)) if m_dd else 0.0
    trades = 0
    try:
        idx = tds.index("10000.00")
        for i in range(idx + 5, min(idx + 15, len(tds))):
            v = tds[i]
            if "." not in v and int(v.replace(",", "")) > 100:
                trades = int(v.replace(",", ""))
                break
    except Exception:
        pass
    return {"profit": profit, "pf": pf, "dd_pct": dd_pct, "trades": trades}


def _gi(pat, s, d=0):
    m = re.search(pat, s)
    return int(m.group(1)) if m else d


def _parse_fname(fn):
    m_sym = re.search(r"_(XAUUSD|BTCUSD|EURUSD|GBPUSD|USDJPY|GBPJPY)_", fn)
    m_rnd = re.search(r"_R(\d+)_", fn)
    if not re.search(r"SC(\d+)", fn) or not m_sym or not m_rnd:
        return None
    m_tf = re.search(r"_(M\d+|H\d+)_", fn)
    return {
        "sc":    _gi(r"SC(\d+)", fn),
        "round": _gi(r"_R(\d+)_", fn),
        "sym":   m_sym.group(1),
        "tf":    m_tf.group(1) if m_tf else "M5",
        "sl":    _gi(r"_SL(\d+)_", fn),
        "tp":    _gi(r"_TP(\d+)_", fn),
        "atr":   _gi(r"_AT(\d+)_", fn),
        "fm":    _gi(r"_FM(\d+)_", fn),
        "sm":    _gi(r"_SM(\d+)_", fn),
        "adx":   _gi(r"_AX(\d+)_", fn),
        "rl":    _gi(r"_RL(\d+)_", fn),
        "rh":    _gi(r"_RH(\d+)_", fn),
        "dd_p":  _gi(r"_DD(\d+)_", fn),
        "mp":    _gi(r"_MP(\d+)_", fn),
        "cd":    _gi(r"_CD(\d+)_", fn),
    }


def _load_all():
    htm_files = list(set(
        glob.glob(os.path.join(_BASE, "reports", "**", "*.htm"), recursive=True) +
        glob.glob(os.path.join(_BASE, "reports", "*.htm"))
    ))
    rows = []
    for path in htm_files:
        fn   = os.path.basename(path)
        info = _parse_fname(fn)
        if not info:
            continue
        p = _parse_htm(path)
        if not p:
            continue
        rows.append({**info, **p})
    return rows


def build_html(rows):
    """rows(_load_all 결과) → 인터랙티브 HTML 문자열 반환 (tkinter 불필요)"""
    from collections import defaultdict
    sc_data = defaultdict(list)
    for r in rows:
        sc_data[r["sc"]].append(r)
    all_scs = sorted(sc_data.keys())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    js_sc = {}
    for sc, rlist in sc_data.items():
        btc  = _best_per_round([r for r in rlist if r["sym"] == "BTCUSD"])
        gold = _best_per_round([r for r in rlist if r["sym"] == "XAUUSD"])
        js_sc[sc] = {
            "btc":  [{"r": r["round"], "profit": r["profit"], "dd": r["dd_pct"],
                      "pf": r["pf"], "sl": r["sl"], "tp": r["tp"], "atr": r["atr"],
                      "fm": r["fm"], "sm": r["sm"], "adx": r["adx"],
                      "rl": r["rl"], "rh": r["rh"]} for r in btc],
            "gold": [{"r": r["round"], "profit": r["profit"], "dd": r["dd_pct"],
                      "pf": r["pf"], "sl": r["sl"], "tp": r["tp"], "atr": r["atr"],
                      "fm": r["fm"], "sm": r["sm"], "adx": r["adx"],
                      "rl": r["rl"], "rh": r["rh"]} for r in gold],
            "all":  sorted([{"r": r["round"], "sym": r["sym"], "profit": r["profit"],
                              "dd": r["dd_pct"], "pf": r["pf"], "trades": r["trades"],
                              "sl": r["sl"], "tp": r["tp"], "atr": r["atr"],
                              "fm": r["fm"], "sm": r["sm"], "adx": r["adx"],
                              "rl": r["rl"], "rh": r["rh"],
                              "mp": r["mp"], "cd": r["cd"]} for r in rlist],
                            key=lambda x: (x["r"], x["sym"])),
            "max_btc":  max((r["profit"] for r in btc),  default=0),
            "max_gold": max((r["profit"] for r in gold), default=0),
            "n_rnd":    len(set(r["round"] for r in rlist)),
            "n_test":   len(rlist),
        }

    sc_list = [{"sc": sc,
                "max_p": max(r["profit"] for r in sc_data[sc]),
                "n_rnd": len(set(r["round"] for r in sc_data[sc]))}
               for sc in all_scs]

    JS_DATA = json.dumps(js_sc, ensure_ascii=False)
    SC_LIST = json.dumps(sc_list, ensure_ascii=False)
    TOTAL   = len(rows)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>EA별 라운드 성과 분석 — {now[:10]}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Malgun Gothic',Arial,sans-serif;background:#f0f9ff;color:#0f172a;display:flex;flex-direction:column;height:100vh}}
header{{background:linear-gradient(135deg,#0369a1,#0284c7);color:#fff;padding:14px 20px;flex-shrink:0}}
header h1{{font-size:17px}} header p{{font-size:11px;opacity:.8;margin-top:3px}}
.main{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:190px;background:#1e293b;flex-shrink:0;overflow-y:auto;padding:6px 0}}
.sidebar input{{width:calc(100% - 12px);margin:4px 6px;padding:4px 8px;background:#334155;border:none;color:white;border-radius:4px;font-size:11px}}
.sc-item{{padding:7px 10px;cursor:pointer;border-left:3px solid transparent;transition:.1s}}
.sc-item:hover{{background:#334155}}
.sc-item.active{{background:#0369a1;border-left-color:#7dd3fc}}
.sc-name{{font-size:12px;font-weight:bold;color:#e2e8f0}}
.sc-meta{{font-size:10px;color:#94a3b8;margin-top:2px}}
.sc-item.active .sc-meta{{color:#bae6fd}}
.panel{{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}}
.card{{background:#fff;border-radius:8px;padding:14px;box-shadow:0 2px 6px rgba(3,105,161,.1)}}
.card h3{{font-size:13px;color:#0369a1;border-bottom:2px solid #bae6fd;padding-bottom:6px;margin-bottom:10px}}
.sum-bar{{display:flex;gap:14px;flex-wrap:wrap}}
.s-item{{background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;padding:8px 12px}}
.s-num{{font-size:18px;font-weight:bold;color:#0369a1}}
.s-lbl{{font-size:10px;color:#64748b;margin-top:2px}}
.chart-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.param-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:8px;margin-top:4px}}
.param-box{{border:1px solid #e2e8f0;border-radius:7px;padding:10px 12px;background:#fafafa;transition:.2s}}
.param-box.sup{{background:#f0fdf4;border-color:#86efac}}
.param-box.sdn{{background:#fef2f2;border-color:#fca5a5}}
.param-box.wk{{background:#fffbeb;border-color:#fde68a}}
.param-name{{font-size:11px;color:#64748b;margin-bottom:3px;font-weight:bold}}
.param-arrow{{font-size:22px;line-height:1}}
.param-corr{{font-size:11px;color:#64748b;margin-top:2px}}
.param-verdict{{font-size:11px;font-weight:bold;margin-top:5px;padding:2px 8px;border-radius:4px;display:inline-block}}
.vup{{background:#dcfce7;color:#15803d}}
.vdn{{background:#fee2e2;color:#b91c1c}}
.vno{{background:#f1f5f9;color:#64748b}}
.overall{{background:linear-gradient(135deg,#f0f9ff,#e0f2fe);border:2px solid #0369a1;border-radius:8px;padding:16px;margin-top:4px}}
.overall-ttl{{font-size:14px;font-weight:bold;color:#0369a1;margin-bottom:10px}}
.overall-txt{{font-size:12px;line-height:2;color:#0f172a}}
.tag{{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:bold;margin:2px 1px}}
.tup{{background:#dcfce7;color:#15803d}}
.tdn{{background:#fee2e2;color:#b91c1c}}
.tok{{background:#dbeafe;color:#1d4ed8}}
.twa{{background:#fef3c7;color:#92400e}}
.chart-box{{position:relative;height:220px}}
table{{width:100%;border-collapse:collapse;font-size:11.5px}}
thead th{{background:#0369a1;color:#fff;padding:6px 8px;position:sticky;top:0;z-index:1}}
tbody td{{padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center}}
tbody tr:hover td{{background:#f1f5f9}}
.badge{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:bold}}
.btc{{background:#fef3c7;color:#b45309}} .gld{{background:#ede9fe;color:#5b21b6}}
.pos{{color:#16a34a;font-weight:bold}} .neg{{color:#dc2626;font-weight:bold}}
.tbl-scroll{{overflow-x:auto;max-height:340px;overflow-y:auto}}
</style>
</head>
<body>
<header>
  <h1>EA별 라운드 성과 분석 — 파라미터 변화 추적</h1>
  <p>생성: {now} &nbsp;|&nbsp; EA {len(all_scs)}종 &nbsp;|&nbsp; 총 {TOTAL:,}개 백테스트</p>
</header>
<div class="main">
<div class="sidebar">
  <input id="srch" placeholder="SC 검색..." oninput="filterList(this.value)">
  <div id="sc-list"></div>
</div>
<div class="panel" id="panel">
  <div style="color:#94a3b8;padding:40px;text-align:center">← 좌측에서 EA를 선택하세요</div>
</div>
</div>
<script>
const DATA={JS_DATA};
const ALL_SC={SC_LIST};
let charts=[],curList=ALL_SC.slice();
function killCharts(){{charts.forEach(c=>c.destroy());charts=[];}}
function getVal(arr,rnd,key){{const r=arr.find(x=>x.r===rnd);return r!=null?r[key]:null;}}

function buildList(list){{
  const el=document.getElementById('sc-list');el.innerHTML='';
  list.forEach(s=>{{
    const d=document.createElement('div');d.className='sc-item';d.id='si-'+s.sc;
    const pc=s.max_p>50000?'#4ade80':s.max_p>0?'#fbbf24':'#f87171';
    d.innerHTML=`<div class="sc-name">SC${{String(s.sc).padStart(3,'0')}}</div>
      <div class="sc-meta">R${{s.n_rnd}} | <span style="color:${{pc}}">$${{Math.round(s.max_p).toLocaleString()}}</span></div>`;
    d.onclick=()=>selectSC(s.sc);el.appendChild(d);
  }});
}}
buildList(curList);
function filterList(q){{
  q=q.toUpperCase();
  curList=ALL_SC.filter(s=>('SC'+String(s.sc).padStart(3,'0')).includes(q));
  buildList(curList);
}}

function selectSC(sc){{
  document.querySelectorAll('.sc-item').forEach(e=>e.classList.remove('active'));
  const el=document.getElementById('si-'+sc);
  if(el){{el.classList.add('active');el.scrollIntoView({{block:'nearest'}});}}
  killCharts();
  const d=DATA[sc];if(!d)return;
  const btc=d.btc||[],gold=d.gold||[],all=d.all||[];
  const src=btc.length?btc:gold;
  const rnds=[...new Set([...btc.map(r=>r.r),...gold.map(r=>r.r)])].sort((a,b)=>a-b);
  const xlbls=rnds.map(r=>'R'+r),sx=src.map(r=>'R'+r.r);

  document.getElementById('panel').innerHTML=`
  <div class="card">
    <h3>SC${{String(sc).padStart(3,'0')}} — 요약</h3>
    <div class="sum-bar">
      <div class="s-item"><div class="s-num">${{d.n_rnd}}</div><div class="s-lbl">라운드수</div></div>
      <div class="s-item"><div class="s-num">${{d.n_test}}</div><div class="s-lbl">총 테스트</div></div>
      <div class="s-item" style="background:#fffbeb;border-color:#fcd34d">
        <div class="s-num" style="color:#b45309">$${{Math.round(d.max_btc).toLocaleString()}}</div>
        <div class="s-lbl">BTC 최고수익</div></div>
      <div class="s-item" style="background:#f0f4ff;border-color:#c7d2fe">
        <div class="s-num" style="color:#6366f1">$${{Math.round(d.max_gold).toLocaleString()}}</div>
        <div class="s-lbl">GOLD 최고수익</div></div>
      <div class="s-item"><div class="s-num">${{src.length?src[src.length-1].sl:'—'}}</div><div class="s-lbl">최신 SL</div></div>
      <div class="s-item"><div class="s-num">${{src.length?src[src.length-1].tp:'—'}}</div><div class="s-lbl">최신 TP</div></div>
    </div>
    <div id="overall-box" style="margin-top:10px"></div>
  </div>
  <div class="card" id="param-card">
    <h3>파라미터 방향 분석 — 수익 영향도</h3>
    <div id="param-analysis"></div>
  </div>
  <div class="card">
    <h3>라운드별 수익 추이 (BTC vs GOLD)</h3>
    <div class="chart-box" style="height:260px"><canvas id="c1"></canvas></div>
  </div>
  <div class="card">
    <h3>SL / TP 변화</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="c2"></canvas></div>
      <div class="chart-box"><canvas id="c3"></canvas></div>
    </div>
  </div>
  <div class="card">
    <h3>EMA / ADX 파라미터 변화</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="c4"></canvas></div>
      <div class="chart-box"><canvas id="c5"></canvas></div>
    </div>
  </div>
  <div class="card">
    <h3>리스크 지표 — DD% / PF 변화</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="c6"></canvas></div>
      <div class="chart-box"><canvas id="c7"></canvas></div>
    </div>
  </div>
  <div class="card">
    <h3>전체 파라미터 × 수익 테이블</h3>
    <div class="tbl-scroll">
      <table><thead><tr>
        <th>R</th><th>심볼</th><th>수익($)</th><th>DD%</th><th>PF</th><th>거래</th>
        <th>SL</th><th>TP</th><th>TP/SL</th><th>ATR</th><th>FastEMA</th><th>SlowEMA</th>
        <th>ADX</th><th>RSI-L</th><th>RSI-H</th><th>MaxPos</th><th>CD</th>
      </tr></thead><tbody id="tbd"></tbody></table>
    </div>
  </div>`;

  charts.push(new Chart(document.getElementById('c1'),{{type:'line',data:{{labels:xlbls,datasets:[
    {{label:'BTCUSD',data:rnds.map(r=>getVal(btc,r,'profit')),borderColor:'#f59e0b',backgroundColor:'#f59e0b22',tension:.3,pointRadius:5,fill:true,spanGaps:true}},
    {{label:'XAUUSD',data:rnds.map(r=>getVal(gold,r,'profit')),borderColor:'#6366f1',backgroundColor:'#6366f122',tension:.3,pointRadius:5,fill:true,spanGaps:true}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'top'}}}},
    scales:{{y:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}}}}}));

  charts.push(new Chart(document.getElementById('c2'),{{type:'line',data:{{labels:sx,datasets:[
    {{label:'SL',data:src.map(r=>r.sl),borderColor:'#ef4444',tension:.3,pointRadius:5,pointHoverRadius:7}},
    {{label:'TP',data:src.map(r=>r.tp),borderColor:'#3b82f6',tension:.3,pointRadius:5,pointHoverRadius:7}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}},title:{{display:true,text:'SL / TP 값 변화'}}}}}}}}));

  charts.push(new Chart(document.getElementById('c3'),{{type:'scatter',data:{{datasets:[
    {{label:'BTC',data:all.filter(r=>r.sym==='BTCUSD').map(r=>{{return{{x:r.sl,y:r.profit,tp:r.tp,rnd:r.r}}}}),backgroundColor:'#f59e0baa',pointRadius:6}},
    {{label:'GOLD',data:all.filter(r=>r.sym==='XAUUSD').map(r=>{{return{{x:r.sl,y:r.profit,tp:r.tp,rnd:r.r}}}}),backgroundColor:'#6366f1aa',pointRadius:6}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}},title:{{display:true,text:'SL값 vs 수익 분포'}},
             tooltip:{{callbacks:{{label:ctx=>`R${{ctx.raw.rnd}} SL=${{ctx.raw.x}} TP=${{ctx.raw.tp}} → $${{ctx.raw.y?.toLocaleString()}}`}}}}}},
    scales:{{x:{{title:{{display:true,text:'SL'}}}},y:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}}}}}));

  charts.push(new Chart(document.getElementById('c4'),{{type:'line',data:{{labels:sx,datasets:[
    {{label:'Fast EMA',data:src.map(r=>r.fm),borderColor:'#f59e0b',tension:.3,pointRadius:4}},
    {{label:'Slow EMA',data:src.map(r=>r.sm),borderColor:'#6366f1',tension:.3,pointRadius:4}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}},title:{{display:true,text:'EMA 기간 변화'}}}}}}}}));

  charts.push(new Chart(document.getElementById('c5'),{{type:'line',data:{{labels:sx,datasets:[
    {{label:'ADX Min',data:src.map(r=>r.adx),borderColor:'#ef4444',tension:.3,pointRadius:4}},
    {{label:'RSI Lower',data:src.map(r=>r.rl),borderColor:'#10b981',tension:.3,pointRadius:4,borderDash:[4,3]}},
    {{label:'RSI Upper',data:src.map(r=>r.rh),borderColor:'#8b5cf6',tension:.3,pointRadius:4,borderDash:[4,3]}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}},title:{{display:true,text:'ADX / RSI 기준 변화'}}}}}}}}));

  charts.push(new Chart(document.getElementById('c6'),{{type:'line',data:{{labels:xlbls,datasets:[
    {{label:'BTC DD%',data:rnds.map(r=>getVal(btc,r,'dd')),borderColor:'#f59e0b',tension:.3,pointRadius:4,spanGaps:true}},
    {{label:'GOLD DD%',data:rnds.map(r=>getVal(gold,r,'dd')),borderColor:'#6366f1',tension:.3,pointRadius:4,spanGaps:true}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}},title:{{display:true,text:'최대 낙폭 DD% 변화'}}}},
    scales:{{y:{{ticks:{{callback:v=>v+'%'}}}}}}}}}}));

  charts.push(new Chart(document.getElementById('c7'),{{type:'line',data:{{labels:xlbls,datasets:[
    {{label:'BTC PF',data:rnds.map(r=>getVal(btc,r,'pf')),borderColor:'#f59e0b',tension:.3,pointRadius:4,spanGaps:true}},
    {{label:'GOLD PF',data:rnds.map(r=>getVal(gold,r,'pf')),borderColor:'#6366f1',tension:.3,pointRadius:4,spanGaps:true}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top'}},title:{{display:true,text:'이익계수 PF 변화'}}}}}}}}));

  const tbody=document.getElementById('tbd');tbody.innerHTML='';
  all.sort((a,b)=>a.r-b.r||(a.sym>b.sym?1:-1)).forEach(r=>{{
    const tr=document.createElement('tr');
    const bc=r.sym==='BTCUSD'?'btc':'gld';
    const pc=r.profit>=0?'pos':'neg';
    const ratio=r.sl>0?(r.tp/r.sl).toFixed(2):'—';
    tr.innerHTML=`<td>R${{r.r}}</td><td><span class="badge ${{bc}}">${{r.sym}}</span></td>
      <td class="${{pc}}"><b>$${{Math.round(r.profit).toLocaleString()}}</b></td>
      <td>${{r.dd.toFixed(1)}}%</td><td>${{r.pf.toFixed(2)}}</td><td>${{(r.trades||0).toLocaleString()}}</td>
      <td><b>${{r.sl}}</b></td><td><b>${{r.tp}}</b></td><td>${{ratio}}</td>
      <td>${{r.atr}}</td><td>${{r.fm}}</td><td>${{r.sm}}</td>
      <td>${{r.adx}}</td><td>${{r.rl}}</td><td>${{r.rh}}</td><td>${{r.mp}}</td><td>${{r.cd}}</td>`;
    tbody.appendChild(tr);
  }});

  // ── 파라미터 방향 분석 ────────────────────────────────────────────
  analyzeParams(all, src);
}}

// Pearson 상관계수
function pearson(xs,ys){{
  const n=xs.length;if(n<3)return 0;
  const mx=xs.reduce((a,b)=>a+b,0)/n, my=ys.reduce((a,b)=>a+b,0)/n;
  let num=0,dx2=0,dy2=0;
  for(let i=0;i<n;i++){{
    const dx=xs[i]-mx,dy=ys[i]-my;
    num+=dx*dy; dx2+=dx*dx; dy2+=dy*dy;
  }}
  return (dx2&&dy2)?num/Math.sqrt(dx2*dy2):0;
}}

function analyzeParams(all, src){{
  // 파라미터 목록 & 설명
  const PARAMS=[
    {{key:'sl', name:'SL (손절 배수)', desc:'클수록 손절을 넓게 설정'}},
    {{key:'tp', name:'TP (익절 배수)', desc:'클수록 목표수익 높게 설정'}},
    {{key:'atr', name:'ATR 기간',    desc:'변동성 측정 기간'}},
    {{key:'fm', name:'Fast EMA',    desc:'빠른 이동평균 기간'}},
    {{key:'sm', name:'Slow EMA',    desc:'느린 이동평균 기간'}},
    {{key:'adx', name:'ADX 최소값', desc:'추세 강도 필터 기준'}},
    {{key:'rl', name:'RSI 하한',    desc:'매수 허용 RSI 하한선'}},
    {{key:'rh', name:'RSI 상한',    desc:'매수 허용 RSI 상한선'}},
    {{key:'mp', name:'최대 포지션', desc:'동시 오픈 가능 주문 수'}},
    {{key:'cd', name:'쿨다운 봉수', desc:'신호 후 대기 캔들 수'}},
  ];

  // 전체(BTC+GOLD) 기준 상관 계산
  const profits=all.map(r=>r.profit);
  const corrs={{}};
  PARAMS.forEach(p=>{{
    const xs=all.map(r=>r[p.key]||0);
    corrs[p.key]=pearson(xs,profits);
  }});

  // 라운드 진행 방향 (src 기준, 최소 2라운드)
  const dirs={{}};
  if(src.length>=2){{
    const last=src[src.length-1], prev=src[src.length-2];
    PARAMS.forEach(p=>{{
      const delta=last[p.key]-prev[p.key];
      dirs[p.key]=delta>0?1:delta<0?-1:0;
    }});
  }}

  // 판정 로직
  // corr>0.15 → param↑ 수익↑ / corr<-0.15 → param↑ 수익↓
  // 현재 방향이 상관 방향과 같으면 "올바른 방향", 다르면 "역방향"
  function verdict(corr, dir){{
    const strong=Math.abs(corr)>0.25, weak=Math.abs(corr)>0.1;
    if(!weak)return {{cls:'vno',txt:'영향 미미',icon:'➖'}};
    const correct=(corr>0&&dir>0)||(corr<0&&dir<0);
    const neutral=dir===0;
    if(neutral)return {{cls:'vno',txt:'유지 중',icon:'⏸'}};
    if(correct)return {{cls:'vup',txt:strong?'✅ 수익 증가 예상':'↗ 증가 가능성',icon:''}};
    return {{cls:'vdn',txt:strong?'⚠️ 수익 감소 주의':'↘ 감소 가능성',icon:''}};
  }}

  // 파라미터 카드 생성
  let gridHtml='';
  const insights=[]; // 종합 평가용
  PARAMS.forEach(p=>{{
    const c=corrs[p.key], dir=dirs[p.key]??0;
    const dirArrow=dir>0?'▲':dir<0?'▽':'━';
    const dirCol=dir>0?'#16a34a':dir<0?'#dc2626':'#94a3b8';
    const corrDir=c>0.1?'↑ 수익 증가':c<-0.1?'↓ 수익 감소':'≈ 영향 작음';
    const corrBar=Math.round(Math.abs(c)*100);
    const boxCls=Math.abs(c)>0.25?(c>0?'sup':'sdn'):'wk';
    const vd=verdict(c,dir);
    gridHtml+=`
    <div class="param-box ${{boxCls}}">
      <div class="param-name">${{p.name}}</div>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="param-arrow" style="color:${{dirCol}}">${{dirArrow}}</span>
        <div>
          <div style="font-size:11px;color:#475569">상관 <b>${{c>=0?'+':''}}${{c.toFixed(2)}}</b>  ${{corrDir}}</div>
          <div style="font-size:10px;color:#94a3b8">${{p.desc}}</div>
        </div>
      </div>
      <span class="param-verdict ${{vd.cls}}">${{vd.txt}}</span>
    </div>`;
    if(Math.abs(c)>0.15)insights.push({{key:p.name,c,dir,vd}});
  }});
  document.getElementById('param-analysis').innerHTML=
    '<div class="param-grid">'+gridHtml+'</div>';

  // 종합 평가 박스
  const last2=src.length>=1?src[src.length-1]:null;
  const lastProfit=last2?last2.profit:0;
  const trending=src.length>=2?src[src.length-1].profit-src[src.length-2].profit:0;
  const trendTxt=trending>0
    ?`<span class="tag tup">▲ 수익 증가 추세 (+$${{Math.round(trending).toLocaleString()}})</span>`
    :trending<0
    ?`<span class="tag tdn">▼ 수익 감소 추세 ($${{Math.round(trending).toLocaleString()}})</span>`
    :`<span class="tag tok">━ 횡보</span>`;

  // 강한 상관 파라미터 요약
  const goodOnes=insights.filter(i=>{{
    const correct=(i.c>0&&i.dir>0)||(i.c<0&&i.dir<0);
    return correct&&i.dir!==0;
  }});
  const badOnes=insights.filter(i=>{{
    const correct=(i.c>0&&i.dir>0)||(i.c<0&&i.dir<0);
    return !correct&&i.dir!==0;
  }});

  let overallHtml=`<div class="overall">
  <div class="overall-ttl">종합 평가 — 현재 방향 진단</div>
  <div class="overall-txt">`;

  overallHtml+=`최근 라운드 수익: <b>$${{Math.round(lastProfit).toLocaleString()}}</b>  &nbsp; 추이: ${{trendTxt}}<br>`;

  if(goodOnes.length>0){{
    overallHtml+=`<br><b style="color:#15803d">▶ 올바른 방향 파라미터:</b><br>`;
    goodOnes.forEach(i=>{{
      const dirTxt=i.dir>0?'증가↑':'감소↓';
      const effTxt=i.c>0?'수익 증가':'수익 개선';
      overallHtml+=`&nbsp;&nbsp;<span class="tag tup">${{i.key}} ${{dirTxt}} → ${{effTxt}} 예상</span> `;
    }});
    overallHtml+='<br>';
  }}
  if(badOnes.length>0){{
    overallHtml+=`<br><b style="color:#b91c1c">▶ 주의 필요 파라미터:</b><br>`;
    badOnes.forEach(i=>{{
      const dirTxt=i.dir>0?'증가↑':'감소↓';
      const effTxt=i.c>0?'수익 감소 위험':'수익 저하 가능';
      overallHtml+=`&nbsp;&nbsp;<span class="tag tdn">${{i.key}} ${{dirTxt}} → ${{effTxt}}</span> `;
    }});
    overallHtml+='<br>';
  }}

  // 가장 영향력 강한 파라미터
  const topParam=insights.sort((a,b)=>Math.abs(b.c)-Math.abs(a.c))[0];
  if(topParam){{
    const optDir=topParam.c>0?'늘리는':'줄이는';
    overallHtml+=`<br><b style="color:#0369a1">▶ 핵심 레버:</b>
      <span class="tag tok">${{topParam.key}}</span> 를 ${{optDir}} 방향이 수익에 가장 큰 영향<br>`;
  }}

  overallHtml+=`<br><span style="color:#94a3b8;font-size:10px">
    ※ 상관관계는 인과관계가 아닙니다. 데이터 수가 적을수록 신뢰도가 낮습니다 (현재: ${{all.length}}개 샘플)
  </span>`;
  overallHtml+=`</div></div>`;
  document.getElementById('overall-box').innerHTML=overallHtml;

  // ── 보수적/균형/공격적 추천 ──────────────────────────────────────
  buildRecommend(all, src, corrs);
}}

function buildRecommend(all, src, corrs){{
  if(!src.length)return;
  const last=src[src.length-1];

  // 각 파라미터 실제 범위 계산 (전체 데이터 기반)
  function rng(key){{
    const vals=all.map(r=>r[key]||0).filter(v=>v>0);
    if(!vals.length)return {{min:0,max:0,mean:0,cur:last[key]||0}};
    const min=Math.min(...vals),max=Math.max(...vals);
    const mean=Math.round(vals.reduce((a,b)=>a+b,0)/vals.length);
    return {{min,max,mean,cur:last[key]||0}};
  }}

  const R={{sl:rng('sl'),tp:rng('tp'),atr:rng('atr'),fm:rng('fm'),
            sm:rng('sm'),adx:rng('adx'),rl:rng('rl'),rh:rng('rh'),
            mp:rng('mp'),cd:rng('cd')}};

  // 상관 부호에 따라 "최적 방향" 결정
  // corr>0 → 값 높을수록 수익↑ / corr<0 → 값 낮을수록 수익↑
  function optVal(key, mode){{
    const r=R[key]; const c=corrs[key]||0;
    const span=r.max-r.min;
    if(!span)return r.cur;
    // mode: -1=보수, 0=균형, 1=공격
    const profitDir=c>0.05?1:c<-0.05?-1:0; // 수익에 유리한 방향
    let base;
    if(mode===-1){{ // 보수: 안전 우선 (DD 줄이는 방향)
      base=r.min+span*0.25;
    }} else if(mode===1){{ // 공격: 수익 극대화 방향
      base=profitDir>0?r.max-span*0.1:r.min+span*0.1;
    }} else {{ // 균형: 중간+상관 방향 약간 반영
      base=r.mean+(profitDir*span*0.1);
    }}
    return Math.round(Math.max(r.min,Math.min(r.max,base)));
  }}

  // SL/TP 비율 계산
  function sltp(mode){{
    const sl=optVal('sl',mode), tp=optVal('tp',mode);
    const ratio=sl>0?(tp/sl).toFixed(1):'—';
    return {{sl,tp,ratio}};
  }}

  function profileCard(title,mode,bgColor,borderColor,emoji,desc){{
    const st=sltp(mode);
    const fm=optVal('fm',mode), sm=optVal('sm',mode);
    const adx=optVal('adx',mode), mp=optVal('mp',mode);
    const rl=optVal('rl',mode), rh=optVal('rh',mode);
    const cd=optVal('cd',mode), atr=optVal('atr',mode);
    // 예상 효과
    const profitUpParams=Object.keys(corrs).filter(k=>corrs[k]>0.2&&mode===1);
    const ddRisk=mode===1?'높음':mode===-1?'낮음':'보통';
    const winRate=mode===1?'높음':mode===-1?'안정':'균형';
    return `
    <div style="flex:1;min-width:240px;background:${{bgColor}};border:2px solid ${{borderColor}};
                border-radius:10px;padding:14px">
      <div style="font-size:15px;font-weight:bold;color:${{borderColor}};margin-bottom:6px">
        ${{emoji}} ${{title}}</div>
      <div style="font-size:11px;color:#64748b;margin-bottom:10px">${{desc}}</div>
      <table style="width:100%;border-collapse:collapse;font-size:12px">
        <tr><td style="color:#64748b;padding:3px 0">SL / TP</td>
            <td style="font-weight:bold;text-align:right">${{st.sl}} / ${{st.tp}}
              <span style="color:#94a3b8;font-size:10px">(비율 1:${{st.ratio}})</span></td></tr>
        <tr><td style="color:#64748b;padding:3px 0">ATR 기간</td>
            <td style="font-weight:bold;text-align:right">${{atr}}</td></tr>
        <tr><td style="color:#64748b;padding:3px 0">EMA Fast / Slow</td>
            <td style="font-weight:bold;text-align:right">${{fm}} / ${{sm}}</td></tr>
        <tr><td style="color:#64748b;padding:3px 0">ADX 최소값</td>
            <td style="font-weight:bold;text-align:right">${{adx}}</td></tr>
        <tr><td style="color:#64748b;padding:3px 0">RSI 범위</td>
            <td style="font-weight:bold;text-align:right">${{rl}} ~ ${{rh}}</td></tr>
        <tr><td style="color:#64748b;padding:3px 0">최대 포지션 / 쿨다운</td>
            <td style="font-weight:bold;text-align:right">${{mp}} / ${{cd}}</td></tr>
      </table>
      <div style="margin-top:10px;padding:8px;background:white;border-radius:6px;
                  font-size:11px;color:#475569;line-height:1.7">
        DD 위험: <b>${{ddRisk}}</b> &nbsp;|&nbsp; 수익 기대: <b>${{winRate}}</b><br>
        ${{mode===-1?'손실 제한 우선. 작은 TP/큰 ADX로 확실한 신호만 진입.':
           mode===1 ?'수익 극대화. 넓은 TP, 낮은 ADX로 많은 신호 포착.':
                     '수익과 안전의 균형. 중간값 파라미터로 안정적 운용.'}}
      </div>
    </div>`;
  }}

  // 현재 파라미터와 비교
  const curSL=last.sl||0, curTP=last.tp||0;
  const curDesc=`현재: SL=${{curSL}} TP=${{curTP}} EMA=${{last.fm}}/${{last.sm}} ADX=${{last.adx}}`;

  const recHtml=`
  <div style="font-size:12px;color:#64748b;margin-bottom:12px">
    ${{curDesc}} &nbsp;→&nbsp; 아래 추천값과 비교하세요
  </div>
  <div style="display:flex;gap:12px;flex-wrap:wrap">
    ${{profileCard('보수적 운용',-1,'#f0fdf4','#16a34a','🛡️',
      'DD 최소화, 안정적 수익 유지 우선')}}
    ${{profileCard('균형 운용',0,'#f0f9ff','#0369a1','⚖️',
      '수익과 리스크의 최적 균형점')}}
    ${{profileCard('공격적 운용',1,'#fffbeb','#f59e0b','🚀',
      '수익 극대화, 높은 리스크 감수')}}
  </div>
  <div style="margin-top:10px;font-size:11px;color:#94a3b8">
    ※ 추천값은 이 EA의 실제 백테스트 데이터(${{all.length}}개)의 상관관계 기반 추정치입니다.
       반드시 백테스트로 검증 후 적용하세요.
  </div>`;

  // 추천 카드를 param-card 뒤에 삽입
  let recCard=document.getElementById('rec-card');
  if(!recCard){{
    recCard=document.createElement('div');
    recCard.id='rec-card';
    recCard.className='card';
    document.getElementById('param-card').insertAdjacentElement('afterend',recCard);
  }}
  recCard.innerHTML=`<h3>파라미터 추천 — 보수적 / 균형 / 공격적</h3>`+recHtml;
}}

if(ALL_SC.length>0)selectSC(ALL_SC[0].sc);
</script>
</body></html>"""


def _best_per_round(lst):
    """같은 라운드 내 여러 테스트 → 수익 최고 1개만"""
    best = {}
    for r in lst:
        k = r["round"]
        if k not in best or r["profit"] > best[k]["profit"]:
            best[k] = r
    return [best[k] for k in sorted(best.keys())]


# ════════════════════════════════════════════════════════════════════
class EADetailTab(tk.Frame):
    def __init__(self, parent, cfg):
        super().__init__(parent, bg=BG)
        self._cfg      = cfg
        self._all_rows = []
        self._sc_data  = {}
        self._cur_sc   = None
        self._charts   = []
        self._build_ui()
        self.after(400, self._load_data)

    # ── UI ─────────────────────────────────────────────────────────
    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg="#0369a1")
        hdr.pack(fill="x")
        tk.Label(hdr, text="EA별 라운드 성과 · 파라미터 변화 분석",
                 font=("Malgun Gothic", 12, "bold"),
                 bg="#0369a1", fg="white", pady=7).pack(side="left", padx=12)
        B(hdr, "새로고침", TEAL,  self._load_data,    padx=8).pack(side="right", padx=4, pady=4)
        B(hdr, "HTML 저장", GREEN, self._export_html,  padx=8).pack(side="right", padx=2, pady=4)

        self._stat = tk.Label(hdr, text="", bg="#0369a1", fg="#7dd3fc",
                              font=LBL)
        self._stat.pack(side="right", padx=10)

        # 본문: 좌(사이드바) + 우(상세)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # ── 사이드바 ──────────────────────────────────────────────
        side = tk.Frame(body, bg="#1e293b", width=175)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="EA 목록", bg="#1e293b", fg="#94a3b8",
                 font=("Malgun Gothic", 8, "bold")).pack(pady=(8, 2))

        # 검색
        sf = tk.Frame(side, bg="#1e293b")
        sf.pack(fill="x", padx=6, pady=(0, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_list())
        tk.Entry(sf, textvariable=self._search_var,
                 bg="#334155", fg="white", insertbackground="white",
                 relief="flat", font=("Consolas", 9)).pack(fill="x")

        # 정렬
        sf2 = tk.Frame(side, bg="#1e293b")
        sf2.pack(fill="x", padx=6, pady=(0, 4))
        self._sort_var = tk.StringVar(value="최고수익")
        sort_cb = ttk.Combobox(sf2, textvariable=self._sort_var,
                               values=["SC번호", "최고수익", "라운드수"],
                               state="readonly", width=14)
        sort_cb.pack(fill="x")
        sort_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_list())

        sc_frame = tk.Frame(side, bg="#1e293b")
        sc_frame.pack(fill="both", expand=True)
        vsb = tk.Scrollbar(sc_frame, orient="vertical", bg="#0f172a")
        self._sc_lb = tk.Listbox(
            sc_frame, bg="#1e293b", fg="#e2e8f0",
            selectbackground="#0369a1", selectforeground="white",
            font=("Consolas", 9), relief="flat", bd=0,
            activestyle="none", yscrollcommand=vsb.set)
        vsb.config(command=self._sc_lb.yview)
        vsb.pack(side="right", fill="y")
        self._sc_lb.pack(side="left", fill="both", expand=True)
        self._sc_lb.bind("<<ListboxSelect>>", self._on_sc_select)
        self._sc_items = []   # (sc_id, label) 순서 저장

        # ── 우측 상세 패널 ─────────────────────────────────────────
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # 요약 바
        self._summary_frame = tk.Frame(right, bg=PANEL, height=56)
        self._summary_frame.pack(fill="x", padx=6, pady=(4, 0))
        self._summary_frame.pack_propagate(False)
        self._sum_labels = {}
        for key, lbl in [("sc","EA"), ("rounds","라운드"), ("tests","테스트"),
                         ("btc_max","BTC최고"), ("gold_max","GOLD최고"),
                         ("sl","최신SL"), ("tp","최신TP")]:
            fr = tk.Frame(self._summary_frame, bg=PANEL)
            fr.pack(side="left", padx=12, pady=6)
            tk.Label(fr, text=lbl, bg=PANEL, fg="#64748b", font=("Malgun Gothic", 8)).pack()
            lv = tk.Label(fr, text="—", bg=PANEL, fg="#0369a1",
                          font=("Malgun Gothic", 10, "bold"))
            lv.pack()
            self._sum_labels[key] = lv

        # 차트 노트북
        if HAS_MPL:
            self._nb = ttk.Notebook(right)
            self._nb.pack(fill="both", expand=True, padx=6, pady=4)
            self._build_chart_tabs()
        else:
            tk.Label(right, text="matplotlib 필요: pip install matplotlib",
                     bg=BG, fg=RED).pack(expand=True)

        # 파라미터 테이블 (하단)
        tbl_fr = tk.Frame(right, bg=BG)
        tbl_fr.pack(fill="x", padx=6, pady=(0, 4))
        self._build_table(tbl_fr)

    def _build_chart_tabs(self):
        # Tab 1: 수익 추이
        t1 = tk.Frame(self._nb, bg=BG)
        self._nb.add(t1, text="  수익 추이  ")
        self._fig1 = Figure(figsize=(9, 3), facecolor=BG, tight_layout=True)
        self._ax1  = self._fig1.add_subplot(111)
        self._canvas1 = FigureCanvasTkAgg(self._fig1, t1)
        self._canvas1.get_tk_widget().pack(fill="both", expand=True)

        # Tab 2: SL / TP 변화
        t2 = tk.Frame(self._nb, bg=BG)
        self._nb.add(t2, text="  SL/TP 변화  ")
        self._fig2 = Figure(figsize=(9, 3), facecolor=BG, tight_layout=True)
        self._ax2a = self._fig2.add_subplot(121)
        self._ax2b = self._fig2.add_subplot(122)
        self._canvas2 = FigureCanvasTkAgg(self._fig2, t2)
        self._canvas2.get_tk_widget().pack(fill="both", expand=True)

        # Tab 3: EMA / ADX 변화
        t3 = tk.Frame(self._nb, bg=BG)
        self._nb.add(t3, text="  EMA/ADX  ")
        self._fig3 = Figure(figsize=(9, 3), facecolor=BG, tight_layout=True)
        self._ax3a = self._fig3.add_subplot(121)
        self._ax3b = self._fig3.add_subplot(122)
        self._canvas3 = FigureCanvasTkAgg(self._fig3, t3)
        self._canvas3.get_tk_widget().pack(fill="both", expand=True)

        # Tab 4: DD% / PF
        t4 = tk.Frame(self._nb, bg=BG)
        self._nb.add(t4, text="  DD / PF  ")
        self._fig4 = Figure(figsize=(9, 3), facecolor=BG, tight_layout=True)
        self._ax4a = self._fig4.add_subplot(121)
        self._ax4b = self._fig4.add_subplot(122)
        self._canvas4 = FigureCanvasTkAgg(self._fig4, t4)
        self._canvas4.get_tk_widget().pack(fill="both", expand=True)

    def _build_table(self, parent):
        cols = ("round","sym","profit","dd_pct","pf","trades",
                "sl","tp","atr","fm","sm","adx","rl","rh","mp","cd")
        hdrs = ("R","심볼","수익","DD%","PF","거래",
                "SL","TP","ATR","FastEMA","SlowEMA","ADX","RSI-L","RSI-H","MaxPos","CD")
        widths = (30,60,85,50,45,55,40,40,35,60,60,40,45,45,45,35)

        fr = tk.Frame(parent, bg=BG)
        fr.pack(fill="x")
        vsb = ttk.Scrollbar(fr, orient="vertical")
        hsb = ttk.Scrollbar(fr, orient="horizontal")
        self._tree = ttk.Treeview(
            fr, columns=cols, show="headings", height=7,
            yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(side="left", fill="x", expand=True)

        for col, hdr, w in zip(cols, hdrs, widths):
            self._tree.heading(col, text=hdr)
            anchor = "center" if col in ("round","sym") else "e"
            self._tree.column(col, width=w, anchor=anchor, minwidth=30)

        self._tree.tag_configure("btc",  background="#fffbeb")
        self._tree.tag_configure("gold", background="#f0f4ff")

    # ── 데이터 로드 ─────────────────────────────────────────────────
    def _load_data(self):
        self._stat.config(text="로딩 중...")
        threading.Thread(target=self._load_thread, daemon=True).start()

    def _load_thread(self):
        rows = _load_all()
        sc_data = defaultdict(list)
        for r in rows:
            sc_data[r["sc"]].append(r)
        self._all_rows = rows
        self._sc_data  = dict(sc_data)
        self.after(0, lambda: self._stat.config(
            text=f"{len(rows):,}개 로드"))
        self.after(0, self._populate_list)

    def _populate_list(self):
        self._filter_list()

    def _filter_list(self):
        keyword = self._search_var.get().strip().upper()
        sort    = self._sort_var.get()

        items = []
        for sc, rlist in self._sc_data.items():
            max_p  = max(r["profit"] for r in rlist)
            n_rnd  = len(set(r["round"] for r in rlist))
            syms   = set(r["sym"] for r in rlist)
            label  = f"SC{sc:03d}  ${max_p/1000:.0f}k  R{n_rnd}"
            if keyword and keyword not in f"SC{sc:03d}":
                continue
            items.append((sc, label, max_p, n_rnd))

        if sort == "최고수익":
            items.sort(key=lambda x: -x[2])
        elif sort == "라운드수":
            items.sort(key=lambda x: (-x[3], x[0]))
        else:
            items.sort(key=lambda x: x[0])

        self._sc_items = [(x[0], x[1]) for x in items]
        self._sc_lb.delete(0, "end")
        for _, label in self._sc_items:
            self._sc_lb.insert("end", label)

        # 현재 선택 복원
        if self._cur_sc is not None:
            for i, (sc, _) in enumerate(self._sc_items):
                if sc == self._cur_sc:
                    self._sc_lb.selection_set(i)
                    self._sc_lb.see(i)
                    break

    def _on_sc_select(self, event):
        sel = self._sc_lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._sc_items):
            return
        sc = self._sc_items[idx][0]
        self._cur_sc = sc
        self._draw(sc)

    # ── 차트 그리기 ─────────────────────────────────────────────────
    def _draw(self, sc):
        rlist = self._sc_data.get(sc, [])
        if not rlist:
            return

        btc  = _best_per_round([r for r in rlist if r["sym"] == "BTCUSD"])
        gold = _best_per_round([r for r in rlist if r["sym"] == "XAUUSD"])
        src  = btc if btc else gold   # 파라미터 기준 심볼

        btc_rnds  = [r["round"] for r in btc]
        gold_rnds = [r["round"] for r in gold]
        all_rnds  = sorted(set(btc_rnds + gold_rnds))
        x_labels  = [f"R{r}" for r in all_rnds]

        def v(lst, key, rnds):
            d = {r["round"]: r[key] for r in lst}
            return [d.get(r) for r in rnds]

        # 요약 바 업데이트
        n_rnd  = len(all_rnds)
        n_test = len(rlist)
        btc_m  = max((r["profit"] for r in btc),  default=0)
        gold_m = max((r["profit"] for r in gold), default=0)
        sl_now = src[-1]["sl"] if src else "—"
        tp_now = src[-1]["tp"] if src else "—"

        self._sum_labels["sc"].config(text=f"SC{sc:03d}")
        self._sum_labels["rounds"].config(text=str(n_rnd))
        self._sum_labels["tests"].config(text=str(n_test))
        self._sum_labels["btc_max"].config(text=f"${btc_m:,.0f}")
        self._sum_labels["gold_max"].config(text=f"${gold_m:,.0f}")
        self._sum_labels["sl"].config(text=str(sl_now))
        self._sum_labels["tp"].config(text=str(tp_now))

        if not HAS_MPL:
            self._refresh_table(rlist)
            return

        # ── Chart 1: 수익 추이 ─────────────────────────────────────
        ax = self._ax1
        ax.clear()
        if btc:
            btc_x = [f"R{r}" for r in btc_rnds]
            ax.plot(btc_x, [r["profit"] for r in btc],
                    "o-", color="#f59e0b", linewidth=2, markersize=5, label="BTCUSD")
        if gold:
            gold_x = [f"R{r}" for r in gold_rnds]
            ax.plot(gold_x, [r["profit"] for r in gold],
                    "s-", color="#6366f1", linewidth=2, markersize=5, label="XAUUSD")
        ax.axhline(0, color="#94a3b8", linewidth=0.8, linestyle="--")
        ax.set_title(f"SC{sc:03d} — 라운드별 수익 추이", fontsize=10)
        ax.set_ylabel("수익 ($)", fontsize=9)
        ax.legend(fontsize=8)
        ax.tick_params(labelsize=8)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        self._fig1.canvas.draw_idle()

        # ── Chart 2: SL/TP 변화 ────────────────────────────────────
        self._ax2a.clear(); self._ax2b.clear()
        src_x = [f"R{r['round']}" for r in src]
        # SL/TP 추이
        self._ax2a.plot(src_x, [r["sl"] for r in src],
                        "o-", color="#ef4444", linewidth=2, markersize=5, label="SL")
        self._ax2a.plot(src_x, [r["tp"] for r in src],
                        "s-", color="#3b82f6", linewidth=2, markersize=5, label="TP")
        self._ax2a.set_title("SL / TP 변화", fontsize=9)
        self._ax2a.legend(fontsize=8); self._ax2a.tick_params(labelsize=8)

        # SL vs 수익 산점도
        btc_pts  = [(r["sl"], r["profit"]) for r in rlist if r["sym"] == "BTCUSD"]
        gold_pts = [(r["sl"], r["profit"]) for r in rlist if r["sym"] == "XAUUSD"]
        if btc_pts:
            self._ax2b.scatter(*zip(*btc_pts), color="#f59e0b", alpha=0.7,
                               s=30, label="BTC")
        if gold_pts:
            self._ax2b.scatter(*zip(*gold_pts), color="#6366f1", alpha=0.7,
                               s=30, label="GOLD")
        self._ax2b.set_title("SL값 vs 수익", fontsize=9)
        self._ax2b.set_xlabel("SL", fontsize=8)
        self._ax2b.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        self._ax2b.legend(fontsize=8); self._ax2b.tick_params(labelsize=8)
        self._fig2.canvas.draw_idle()

        # ── Chart 3: EMA / ADX 변화 ────────────────────────────────
        self._ax3a.clear(); self._ax3b.clear()
        self._ax3a.plot(src_x, [r["fm"] for r in src],
                        "o-", color="#f59e0b", markersize=4, label="Fast EMA")
        self._ax3a.plot(src_x, [r["sm"] for r in src],
                        "s-", color="#6366f1", markersize=4, label="Slow EMA")
        self._ax3a.set_title("EMA 기간 변화", fontsize=9)
        self._ax3a.legend(fontsize=8); self._ax3a.tick_params(labelsize=8)

        self._ax3b.plot(src_x, [r["adx"] for r in src],
                        "o-", color="#ef4444", markersize=4, label="ADX Min")
        self._ax3b.plot(src_x, [r["rl"] for r in src],
                        "s--", color="#10b981", markersize=4, label="RSI Lower")
        self._ax3b.plot(src_x, [r["rh"] for r in src],
                        "^--", color="#8b5cf6", markersize=4, label="RSI Upper")
        self._ax3b.set_title("ADX / RSI 기준 변화", fontsize=9)
        self._ax3b.legend(fontsize=8); self._ax3b.tick_params(labelsize=8)
        self._fig3.canvas.draw_idle()

        # ── Chart 4: DD% / PF ─────────────────────────────────────
        self._ax4a.clear(); self._ax4b.clear()
        if btc:
            self._ax4a.plot([f"R{r['round']}" for r in btc],
                            [r["dd_pct"] for r in btc],
                            "o-", color="#f59e0b", linewidth=2, markersize=5, label="BTC")
        if gold:
            self._ax4a.plot([f"R{r['round']}" for r in gold],
                            [r["dd_pct"] for r in gold],
                            "s-", color="#6366f1", linewidth=2, markersize=5, label="GOLD")
        self._ax4a.set_title("최대 낙폭 DD% 변화", fontsize=9)
        self._ax4a.set_ylabel("DD%", fontsize=8)
        self._ax4a.legend(fontsize=8); self._ax4a.tick_params(labelsize=8)

        if btc:
            self._ax4b.plot([f"R{r['round']}" for r in btc],
                            [r["pf"] for r in btc],
                            "o-", color="#f59e0b", linewidth=2, markersize=5, label="BTC")
        if gold:
            self._ax4b.plot([f"R{r['round']}" for r in gold],
                            [r["pf"] for r in gold],
                            "s-", color="#6366f1", linewidth=2, markersize=5, label="GOLD")
        self._ax4b.axhline(1.0, color="#94a3b8", linewidth=0.7, linestyle="--")
        self._ax4b.set_title("이익계수 PF 변화", fontsize=9)
        self._ax4b.legend(fontsize=8); self._ax4b.tick_params(labelsize=8)
        self._fig4.canvas.draw_idle()

        # 테이블
        self._refresh_table(rlist)

    def _refresh_table(self, rlist):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for r in sorted(rlist, key=lambda x: (x["round"], x["sym"])):
            tag  = "btc" if r["sym"] == "BTCUSD" else "gold"
            pcol = "" if r["profit"] >= 0 else ""
            self._tree.insert("", "end", values=(
                f"R{r['round']}", r["sym"],
                f"${r['profit']:,.0f}",
                f"{r['dd_pct']:.1f}%",
                f"{r['pf']:.2f}",
                f"{r['trades']:,}",
                r["sl"], r["tp"], r["atr"],
                r["fm"], r["sm"], r["adx"],
                r["rl"], r["rh"], r["mp"], r["cd"],
            ), tags=(tag,))

    # ── HTML 내보내기 ────────────────────────────────────────────────
    def _export_html(self):
        if not self._sc_data:
            messagebox.showwarning("경고", "데이터 없음 — 먼저 새로고침")
            return
        threading.Thread(target=self._export_thread, daemon=True).start()

    def _export_thread(self):
        try:
            os.makedirs(OUT_DIR, exist_ok=True)
            html = self._build_export_html()
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(OUT_DIR, f"ea_detail_{ts}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.after(0, lambda: self._open_and_notify(path))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("오류", str(e)))

    def _open_and_notify(self, path):
        subprocess.Popen(["cmd", "/c", "start", "", path],
                         creationflags=subprocess.CREATE_NO_WINDOW)
        messagebox.showinfo("완료", f"저장 & 오픈:\n{path}")

    def _fig_b64(self, fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        return base64.b64encode(buf.getvalue()).decode()

    def _build_export_html(self):
        rows = self._all_rows
        sc_data = self._sc_data
        all_scs = sorted(sc_data.keys())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # JS 데이터
        js_sc = {}
        for sc, rlist in sc_data.items():
            btc  = _best_per_round([r for r in rlist if r["sym"] == "BTCUSD"])
            gold = _best_per_round([r for r in rlist if r["sym"] == "XAUUSD"])
            src  = btc if btc else gold
            js_sc[sc] = {
                "btc":  [{"r": r["round"], "profit": r["profit"], "dd": r["dd_pct"],
                          "pf": r["pf"], "sl": r["sl"], "tp": r["tp"],
                          "atr": r["atr"], "fm": r["fm"], "sm": r["sm"],
                          "adx": r["adx"], "rl": r["rl"], "rh": r["rh"]}
                         for r in btc],
                "gold": [{"r": r["round"], "profit": r["profit"], "dd": r["dd_pct"],
                          "pf": r["pf"], "sl": r["sl"], "tp": r["tp"],
                          "atr": r["atr"], "fm": r["fm"], "sm": r["sm"],
                          "adx": r["adx"], "rl": r["rl"], "rh": r["rh"]}
                         for r in gold],
                "all":  sorted([{"r": r["round"], "sym": r["sym"],
                                  "profit": r["profit"], "dd": r["dd_pct"],
                                  "pf": r["pf"], "trades": r["trades"],
                                  "sl": r["sl"], "tp": r["tp"], "atr": r["atr"],
                                  "fm": r["fm"], "sm": r["sm"], "adx": r["adx"],
                                  "rl": r["rl"], "rh": r["rh"],
                                  "mp": r["mp"], "cd": r["cd"]}
                                 for r in rlist],
                                key=lambda x: (x["r"], x["sym"])),
                "max_btc":  max((r["profit"] for r in btc),  default=0),
                "max_gold": max((r["profit"] for r in gold), default=0),
                "n_rnd":    len(set(r["round"] for r in rlist)),
                "n_test":   len(rlist),
            }

        sc_list = [{"sc": sc,
                    "max_p": max(r["profit"] for r in sc_data[sc]),
                    "n_rnd": len(set(r["round"] for r in sc_data[sc]))}
                   for sc in all_scs]

        JS_DATA = json.dumps(js_sc, ensure_ascii=False)
        SC_LIST = json.dumps(sc_list, ensure_ascii=False)

        # 현재 차트 스크린샷 (선택된 SC)
        chart_imgs = ""
        if HAS_MPL and self._cur_sc is not None:
            for fig, title in [
                (self._fig1, f"SC{self._cur_sc:03d} 수익 추이"),
                (self._fig2, "SL/TP 변화"),
                (self._fig3, "EMA/ADX 변화"),
                (self._fig4, "DD/PF 변화"),
            ]:
                b64 = self._fig_b64(fig)
                chart_imgs += f"""
                <div style="margin:12px 0">
                  <div style="font-size:13px;font-weight:bold;color:#0369a1;
                              margin-bottom:6px">{title}</div>
                  <img src="data:image/png;base64,{b64}"
                       style="max-width:100%;border-radius:6px;
                              box-shadow:0 2px 6px #0002">
                </div>"""

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>EA별 라운드 성과 분석 — {now[:10]}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Malgun Gothic',Arial,sans-serif;background:#f0f9ff;
      color:#0f172a;display:flex;flex-direction:column;height:100vh}}
header{{background:linear-gradient(135deg,#0369a1,#0284c7);color:#fff;
        padding:14px 20px;flex-shrink:0}}
header h1{{font-size:17px}} header p{{font-size:11px;opacity:.8;margin-top:3px}}
.main{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:190px;background:#1e293b;flex-shrink:0;overflow-y:auto;padding:6px 0}}
.sidebar input{{width:calc(100% - 12px);margin:4px 6px;padding:4px 8px;
                background:#334155;border:none;color:white;border-radius:4px;
                font-size:11px}}
.sc-item{{padding:7px 10px;cursor:pointer;border-left:3px solid transparent}}
.sc-item:hover{{background:#334155}}
.sc-item.active{{background:#0369a1;border-left-color:#7dd3fc}}
.sc-name{{font-size:12px;font-weight:bold;color:#e2e8f0}}
.sc-meta{{font-size:10px;color:#94a3b8;margin-top:2px}}
.sc-item.active .sc-meta{{color:#bae6fd}}
.panel{{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}}
.card{{background:#fff;border-radius:8px;padding:14px;
       box-shadow:0 2px 6px rgba(3,105,161,.1)}}
.card h3{{font-size:13px;color:#0369a1;border-bottom:2px solid #bae6fd;
          padding-bottom:6px;margin-bottom:10px}}
.sum-bar{{display:flex;gap:14px;flex-wrap:wrap}}
.s-item{{background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;
         padding:8px 12px}}
.s-num{{font-size:18px;font-weight:bold;color:#0369a1}}
.s-lbl{{font-size:10px;color:#64748b;margin-top:2px}}
.chart-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.chart-box{{position:relative;height:240px}}
table{{width:100%;border-collapse:collapse;font-size:11.5px}}
thead th{{background:#0369a1;color:#fff;padding:6px 8px;position:sticky;top:0}}
tbody td{{padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center}}
tbody tr:hover td{{background:#f1f5f9}}
.badge{{display:inline-block;padding:1px 7px;border-radius:10px;
        font-size:10px;font-weight:bold}}
.btc{{background:#fef3c7;color:#b45309}}
.gld{{background:#ede9fe;color:#5b21b6}}
.pos{{color:#16a34a;font-weight:bold}} .neg{{color:#dc2626;font-weight:bold}}
.tbl-scroll{{overflow-x:auto;max-height:320px;overflow-y:auto}}
.snapshot h3{{margin-bottom:10px}}
</style>
</head>
<body>
<header>
  <h1>EA별 라운드 성과 분석 — 파라미터 변화 추적</h1>
  <p>생성: {now} &nbsp;|&nbsp; EA {len(all_scs)}종 &nbsp;|&nbsp;
     총 {len(rows):,}개 백테스트</p>
</header>
<div class="main">

<div class="sidebar">
  <input id="srch" placeholder="SC 검색..." oninput="filterList(this.value)">
  <div id="sc-list"></div>
</div>

<div class="panel" id="panel">
  <div style="color:#94a3b8;padding:40px;text-align:center">
    ← 좌측에서 EA를 선택하세요</div>
</div>

</div>

<script>
const DATA={JS_DATA};
const SC_LIST={SC_LIST};
let charts=[];
function killCharts(){{charts.forEach(c=>c.destroy());charts=[];}}

// 사이드바 생성
function buildList(list){{
  const el=document.getElementById('sc-list');
  el.innerHTML='';
  list.forEach(s=>{{
    const d=document.createElement('div');
    d.className='sc-item'; d.id='si-'+s.sc;
    const pc=s.max_p>0?'#4ade80':s.max_p>-5000?'#fbbf24':'#f87171';
    d.innerHTML=`<div class="sc-name">SC${{String(s.sc).padStart(3,'0')}}</div>
      <div class="sc-meta">R${{s.n_rnd}} | <span style="color:${{pc}}">$${{s.max_p.toLocaleString('ko',{{maximumFractionDigits:0}})}}</span></div>`;
    d.onclick=()=>selectSC(s.sc);
    el.appendChild(d);
  }});
}}
buildList(SC_LIST);

function filterList(q){{
  q=q.toUpperCase();
  buildList(SC_LIST.filter(s=>('SC'+String(s.sc).padStart(3,'0')).includes(q)));
}}

function getVal(arr,rnd,key){{const r=arr.find(x=>x.r===rnd);return r?r[key]:null;}}

function selectSC(sc){{
  document.querySelectorAll('.sc-item').forEach(e=>e.classList.remove('active'));
  const el=document.getElementById('si-'+sc);
  if(el){{el.classList.add('active');el.scrollIntoView({{block:'nearest'}});}}
  killCharts();
  const d=DATA[sc];
  if(!d)return;
  const btc=d.btc||[],gold=d.gold||[],all=d.all||[];
  const src=btc.length?btc:gold;
  const rnds=[...new Set([...btc.map(r=>r.r),...gold.map(r=>r.r)])].sort((a,b)=>a-b);
  const xlbls=rnds.map(r=>'R'+r);
  const fmtN=n=>n==null?null:n;

  document.getElementById('panel').innerHTML=`
  <div class="card">
    <h3>SC${{String(sc).padStart(3,'0')}} — 요약</h3>
    <div class="sum-bar">
      <div class="s-item"><div class="s-num">${{d.n_rnd}}</div><div class="s-lbl">라운드수</div></div>
      <div class="s-item"><div class="s-num">${{d.n_test}}</div><div class="s-lbl">총 테스트</div></div>
      <div class="s-item" style="background:#fffbeb;border-color:#fcd34d">
        <div class="s-num" style="color:#b45309">$${{d.max_btc.toLocaleString('ko',{{maximumFractionDigits:0}})}}</div>
        <div class="s-lbl">BTC 최고수익</div></div>
      <div class="s-item" style="background:#f0f4ff;border-color:#c7d2fe">
        <div class="s-num" style="color:#6366f1">$${{d.max_gold.toLocaleString('ko',{{maximumFractionDigits:0}})}}</div>
        <div class="s-lbl">GOLD 최고수익</div></div>
      <div class="s-item"><div class="s-num">${{src.length?src[src.length-1].sl:'—'}}</div><div class="s-lbl">최신 SL</div></div>
      <div class="s-item"><div class="s-num">${{src.length?src[src.length-1].tp:'—'}}</div><div class="s-lbl">최신 TP</div></div>
    </div>
  </div>
  <div class="card">
    <h3>라운드별 수익 추이</h3>
    <div class="chart-box" style="height:260px"><canvas id="c1"></canvas></div>
  </div>
  <div class="card">
    <h3>파라미터 변화</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="c2"></canvas></div>
      <div class="chart-box"><canvas id="c3"></canvas></div>
    </div>
    <div class="chart-row" style="margin-top:12px">
      <div class="chart-box"><canvas id="c4"></canvas></div>
      <div class="chart-box"><canvas id="c5"></canvas></div>
    </div>
  </div>
  <div class="card">
    <h3>DD% / PF 변화</h3>
    <div class="chart-row">
      <div class="chart-box"><canvas id="c6"></canvas></div>
      <div class="chart-box"><canvas id="c7"></canvas></div>
    </div>
  </div>
  <div class="card">
    <h3>전체 파라미터 × 수익 테이블</h3>
    <div class="tbl-scroll">
      <table><thead><tr>
        <th>R</th><th>심볼</th><th>수익</th><th>DD%</th><th>PF</th><th>거래</th>
        <th>SL</th><th>TP</th><th>ATR</th><th>FastEMA</th><th>SlowEMA</th>
        <th>ADX</th><th>RSI-L</th><th>RSI-H</th><th>MaxPos</th><th>CD</th>
      </tr></thead><tbody id="tbd"></tbody></table>
    </div>
  </div>`;

  // 수익 추이
  charts.push(new Chart(document.getElementById('c1'),{{
    type:'line',data:{{labels:xlbls,datasets:[
      {{label:'BTCUSD',data:rnds.map(r=>getVal(btc,r,'profit')),
        borderColor:'#f59e0b',backgroundColor:'#f59e0b22',
        tension:.3,pointRadius:5,fill:true,spanGaps:true}},
      {{label:'XAUUSD',data:rnds.map(r=>getVal(gold,r,'profit')),
        borderColor:'#6366f1',backgroundColor:'#6366f122',
        tension:.3,pointRadius:5,fill:true,spanGaps:true}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}}}},
      scales:{{y:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}
    }}
  }}));

  // SL/TP 추이
  const sx=src.map(r=>'R'+r.r);
  charts.push(new Chart(document.getElementById('c2'),{{
    type:'line',data:{{labels:sx,datasets:[
      {{label:'SL',data:src.map(r=>r.sl),borderColor:'#ef4444',tension:.3,pointRadius:4}},
      {{label:'TP',data:src.map(r=>r.tp),borderColor:'#3b82f6',tension:.3,pointRadius:4}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},title:{{display:true,text:'SL / TP 변화'}}}}}}
  }}));

  // SL vs 수익 산점도
  charts.push(new Chart(document.getElementById('c3'),{{
    type:'scatter',
    data:{{datasets:[
      {{label:'BTC',data:all.filter(r=>r.sym==='BTCUSD').map(r=>{{return{{x:r.sl,y:r.profit,rnd:r.r,tp:r.tp}}}}),
        backgroundColor:'#f59e0baa',pointRadius:5}},
      {{label:'GOLD',data:all.filter(r=>r.sym==='XAUUSD').map(r=>{{return{{x:r.sl,y:r.profit,rnd:r.r,tp:r.tp}}}}),
        backgroundColor:'#6366f1aa',pointRadius:5}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},title:{{display:true,text:'SL값 vs 수익'}},
               tooltip:{{callbacks:{{label:ctx=>`SL=${{ctx.raw.x}} TP=${{ctx.raw.tp}} R${{ctx.raw.rnd}} $${{ctx.raw.y?.toLocaleString()}}`}}}}}},
      scales:{{x:{{title:{{display:true,text:'SL'}}}},
               y:{{ticks:{{callback:v=>'$'+v.toLocaleString()}}}}}}
    }}
  }}));

  // EMA 변화
  charts.push(new Chart(document.getElementById('c4'),{{
    type:'line',data:{{labels:sx,datasets:[
      {{label:'Fast EMA',data:src.map(r=>r.fm),borderColor:'#f59e0b',tension:.3,pointRadius:4}},
      {{label:'Slow EMA',data:src.map(r=>r.sm),borderColor:'#6366f1',tension:.3,pointRadius:4}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},title:{{display:true,text:'EMA 기간 변화'}}}}}}
  }}));

  // ADX/RSI 변화
  charts.push(new Chart(document.getElementById('c5'),{{
    type:'line',data:{{labels:sx,datasets:[
      {{label:'ADX Min',data:src.map(r=>r.adx),borderColor:'#ef4444',tension:.3,pointRadius:4}},
      {{label:'RSI Lower',data:src.map(r=>r.rl),borderColor:'#10b981',tension:.3,pointRadius:4,borderDash:[4,3]}},
      {{label:'RSI Upper',data:src.map(r=>r.rh),borderColor:'#8b5cf6',tension:.3,pointRadius:4,borderDash:[4,3]}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},title:{{display:true,text:'ADX / RSI 변화'}}}}}}
  }}));

  // DD% 변화
  charts.push(new Chart(document.getElementById('c6'),{{
    type:'line',data:{{labels:xlbls,datasets:[
      {{label:'BTC DD%',data:rnds.map(r=>getVal(btc,r,'dd')),
        borderColor:'#f59e0b',tension:.3,pointRadius:4,spanGaps:true}},
      {{label:'GOLD DD%',data:rnds.map(r=>getVal(gold,r,'dd')),
        borderColor:'#6366f1',tension:.3,pointRadius:4,spanGaps:true}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},title:{{display:true,text:'DD% 변화'}}}},
      scales:{{y:{{ticks:{{callback:v=>v+'%'}}}}}}
    }}
  }}));

  // PF 변화
  charts.push(new Chart(document.getElementById('c7'),{{
    type:'line',data:{{labels:xlbls,datasets:[
      {{label:'BTC PF',data:rnds.map(r=>getVal(btc,r,'pf')),
        borderColor:'#f59e0b',tension:.3,pointRadius:4,spanGaps:true}},
      {{label:'GOLD PF',data:rnds.map(r=>getVal(gold,r,'pf')),
        borderColor:'#6366f1',tension:.3,pointRadius:4,spanGaps:true}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},title:{{display:true,text:'PF 변화'}}}}}}
  }}));

  // 테이블
  const tbody=document.getElementById('tbd');
  tbody.innerHTML='';
  all.forEach(r=>{{
    const tr=document.createElement('tr');
    const bc=r.sym==='BTCUSD'?'btc':'gld';
    const pc=r.profit>=0?'pos':'neg';
    const ratio=r.sl>0?(r.tp/r.sl).toFixed(2):'—';
    tr.innerHTML=`<td>R${{r.r}}</td>
      <td><span class="badge ${{bc}}">${{r.sym}}</span></td>
      <td class="${{pc}}"><b>$${{r.profit.toLocaleString('ko',{{maximumFractionDigits:0}})}}</b></td>
      <td>${{r.dd.toFixed(1)}}%</td><td>${{r.pf.toFixed(2)}}</td><td>${{r.trades?.toLocaleString()||'—'}}</td>
      <td><b>${{r.sl}}</b></td><td><b>${{r.tp}}</b></td><td>${{r.atr}}</td>
      <td>${{r.fm}}</td><td>${{r.sm}}</td><td>${{r.adx}}</td>
      <td>${{r.rl}}</td><td>${{r.rh}}</td><td>${{r.mp}}</td><td>${{r.cd}}</td>`;
    tbody.appendChild(tr);
  }});
}}

if(SC_LIST.length>0) selectSC(SC_LIST[0].sc);
</script>
</body>
</html>"""
