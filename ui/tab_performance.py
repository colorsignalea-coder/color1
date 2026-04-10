"""
ui/tab_performance.py — EA Auto Master v7.0
============================================
BTC/GOLD 심볼별 성과 분석 탭:
  - g4_results/ JSON 전체 로드
  - EA × Round × Symbol 테이블 (profit, DD, PF, score)
  - 바차트 / 라운드별 추이 / 히트맵 차트
  - HTML 내보내기 (reports/performance/)
"""

import base64
import glob
import io
import json
import os
import re
import threading
import tkinter as tk
from collections import defaultdict
from tkinter import messagebox, ttk

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from ui.theme import BG, FG, PANEL, PANEL2, BLUE, GREEN, TEAL, AMBER, RED, B, LBL, TITLE, MONO

# ── 경로 (ui/ 기준 → 상위 폴더 = EA_AUTO_MASTER_v7.0) ───────────────
_BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G4_DIR  = os.path.join(_BASE, "g4_results")
OUT_DIR = os.path.join(_BASE, "reports", "performance")

# ── 색상 ────────────────────────────────────────────────────────────
BTC_COLOR  = "#f59e0b"   # amber
GOLD_COLOR = "#6366f1"   # indigo


# ════════════════════════════════════════════════════════════════════
def _load_all_results() -> pd.DataFrame:
    """g4_results/*.json → 단일 DataFrame"""
    rows = []
    for fn in glob.glob(os.path.join(G4_DIR, "*.json")):
        try:
            with open(fn, encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:
            continue
        rnd        = str(d.get("round", "?"))
        sym_def    = d.get("symbol", "XAUUSD")
        for r in d.get("results", []):
            sym  = r.get("symbol", sym_def)
            ea   = r.get("ea_name", "")
            m    = re.search(r"SC(\d+)", ea)
            sc   = int(m.group(1)) if m else 0
            rows.append({
                "round":       rnd,
                "symbol":      sym,
                "sc_id":       sc,
                "ea_name":     ea,
                "profit":      float(r.get("profit", 0)),
                "drawdown_pct":float(r.get("drawdown_pct", 0)),
                "profit_factor":float(r.get("profit_factor", 0)),
                "trades":      int(r.get("trades", 0)),
                "score":       float(r.get("score", 0)),
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _best_per_sc_round_sym(df: pd.DataFrame) -> pd.DataFrame:
    """SC × Round × Symbol → 최고 score 1개만"""
    return (
        df.sort_values("score", ascending=False)
          .groupby(["sc_id", "round", "symbol"], sort=False)
          .first()
          .reset_index()
    )


# ════════════════════════════════════════════════════════════════════
class PerformanceTab(tk.Frame):
    def __init__(self, parent, cfg):
        super().__init__(parent, bg=BG)
        self._cfg  = cfg
        self._df   = pd.DataFrame()
        self._view = pd.DataFrame()
        self._build_ui()
        self.after(300, self._load_data)

    # ── UI 구성 ─────────────────────────────────────────────────────
    def _build_ui(self):
        # ── 제목바 ──────────────────────────────────────────────────
        ACCENT_BG = "#0369a1"
        hdr = tk.Frame(self, bg=ACCENT_BG)
        hdr.pack(fill="x", pady=(0, 4))
        tk.Label(hdr, text="BTC / GOLD  성과 분석",
                 font=("Malgun Gothic", 12, "bold"),
                 bg=ACCENT_BG, fg="white", pady=8).pack(side="left", padx=12)
        B(hdr, "새로고침", TEAL, self._load_data, padx=8).pack(side="right", padx=6, pady=4)
        B(hdr, "HTML 내보내기", GREEN, self._export_html, padx=8).pack(side="right", padx=2, pady=4)

        # ── 필터바 ──────────────────────────────────────────────────
        flt = tk.Frame(self, bg=PANEL, bd=0)
        flt.pack(fill="x", padx=6, pady=2)

        tk.Label(flt, text="라운드:", bg=PANEL, font=LBL).pack(side="left", padx=(8, 2))
        self._rnd_var = tk.StringVar(value="전체")
        self._rnd_cb  = ttk.Combobox(flt, textvariable=self._rnd_var, width=14,
                                      state="readonly")
        self._rnd_cb.pack(side="left", padx=2)
        self._rnd_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        tk.Label(flt, text="심볼:", bg=PANEL, font=LBL).pack(side="left", padx=(12, 2))
        self._sym_var = tk.StringVar(value="전체")
        sym_cb = ttk.Combobox(flt, textvariable=self._sym_var, width=12,
                               values=["전체", "BTCUSD", "XAUUSD"], state="readonly")
        sym_cb.pack(side="left", padx=2)
        sym_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        tk.Label(flt, text="정렬:", bg=PANEL, font=LBL).pack(side="left", padx=(12, 2))
        self._sort_var = tk.StringVar(value="score")
        sort_cb = ttk.Combobox(flt, textvariable=self._sort_var, width=14,
                                values=["score", "profit", "drawdown_pct",
                                        "profit_factor", "trades"],
                                state="readonly")
        sort_cb.pack(side="left", padx=2)
        sort_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        tk.Label(flt, text="상위:", bg=PANEL, font=LBL).pack(side="left", padx=(12, 2))
        self._top_var = tk.StringVar(value="50")
        ttk.Combobox(flt, textvariable=self._top_var, width=6,
                     values=["20", "50", "100", "200", "전체"],
                     state="readonly").pack(side="left", padx=2)

        B(flt, "적용", BLUE, self._apply_filter, padx=6).pack(side="left", padx=8)

        self._stat_lbl = tk.Label(flt, text="", bg=PANEL, fg=TEAL, font=LBL)
        self._stat_lbl.pack(side="right", padx=10)

        # ── 메인 PanedWindow ────────────────────────────────────────
        pw = tk.PanedWindow(self, orient="vertical", bg=BG, sashwidth=5,
                            sashrelief="raised")
        pw.pack(fill="both", expand=True, padx=6, pady=4)

        # ── 상단: Treeview ──────────────────────────────────────────
        top_fr = tk.Frame(pw, bg=BG)
        pw.add(top_fr, minsize=180)
        self._build_tree(top_fr)

        # ── 하단: 차트 탭 ───────────────────────────────────────────
        bot_fr = tk.Frame(pw, bg=BG)
        pw.add(bot_fr, minsize=260)
        self._build_charts(bot_fr)

    def _build_tree(self, parent):
        cols = ("sc_id", "round", "symbol", "profit", "drawdown_pct",
                "profit_factor", "trades", "score")
        hdrs = ("SC", "Round", "심볼", "수익($)", "DD(%)",
                "PF", "거래수", "점수")
        widths = (50, 80, 80, 100, 70, 60, 70, 65)

        tree_fr = tk.Frame(parent, bg=BG)
        tree_fr.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_fr, orient="vertical")
        hsb = ttk.Scrollbar(tree_fr, orient="horizontal")
        self._tree = ttk.Treeview(
            tree_fr, columns=cols, show="headings",
            yscrollcommand=vsb.set, xscrollcommand=hsb.set, height=10)
        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(side="left", fill="both", expand=True)

        for col, hdr, w in zip(cols, hdrs, widths):
            self._tree.heading(col, text=hdr,
                               command=lambda c=col: self._sort_tree(c))
            anchor = "center" if col in ("sc_id", "round", "symbol") else "e"
            self._tree.column(col, width=w, anchor=anchor, minwidth=40)

        # 색상 태그
        self._tree.tag_configure("btc",  background="#fffbeb")
        self._tree.tag_configure("gold", background="#f0f4ff")
        self._tree.tag_configure("top",  foreground=GREEN)

    def _build_charts(self, parent):
        if not HAS_MPL:
            tk.Label(parent, text="matplotlib 없음 — pip install matplotlib",
                     bg=BG, fg=RED).pack()
            return

        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        # Tab 1: 상위 EA 바차트
        self._fig1 = Figure(figsize=(10, 3.5), facecolor=BG, tight_layout=True)
        self._ax1a = self._fig1.add_subplot(121)
        self._ax1b = self._fig1.add_subplot(122)
        t1 = tk.Frame(nb, bg=BG)
        nb.add(t1, text="  상위 EA 비교  ")
        FigureCanvasTkAgg(self._fig1, t1).get_tk_widget().pack(
            fill="both", expand=True)

        # Tab 2: 라운드별 추이
        self._fig2 = Figure(figsize=(10, 3.5), facecolor=BG, tight_layout=True)
        self._ax2a = self._fig2.add_subplot(121)
        self._ax2b = self._fig2.add_subplot(122)
        t2 = tk.Frame(nb, bg=BG)
        nb.add(t2, text="  라운드별 추이  ")
        FigureCanvasTkAgg(self._fig2, t2).get_tk_widget().pack(
            fill="both", expand=True)

        # Tab 3: BTC vs GOLD 산점도
        self._fig3 = Figure(figsize=(10, 3.5), facecolor=BG, tight_layout=True)
        self._ax3  = self._fig3.add_subplot(111)
        t3 = tk.Frame(nb, bg=BG)
        nb.add(t3, text="  BTC vs GOLD  ")
        FigureCanvasTkAgg(self._fig3, t3).get_tk_widget().pack(
            fill="both", expand=True)

        self._chart_nb = nb

    # ── 데이터 로드 ─────────────────────────────────────────────────
    def _load_data(self):
        self._stat_lbl.config(text="로딩 중...", fg=AMBER)
        threading.Thread(target=self._load_thread, daemon=True).start()

    def _load_thread(self):
        try:
            df = _load_all_results()
            if df.empty:
                self.after(0, lambda: self._stat_lbl.config(
                    text="데이터 없음 (g4_results/ 확인)", fg=RED))
                return
            self._df = _best_per_sc_round_sym(df)
            rounds = ["전체"] + sorted(self._df["round"].unique())
            self.after(0, lambda: self._rnd_cb.config(values=rounds))
            self.after(0, self._apply_filter)
        except Exception as e:
            self.after(0, lambda: self._stat_lbl.config(
                text=f"오류: {e}", fg=RED))

    # ── 필터 적용 ───────────────────────────────────────────────────
    def _apply_filter(self):
        if self._df.empty:
            return
        df = self._df.copy()

        rnd = self._rnd_var.get()
        if rnd != "전체":
            df = df[df["round"] == rnd]

        sym = self._sym_var.get()
        if sym != "전체":
            df = df[df["symbol"] == sym]

        sort_col = self._sort_var.get()
        asc = sort_col == "drawdown_pct"
        df = df.sort_values(sort_col, ascending=asc)

        top = self._top_var.get()
        if top != "전체":
            df = df.head(int(top))

        self._view = df
        self._refresh_tree()
        if HAS_MPL:
            self._refresh_charts()
        self._stat_lbl.config(
            text=f"표시: {len(df)}개  (전체 {len(self._df)}개)", fg=TEAL)

    # ── 트리 갱신 ───────────────────────────────────────────────────
    def _refresh_tree(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for _, r in self._view.iterrows():
            tag = "btc" if r["symbol"] == "BTCUSD" else "gold"
            self._tree.insert("", "end", values=(
                f"SC{int(r['sc_id']):03d}",
                r["round"],
                r["symbol"],
                f"{r['profit']:,.0f}",
                f"{r['drawdown_pct']:.1f}",
                f"{r['profit_factor']:.2f}",
                f"{int(r['trades']):,}",
                f"{r['score']:.1f}",
            ), tags=(tag,))

    def _sort_tree(self, col):
        self._sort_var.set(col)
        self._apply_filter()

    # ── 차트 갱신 ───────────────────────────────────────────────────
    def _refresh_charts(self):
        if self._view.empty:
            return
        df = self._view
        # ─ 차트 1: 상위 20 EA 수익 바차트 (BTC vs GOLD 색상) ────────
        self._ax1a.clear(); self._ax1b.clear()

        top20 = df.nlargest(20, "score")
        colors = [BTC_COLOR if s == "BTCUSD" else GOLD_COLOR
                  for s in top20["symbol"]]
        labels = [f"SC{int(x):03d} R{r}" for x, r in
                  zip(top20["sc_id"], top20["round"])]

        self._ax1a.barh(range(len(top20)), top20["profit"].values,
                        color=colors, edgecolor="white", linewidth=0.3)
        self._ax1a.set_yticks(range(len(top20)))
        self._ax1a.set_yticklabels(labels, fontsize=7)
        self._ax1a.invert_yaxis()
        self._ax1a.set_xlabel("수익 ($)", fontsize=8)
        self._ax1a.set_title("상위 20 EA — 수익", fontsize=9)
        self._ax1a.tick_params(labelsize=7)

        self._ax1b.barh(range(len(top20)), top20["score"].values,
                        color=colors, edgecolor="white", linewidth=0.3)
        self._ax1b.set_yticks(range(len(top20)))
        self._ax1b.set_yticklabels(labels, fontsize=7)
        self._ax1b.invert_yaxis()
        self._ax1b.set_xlabel("점수", fontsize=8)
        self._ax1b.set_title("상위 20 EA — 점수", fontsize=9)
        self._ax1b.tick_params(labelsize=7)

        legend = [mpatches.Patch(color=BTC_COLOR, label="BTCUSD"),
                  mpatches.Patch(color=GOLD_COLOR, label="XAUUSD")]
        self._ax1b.legend(handles=legend, fontsize=7, loc="lower right")
        self._fig1.canvas.draw_idle()

        # ─ 차트 2: 라운드별 평균 수익/점수 ──────────────────────────
        self._ax2a.clear(); self._ax2b.clear()
        g = df.groupby(["round", "symbol"])[["profit", "score"]].mean().reset_index()
        for sym, col in [("BTCUSD", BTC_COLOR), ("XAUUSD", GOLD_COLOR)]:
            sub = g[g["symbol"] == sym].sort_values("round")
            if sub.empty:
                continue
            rnds = sub["round"].tolist()
            self._ax2a.plot(rnds, sub["profit"].values, "o-", color=col,
                            label=sym, linewidth=1.5, markersize=5)
            self._ax2b.plot(rnds, sub["score"].values,  "o-", color=col,
                            label=sym, linewidth=1.5, markersize=5)

        self._ax2a.set_title("라운드별 평균 수익", fontsize=9)
        self._ax2a.set_xlabel("Round", fontsize=8)
        self._ax2a.set_ylabel("평균 수익 ($)", fontsize=8)
        self._ax2a.tick_params(labelsize=7)
        self._ax2a.legend(fontsize=7)

        self._ax2b.set_title("라운드별 평균 점수", fontsize=9)
        self._ax2b.set_xlabel("Round", fontsize=8)
        self._ax2b.set_ylabel("평균 점수", fontsize=8)
        self._ax2b.tick_params(labelsize=7)
        self._ax2b.legend(fontsize=7)
        self._fig2.canvas.draw_idle()

        # ─ 차트 3: BTC vs GOLD 산점도 (동일 SC) ────────────────────
        self._ax3.clear()
        btc  = df[df["symbol"] == "BTCUSD"].set_index(["sc_id", "round"])
        gold = df[df["symbol"] == "XAUUSD"].set_index(["sc_id", "round"])
        common = btc.index.intersection(gold.index)
        if len(common) > 0:
            bx = btc.loc[common, "score"].values
            gy = gold.loc[common, "score"].values
            self._ax3.scatter(bx, gy, alpha=0.6, s=30,
                              c="#0284c7", edgecolors="white", linewidth=0.3)
            mn = min(bx.min(), gy.min()) - 2
            mx = max(bx.max(), gy.max()) + 2
            self._ax3.plot([mn, mx], [mn, mx], "--", color="gray",
                           linewidth=0.8, label="BTC=GOLD 기준선")
            self._ax3.set_xlabel("BTC 점수", fontsize=8)
            self._ax3.set_ylabel("GOLD 점수", fontsize=8)
            self._ax3.set_title(f"BTC vs GOLD 점수 산점도  (n={len(common)})",
                                fontsize=9)
            self._ax3.legend(fontsize=7)
            self._ax3.tick_params(labelsize=7)
        else:
            self._ax3.text(0.5, 0.5, "공통 SC 없음",
                           ha="center", va="center", transform=self._ax3.transAxes)
        self._fig3.canvas.draw_idle()

    # ── HTML 내보내기 ────────────────────────────────────────────────
    def _export_html(self):
        if self._view.empty:
            messagebox.showwarning("경고", "데이터 없음")
            return
        threading.Thread(target=self._export_thread, daemon=True).start()

    def _export_thread(self):
        try:
            os.makedirs(OUT_DIR, exist_ok=True)
            from datetime import datetime
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(OUT_DIR, f"performance_{ts}.html")
            html = self._build_html()
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.after(0, lambda: messagebox.showinfo(
                "완료", f"저장됨:\n{path}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("오류", str(e)))

    def _fig_to_b64(self, fig) -> str:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        return base64.b64encode(buf.getvalue()).decode()

    def _build_html(self) -> str:
        df = self._view
        rnd_sel = self._rnd_var.get()
        sym_sel = self._sym_var.get()
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 통계 요약
        btc_rows  = df[df["symbol"] == "BTCUSD"]
        gold_rows = df[df["symbol"] == "XAUUSD"]

        def stat_block(rows, title, color):
            if rows.empty:
                return f"<p style='color:#999'>데이터 없음</p>"
            return f"""
            <div style='background:{color}22;border:2px solid {color};border-radius:8px;
                        padding:12px;flex:1;min-width:220px'>
              <h3 style='margin:0 0 8px;color:{color}'>{title}</h3>
              <table style='width:100%;border-collapse:collapse;font-size:13px'>
                <tr><td>결과 수</td><td align='right'><b>{len(rows)}</b></td></tr>
                <tr><td>평균 수익</td><td align='right'><b>${rows['profit'].mean():,.0f}</b></td></tr>
                <tr><td>최고 수익</td><td align='right'><b>${rows['profit'].max():,.0f}</b></td></tr>
                <tr><td>평균 점수</td><td align='right'><b>{rows['score'].mean():.1f}</b></td></tr>
                <tr><td>최고 점수</td><td align='right'><b>{rows['score'].max():.1f}</b></td></tr>
                <tr><td>평균 DD</td><td align='right'><b>{rows['drawdown_pct'].mean():.1f}%</b></td></tr>
                <tr><td>평균 PF</td><td align='right'><b>{rows['profit_factor'].mean():.2f}</b></td></tr>
              </table>
            </div>"""

        # 테이블 행
        table_rows = []
        for _, r in df.iterrows():
            sym_col = BTC_COLOR if r["symbol"] == "BTCUSD" else GOLD_COLOR
            table_rows.append(f"""
            <tr>
              <td align='center'><b>SC{int(r['sc_id']):03d}</b></td>
              <td align='center'>R{r['round']}</td>
              <td align='center'><span style='background:{sym_col}33;color:{sym_col};
                  padding:2px 8px;border-radius:4px;font-weight:bold'>{r['symbol']}</span></td>
              <td align='right'>${r['profit']:,.0f}</td>
              <td align='right'>{r['drawdown_pct']:.1f}%</td>
              <td align='right'>{r['profit_factor']:.2f}</td>
              <td align='right'>{int(r['trades']):,}</td>
              <td align='right'><b>{r['score']:.1f}</b></td>
            </tr>""")

        # 차트 이미지
        charts_html = ""
        if HAS_MPL:
            for fig, title in [
                (self._fig1, "상위 EA 수익/점수 비교"),
                (self._fig2, "라운드별 평균 추이"),
                (self._fig3, "BTC vs GOLD 점수 산점도"),
            ]:
                b64 = self._fig_to_b64(fig)
                charts_html += f"""
                <div style='margin:20px 0'>
                  <h3 style='color:#0369a1;border-bottom:2px solid #0369a1;padding-bottom:4px'>
                    {title}</h3>
                  <img src='data:image/png;base64,{b64}'
                       style='max-width:100%;border-radius:6px;box-shadow:0 2px 8px #0002'>
                </div>"""

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>EA 성과 분석 — BTC / GOLD</title>
<style>
  body {{font-family:'Malgun Gothic',sans-serif;margin:0;padding:20px;
        background:#f0f9ff;color:#0f172a}}
  h1   {{color:#0369a1;margin-bottom:4px}}
  .meta{{color:#64748b;font-size:13px;margin-bottom:20px}}
  .stat-wrap{{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}}
  table.data{{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}}
  table.data th{{background:#0369a1;color:#fff;padding:7px 10px;text-align:center}}
  table.data td{{padding:5px 10px;border-bottom:1px solid #dbeafe}}
  table.data tr:hover td{{background:#eff6ff}}
  .section{{background:#fff;border-radius:8px;padding:16px;
            margin-bottom:20px;box-shadow:0 1px 4px #0001}}
</style>
</head>
<body>
<h1>📊  EA 성과 분석 — BTC / GOLD</h1>
<div class='meta'>
  생성: {now} &nbsp;|&nbsp; 라운드: {rnd_sel} &nbsp;|&nbsp;
  심볼: {sym_sel} &nbsp;|&nbsp; 표시: {len(df)}개
</div>

<div class='section'>
  <h2 style='margin-top:0;color:#0369a1'>요약 통계</h2>
  <div class='stat-wrap'>
    {stat_block(btc_rows,  'BTCUSD', BTC_COLOR)}
    {stat_block(gold_rows, 'XAUUSD (GOLD)', GOLD_COLOR)}
  </div>
</div>

<div class='section'>
  <h2 style='margin-top:0;color:#0369a1'>차트</h2>
  {charts_html if charts_html else '<p style="color:#999">matplotlib 없음</p>'}
</div>

<div class='section'>
  <h2 style='margin-top:0;color:#0369a1'>전체 성과 테이블</h2>
  <table class='data'>
    <thead>
      <tr>
        <th>SC</th><th>Round</th><th>심볼</th>
        <th>수익($)</th><th>DD(%)</th><th>PF</th><th>거래수</th><th>점수</th>
      </tr>
    </thead>
    <tbody>
      {''.join(table_rows)}
    </tbody>
  </table>
</div>

<div style='color:#94a3b8;font-size:11px;text-align:right;margin-top:8px'>
  EA Auto Master v7.0 — 자동 생성
</div>
</body>
</html>"""
