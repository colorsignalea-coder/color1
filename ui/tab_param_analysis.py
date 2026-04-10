"""
ui/tab_param_analysis.py — EA Auto Master v7.0
================================================
파라미터 영향도 분석 + 시뮬레이터 탭:
  - g4_results/ JSON 전체 로드
  - 심볼별 파라미터 vs 수익 상관관계 시각화
  - Top/Bottom 비교 바차트, 히트맵
  - 🎮 시뮬레이터: 슬라이더로 파라미터 조정 → GBR+KNN 예측
  - CSV 내보내기
"""

import glob
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import pandas as pd

# sklearn: AppData 경로 fallback 포함
_SKLEARN_PATHS = [
    os.path.join(os.environ.get("APPDATA",""), "Python","Python313","site-packages"),
    os.path.join(os.environ.get("LOCALAPPDATA",""),
                 "Packages","PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0",
                 "LocalCache","local-packages","Python313","site-packages"),
]
for _p in _SKLEARN_PATHS:
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    HAS_SKL = True
except ImportError:
    HAS_SKL = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from core.config import HERE
from ui.theme import BG, FG, PANEL, PANEL2, BLUE, GREEN, TEAL, AMBER, RED, B, LBL, TITLE, MONO

# ── 파라미터 목록 ───────────────────────────────────────────────
PARAMS = ['SL', 'TP', 'TP_SL_ratio', 'ATR', 'FastMA', 'SlowMA',
          'ADXPeriod', 'ADXMin', 'RSIPeriod', 'RSILower', 'RSIUpper',
          'MaxDD', 'MaxPos', 'Cooldown']

METRICS = ['profit', 'score', 'drawdown_pct', 'profit_factor', 'trades']

DARK = "#0d1117"
DPANEL = "#161b22"
DGRID = "#30363d"
DTEXT = "#c9d1d9"
SYM_COLOR = {'XAUUSD': '#FFD700', 'BTCUSD': '#F7931A'}


def _load_df(results_dir: str) -> pd.DataFrame:
    """g4_results/ JSON 파일들을 읽어 DataFrame 반환."""
    rows = []
    for f in sorted(glob.glob(os.path.join(results_dir, '*.json'))):
        try:
            with open(f, encoding='utf-8') as fp:
                d = json.load(fp)
            if not (isinstance(d, dict) and 'results' in d):
                continue
            rnd = d.get('round', 0)
            for r in d['results']:
                if r.get('score', 0) <= 0:
                    continue
                p = r.get('params', {})
                for c in r.get('combos', []):
                    if c.get('score', 0) <= 0:
                        continue
                    row = {
                        'ea_name': r.get('ea_name', ''),
                        'round': rnd,
                        'symbol': c.get('sym', d.get('symbol', '')),
                        'profit': float(c.get('profit', r.get('profit', 0))),
                        'drawdown_pct': float(c.get('dd', r.get('drawdown_pct', 0))),
                        'score': float(c.get('score', r.get('score', 0))),
                        'profit_factor': float(r.get('profit_factor', 0)),
                        'trades': int(r.get('trades', 0)),
                        'SL': p.get('InpSLMultiplier', 0),
                        'TP': p.get('InpTPMultiplier', 0),
                        'ATR': p.get('InpATRPeriod', 0),
                        'FastMA': p.get('InpFastMA', 0),
                        'SlowMA': p.get('InpSlowMA', 0),
                        'ADXPeriod': p.get('InpADXPeriod', 0),
                        'ADXMin': p.get('InpADXMin', 0),
                        'RSIPeriod': p.get('InpRSIPeriod', 0),
                        'RSILower': p.get('InpRSILower', 0),
                        'RSIUpper': p.get('InpRSIUpper', 0),
                        'MaxDD': p.get('InpMaxDD', 0),
                        'MaxPos': p.get('InpMaxPositions', 0),
                        'Cooldown': p.get('InpCooldownBars', 0),
                    }
                    sl = row['SL'] or 0.01
                    row['TP_SL_ratio'] = round(row['TP'] / sl, 2)
                    rows.append(row)
        except Exception:
            pass
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df[df['profit'] > 0].copy()


# ── 파라미터 범위 정의 (슬라이더용) ─────────────────────────────
PARAM_RANGES = {
    'SL':        (0.10, 0.80, 0.025, float),
    'TP':        (4.0,  28.0, 0.5,   float),
    'ATR':       (7,    28,   1,     int),
    'FastMA':    (5,    20,   1,     int),
    'SlowMA':    (14,   55,   1,     int),
    'ADXPeriod': (10,   30,   2,     int),
    'ADXMin':    (15.0, 35.0, 2.5,   float),
    'RSIPeriod': (7,    21,   2,     int),
    'RSILower':  (25.0, 45.0, 5.0,   float),
    'RSIUpper':  (55.0, 75.0, 5.0,   float),
    'MaxDD':     (5.0,  25.0, 2.5,   float),
    'MaxPos':    (1,    5,    1,     int),
    'Cooldown':  (1,    10,   1,     int),
}
# TP_SL_ratio 는 SL/TP에서 자동 계산

SIM_FEATURES = [p for p in PARAMS if p != 'TP_SL_ratio']  # 13개 (TP_SL_ratio 제외)


class ParamAnalysisTab(ttk.Frame):
    """파라미터 영향도 분석 + 시뮬레이터 탭"""

    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        self._df = pd.DataFrame()
        self._results_dir = os.path.join(
            cfg.get("solo_dir", HERE), "g4_results"
        )
        if not os.path.isdir(self._results_dir):
            self._results_dir = os.path.join(HERE, "g4_results")
        self._sym_var = tk.StringVar(value="ALL")
        self._chart_var = tk.StringVar(value="scatter")
        self._x_var = tk.StringVar(value="TP")
        self._canvas_widget = None
        self._sim_frame = None        # 시뮬레이터 전용 프레임
        self._fig = None
        # 시뮬레이터 모델
        self._models = {}             # {sym: {'profit': gbr, 'score': gbr, 'dd': gbr}}
        self._scaler = {}             # {sym: StandardScaler}
        self._model_ready = False
        self._sim_after_id = None     # debounce
        # 슬라이더 변수
        self._slider_vars = {}
        self._build()
        self.after(200, self._load_data)

    # ─────────────────────────────────────────────────────────
    def _build(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True, padx=6, pady=4)

        # ── 상단 컨트롤 ─────────────────────────────────────
        ctrl = tk.LabelFrame(root, text="  데이터 설정  ", font=TITLE,
                             fg=FG, bg=PANEL, relief="groove", bd=2)
        ctrl.pack(fill="x", pady=(0, 4))

        row1 = tk.Frame(ctrl, bg=PANEL)
        row1.pack(fill="x", padx=8, pady=4)

        # 결과 폴더
        tk.Label(row1, text="결과폴더:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        self._dir_var = tk.StringVar(value=self._results_dir)
        tk.Entry(row1, textvariable=self._dir_var, font=MONO, bg=PANEL2, fg=TEAL,
                 relief="flat", width=50).pack(side="left", padx=4)
        B(row1, "...", TEAL, self._pick_dir, padx=5).pack(side="left")
        B(row1, "🔄 새로고침", BLUE, self._load_data, padx=8).pack(side="left", padx=4)

        row2 = tk.Frame(ctrl, bg=PANEL)
        row2.pack(fill="x", padx=8, pady=4)

        # 심볼 필터
        tk.Label(row2, text="심볼:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        for sym in ["ALL", "XAUUSD", "BTCUSD"]:
            tk.Radiobutton(row2, text=sym, variable=self._sym_var, value=sym,
                           font=LBL, fg=FG, bg=PANEL, activebackground=PANEL,
                           selectcolor=PANEL2, command=self._redraw
                           ).pack(side="left", padx=4)

        tk.Label(row2, text="   차트종류:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        charts = [("산점도+상관관계", "scatter"), ("박스플롯(수익구간)", "boxplot"),
                  ("히트맵", "heatmap"), ("Top/Bottom비교", "topbot"),
                  ("수익구간별파라미터", "bins"), ("🎮 시뮬레이터", "sim")]
        for txt, val in charts:
            tk.Radiobutton(row2, text=txt, variable=self._chart_var, value=val,
                           font=LBL, fg=FG, bg=PANEL, activebackground=PANEL,
                           selectcolor=PANEL2, command=self._redraw
                           ).pack(side="left", padx=3)

        row3 = tk.Frame(ctrl, bg=PANEL)
        row3.pack(fill="x", padx=8, pady=4)

        # 산점도 X축 선택
        tk.Label(row3, text="X축 파라미터:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        cb = ttk.Combobox(row3, textvariable=self._x_var, values=PARAMS,
                          font=MONO, width=14, state="readonly")
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._redraw())

        B(row3, "📊 차트 저장", GREEN, self._save_chart, padx=8).pack(side="left", padx=8)
        B(row3, "💾 CSV 내보내기", AMBER, self._export_csv, padx=8).pack(side="left")

        # 상태 레이블
        self._status = tk.Label(row3, text="로딩 중...", font=LBL, fg=TEAL, bg=PANEL)
        self._status.pack(side="right", padx=10)

        # ── 메인 분할: 차트(왼) + 통계표(오) ──────────────────
        pane = tk.PanedWindow(root, orient="horizontal", bg=BG,
                              sashwidth=5, sashrelief="flat")
        pane.pack(fill="both", expand=True)

        # 차트 영역
        self._chart_frame = tk.Frame(pane, bg=DARK, relief="flat", bd=2)
        pane.add(self._chart_frame, width=820, minsize=400)

        if not HAS_MPL:
            tk.Label(self._chart_frame,
                     text="matplotlib 없음\npip install matplotlib",
                     fg="red", bg=DARK, font=TITLE).pack(expand=True)

        # 통계 테이블 영역
        right = tk.Frame(pane, bg=BG)
        pane.add(right, minsize=200)
        self._build_stats_panel(right)

    def _build_stats_panel(self, parent):
        tk.Label(parent, text="📋 상관계수 순위", font=TITLE, fg=FG, bg=BG
                 ).pack(fill="x", pady=(4, 2), padx=4)

        cols = ("파라미터", "XAU r", "BTC r", "우위")
        self._corr_tree = ttk.Treeview(parent, columns=cols, show="headings",
                                       height=15, selectmode="browse")
        for c, w in zip(cols, [90, 60, 60, 60]):
            self._corr_tree.heading(c, text=c)
            self._corr_tree.column(c, width=w, anchor="center")
        self._corr_tree.pack(fill="x", padx=4, pady=2)

        # 구분선
        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=4, pady=4)

        tk.Label(parent, text="📊 요약 통계", font=TITLE, fg=FG, bg=BG
                 ).pack(fill="x", pady=(0, 2), padx=4)

        self._summary_text = tk.Text(parent, height=18, font=MONO, bg=PANEL,
                                     fg=FG, relief="flat", bd=4, wrap="word",
                                     state="disabled")
        self._summary_text.pack(fill="both", expand=True, padx=4, pady=2)

    # ─────────────────────────────────────────────────────────
    def _pick_dir(self):
        d = filedialog.askdirectory(title="g4_results 폴더 선택",
                                    initialdir=self._results_dir)
        if d:
            self._dir_var.set(d)
            self._results_dir = d
            self._load_data()

    def _load_data(self):
        self._status.config(text="⏳ 로딩 중...", fg=AMBER)
        self._model_ready = False
        self.update()

        def _worker():
            try:
                df = _load_df(self._dir_var.get())
                self._df = df
                n = len(df)
                xau = (df.symbol == 'XAUUSD').sum() if not df.empty else 0
                btc = (df.symbol == 'BTCUSD').sum() if not df.empty else 0
                self.after(0, lambda: self._status.config(
                    text=f"✅ {n}건 로드 (XAU={xau} / BTC={btc})  — 모델 학습 중...", fg=AMBER))
                self.after(0, self._update_stats)
                self.after(0, self._redraw)
                # 모델 학습 (백그라운드에서 계속)
                self._train_models(df)
            except Exception as e:
                self.after(0, lambda: self._status.config(
                    text=f"❌ 오류: {e}", fg=RED))

        threading.Thread(target=_worker, daemon=True).start()

    def _train_models(self, df: pd.DataFrame):
        """GradientBoosting 모델 학습 (백그라운드 스레드)"""
        if not HAS_SKL or df.empty:
            self.after(0, lambda: self._status.config(
                text="⚠️ sklearn 없음 — KNN 모드로 동작", fg=AMBER))
            self._model_ready = True
            return
        try:
            self._models = {}
            self._scaler = {}
            for sym in df['symbol'].unique():
                sub = df[df['symbol'] == sym].dropna(subset=SIM_FEATURES)
                if len(sub) < 15:
                    continue
                X = sub[SIM_FEATURES].values.astype(float)
                sc = StandardScaler()
                Xs = sc.fit_transform(X)
                self._scaler[sym] = sc
                self._models[sym] = {}
                for target in ['profit', 'score', 'drawdown_pct']:
                    y = sub[target].values.astype(float)
                    gbr = GradientBoostingRegressor(
                        n_estimators=200, max_depth=4,
                        learning_rate=0.05, subsample=0.8,
                        random_state=42)
                    gbr.fit(Xs, y)
                    self._models[sym][target] = gbr
            self._model_ready = True
            n = len(df)
            xau = (df.symbol == 'XAUUSD').sum()
            btc = (df.symbol == 'BTCUSD').sum()
            self.after(0, lambda: self._status.config(
                text=f"✅ {n}건 로드 (XAU={xau} / BTC={btc})  ✔ 모델 학습 완료", fg=GREEN))
        except Exception as e:
            self._model_ready = True
            self.after(0, lambda: self._status.config(
                text=f"⚠️ 모델 학습 실패: {e}", fg=AMBER))

    def _get_filtered(self) -> pd.DataFrame:
        if self._df.empty:
            return self._df
        sym = self._sym_var.get()
        if sym == "ALL":
            return self._df
        return self._df[self._df['symbol'] == sym].copy()

    # ── 차트 그리기 ──────────────────────────────────────────
    def _redraw(self):
        chart = self._chart_var.get()
        # 시뮬레이터는 별도 처리
        if chart == "sim":
            self._show_simulator()
            return
        # 시뮬레이터 프레임 숨기기
        if self._sim_frame:
            self._sim_frame.pack_forget()
        if not HAS_MPL or self._df.empty:
            return
        try:
            if chart == "scatter":
                self._draw_scatter()
            elif chart == "boxplot":
                self._draw_boxplot()
            elif chart == "heatmap":
                self._draw_heatmap()
            elif chart == "topbot":
                self._draw_topbot()
            elif chart == "bins":
                self._draw_bins()
        except Exception as e:
            print(f"[ParamAnalysis] 차트 오류: {e}")
            import traceback
            traceback.print_exc()

    # ── 시뮬레이터 UI ─────────────────────────────────────────
    def _show_simulator(self):
        """matplotlib 캔버스 숨기고 시뮬레이터 프레임 표시."""
        # matplotlib 캔버스 숨기기
        if self._canvas_widget:
            self._canvas_widget.get_tk_widget().pack_forget()
            try:
                self._canvas_widget.toolbar.pack_forget()
            except Exception:
                pass

        if self._sim_frame is None:
            self._build_simulator()
        self._sim_frame.pack(fill="both", expand=True)
        self._run_simulation()

    def _build_simulator(self):
        """시뮬레이터 UI 빌드 (최초 1회)."""
        self._sim_frame = tk.Frame(self._chart_frame, bg=DARK)

        # ── 상단: 심볼 선택 + 모델 정보 ────────────────────
        top = tk.Frame(self._sim_frame, bg="#1c2128")
        top.pack(fill="x", padx=8, pady=4)

        tk.Label(top, text="🎮  파라미터 시뮬레이터",
                 font=("Malgun Gothic", 11, "bold"), fg="#58a6ff", bg="#1c2128"
                 ).pack(side="left", padx=8)

        tk.Label(top, text="심볼:", font=LBL, fg=DTEXT, bg="#1c2128").pack(side="left", padx=(16, 2))
        self._sim_sym_var = tk.StringVar(value="XAUUSD")
        for sym in ["XAUUSD", "BTCUSD"]:
            tk.Radiobutton(top, text=sym, variable=self._sim_sym_var, value=sym,
                           font=LBL, fg=DTEXT, bg="#1c2128",
                           activebackground="#1c2128", selectcolor=DPANEL,
                           command=self._run_simulation
                           ).pack(side="left", padx=3)

        self._model_info = tk.Label(top, text="", font=MONO, fg="#56d364", bg="#1c2128")
        self._model_info.pack(side="right", padx=12)

        # ── 메인 분할: 슬라이더(왼) + 결과(오) ─────────────
        main = tk.Frame(self._sim_frame, bg=DARK)
        main.pack(fill="both", expand=True, padx=4, pady=4)

        # 슬라이더 패널
        slider_outer = tk.LabelFrame(main, text="  파라미터 설정  ",
                                     font=("Malgun Gothic", 9, "bold"),
                                     fg="#79c0ff", bg=DPANEL, relief="groove", bd=2)
        slider_outer.pack(side="left", fill="both", expand=True, padx=(0, 4))

        canvas_s = tk.Canvas(slider_outer, bg=DPANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(slider_outer, orient="vertical", command=canvas_s.yview)
        self._slider_inner = tk.Frame(canvas_s, bg=DPANEL)
        self._slider_inner.bind("<Configure>",
            lambda e: canvas_s.configure(scrollregion=canvas_s.bbox("all")))
        canvas_s.create_window((0, 0), window=self._slider_inner, anchor="nw")
        canvas_s.configure(yscrollcommand=scrollbar.set)
        canvas_s.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._build_sliders(self._slider_inner)

        # 결과 패널
        result_outer = tk.Frame(main, bg=DPANEL, width=340)
        result_outer.pack(side="right", fill="y", padx=(4, 0))
        result_outer.pack_propagate(False)
        self._build_result_panel(result_outer)

    def _build_sliders(self, parent):
        """파라미터 슬라이더 생성."""
        self._slider_vars = {}
        self._val_labels = {}

        for i, (param, (mn, mx, step, dtype)) in enumerate(PARAM_RANGES.items()):
            row = tk.Frame(parent, bg=DPANEL)
            row.pack(fill="x", padx=8, pady=3)

            # 파라미터 이름
            tk.Label(row, text=f"{param:12s}", font=MONO,
                     fg="#79c0ff", bg=DPANEL, width=12, anchor="w"
                     ).pack(side="left")

            # 범위 표시
            tk.Label(row, text=f"{mn}", font=MONO,
                     fg="#8b949e", bg=DPANEL, width=5, anchor="e"
                     ).pack(side="left")

            # 슬라이더 (resolution=step)
            var = tk.DoubleVar(value=(mn + mx) / 2)
            self._slider_vars[param] = var

            sl = tk.Scale(row, from_=mn, to=mx, resolution=step,
                          orient="horizontal", variable=var,
                          bg=DPANEL, fg=DTEXT, troughcolor="#21262d",
                          highlightthickness=0, relief="flat",
                          length=220, showvalue=False,
                          command=lambda v, p=param: self._on_slider(p, v))
            sl.pack(side="left", padx=4)

            tk.Label(row, text=f"{mx}", font=MONO,
                     fg="#8b949e", bg=DPANEL, width=5, anchor="w"
                     ).pack(side="left")

            # 현재 값 표시
            val_lbl = tk.Label(row, text=f"{(mn+mx)/2:.2f}" if dtype == float else f"{int((mn+mx)/2)}",
                               font=("Consolas", 10, "bold"),
                               fg="#f0e68c", bg=DPANEL, width=6)
            val_lbl.pack(side="left", padx=4)
            self._val_labels[param] = val_lbl

        # 초기화 버튼
        btn_row = tk.Frame(parent, bg=DPANEL)
        btn_row.pack(fill="x", padx=8, pady=8)
        B(btn_row, "⟳ 기본값으로", "#30363d", self._reset_sliders, padx=6
          ).pack(side="left", padx=4)
        B(btn_row, "★ 최적값 로드", TEAL, self._load_best_params, padx=6
          ).pack(side="left", padx=4)

    def _build_result_panel(self, parent):
        """예측 결과 패널."""
        tk.Label(parent, text="📊 예측 결과",
                 font=("Malgun Gothic", 10, "bold"), fg="#58a6ff", bg=DPANEL
                 ).pack(pady=(8, 4))

        # ── 주요 지표 (크게 표시) ─────────────────────────
        gauges = tk.Frame(parent, bg=DPANEL)
        gauges.pack(fill="x", padx=8, pady=4)

        self._gauge_labels = {}
        gauge_defs = [
            ("💰 예측 수익", "profit",    "#56d364", "$0"),
            ("🎯 예측 Score", "score",    "#58a6ff", "0.0"),
            ("📉 예측 DD%",   "dd",       "#f85149", "0%"),
            ("⚡ 신뢰도",     "conf",     "#e3a53a", "—"),
        ]
        for lbl_text, key, color, default in gauge_defs:
            cell = tk.Frame(gauges, bg="#21262d", relief="flat", bd=1)
            cell.pack(fill="x", pady=3, padx=4)
            tk.Label(cell, text=lbl_text, font=LBL, fg="#8b949e", bg="#21262d"
                     ).pack(pady=(4, 0))
            val_lbl = tk.Label(cell, text=default,
                               font=("Consolas", 18, "bold"), fg=color, bg="#21262d")
            val_lbl.pack(pady=(0, 4))
            self._gauge_labels[key] = val_lbl

        # ── 예측 범위 ─────────────────────────────────────
        range_frame = tk.LabelFrame(parent, text="  예측 범위 (KNN 5개 유사 EA)  ",
                                    font=LBL, fg=DTEXT, bg=DPANEL,
                                    relief="groove", bd=1)
        range_frame.pack(fill="x", padx=6, pady=4)
        self._range_text = tk.Text(range_frame, height=6, font=MONO,
                                   bg="#0d1117", fg=DTEXT, relief="flat",
                                   bd=4, state="disabled")
        self._range_text.pack(fill="x", padx=4, pady=4)

        # ── 유사 EA 목록 ──────────────────────────────────
        tk.Label(parent, text="🔍 유사 EA (실제 결과)",
                 font=LBL, fg=DTEXT, bg=DPANEL).pack(pady=(8, 2))

        cols = ("EA명(축약)", "심볼", "수익", "Score", "DD%")
        self._sim_tree = ttk.Treeview(parent, columns=cols, show="headings",
                                      height=7, selectmode="browse")
        col_widths = [140, 55, 75, 55, 45]
        for c, w in zip(cols, col_widths):
            self._sim_tree.heading(c, text=c)
            self._sim_tree.column(c, width=w, anchor="center")
        self._sim_tree.pack(fill="x", padx=6, pady=4)
        self._sim_tree.tag_configure("top", foreground="#56d364")
        self._sim_tree.tag_configure("mid", foreground="#e3a53a")
        self._sim_tree.tag_configure("bot", foreground="#f85149")

    # ── 슬라이더 이벤트 ──────────────────────────────────────
    def _on_slider(self, param, val):
        """슬라이더 변경 → 값 레이블 업데이트 + 예측 debounce."""
        if param in self._val_labels:
            _, _, _, dtype = PARAM_RANGES.get(param, (0, 0, 1, float))
            v = float(val)
            txt = f"{v:.3f}" if dtype == float else f"{int(v)}"
            self._val_labels[param].config(text=txt)

        # FastMA < SlowMA 제약 체크
        if param == 'FastMA':
            fast = float(val)
            slow = self._slider_vars.get('SlowMA', tk.DoubleVar(value=30)).get()
            if fast >= slow:
                self._slider_vars['SlowMA'].set(min(fast + 5, PARAM_RANGES['SlowMA'][1]))
        elif param == 'SlowMA':
            slow = float(val)
            fast = self._slider_vars.get('FastMA', tk.DoubleVar(value=10)).get()
            if fast >= slow:
                self._slider_vars['FastMA'].set(max(slow - 5, PARAM_RANGES['FastMA'][0]))

        # debounce: 300ms 후 예측
        if self._sim_after_id:
            self.after_cancel(self._sim_after_id)
        self._sim_after_id = self.after(300, self._run_simulation)

    def _reset_sliders(self):
        """슬라이더를 파라미터 범위 중간값으로 초기화."""
        for param, (mn, mx, step, dtype) in PARAM_RANGES.items():
            if param in self._slider_vars:
                self._slider_vars[param].set((mn + mx) / 2)
                lbl_txt = f"{(mn+mx)/2:.3f}" if dtype == float else f"{int((mn+mx)/2)}"
                if param in self._val_labels:
                    self._val_labels[param].config(text=lbl_txt)
        self._run_simulation()

    def _load_best_params(self):
        """데이터에서 최고 수익 EA의 파라미터를 슬라이더에 로드."""
        sym = self._sim_sym_var.get()
        df = self._df if self._df.empty or sym == 'ALL' else self._df[self._df['symbol'] == sym]
        if df.empty:
            return
        best = df.loc[df['profit'].idxmax()]
        for param in SIM_FEATURES:
            if param in self._slider_vars and param in best:
                v = best[param]
                mn, mx, step, dtype = PARAM_RANGES[param]
                v = max(mn, min(mx, v))
                self._slider_vars[param].set(v)
                lbl_txt = f"{v:.3f}" if dtype == float else f"{int(v)}"
                if param in self._val_labels:
                    self._val_labels[param].config(text=lbl_txt)
        self._run_simulation()

    # ── 예측 실행 ────────────────────────────────────────────
    def _run_simulation(self):
        """현재 슬라이더 값으로 예측 실행."""
        if self._df.empty or not self._slider_vars:
            return

        sym = self._sim_sym_var.get()
        # 슬라이더 값 수집
        params_vec = []
        for param in SIM_FEATURES:
            _, _, _, dtype = PARAM_RANGES.get(param, (0, 100, 1, float))
            v = self._slider_vars.get(param, tk.DoubleVar(value=0)).get()
            params_vec.append(int(v) if dtype == int else float(v))

        # ── KNN 유사 EA 탐색 (항상 동작) ────────────────────
        sub = self._df[self._df['symbol'] == sym].copy()
        if sym not in self._df['symbol'].values or sub.empty:
            sub = self._df.copy()

        feat_matrix = sub[SIM_FEATURES].values.astype(float)
        query = np.array(params_vec, dtype=float)

        # 정규화 거리 계산
        feat_std = feat_matrix.std(axis=0) + 1e-9
        feat_mean = feat_matrix.mean(axis=0)
        norm_matrix = (feat_matrix - feat_mean) / feat_std
        norm_query = (query - feat_mean) / feat_std
        dists = np.linalg.norm(norm_matrix - norm_query, axis=1)
        k = min(10, len(sub))
        knn_idx = np.argsort(dists)[:k]
        knn_rows = sub.iloc[knn_idx]

        # KNN 가중 평균 (거리 역수 가중)
        weights = 1.0 / (dists[knn_idx] + 1e-6)
        weights /= weights.sum()
        knn_profit = float(np.dot(weights, knn_rows['profit'].values))
        knn_score  = float(np.dot(weights, knn_rows['score'].values))
        knn_dd     = float(np.dot(weights, knn_rows['drawdown_pct'].values))

        # ── GBR 모델 예측 (학습 완료 시) ─────────────────────
        gbr_profit = knn_profit
        gbr_score  = knn_score
        gbr_dd     = knn_dd
        use_model  = False

        if self._model_ready and sym in self._models and sym in self._scaler:
            try:
                Xq = self._scaler[sym].transform([params_vec])
                gbr_profit = float(self._models[sym]['profit'].predict(Xq)[0])
                gbr_score  = float(self._models[sym]['score'].predict(Xq)[0])
                gbr_dd     = float(self._models[sym]['drawdown_pct'].predict(Xq)[0])
                use_model  = True
            except Exception:
                pass

        # ── 앙상블: GBR 70% + KNN 30% ────────────────────────
        if use_model:
            pred_profit = gbr_profit * 0.7 + knn_profit * 0.3
            pred_score  = gbr_score  * 0.7 + knn_score  * 0.3
            pred_dd     = gbr_dd     * 0.7 + knn_dd     * 0.3
        else:
            pred_profit = knn_profit
            pred_score  = knn_score
            pred_dd     = knn_dd

        pred_profit = max(0, pred_profit)
        pred_score  = max(0, min(100, pred_score))
        pred_dd     = max(0, pred_dd)

        # ── 신뢰도: KNN 거리 기반 (거리 작을수록 신뢰도 높음) ──
        max_dist = dists[knn_idx].max() + 1e-6
        min_dist = dists[knn_idx].min()
        confidence = max(5, int(100 - (min_dist / max_dist) * 60))
        if use_model:
            confidence = min(confidence + 10, 95)

        # ── UI 업데이트 ───────────────────────────────────────
        # 수익 색상 (크면 초록, 작으면 빨강)
        all_mean = sub['profit'].mean() if not sub.empty else 50000
        profit_color = '#56d364' if pred_profit >= all_mean else '#f85149'

        self._gauge_labels['profit'].config(
            text=f"${pred_profit:,.0f}", fg=profit_color)
        self._gauge_labels['score'].config(
            text=f"{pred_score:.1f}")
        dd_color = '#56d364' if pred_dd < 15 else ('#e3a53a' if pred_dd < 25 else '#f85149')
        self._gauge_labels['dd'].config(
            text=f"{pred_dd:.1f}%", fg=dd_color)
        conf_color = '#56d364' if confidence > 70 else ('#e3a53a' if confidence > 40 else '#f85149')
        self._gauge_labels['conf'].config(
            text=f"{confidence}%", fg=conf_color)

        model_txt = "GBR+KNN" if use_model else "KNN only"
        self._model_info.config(text=f"[{model_txt}]  {sym}")

        # ── 예측 범위 텍스트 ──────────────────────────────────
        top5 = knn_rows.head(5)
        self._range_text.config(state="normal")
        self._range_text.delete("1.0", "end")
        lines = [
            f"  수익 범위: ${knn_rows['profit'].min():>9,.0f} ~ ${knn_rows['profit'].max():>9,.0f}",
            f"  Score 범위: {knn_rows['score'].min():.1f} ~ {knn_rows['score'].max():.1f}",
            f"  DD 범위:   {knn_rows['drawdown_pct'].min():.1f}% ~ {knn_rows['drawdown_pct'].max():.1f}%",
            f"  유사 EA {len(knn_rows)}개 평균 수익: ${knn_rows['profit'].mean():>,.0f}",
            f"  ─────────────────────────────",
            f"  ※ 참고용 예측 (정확도 {confidence}%)",
        ]
        self._range_text.insert("end", "\n".join(lines))
        self._range_text.config(state="disabled")

        # ── 유사 EA 목록 ──────────────────────────────────────
        for item in self._sim_tree.get_children():
            self._sim_tree.delete(item)

        q75 = sub['profit'].quantile(0.75) if not sub.empty else 0
        q25 = sub['profit'].quantile(0.25) if not sub.empty else 0

        for _, row in top5.iterrows():
            name = str(row.get('ea_name', ''))
            # 이름 축약: SC부터 끝까지
            short = name.split('_', 2)[-1] if '_' in name else name
            short = short[:30] if len(short) > 30 else short
            sym_r = str(row.get('symbol', ''))
            profit_r = row.get('profit', 0)
            score_r  = row.get('score', 0)
            dd_r     = row.get('drawdown_pct', 0)
            tag = 'top' if profit_r >= q75 else ('bot' if profit_r <= q25 else 'mid')
            self._sim_tree.insert('', 'end',
                values=(short, sym_r, f"${profit_r:,.0f}", f"{score_r:.1f}", f"{dd_r:.1f}%"),
                tags=(tag,))

    def _embed_figure(self, fig):
        """Figure를 tkinter 차트 프레임에 임베드."""
        # 시뮬레이터 숨기기
        if self._sim_frame:
            self._sim_frame.pack_forget()

        if self._canvas_widget:
            self._canvas_widget.get_tk_widget().destroy()
            try:
                self._canvas_widget.toolbar.destroy()
            except Exception:
                pass

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        w = canvas.get_tk_widget()
        w.pack(fill="both", expand=True)

        # 툴바 (저장/확대 버튼)
        toolbar_frame = tk.Frame(self._chart_frame, bg=DPANEL)
        toolbar_frame.pack(fill="x")
        tb = NavigationToolbar2Tk(canvas, toolbar_frame)
        tb.update()
        canvas.toolbar = tb

        self._canvas_widget = canvas
        self._fig = fig

    def _draw_scatter(self):
        df = self._get_filtered()
        if df.empty:
            return
        param = self._x_var.get()
        syms = df['symbol'].unique()

        fig = Figure(figsize=(9, 6), facecolor=DARK)
        ax = fig.add_subplot(111, facecolor=DPANEL)
        ax.tick_params(colors=DTEXT, labelsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor(DGRID)
        ax.set_xlabel(param, color="#8b949e", fontsize=9)
        ax.set_ylabel("Profit ($)", color="#8b949e", fontsize=9)

        for sym in syms:
            color = SYM_COLOR.get(sym, '#aaa')
            sub = df[df['symbol'] == sym]
            ax.scatter(sub[param], sub['profit'], alpha=0.45, s=20,
                       color=color, label=sym, zorder=3)
            try:
                z = np.polyfit(sub[param], sub['profit'], 1)
                xr = np.linspace(sub[param].min(), sub[param].max(), 50)
                ax.plot(xr, np.poly1d(z)(xr), color=color, lw=2, alpha=0.9)
            except Exception:
                pass
            r = sub[param].corr(sub['profit'])
            ax.text(0.02, 0.98 - (list(syms).index(sym) * 0.07),
                    f"{sym} r={r:.3f}", transform=ax.transAxes,
                    color=color, fontsize=9, va='top', fontweight='bold')

        ax.set_title(f"{param}  vs  Profit", color=DTEXT, fontsize=12, fontweight='bold')
        ax.legend(facecolor=DPANEL, edgecolor=DGRID, labelcolor=DTEXT, fontsize=9)
        ax.grid(True, color=DGRID, lw=0.5, alpha=0.6)
        fig.tight_layout()
        self._embed_figure(fig)

    def _draw_boxplot(self):
        df = self._get_filtered()
        if df.empty:
            return
        sym = self._sym_var.get()
        syms_to_draw = list(df['symbol'].unique()) if sym == 'ALL' else [sym]

        n_rows = len(syms_to_draw)
        show = ['SL', 'TP', 'TP_SL_ratio', 'ATR', 'FastMA', 'SlowMA',
                'ADXMin', 'MaxDD', 'MaxPos', 'Cooldown']

        fig = Figure(figsize=(11, 5 * n_rows), facecolor=DARK)
        tier_colors = ['#f85149', '#e3a53a', '#56d364', '#58a6ff']

        for row_idx, sym_name in enumerate(syms_to_draw):
            sub = df[df['symbol'] == sym_name].copy()
            if len(sub) < 8:
                continue
            sub['tier'] = pd.qcut(sub['profit'], q=4, labels=False, duplicates='drop')
            tier_map = {0: 'Low', 1: 'MidL', 2: 'MidH', 3: 'Top'}
            sub['tier'] = sub['tier'].map(tier_map)

            for col_idx, param in enumerate(show):
                ax = fig.add_subplot(n_rows, len(show),
                                     row_idx * len(show) + col_idx + 1,
                                     facecolor=DPANEL)
                ax.tick_params(colors=DTEXT, labelsize=6)
                for sp in ax.spines.values():
                    sp.set_edgecolor(DGRID)

                groups = [sub[sub['tier'] == t][param].dropna().values
                          for t in ['Low', 'MidL', 'MidH', 'Top']]
                valid_groups = [g for g in groups if len(g) > 0]
                if not valid_groups:
                    continue

                bp = ax.boxplot(valid_groups, patch_artist=True,
                                tick_labels=['L', 'ML', 'MH', 'T'][:len(valid_groups)],
                                medianprops=dict(color='white', lw=2),
                                whiskerprops=dict(color='#8b949e'),
                                capprops=dict(color='#8b949e'),
                                flierprops=dict(marker='o', color='#8b949e', ms=2, alpha=0.4))
                for patch, c in zip(bp['boxes'], tier_colors):
                    patch.set_facecolor(c)
                    patch.set_alpha(0.7)

                title_color = SYM_COLOR.get(sym_name, DTEXT)
                ax.set_title(f"[{sym_name}] {param}" if col_idx == 0 else param,
                             color=title_color if col_idx == 0 else DTEXT,
                             fontsize=7, fontweight='bold')
                ax.grid(True, color=DGRID, lw=0.4, alpha=0.5, axis='y')

        fig.suptitle("Profit Tier Boxplot  (Low→Top: 하위→상위 25%)",
                     color=DTEXT, fontsize=11, fontweight='bold')
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        self._embed_figure(fig)

    def _draw_heatmap(self):
        df = self._get_filtered()
        if df.empty:
            return
        syms = list(df['symbol'].unique())
        n = len(syms)

        fig = Figure(figsize=(10, 5 * n), facecolor=DARK)
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
            'rg', ['#f85149', DPANEL, '#56d364'])

        for idx, sym_name in enumerate(syms):
            ax = fig.add_subplot(n, 1, idx + 1, facecolor=DPANEL)
            ax.tick_params(colors=DTEXT, labelsize=8)
            for sp in ax.spines.values():
                sp.set_edgecolor(DGRID)

            sub = df[df['symbol'] == sym_name]
            metric_labels = ['Profit', 'Score', 'DD%', 'PF', 'Trades']
            corr_matrix = np.zeros((len(PARAMS), len(METRICS)))
            for i, p in enumerate(PARAMS):
                for j, m in enumerate(METRICS):
                    try:
                        r = sub[p].corr(sub[m])
                        corr_matrix[i][j] = r if not np.isnan(r) else 0
                    except Exception:
                        pass

            im = ax.imshow(corr_matrix, cmap=cmap, vmin=-0.6, vmax=0.6, aspect='auto')
            ax.set_xticks(range(len(METRICS)))
            ax.set_yticks(range(len(PARAMS)))
            ax.set_xticklabels(metric_labels, color=DTEXT, fontsize=9)
            ax.set_yticklabels(PARAMS, color=DTEXT, fontsize=9)

            for i in range(len(PARAMS)):
                for j in range(len(METRICS)):
                    val = corr_matrix[i][j]
                    fc = 'white' if abs(val) > 0.2 else '#8b949e'
                    fw = 'bold' if abs(val) > 0.3 else 'normal'
                    ax.text(j, i, f"{val:.2f}", ha='center', va='center',
                            color=fc, fontsize=8, fontweight=fw)

            ax.set_title(f"[{sym_name}]  Correlation Heatmap  n={len(sub)}",
                         color=SYM_COLOR.get(sym_name, DTEXT), fontsize=11, fontweight='bold')
            fig.colorbar(im, ax=ax, label='r', shrink=0.7)

        fig.tight_layout()
        self._embed_figure(fig)

    def _draw_topbot(self):
        df = self._get_filtered()
        if df.empty:
            return
        syms = list(df['symbol'].unique())
        show = ['SL', 'TP', 'ATR', 'FastMA', 'SlowMA', 'ADXMin',
                'MaxDD', 'MaxPos', 'Cooldown', 'TP_SL_ratio']

        fig = Figure(figsize=(11, 5 * len(syms)), facecolor=DARK)

        for idx, sym_name in enumerate(syms):
            ax = fig.add_subplot(len(syms), 1, idx + 1, facecolor=DPANEL)
            ax.tick_params(colors=DTEXT, labelsize=9)
            for sp in ax.spines.values():
                sp.set_edgecolor(DGRID)

            sub = df[df['symbol'] == sym_name].copy()
            if len(sub) < 10:
                continue
            q25 = sub['profit'].quantile(0.25)
            q75 = sub['profit'].quantile(0.75)
            top = sub[sub['profit'] >= q75]
            bot = sub[sub['profit'] <= q25]

            x = np.arange(len(show))
            w = 0.35
            top_vals, bot_vals = [], []
            for p in show:
                std = sub[p].std()
                mean = sub[p].mean()
                top_vals.append((top[p].mean() - mean) / (std + 1e-9))
                bot_vals.append((bot[p].mean() - mean) / (std + 1e-9))

            ax.bar(x - w/2, top_vals, w, label=f"Top25% (≥{q75/1000:.0f}k)",
                   color='#56d364', alpha=0.8)
            ax.bar(x + w/2, bot_vals, w, label=f"Bottom25% (≤{q25/1000:.0f}k)",
                   color='#f85149', alpha=0.8)
            ax.set_xticks(x)
            ax.set_xticklabels(show, color=DTEXT, fontsize=9)
            ax.set_ylabel("Normalized σ from mean", color="#8b949e", fontsize=8)
            ax.axhline(0, color=DGRID, lw=1)
            ax.set_title(f"[{sym_name}]  Top vs Bottom 파라미터 비교  (top n={len(top)}, bot n={len(bot)})",
                         color=SYM_COLOR.get(sym_name, DTEXT), fontsize=11, fontweight='bold')
            ax.legend(facecolor=DPANEL, edgecolor=DGRID, labelcolor=DTEXT, fontsize=9)
            ax.grid(True, color=DGRID, lw=0.5, alpha=0.5, axis='y')

        fig.suptitle("Top 25% vs Bottom 25%  — Normalized Parameter Deviation",
                     color=DTEXT, fontsize=12, fontweight='bold')
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        self._embed_figure(fig)

    def _draw_bins(self):
        df = self._get_filtered()
        if df.empty:
            return
        param = self._x_var.get()
        syms = list(df['symbol'].unique())

        fig = Figure(figsize=(10, 5 * len(syms)), facecolor=DARK)

        for idx, sym_name in enumerate(syms):
            ax = fig.add_subplot(len(syms), 1, idx + 1, facecolor=DPANEL)
            ax.tick_params(colors=DTEXT, labelsize=8)
            for sp in ax.spines.values():
                sp.set_edgecolor(DGRID)

            sub = df[df['symbol'] == sym_name].copy()
            if len(sub) < 5:
                continue

            unique_vals = sorted(sub[param].unique())
            if len(unique_vals) > 8:
                bins = pd.cut(sub[param], bins=6)
                groups = sub.groupby(bins, observed=True)['profit']
                labels = [str(b) for b in groups.groups.keys()]
            else:
                groups = sub.groupby(param)['profit']
                labels = [str(v) for v in groups.groups.keys()]

            means = groups.mean().values / 1000
            stds = groups.std().fillna(0).values / 1000
            counts = groups.count().values

            if len(means) == 0:
                continue

            norm_vals = means / (max(means) + 1e-9)
            bar_colors = [plt.cm.RdYlGn(v) for v in norm_vals]

            bars = ax.bar(range(len(means)), means, color=bar_colors, alpha=0.85,
                          yerr=stds, error_kw=dict(color='#8b949e', capsize=3))
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, color=DTEXT, fontsize=7, rotation=25, ha='right')
            ax.set_ylabel("Mean Profit (k$)", color="#8b949e", fontsize=8)
            ax.set_title(f"[{sym_name}]  Profit Distribution by {param}",
                         color=SYM_COLOR.get(sym_name, DTEXT), fontsize=11, fontweight='bold')
            ax.grid(True, color=DGRID, lw=0.5, alpha=0.5, axis='y')

            for bar, cnt in zip(bars, counts):
                ax.text(bar.get_x() + bar.get_width() / 2, 0.3,
                        f"n={cnt}", ha='center', va='bottom',
                        color='white', fontsize=7, rotation=90)

        fig.tight_layout()
        self._embed_figure(fig)

    # ── 통계 업데이트 ────────────────────────────────────────
    def _update_stats(self):
        if self._df.empty:
            return
        df = self._get_filtered()

        # 상관계수 테이블
        for item in self._corr_tree.get_children():
            self._corr_tree.delete(item)

        corrs = {}
        for sym in ['XAUUSD', 'BTCUSD']:
            sub = df[df['symbol'] == sym] if sym in df['symbol'].values else pd.DataFrame()
            if len(sub) < 3:
                continue
            for p in PARAMS:
                r = sub[p].corr(sub['profit'])
                if p not in corrs:
                    corrs[p] = {}
                corrs[p][sym] = r if not np.isnan(r) else 0.0

        # Sort by max abs correlation
        sorted_params = sorted(PARAMS,
                               key=lambda p: max(abs(corrs.get(p, {}).get(s, 0))
                                                  for s in ['XAUUSD', 'BTCUSD']),
                               reverse=True)
        for p in sorted_params:
            xr = corrs.get(p, {}).get('XAUUSD', 0.0)
            br = corrs.get(p, {}).get('BTCUSD', 0.0)
            winner = 'XAU' if abs(xr) > abs(br) else 'BTC'
            tag = 'high' if max(abs(xr), abs(br)) > 0.15 else ''
            self._corr_tree.insert('', 'end', values=(
                p, f"{xr:.3f}", f"{br:.3f}", winner), tags=(tag,))

        self._corr_tree.tag_configure('high', foreground='#dc2626')

        # Summary text
        self._summary_text.config(state="normal")
        self._summary_text.delete("1.0", "end")
        lines = []
        for sym in ['XAUUSD', 'BTCUSD']:
            sub = df[df['symbol'] == sym]
            if len(sub) < 3:
                continue
            lines.append(f"[{sym}]  n={len(sub)}")
            lines.append(f"  수익 최소  : ${sub.profit.min():>10,.0f}")
            lines.append(f"  수익 중앙값: ${sub.profit.median():>10,.0f}")
            lines.append(f"  수익 평균  : ${sub.profit.mean():>10,.0f}")
            lines.append(f"  수익 최대  : ${sub.profit.max():>10,.0f}")
            lines.append(f"  평균 DD    : {sub.drawdown_pct.mean():.1f}%")
            lines.append(f"  평균 Score : {sub.score.mean():.1f}")
            lines.append(f"  평균 PF    : {sub.profit_factor.mean():.2f}")
            lines.append("")
            # Top 3 highest corr with profit
            pcorrs = sorted(
                [(p, sub[p].corr(sub['profit'])) for p in PARAMS if not np.isnan(sub[p].corr(sub['profit']))],
                key=lambda x: abs(x[1]), reverse=True
            )[:3]
            lines.append("  수익 최고 상관:")
            for p, r in pcorrs:
                direction = "↑ 높을수록↑" if r > 0 else "↑ 높을수록↓"
                lines.append(f"    {p:12s} r={r:.3f}  {direction}")
            lines.append("")
        self._summary_text.insert("end", "\n".join(lines))
        self._summary_text.config(state="disabled")

    # ── 내보내기 ─────────────────────────────────────────────
    def _export_csv(self):
        if self._df.empty:
            messagebox.showwarning("경고", "데이터가 없습니다.\n먼저 새로고침 하세요.")
            return
        df = self._get_filtered()
        path = filedialog.asksaveasfilename(
            title="CSV 저장", defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("모두", "*.*")],
            initialfile="ea_param_analysis.csv",
            initialdir=os.path.join(HERE, ".."))
        if not path:
            return
        try:
            df.to_csv(path, index=False, encoding='utf-8-sig')
            messagebox.showinfo("완료", f"CSV 저장 완료:\n{path}\n\n{len(df)}건")
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def _save_chart(self):
        if self._fig is None:
            messagebox.showwarning("경고", "먼저 차트를 그려주세요.")
            return
        path = filedialog.asksaveasfilename(
            title="차트 저장", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("모두", "*.*")],
            initialfile=f"ea_analysis_{self._chart_var.get()}.png",
            initialdir=os.path.join(HERE, ".."))
        if not path:
            return
        try:
            self._fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=DARK)
            messagebox.showinfo("완료", f"저장 완료:\n{path}")
        except Exception as e:
            messagebox.showerror("오류", str(e))
