"""
ui/tab_round_opt.py — EA Auto Master v6.0
==========================================
라운드 최적화 탭 — 설정 + SOLO 연동 + AHK IPC 백테스트 + 분석기.
v5.4 L1395-2631 추출.
"""
import csv as _csv
import datetime
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

from core.config import HERE
from core.diagnostics import diagnose_zero_trades
from core.email_sender import send_email_report
from core.encoding import read_ini
from core.round_engine import (parse_set_file, parse_ea_params, smart_vary,
                                gen_round_sets, gen_round_sets_v2, gen_bottom_fix_sets)
from core.round_optimizer import RoundDirector, ParamAnalyzer
from core.scoring import calc_score_grade, calc_adjusted_params
from ui.tab_dashboard import EADashboardTab
from ui.theme import (BG, FG, PANEL, PANEL2, BLUE, GREEN, RED, TEAL, CYAN,
                      AMBER, TITLE, LBL, MONO, B, LB, WL)


class RoundOptTab(ttk.Frame):
    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        self._stop = False
        self._round_data = {}
        self._build()

    def _build(self):
        b = tk.Frame(self, bg=BG); b.pack(fill="both", expand=True, padx=10, pady=8)

        top = tk.PanedWindow(b, orient="horizontal", bg=BG,
                             sashwidth=5, sashrelief="groove", sashpad=2)
        top.pack(fill="both", expand=True, pady=(0, 5))

        # -- 설정 패널 --
        lp = tk.LabelFrame(top, text="  최적화 설정", font=TITLE, fg=FG, bg=PANEL,
                           relief="groove", bd=2)
        top.add(lp, width=350, minsize=220, sticky="nsew")

        def rowf(lbl, var, br=None, w=28):
            r = tk.Frame(lp, bg=PANEL); r.pack(fill="x", padx=8, pady=3)
            tk.Label(r, text=lbl+":", font=LBL, fg=FG, bg=PANEL, width=12, anchor="e").pack(side="left")
            tk.Entry(r, textvariable=var, font=MONO, bg=PANEL2, fg="#ff6b35",
                     insertbackground=FG, relief="flat", bd=3, width=w
                     ).pack(side="left", fill="x", expand=True, padx=(4, 4))
            if br:
                B(r, "...", PANEL2, br, padx=4).pack(side="left")

        self.ea_v  = tk.StringVar(); rowf("EA 파일", self.ea_v, lambda: self._bf(self.ea_v, [("MQ4", "*.mq4")]))
        self.set_v = tk.StringVar(); rowf("SET 파일", self.set_v, lambda: self._bf(self.set_v, [("SET", "*.set"), ("all", "*")]))
        self.sym_v = tk.StringVar(value="BTCUSD"); rowf("심볼", self.sym_v)
        self.tf_v  = tk.StringVar(value="M5");     rowf("타임프레임", self.tf_v)
        self.fr_v  = tk.StringVar(value="2025.01.01"); rowf("시작일", self.fr_v)
        self.to_v  = tk.StringVar(value="2025.09.30"); rowf("종료일", self.to_v)
        self.rd_v  = tk.StringVar(value="10");     rowf("라운드 수", self.rd_v)
        self.st_v  = tk.StringVar(value="0.15");   rowf("변동 폭", self.st_v)
        self.mx_v  = tk.StringVar(value="3");      rowf("최대 변동수", self.mx_v)

        def_solo = self.cfg.get("solo_dir", HERE)
        self.solo_v = tk.StringVar(value=def_solo); rowf("SOLO 폴더", self.solo_v, lambda: self._bd(self.solo_v))
        def_analyzer = self.cfg.get("analyzer_path", os.path.join(HERE, "BacktestAnalyzer.py"))
        self.ana_v = tk.StringVar(value=def_analyzer); rowf("분석기 경로", self.ana_v, lambda: self._bf(self.ana_v, [("py", "*.py"), ("all", "*")]))
        def_rep = self.cfg.get("report_base", r"C:\2026NEWOPTMIZER")
        self.rep_v = tk.StringVar(value=def_rep); rowf("리포트 폴더", self.rep_v, lambda: self._bd(self.rep_v))

        # -- 전략 프리셋 --
        pf = tk.LabelFrame(lp, text="  전략 프리셋", font=LBL, fg="#94a3b8", bg=PANEL, relief="flat", bd=1)
        pf.pack(fill="x", padx=8, pady=(4, 2))
        af = tk.Frame(pf, bg=PANEL); af.pack(fill="x", pady=(3, 1))
        tk.Label(af, text="자산:", font=LBL, fg=FG, bg=PANEL).pack(side="left", padx=(4, 4))
        self._asset_v = tk.StringVar(value="BTC")
        for ast, clr in [("BTC", "#f7931a"), ("GOLD", "#f0b90b"), ("FX", "#22d3ee")]:
            tk.Radiobutton(af, text=ast, variable=self._asset_v, value=ast,
                           font=("Malgun Gothic", 9, "bold"), fg=clr, bg=PANEL,
                           selectcolor=PANEL2, activebackground=PANEL,
                           command=self._on_asset_change).pack(side="left", padx=3)
        sf = tk.Frame(pf, bg=PANEL); sf.pack(fill="x", pady=(1, 4))
        for lbl, clr, key in [("보수적", "#0ea5e9", "conservative"), ("균형", "#16a34a", "balanced"),
                               ("공격적", "#b45309", "aggressive"), ("고수익", "#9f1239", "high_yield")]:
            B(sf, lbl, clr, lambda k=key: self._apply_preset(k),
              font=("Malgun Gothic", 8, "bold"), pady=4, padx=6).pack(side="left", padx=2)

        # -- 도구 버튼 --
        bf2 = tk.Frame(lp, bg=PANEL); bf2.pack(fill="x", padx=8, pady=(2, 2))
        B(bf2, "로드", BLUE, self._load_params, pady=4, padx=8).pack(side="left", padx=(0, 3))
        B(bf2, "연결확인", TEAL, self._test_solo, pady=4, padx=6).pack(side="left", padx=(0, 3))
        B(bf2, "선택적용", GREEN, self._apply_table_params, pady=4, padx=6).pack(side="left", padx=(0, 3))
        B(bf2, "전체선택", "#374151", lambda: self._tbl_sel_all(True), pady=4, padx=4).pack(side="left", padx=(0, 2))
        B(bf2, "전체해제", "#374151", lambda: self._tbl_sel_all(False), pady=4, padx=4).pack(side="left")

        # -- 파라미터 테이블 --
        tbl_frm = tk.Frame(lp, bg=PANEL); tbl_frm.pack(fill="both", expand=True, padx=6, pady=(2, 4))
        hdr = tk.Frame(tbl_frm, bg="#2a2a40"); hdr.pack(fill="x")
        for txt, w in [("V", 28), ("역할", 46), ("파라미터", 110), ("현재값", 70), ("+-조정", 60), ("적용", 32)]:
            tk.Label(hdr, text=txt, font=("Malgun Gothic", 8, "bold"), fg="#94a3b8", bg="#2a2a40",
                     width=w//8, anchor="center", relief="flat").pack(side="left", padx=1)

        cvs = tk.Canvas(tbl_frm, bg=PANEL, highlightthickness=0, height=200)
        vsb2 = ttk.Scrollbar(tbl_frm, orient="vertical", command=cvs.yview)
        cvs.configure(yscrollcommand=vsb2.set)
        vsb2.pack(side="right", fill="y"); cvs.pack(side="left", fill="both", expand=True)
        self._ptbl_inner = tk.Frame(cvs, bg=PANEL)
        self._ptbl_win = cvs.create_window((0, 0), window=self._ptbl_inner, anchor="nw")
        self._ptbl_inner.bind("<Configure>", lambda e: (
            cvs.configure(scrollregion=cvs.bbox("all")),
            cvs.itemconfig(self._ptbl_win, width=cvs.winfo_width())))
        cvs.bind("<Configure>", lambda e: cvs.itemconfig(self._ptbl_win, width=e.width))
        cvs.bind("<MouseWheel>", lambda e: cvs.yview_scroll(-1*(1 if e.delta > 0 else -1), "units"))
        self._ptbl_rows = []
        self._ptbl_cvs = cvs

        self.param_info = scrolledtext.ScrolledText(lp, height=3, font=("Consolas", 8),
                                                     bg="#12121e", fg="#a3e635",
                                                     relief="flat", bd=1, width=30)
        self.param_info.pack(fill="x", padx=8, pady=(0, 4))

        # -- 오른쪽: Notebook --
        right_nb = ttk.Notebook(top)
        top.add(right_nb, minsize=200, sticky="nsew")

        rp = tk.Frame(right_nb, bg=PANEL)
        right_nb.add(rp, text="라운드 진행")
        cols = ("라운드", "상태", "세트수", "BEST수익", "BEST PF", "WIN%", "MDD", "등급", "변경내용")
        self.rt = ttk.Treeview(rp, columns=cols, show="headings", height=14)
        cw = {"라운드": 55, "상태": 75, "세트수": 55, "BEST수익": 80, "BEST PF": 65,
              "WIN%": 55, "MDD": 65, "등급": 45, "변경내용": 220}
        for c in cols:
            self.rt.heading(c, text=c, anchor="center")
            self.rt.column(c, width=cw.get(c, 80), anchor="center", stretch=(c == "변경내용"))
        for tag, clr in [("RUN", "#fbbf24"), ("DONE", "#22c55e"), ("BEST", "#7c3aed"),
                          ("FAIL", "#ef4444"), ("WAIT", "#475569")]:
            self.rt.tag_configure(tag, foreground=clr)
        vsb = ttk.Scrollbar(rp, orient="vertical", command=self.rt.yview)
        self.rt.configure(yscrollcommand=vsb.set)
        self.rt.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=5)
        vsb.pack(side="right", fill="y", pady=5)

        self._dash_tab = EADashboardTab(right_nb, self.cfg)
        right_nb.add(self._dash_tab, text="EA 대시보드")

        # ── 라운드 분석 탭 ──────────────────────────────────────────────
        self._build_analysis_tab(right_nb)

        # -- 버튼 + 로그 --
        bf = tk.Frame(b, bg=BG); bf.pack(fill="x", pady=(0, 4))
        self.r_btn = B(bf, "라운드 최적화 시작", GREEN, self._start,
                       font=("Malgun Gothic", 11, "bold"), pady=8, padx=14)
        self.r_btn.pack(side="left", padx=(0, 6))
        self.s_btn = B(bf, "중지", RED, self._do_stop, pady=8, padx=10)
        self.s_btn.config(state="disabled"); self.s_btn.pack(side="left", padx=(0, 6))
        B(bf, "결과 불러오기", CYAN, self._load_db, pady=8, padx=10).pack(side="left", padx=(0, 6))
        B(bf, "SET 폴더", TEAL, self._open_set, pady=8, padx=8).pack(side="left")
        B(bf, "로그 삭제", "#374151", lambda: self.log.delete("1.0", "end"), pady=8, padx=6).pack(side="right")
        self.prog = tk.Label(bf, text="대기 중", font=("Malgun Gothic", 10, "bold"),
                             fg="#94a3b8", bg=BG)
        self.prog.pack(side="right", padx=10)

        fl = tk.LabelFrame(b, text="  로그", font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        fl.pack(fill="both", expand=True)
        self.log = LB(fl, 5); self.log.pack(fill="both", expand=True, padx=8, pady=5)

        self._init_table()

    # -- 프리셋 데이터 -------------------------------------------
    _PRESETS = {
        "BTC": {
            "conservative": {
                "sym": "BTCUSD", "tf": "H4", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.08", "max_vary": "2",
                "desc": "BTC 보수적 -- 낮은 위험, 넓은 SL/TP, 변동 폭 +-8%",
                "hint": ("InpRiskPercent=0.5\nInpMaxDrawdown=6.0\n"
                         "InpTrendSL_ATR=3.0\nInpTrendTP_ATR=5.5\n"
                         "InpTrailATR=2.5\nInpCooldownBars=10\n"
                         "InpSkipHighVol=1\nInpUseCrashGuard=1")
            },
            "balanced": {
                "sym": "BTCUSD", "tf": "H4", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.15", "max_vary": "3",
                "desc": "BTC 균형 -- EMA10/30 + ADX20 기준값",
                "hint": ("InpRiskPercent=0.75\nInpMaxDrawdown=10.0\n"
                         "InpEmaFast=10\nInpEmaSlow=30\nInpAdxTrendMin=20.0\n"
                         "InpTrendSL_ATR=3.0\nInpTrendTP_ATR=5.5\n"
                         "InpTrailATR=2.5\nInpCooldownBars=8")
            },
            "aggressive": {
                "sym": "BTCUSD", "tf": "H1", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.20", "max_vary": "4",
                "desc": "BTC 공격적 -- 높은 위험, 좁은 SL, 빠른 TF",
                "hint": ("InpRiskPercent=1.5\nInpMaxDrawdown=15.0\n"
                         "InpTrendSL_ATR=2.0\nInpTrendTP_ATR=4.0\n"
                         "InpTrailATR=1.5\nInpCooldownBars=4\n"
                         "InpSkipHighVol=0")
            },
            "high_yield": {
                "sym": "BTCUSD", "tf": "M30", "fr": "2025.01.01", "to": "2025.12.31",
                "step": "0.25", "max_vary": "5",
                "desc": "BTC 고수익 -- 단기 M30, 대규모 변동 탐색",
                "hint": ("InpRiskPercent=2.5\nInpMaxDrawdown=20.0\n"
                         "InpTrendSL_ATR=1.5\nInpTrendTP_ATR=3.5\n"
                         "InpTrailATR=1.0\nInpCooldownBars=2\n"
                         "InpSkipHighVol=0\nInpAutoHedge=1")
            },
        },
        "GOLD": {
            "conservative": {
                "sym": "XAUUSD", "tf": "H4", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.08", "max_vary": "2",
                "desc": "GOLD 보수적 -- 런던세션 집중, 좁은 변동",
                "hint": ("InpRiskPercent=0.75\nInpMaxDrawdown=5.0\n"
                         "InpTrendSL_ATR=2.0\nInpTrendTP_ATR=3.5\n"
                         "InpTrailATR=1.5\nInpUseTimeFilter=1\n"
                         "InpStartHour=7\nInpEndHour=20\nInpCloseOnFriday=1")
            },
            "balanced": {
                "sym": "XAUUSD", "tf": "H1", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.15", "max_vary": "3",
                "desc": "GOLD 균형 -- EMA12/26 + ADX22 기준값",
                "hint": ("InpRiskPercent=1.0\nInpMaxDrawdown=8.0\n"
                         "InpEmaFast=12\nInpEmaSlow=26\nInpAdxTrendMin=22.0\n"
                         "InpTrendSL_ATR=2.0\nInpTrendTP_ATR=3.5\n"
                         "InpRsiOB=72\nInpRsiOS=28")
            },
            "aggressive": {
                "sym": "XAUUSD", "tf": "H1", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.20", "max_vary": "4",
                "desc": "GOLD 공격적 -- 좁은 SL, 높은 RR",
                "hint": ("InpRiskPercent=2.0\nInpMaxDrawdown=12.0\n"
                         "InpTrendSL_ATR=1.5\nInpTrendTP_ATR=3.5\n"
                         "InpTrailATR=1.0\nInpRsiOB=68\nInpRsiOS=32")
            },
            "high_yield": {
                "sym": "XAUUSD", "tf": "M15", "fr": "2025.01.01", "to": "2025.12.31",
                "step": "0.25", "max_vary": "5",
                "desc": "GOLD 고수익 -- 단기 M15, 대규모 변동",
                "hint": ("InpRiskPercent=3.0\nInpMaxDrawdown=18.0\n"
                         "InpTrendSL_ATR=1.0\nInpTrendTP_ATR=2.5\n"
                         "InpTrailATR=0.8\nInpUseTimeFilter=0")
            },
        },
        "FX": {
            "conservative": {
                "sym": "EURUSD", "tf": "H4", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.08", "max_vary": "2",
                "desc": "FX 보수적 -- 낮은 위험, 넓은 SL",
                "hint": ("InpRiskPercent=0.5\nInpMaxDrawdown=5.0\n"
                         "StopLoss=200\nTakeProfit=400\nTrailingStop=100")
            },
            "balanced": {
                "sym": "EURUSD", "tf": "H1", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.12", "max_vary": "3",
                "desc": "FX 균형 -- H1 기본 설정",
                "hint": ("InpRiskPercent=1.0\nInpMaxDrawdown=8.0\n"
                         "StopLoss=150\nTakeProfit=300\nTrailingStop=80")
            },
            "aggressive": {
                "sym": "USDJPY", "tf": "M30", "fr": "2024.01.01", "to": "2025.12.31",
                "step": "0.18", "max_vary": "4",
                "desc": "FX 공격적 -- M30, 높은 RR",
                "hint": ("InpRiskPercent=2.0\nInpMaxDrawdown=12.0\n"
                         "StopLoss=100\nTakeProfit=300\nTrailingStop=60")
            },
            "high_yield": {
                "sym": "USDJPY", "tf": "M15", "fr": "2025.01.01", "to": "2025.12.31",
                "step": "0.25", "max_vary": "5",
                "desc": "FX 고수익 -- M15 스캘핑 스타일",
                "hint": ("InpRiskPercent=3.0\nInpMaxDrawdown=18.0\n"
                         "StopLoss=80\nTakeProfit=200\nTrailingStop=50")
            },
        },
    }

    def _on_asset_change(self):
        ast = self._asset_v.get()
        sym_map = {"BTC": "BTCUSD", "GOLD": "XAUUSD", "FX": "EURUSD"}
        tf_map  = {"BTC": "H4", "GOLD": "H1", "FX": "H1"}
        self.sym_v.set(sym_map.get(ast, self.sym_v.get()))
        self.tf_v.set(tf_map.get(ast, self.tf_v.get()))

    def _apply_preset(self, preset_key):
        ast = self._asset_v.get()
        d = self._PRESETS.get(ast, {}).get(preset_key, {})
        if not d:
            return
        self.sym_v.set(d.get("sym", self.sym_v.get()))
        self.tf_v.set(d.get("tf", self.tf_v.get()))
        self.fr_v.set(d.get("fr", self.fr_v.get()))
        self.to_v.set(d.get("to", self.to_v.get()))
        self.st_v.set(d.get("step", self.st_v.get()))
        self.mx_v.set(d.get("max_vary", self.mx_v.get()))
        self.param_info.delete("1.0", "end")
        self.param_info.insert("end", f"[{d.get('desc', '')}]\n\n")
        self.param_info.insert("end", "[ 권장 파라미터 기준값 ]\n")
        self.param_info.insert("end", d.get("hint", "") + "\n\n")
        self.param_info.insert("end", f"변동폭: +-{float(d['step'])*100:.0f}% / 변동대상: {d['max_vary']}개\n")
        hint_params = {}
        for line in d.get("hint", "").splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                hint_params[k.strip()] = v.strip()
        if hint_params:
            if not hasattr(self, "_base_params") or not self._base_params:
                self._base_params = hint_params
                WL(self.log, f"[{ast} {preset_key}] 프리셋 로드 -- {len(hint_params)}개")
            else:
                added = 0
                for k, v in hint_params.items():
                    if k not in self._base_params:
                        self._base_params[k] = v
                        added += 1
                WL(self.log, f"[{ast} {preset_key}] 프리셋 적용 -- {added}개 추가")
            self._render_param_table(self._base_params)
            self.param_info.delete("1.0", "end")
            WL(self.param_info, f"[{ast} {preset_key}] {d.get('desc', '')}")
        WL(self.log, f"  {d.get('desc', '')}", "o")
        WL(self.log, f"  심볼:{self.sym_v.get()} TF:{self.tf_v.get()} 변동:{self.st_v.get()} 최대:{self.mx_v.get()}개")

    # -- 파라미터 테이블 ------------------------------------------
    _ROLE_MAP = {
        "lot": "risk", "risk": "risk", "size": "risk",
        "period": "period", "bars": "period", "length": "period", "lookback": "period",
        "sl": "stop", "stoploss": "stop", "tp": "stop", "takeprofit": "stop",
        "trail": "stop", "drawdown": "stop", "loss": "stop", "profit": "stop",
        "rsi": "signal", "macd": "signal", "bb": "signal", "ema": "signal",
        "adx": "signal", "stoch": "signal", "atr": "signal", "signal": "signal",
        "filter": "filter", "slippage": "filter", "spread": "filter",
        "allow": "mode", "use": "mode", "enable": "mode", "mode": "mode",
    }
    _ROLE_CLR = {"risk": "#f87171", "period": "#f59e0b", "stop": "#60a5fa",
                 "signal": "#34d399", "filter": "#a78bfa", "mode": "#94a3b8", "?": "#64748b"}

    def _get_role(self, key):
        kl = key.lower()
        for kw, role in self._ROLE_MAP.items():
            if kw in kl:
                return role
        return "?"

    def _render_param_table(self, params):
        for w in self._ptbl_inner.winfo_children():
            w.destroy()
        self._ptbl_rows.clear()

        role_order = {"risk": 0, "period": 1, "stop": 2, "signal": 3, "filter": 4, "mode": 5, "?": 6}
        sorted_params = sorted(params.items(), key=lambda kv: role_order.get(self._get_role(kv[0]), 9))

        for i, (k, v) in enumerate(sorted_params):
            role = self._get_role(k)
            clr = self._ROLE_CLR.get(role, "#64748b")
            bg_c = PANEL if i % 2 == 0 else PANEL2

            row = tk.Frame(self._ptbl_inner, bg=bg_c); row.pack(fill="x", pady=0)

            chk_v = tk.BooleanVar(value=len(smart_vary(k, str(v))) > 1)
            tk.Checkbutton(row, variable=chk_v, bg=bg_c, activebackground=bg_c,
                           selectcolor=PANEL2, fg=FG).pack(side="left", padx=(3, 0))

            tk.Label(row, text=role, font=("Malgun Gothic", 7, "bold"), fg=clr, bg=bg_c,
                     width=6, anchor="center").pack(side="left", padx=1)

            tk.Label(row, text=k, font=("Consolas", 8), fg=FG, bg=bg_c,
                     width=14, anchor="w").pack(side="left", padx=2)

            val_v = tk.StringVar(value=str(v))
            tk.Entry(row, textvariable=val_v, font=("Consolas", 8),
                     bg=PANEL2, fg="#ff6b35", insertbackground=FG,
                     relief="flat", bd=2, width=9).pack(side="left", padx=2)

            step_v = tk.StringVar(value="")
            tk.Entry(row, textvariable=step_v, font=("Consolas", 8),
                     bg="#1e2a3a", fg="#22d3ee", insertbackground=FG,
                     relief="flat", bd=2, width=7).pack(side="left", padx=2)

            def _adj(kk, vv, ss, sign, orig_v=v):
                try:
                    cur = float(vv.get())
                    delta = float(ss.get()) if ss.get().strip() else (abs(cur) * 0.1 or 1)
                    nv = cur + sign * delta
                    if '.' not in str(orig_v):
                        nv = int(round(nv))
                    vv.set(str(nv))
                except Exception:
                    pass

            tk.Button(row, text="+", font=("Consolas", 8, "bold"), bg="#16a34a", fg="white",
                      relief="flat", bd=0, width=2,
                      command=lambda kk=k, vv=val_v, ss=step_v: _adj(kk, vv, ss, +1)
                      ).pack(side="left", padx=1)
            tk.Button(row, text="-", font=("Consolas", 8, "bold"), bg="#dc2626", fg="white",
                      relief="flat", bd=0, width=2,
                      command=lambda kk=k, vv=val_v, ss=step_v: _adj(kk, vv, ss, -1)
                      ).pack(side="left", padx=1)

            self._ptbl_rows.append((k, chk_v, val_v, step_v))

        self._ptbl_cvs.update_idletasks()
        self._ptbl_cvs.configure(scrollregion=self._ptbl_cvs.bbox("all"))

    def _tbl_sel_all(self, state):
        for _, chk_v, _, _ in self._ptbl_rows:
            chk_v.set(state)

    def _apply_table_params(self):
        if not self._ptbl_rows:
            messagebox.showwarning("알림", "먼저 파라미터를 로드하세요")
            return
        new_params = {}
        selected = []
        for k, chk_v, val_v, _ in self._ptbl_rows:
            new_params[k] = val_v.get().strip()
            if chk_v.get():
                selected.append(k)
        self._base_params = new_params
        self._selected_params = selected
        WL(self.param_info, f"{len(new_params)}개 적용 / 최적화대상: {len(selected)}개", "o")
        WL(self.param_info, f"  {', '.join(selected[:6])}{'...' if len(selected) > 6 else ''}")

    # -- 파일 선택 헬퍼 ------------------------------------------
    def _bf(self, var, types):
        p = filedialog.askopenfilename(filetypes=types + [("all", "*")])
        if p:
            var.set(p)

    def _bd(self, var):
        p = filedialog.askdirectory()
        if p:
            var.set(p)

    def _test_solo(self):
        solo = self.solo_v.get().strip()
        ini = os.path.join(solo, "configs", "current_config.ini")
        ahk = os.path.join(solo, "scripts", "SIMPLE_4STEPS_NC23.ahk")
        if not os.path.exists(ahk):
            ahk = os.path.join(solo, "scripts", "SIMPLE_4STEPS_v5.3.ahk")
        solo_ahk = os.path.join(solo, "SOLO_nc2.3.ahk")
        ana = self.ana_v.get().strip()
        msgs = [
            f"{'OK' if os.path.exists(ini) else 'MISS'} current_config.ini: {ini}",
            f"{'OK' if os.path.exists(ahk) else 'MISS'} AHK 스크립트 (NC): {ahk}",
            f"{'OK' if os.path.exists(solo_ahk) else 'MISS'} SOLO_nc2.3.ahk: {solo_ahk}",
            f"{'OK' if os.path.exists(ana) else 'MISS'} 분석기: {ana}",
        ]
        if os.path.exists(ini):
            cp = read_ini(ini)
            ep = cp.get("folders", "ea_path", fallback="").strip()
            msgs.append(f"{'OK' if os.path.exists(ep) else 'MISS'} Experts: {ep}")
            rp = cp.get("folders", "terminal_path", fallback="").strip()
            msgs.append(f"{'OK' if os.path.exists(rp) else 'MISS'} MT4: {rp}")
        WL(self.log, "=== SOLO 연결 테스트 ===")
        for m in msgs:
            WL(self.log, m, "o" if "OK" in m else "e")

    # ── 라운드 분석 탭 ────────────────────────────────────────────────────
    def _build_analysis_tab(self, nb):
        """라운드별 시장분석 결과 + 사용자 메모 입력 탭."""
        import tkinter.scrolledtext as ST
        ap = tk.Frame(nb, bg=PANEL)
        nb.add(ap, text="라운드 분석")

        # 상단: 라운드 선택
        top_f = tk.Frame(ap, bg=PANEL)
        top_f.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(top_f, text="라운드:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        self._ana_round_v = tk.StringVar(value="4")
        rnd_cb = ttk.Combobox(top_f, textvariable=self._ana_round_v,
                              values=[str(i) for i in range(1, 11)],
                              width=4, state="readonly")
        rnd_cb.pack(side="left", padx=(4, 12))
        B(top_f, "불러오기", CYAN, self._load_analysis, pady=3, padx=8).pack(side="left", padx=2)
        B(top_f, "지금 분석 실행", GREEN, self._run_analysis_now, pady=3, padx=8).pack(side="left", padx=2)
        B(top_f, "저장", "#7c3aed", self._save_analysis_notes, pady=3, padx=8).pack(side="left", padx=2)
        self._ana_status = tk.Label(top_f, text="", font=LBL, fg="#94a3b8", bg=PANEL)
        self._ana_status.pack(side="left", padx=8)

        # 중단: 시장분석 결과 (읽기전용)
        mf = tk.LabelFrame(ap, text="  시장분석 결과 (자동)", font=LBL,
                           fg="#7c3aed", bg=PANEL, relief="groove", bd=2)
        mf.pack(fill="both", expand=True, padx=8, pady=(4, 2))
        self._ana_market_txt = ST.ScrolledText(
            mf, height=10, font=("Consolas", 9),
            bg="#0f172a", fg="#e2e8f0", insertbackground="white",
            state="disabled", wrap="word")
        self._ana_market_txt.pack(fill="both", expand=True, padx=4, pady=4)

        # 하단: 사용자 메모 입력
        nf = tk.LabelFrame(ap, text="  내 분석 & 변경 이유 메모 (직접 입력)", font=LBL,
                           fg="#f59e0b", bg=PANEL, relief="groove", bd=2)
        nf.pack(fill="both", expand=True, padx=8, pady=(2, 6))
        hint = ("예시:\n"
                "R4 관찰: TP=24.0 계열은 낙폭 14.9%로 과대, 실제 가격이 TP 전 반전함\n"
                "→ R5는 TP를 10~12 범위로 축소\n"
                "추세 역방향 진입 40% → ADX 임계값을 20→25로 상향 테스트")
        self._ana_notes_txt = ST.ScrolledText(
            nf, height=6, font=("Malgun Gothic", 9),
            bg="#1e1b2e", fg="#fef3c7", insertbackground="white", wrap="word")
        self._ana_notes_txt.pack(fill="both", expand=True, padx=4, pady=4)
        self._ana_notes_txt.insert("1.0", hint)
        self._ana_notes_txt.config(fg="#6b7280")  # 힌트 색상

        # 메모 포커스 시 힌트 지우기
        def _clear_hint(e):
            if self._ana_notes_txt.get("1.0", "end").strip() == hint.strip():
                self._ana_notes_txt.delete("1.0", "end")
                self._ana_notes_txt.config(fg="#fef3c7")
        self._ana_notes_txt.bind("<FocusIn>", _clear_hint)

    def _ana_log(self, text):
        """시장분석 텍스트박스에 출력."""
        self._ana_market_txt.config(state="normal")
        self._ana_market_txt.delete("1.0", "end")
        self._ana_market_txt.insert("1.0", text)
        self._ana_market_txt.config(state="disabled")

    def _get_notes_path(self):
        here = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(os.path.dirname(here), "g4_results")
        os.makedirs(results_dir, exist_ok=True)
        return os.path.join(results_dir, "round_analysis_notes.json")

    def _load_analysis(self):
        """저장된 분석 메모 불러오기."""
        try:
            from core.market_analyzer import load_round_notes
        except ImportError:
            self._ana_status.config(text="market_analyzer 없음", fg="#ef4444")
            return
        rnd = int(self._ana_round_v.get())
        note = load_round_notes(self._get_notes_path(), rnd)
        if not note:
            self._ana_status.config(text=f"R{rnd} 저장된 분석 없음", fg="#f59e0b")
            self._ana_log(f"R{rnd} 분석 데이터 없음.\n'지금 분석 실행'으로 생성하세요.")
            return
        self._ana_log(note.get('market_context', '') + "\n\n" +
                      note.get('recommendation', ''))
        user = note.get('user_notes', '')
        self._ana_notes_txt.delete("1.0", "end")
        self._ana_notes_txt.config(fg="#fef3c7")
        self._ana_notes_txt.insert("1.0", user)
        self._ana_status.config(text=f"R{rnd} 로드 완료 ({note.get('saved_at','')})",
                                fg="#22c55e")

    def _run_analysis_now(self):
        """현재 라운드 HTM 파일로 즉시 시장분석 실행."""
        import threading, glob as _glob
        rnd = int(self._ana_round_v.get())
        self._ana_status.config(text=f"R{rnd} 분석 중...", fg="#fbbf24")
        self._ana_log(f"R{rnd} 시장분석 실행 중...\nXAUUSD M5 HST 로드 + HTM 거래 대조 중")

        def _do():
            try:
                from core.market_analyzer import analyze_round, save_round_notes
                here = os.path.dirname(os.path.abspath(__file__))
                reports = os.path.join(os.path.dirname(here), "reports")
                # 이 라운드 HTM 파일 탐색
                htm_paths = _glob.glob(
                    os.path.join(reports, "**", f"*_R{rnd}*.htm"), recursive=True)
                if not htm_paths:
                    self.after(0, lambda: self._ana_status.config(
                        text=f"R{rnd} HTM 없음", fg="#ef4444"))
                    self.after(0, lambda: self._ana_log(
                        f"R{rnd} HTM 파일을 reports 폴더에서 찾지 못했습니다.\n"
                        f"탐색 경로: {reports}"))
                    return
                analysis = analyze_round(htm_paths, rnd)
                save_round_notes(self._get_notes_path(), rnd, analysis, user_notes="")
                ctx = analysis.get('market_context', '')
                rec = analysis.get('recommendation', '')
                full_text = ctx + ("\n\n[제안]\n" + rec if rec else "")
                self.after(0, lambda: self._ana_log(full_text))
                self.after(0, lambda: self._ana_status.config(
                    text=f"R{rnd} 분석 완료 ({len(htm_paths)}개 HTM)", fg="#22c55e"))
            except Exception as e:
                self.after(0, lambda: self._ana_status.config(
                    text=f"오류: {e}", fg="#ef4444"))
        threading.Thread(target=_do, daemon=True).start()

    def _save_analysis_notes(self):
        """사용자 메모 저장."""
        try:
            from core.market_analyzer import load_round_notes, save_round_notes
        except ImportError:
            return
        rnd = int(self._ana_round_v.get())
        user_notes = self._ana_notes_txt.get("1.0", "end").strip()
        existing = load_round_notes(self._get_notes_path(), rnd)
        analysis_stub = {
            'market_context': existing.get('market_context', ''),
            'recommendation': existing.get('recommendation', ''),
            'total_trades':   existing.get('stats', {}).get('total_trades', 0),
            'tp_hit_pct':     existing.get('stats', {}).get('tp_hit_pct', 0),
            'sl_hit_pct':     existing.get('stats', {}).get('sl_hit_pct', 0),
            'trend_aligned_pct': existing.get('stats', {}).get('trend_aligned_pct'),
            'avg_tp_dist':    existing.get('stats', {}).get('avg_tp_dist', 0),
            'avg_sl_dist':    existing.get('stats', {}).get('avg_sl_dist', 0),
            'avg_mfe':        existing.get('stats', {}).get('avg_mfe'),
            'tp_reachable_pct': existing.get('stats', {}).get('tp_reachable_pct'),
        }
        save_round_notes(self._get_notes_path(), rnd, analysis_stub, user_notes)
        self._ana_status.config(text=f"R{rnd} 메모 저장 완료", fg="#22c55e")

    def _init_table(self):
        n = int(self.rd_v.get() or 10)
        for iid in self.rt.get_children():
            self.rt.delete(iid)
        for i in range(1, n + 1):
            iid = self.rt.insert("", "end", values=(f"R{i:02d}", "대기", "--", "--", "--", "--", "--", "--", "--"),
                                 tags=("WAIT",))
            self._round_data[i] = {"iid": iid}

    def _load_params(self):
        ea = self.ea_v.get().strip()
        sp = self.set_v.get().strip()
        if sp and os.path.exists(sp):
            params = parse_set_file(sp)
            WL(self.log, f"SET 파일 로드: {os.path.basename(sp)} -- {len(params)}개")
        elif ea and os.path.exists(ea):
            raw = parse_ea_params(ea)
            params = {k: v['val'] for k, v in raw.items()}
            WL(self.log, f"EA 파라미터 파싱: {os.path.basename(ea)} -- {len(params)}개")
        else:
            messagebox.showwarning("알림", "EA 또는 SET 파일을 선택하세요")
            return
        self._base_params = params
        self._selected_params = [k for k, v in params.items() if len(smart_vary(k, str(v))) > 1]
        self._render_param_table(params)
        self.param_info.delete("1.0", "end")
        WL(self.param_info, f"로드완료 {len(params)}개 / 변동대상 {len(self._selected_params)}개")
        WL(self.log, f"파라미터 로드 완료 -- 변동 대상 {len(self._selected_params)}개")

    def _start(self):
        if not hasattr(self, '_base_params') or not self._base_params:
            messagebox.showwarning("알림", "먼저 파라미터를 로드하세요")
            return
        self._stop = False
        n = int(self.rd_v.get() or 10)
        self._init_table()
        self.r_btn.config(state="disabled"); self.s_btn.config(state="normal")
        self.prog.config(text="실행 중...")
        threading.Thread(target=self._run_rounds, args=(n,), daemon=True).start()

    # -- SOLO 백테스터 연동 헬퍼 ----------------------------------
    @staticmethod
    def _find_mt4_dir():
        search_roots = []
        p = HERE
        for _ in range(3):
            p = os.path.dirname(p)
            if p and os.path.isdir(p):
                search_roots.append(p)
        for root in search_roots:
            try:
                for name in os.listdir(root):
                    d = os.path.join(root, name)
                    if not os.path.isdir(d):
                        continue
                    if os.path.exists(os.path.join(d, "terminal.exe")):
                        return d
                    if os.path.exists(os.path.join(d, "Start_Portable.bat")):
                        return d
            except Exception:
                continue
        return ""

    def _get_solo_paths(self):
        solo = self.solo_v.get().strip() or HERE
        ini = os.path.join(solo, "configs", "current_config.ini")
        ahk = ""
        for name in ("SIMPLE_4STEPS_NC23.ahk", "SIMPLE_4STEPS_v5.3.ahk", "SIMPLE_4STEPS_v4_0.ahk"):
            cand = os.path.join(solo, "scripts", name)
            if os.path.exists(cand):
                ahk = cand; break
            cand = os.path.join(solo, name)
            if os.path.exists(cand):
                ahk = cand; break
        if not ahk:
            ahk = os.path.join(solo, "scripts", "SIMPLE_4STEPS_NC23.ahk")
        flag = os.path.join(solo, "configs", "test_completed.flag")
        ahk_exe = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
        if not os.path.exists(ahk_exe):
            ahk_exe = r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
        ea_path = ""
        mt4_files = ""
        if os.path.exists(ini):
            cp = read_ini(ini)
            ea_path = cp.get("folders", "ea_path", fallback="").strip()
            mt4_files = cp.get("folders", "setfiles_path", fallback="").strip()
            if not mt4_files:
                tp = cp.get("folders", "terminal_path", fallback="").strip()
                if tp:
                    mt4_files = os.path.join(tp, "MQL4", "Files")
        if not ea_path or not os.path.isdir(ea_path):
            mt4d = self._find_mt4_dir()
            if mt4d:
                ea_path = os.path.join(mt4d, "MQL4", "Experts")
                mt4_files = os.path.join(mt4d, "MQL4", "Files")
        return {"solo": solo, "ini": ini, "ahk": ahk, "flag": flag,
                "ahk_exe": ahk_exe, "ea_path": ea_path, "mt4_files": mt4_files}

    def _update_ini(self, ini_path, ea_name, symbol, period, from_date, to_date, set_file_path=""):
        cp = read_ini(ini_path)
        if not cp.has_section("current_backtest"):
            cp.add_section("current_backtest")
        cp.set("current_backtest", "ea_name", ea_name)
        cp.set("current_backtest", "symbol", symbol)
        cp.set("current_backtest", "period", period)
        cp.set("current_backtest", "from_date", from_date)
        cp.set("current_backtest", "to_date", to_date)
        cp.set("current_backtest", "set_file_path", set_file_path)
        cp.set("current_backtest", "has_set", "1" if set_file_path else "0")
        if not cp.has_section("test_date"):
            cp.add_section("test_date")
        cp.set("test_date", "enable", "1")
        cp.set("test_date", "from_date", from_date)
        cp.set("test_date", "to_date", to_date)
        with open(ini_path, "w", encoding="utf-8-sig") as f:
            cp.write(f)
        ea_txt = os.path.join(os.path.dirname(ini_path), "current_ea_name.txt")
        with open(ea_txt, "w", encoding="utf-8") as f:
            f.write(ea_name + ".ex4\n")

    def _write_set_mt4(self, set_params, mt4_files, set_filename):
        os.makedirs(mt4_files, exist_ok=True)
        lines = [f"{k}={v}||0||0" for k, v in set_params.items()]
        path = os.path.join(mt4_files, set_filename)
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(lines) + "\n")
        return path

    def _run_ahk_backtest(self, paths, ea_name, symbol, period, test_num=1, timeout=300,
                          from_date="", to_date="", total_sets=1):
        flag = paths["flag"]
        solo = paths.get("solo", HERE)
        cmd_path = os.path.join(solo, "configs", "command.json")
        proc_path = os.path.join(solo, "configs", "command_processing.json")

        for fp in (flag, proc_path):
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                except OSError:
                    pass

        cmd_data = {
            "ea_name": ea_name, "symbol": symbol, "timeframe": period,
            "iteration": test_num, "total_sets": total_sets,
            "from_date": from_date, "to_date": to_date
        }
        try:
            with open(cmd_path, "w", encoding="utf-8") as f:
                json.dump(cmd_data, f, ensure_ascii=False)
            WL(self.log, f"  [NC] command.json 생성: {ea_name} {symbol} {period}")
        except Exception as e:
            WL(self.log, f"  command.json 생성 실패: {e}", "e")

        solo_detected = False
        for _ in range(10):
            if os.path.exists(proc_path) or not os.path.exists(cmd_path):
                solo_detected = True
                WL(self.log, "  [NC] SOLO_nc2.3 AutoTrigger 감지 OK")
                break
            time.sleep(1)

        if not solo_detected:
            WL(self.log, "  [FALLBACK] SOLO_nc2.3 미감지 - 직접 AHK 실행", "w")
            if os.path.exists(cmd_path):
                try:
                    os.remove(cmd_path)
                except OSError:
                    pass
            ahk_script = paths.get("ahk", "")
            if ahk_script and os.path.exists(ahk_script):
                cmd = [paths["ahk_exe"], ahk_script, ea_name, symbol, period, str(test_num)]
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)

        start = time.time()
        while time.time() - start < timeout:
            if self._stop:
                return False
            if os.path.exists(flag):
                try:
                    txt = open(flag, "r").read().strip()
                    if txt in ("DONE", "1"):
                        return True
                except Exception:
                    pass
            time.sleep(2)
        WL(self.log, f"  AHK 타임아웃 ({timeout}s)", "w")
        return False

    def _run_analyzer(self, report_folder, ea_name, round_num, analyzer_py):
        if not os.path.exists(analyzer_py):
            WL(self.log, f"  분석기 없음: {analyzer_py}", "w")
            return None
        if not os.path.exists(report_folder):
            WL(self.log, f"  리포트 폴더 없음: {report_folder}", "w")
            return None

        result_json = os.path.join(report_folder, "SUMMARY", "test_result.json")
        if os.path.exists(result_json):
            os.remove(result_json)

        WL(self.log, f"  분석기 실행: R{round_num:02d}")
        cmd = [sys.executable, analyzer_py, "--auto", report_folder,
               "--round", str(round_num), "--ea", ea_name]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            start = time.time()
            while time.time() - start < 120:
                if self._stop:
                    proc.terminate()
                    return None
                if os.path.exists(result_json):
                    break
                time.sleep(2)
            proc.terminate()
            if os.path.exists(result_json):
                with open(result_json, "r", encoding="utf-8") as f:
                    return json.load(f)
            return self._parse_summary_csv(report_folder, round_num)
        except Exception as e:
            WL(self.log, f"  분석기 오류: {e}", "e")
            return None

    def _parse_summary_csv(self, report_folder, round_num):
        summary_dir = os.path.join(report_folder, "SUMMARY")
        csvs = sorted(glob.glob(os.path.join(summary_dir, "Full_Report_*.csv")),
                      key=os.path.getmtime, reverse=True)
        if not csvs:
            return None
        best = {'net_profit': 0, 'profit_factor': 1.0, 'win_rate': 0, 'max_drawdown': 0}
        try:
            with open(csvs[0], "r", encoding="utf-8-sig") as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    np = float(row.get('net_profit', 0) or 0)
                    if np > best['net_profit']:
                        best['net_profit'] = np
                        best['profit_factor'] = float(row.get('profit_factor', 1) or 1)
                        best['win_rate'] = float(row.get('win_rate', 0) or 0)
                        best['max_drawdown'] = float(row.get('max_drawdown', 0) or 0)
        except Exception as e:
            WL(self.log, f"  CSV 파싱 오류: {e}", "w")
        return best

    # -- 거래 없음 감지 + EA 소스 자동 수정 -----------------------
    def _check_zero_trades(self, mt4_dir, ea_name):
        if not mt4_dir:
            return False
        log_dir = os.path.join(mt4_dir, "tester", "logs")
        if not os.path.exists(log_dir):
            return False
        logs = sorted(glob.glob(os.path.join(log_dir, "*.log")), key=os.path.getmtime, reverse=True)
        if not logs:
            return False
        txt = ""
        for enc in ("utf-16", "utf-8", "cp949"):
            try:
                txt = open(logs[0], encoding=enc, errors="ignore").read()
                break
            except Exception:
                pass
        if re.search(r'\b0\s+trades?\b', txt, re.IGNORECASE):
            return True
        if "no trading" in txt.lower():
            return True
        if re.search(r'total trades\s*:\s*0', txt, re.IGNORECASE):
            return True
        return False

    _ZERO_TRADE_FIXES = [
        ("ADX 필터 너무 높음",
         r'InpAdxTrendMin\s*=\s*([3-9]\d)',
         lambda m, c: re.sub(r'(extern\s+\w+\s+InpAdxTrendMin\s*=\s*)\d+', r'\g<1>15', c)),
        ("RSI 범위 너무 좁음",
         r'InpRsiOB\s*=\s*([5-6]\d).*InpRsiOS\s*=\s*([3-4]\d)',
         lambda m, c: re.sub(r'(extern\s+\w+\s+InpRsiOB\s*=\s*)\d+', r'\g<1>75',
                    re.sub(r'(extern\s+\w+\s+InpRsiOS\s*=\s*)\d+', r'\g<1>25', c))),
        ("시간 필터 활성화",
         r'InpUseTimeFilter\s*=\s*1',
         lambda m, c: re.sub(r'(extern\s+\w+\s+InpUseTimeFilter\s*=\s*)1', r'\g<1>0', c)),
        ("CrashGuard 쿨다운 과도",
         r'InpCooldownBars\s*=\s*(\d{2,})',
         lambda m, c: re.sub(r'(extern\s+\w+\s+InpCooldownBars\s*=\s*)\d+', r'\g<1>3', c)),
        ("EMA 간격 너무 작음",
         r'InpEmaFast\s*=\s*(\d+).*InpEmaSlow\s*=\s*(\d+)',
         None),
        ("MaxSpread 너무 좁음",
         r'InpMaxSpreadBTC\s*=\s*([1-9]\d{2,3})\b',
         lambda m, c: re.sub(r'(extern\s+\w+\s+InpMaxSpreadBTC\s*=\s*)\d+', r'\g<1>7000', c)),
    ]

    def _fix_zero_trade_ea(self, mq4_path):
        if not mq4_path or not os.path.exists(mq4_path):
            return [], "mq4 파일 없음"
        content = None
        for enc in ("utf-8-sig", "utf-8", "cp949"):
            try:
                content = open(mq4_path, encoding=enc).read()
                break
            except Exception:
                pass
        if content is None:
            return [], "파일 읽기 실패"

        applied = []
        new_content = content
        for desc, pattern, fix_fn in self._ZERO_TRADE_FIXES:
            m = re.search(pattern, new_content, re.DOTALL | re.IGNORECASE)
            if m:
                if fix_fn:
                    try:
                        fixed = fix_fn(m, new_content)
                        if fixed != new_content:
                            new_content = fixed
                            applied.append(f"[수정] {desc}")
                        else:
                            applied.append(f"[감지] {desc} (이미 조정됨)")
                    except Exception as e:
                        applied.append(f"[오류] {desc}: {e}")
                else:
                    applied.append(f"[경고] {desc} -- 수동 확인 필요")

        if applied and new_content != content:
            bak = mq4_path + ".zerotrade_bak"
            with open(bak, "w", encoding="utf-8-sig") as f:
                f.write(content)
            with open(mq4_path, "w", encoding="utf-8-sig") as f:
                f.write(new_content)
            applied.append(f"저장완료 (백업: {os.path.basename(bak)})")
        elif not applied:
            applied.append("자동 수정 패턴 없음 -- 수동 확인 필요")
        return applied, new_content

    def _grade(self, profit, pf, win, mdd):
        sc = 0
        if profit > 5000: sc += 3
        elif profit > 1000: sc += 2
        elif profit > 0: sc += 1
        if pf > 1.5: sc += 3
        elif pf > 1.2: sc += 2
        elif pf > 1.0: sc += 1
        if win > 60: sc += 2
        elif win > 50: sc += 1
        if mdd < 20: sc += 2
        elif mdd < 40: sc += 1
        return ['F', 'D', 'C', 'B', 'A', 'S'][min(sc // 2, 5)]

    # -- 메인 라운드 실행 (v6.0 완전 연결) --------------------------
    def _run_rounds(self, max_rounds):
        step = float(self.st_v.get() or 0.15)
        mx = int(self.mx_v.get() or 3)
        self._step_override = {}
        for k, chk_v, val_v, step_v in getattr(self, "_ptbl_rows", []):
            sv = step_v.get().strip()
            if sv:
                try:
                    self._step_override[k] = float(sv)
                except Exception:
                    pass
        best_params = dict(self._base_params)
        best_profit = None
        ea_full = self.ea_v.get().strip()
        ea_name = os.path.splitext(os.path.basename(ea_full))[0] if ea_full else "EA"
        symbol = self.sym_v.get().strip() or "XAUUSD"
        period = self.tf_v.get().strip() or "H1"
        from_date = self.fr_v.get().strip() or "2025.01.01"
        to_date = self.to_v.get().strip() or "2025.09.30"

        paths = self._get_solo_paths()
        if not os.path.exists(paths["ini"]):
            WL(self.log, f"current_config.ini 없음: {paths['ini']}", "e")
            self.after(0, lambda: (self.r_btn.config(state="normal"), self.s_btn.config(state="disabled")))
            return
        if not os.path.exists(paths["ahk"]):
            WL(self.log, f"AHK 스크립트 없음: {paths['ahk']}", "e")
            self.after(0, lambda: (self.r_btn.config(state="normal"), self.s_btn.config(state="disabled")))
            return

        set_dir = os.path.join(HERE, "round_sets"); os.makedirs(set_dir, exist_ok=True)
        report_base = self.rep_v.get().strip() or r"C:\2026NEWOPTMIZER"
        analyzer = self.ana_v.get().strip()

        ea_path = paths["ea_path"]
        ex4_path = os.path.join(ea_path, ea_name + ".ex4") if ea_path else ""
        if not os.path.exists(ex4_path) and ea_path:
            ex4_path = os.path.join(ea_path, "ee", ea_name + ".ex4")
        if not os.path.exists(ex4_path):
            WL(self.log, f".ex4 없음 -- EA를 먼저 컴파일하세요: {ea_name}.ex4", "w")

        # ── v6.0: RoundDirector 초기화 ───────────────────────────────
        director = RoundDirector()
        WL(self.log, f"[v6.0] RoundDirector 초기화 — 상관분석·하위수리·롤백 활성화")

        for rn in range(1, max_rounds + 1):
            if self._stop:
                WL(self.log, f"R{rn}에서 중단", "e")
                break
            iid = self._round_data.get(rn, {}).get("iid")
            if iid:
                self.after(0, lambda i=iid: (self.rt.set(i, "상태", "실행중"), self.rt.item(i, tags=("RUN",))))
            self.after(0, lambda r=rn: self.prog.config(text=f"R{r:02d}/{max_rounds} 진행 중"))
            WL(self.log, f"\n{'='*50}\n[R{rn:02d}] 시작 -- {ea_name} | {symbol} {period}")

            sel = getattr(self, "_selected_params", None)
            vary_params = best_params
            if sel:
                vary_params = {k: v for k, v in best_params.items() if k in sel}
                fixed_params = {k: v for k, v in best_params.items() if k not in sel}
            else:
                fixed_params = {}

            # ── v6.0: SET 생성 전략 분기 ─────────────────────────────
            # R1: 균등 격자 탐색 (데이터 없음)
            # R2+: 상관분석 기반 비균등 탐색 + 하위 수리 세트 추가
            hist = director.analyzer.get_history()
            if rn >= 2 and hist:
                sweet_spots   = director.analyzer.find_sweet_spots()
                correlations  = director.analyzer.rank_param_impact()
                sets = gen_round_sets_v2(vary_params, rn,
                                          sweet_spots=sweet_spots,
                                          correlations=correlations,
                                          max_vary=mx)
                WL(self.log, f"  [v2탐색] 상관분석 기반 — "
                             f"sweet_spots:{len(sweet_spots)}개 / "
                             f"top상관: {list(correlations.items())[:2]}")

                # 하위 수리 세트 추가 (직전 라운드 분석 결과 활용)
                if director._round_history:
                    last_analysis = director._round_history[-1]
                    bottom_group  = last_analysis.get("bottom_group", [])
                    comparison    = last_analysis.get("comparison", {})
                    if bottom_group and comparison:
                        fix_sets = gen_bottom_fix_sets(bottom_group, comparison, best_params)
                        if fix_sets:
                            sets = sets + fix_sets
                            WL(self.log, f"  [하위수리] {len(fix_sets)}개 수리세트 추가 "
                                         f"(하위{len(bottom_group)}개 → 상위 방향 50% 이동)")
            else:
                eff_step = step * max(0.2, 1.0 - (rn - 1) * 0.13)
                WL(self.log, f"  [v1탐색] 균등격자 step:{eff_step:.4f} "
                             f"(R{rn} 수렴률 {eff_step/step*100:.0f}%)")
                sets = gen_round_sets(vary_params, rn, max_vary=mx, n_steps=3, step=step,
                                      step_override=getattr(self, "_step_override", None))

            if fixed_params:
                sets = [{**fixed_params, **s} for s in sets]
            WL(self.log, f"  총 세트: {len(sets)}개 (변동:{len(vary_params)}개, 고정:{len(fixed_params)}개)")

            rset_dir = os.path.join(set_dir, ea_name, f"R{rn:02d}"); os.makedirs(rset_dir, exist_ok=True)

            r_results = []
            for si, sp in enumerate(sets):
                if self._stop:
                    break
                sfname = f"R{rn:02d}_{ea_name}_set{si+1:03d}.set"
                sfpath = os.path.join(rset_dir, sfname)

                content = "\n".join(f"{k}={v}||0||0" for k, v in sp.items()) + "\n"
                with open(sfpath, "w", encoding="utf-8-sig") as f:
                    f.write(content)

                mt4_set_path = ""
                if paths["mt4_files"]:
                    mt4_set_path = self._write_set_mt4(sp, paths["mt4_files"], sfname)
                    WL(self.log, f"  SET -> MT4: {sfname}")

                self._update_ini(paths["ini"], ea_name, symbol, period,
                                 from_date, to_date, mt4_set_path or sfpath)

                WL(self.log, f"  [{si+1}/{len(sets)}] 백테스트 실행...")
                self.after(0, lambda r=rn, si=si: self.prog.config(
                    text=f"R{r:02d} -- SET {si+1}/{len(sets)}"))

                ok = self._run_ahk_backtest(paths, ea_name, symbol, period,
                                            test_num=rn*100+si+1, timeout=300,
                                            from_date=from_date, to_date=to_date,
                                            total_sets=len(sets))

                mt4_dir = os.path.dirname(paths.get("ea_path", "")) if paths.get("ea_path") else ""
                if mt4_dir:
                    mt4_dir = os.path.dirname(os.path.dirname(mt4_dir))
                if ok and self._check_zero_trades(mt4_dir, ea_name):
                    WL(self.log, "  거래 0건 감지! EA 소스 자동 수정 시도...", "w")
                    mq4_path = ""
                    if ea_full and os.path.exists(ea_full):
                        mq4_path = ea_full
                    elif paths.get("ea_path"):
                        cand = os.path.join(paths["ea_path"], ea_name + ".mq4")
                        if os.path.exists(cand):
                            mq4_path = cand
                        else:
                            cand2 = os.path.join(paths["ea_path"], "ee", ea_name + ".mq4")
                            if os.path.exists(cand2):
                                mq4_path = cand2
                    if mq4_path:
                        fixes, _ = self._fix_zero_trade_ea(mq4_path)
                        for fx in fixes:
                            WL(self.log, f"    {fx}", "w")
                    else:
                        WL(self.log, "  mq4 파일 없음 -- 수동 확인 필요", "e")

                if ok:
                    today_dir = os.path.join(report_base,
                                             datetime.datetime.now().strftime("%Y%m%d"))
                    rep_folder = today_dir if os.path.exists(today_dir) else report_base
                    res = self._run_analyzer(rep_folder, ea_name, rn, analyzer)
                    if res:
                        res['set_params'] = sp
                        r_results.append(res)
                        np_val = res.get('net_profit', 0)
                        WL(self.log, f"  SET{si+1} 결과: ${np_val:.2f} / PF:{res.get('profit_factor', 0):.2f}")
                    else:
                        WL(self.log, f"  SET{si+1} 분석 결과 없음", "w")
                else:
                    WL(self.log, f"  SET{si+1} 백테스트 실패", "e")

            if r_results:
                # ── 스코어 계산 ──────────────────────────────────────
                for res in r_results:
                    sc, grd, rec = calc_score_grade(res)
                    res['score'] = sc
                    res['grade_v45'] = grd
                    res['recommendation'] = rec

                best_r = max(r_results, key=lambda x: (x.get('score', 0), x.get('net_profit', 0)))
                bp  = best_r.get('net_profit', 0)
                bpf = best_r.get('profit_factor', 1.0)
                win = best_r.get('win_rate', 0)
                mdd = best_r.get('max_drawdown', 0)
                sc  = best_r.get('score', 0)
                grade = best_r.get('grade_v45', self._grade(bp, bpf, win, mdd))
                rec   = best_r.get('recommendation', '')
                chg   = ", ".join(f"{k}:{v}" for k, v in list(best_r.get('set_params', {}).items())[:3])

                WL(self.log, f"  [SCORE] {sc}점 / 등급:{grade} / {rec}")

                # 거래 0건 진단
                rep_folder = self.rep_v.get().strip() or r"C:\2026NEWOPTMIZER"
                htm_files = glob.glob(os.path.join(rep_folder, "**", "*.htm"), recursive=True)
                if htm_files and best_r.get('total_trades', 1) == 0:
                    latest_htm = max(htm_files, key=os.path.getmtime)
                    diags = diagnose_zero_trades(latest_htm)
                    for d in diags:
                        WL(self.log, f"  [진단] {d}", "w")

                # ── v6.0: RoundDirector 분석 ─────────────────────────
                # analyzer 입력 포맷 변환 (htm 키 정규화)
                director_input = []
                for res in r_results:
                    director_input.append({
                        "params": res.get("set_params", {}),
                        "htm": {
                            "net_profit":       res.get("net_profit", 0),
                            "profit_factor":    res.get("profit_factor", 0),
                            "win_rate":         res.get("win_rate", 0),
                            "max_drawdown_pct": res.get("max_drawdown", 0),
                            "total_trades":     res.get("total_trades", 0),
                        }
                    })
                analysis = director.analyze_round(rn, director_input)
                top_n   = len(analysis.get("top_group", []))
                bot_n   = len(analysis.get("bottom_group", []))
                WL(self.log, f"  [분석] 상위{top_n}개 / 하위{bot_n}개 / "
                             f"BEST:{analysis.get('best_score',0):.1f}pts / "
                             f"AVG:{analysis.get('avg_score',0):.1f}pts")

                # ── v6.0: 방향 검증 + 롤백 판단 ─────────────────────
                direction = director.check_direction()
                status_kr = {"improving": "개선↑", "declining": "악화↓",
                             "stagnant": "정체→", "first_round": "첫라운드"
                             }.get(direction["status"], direction["status"])
                WL(self.log, f"  [방향] {status_kr} — {direction['details']}")

                if direction["should_rollback"]:
                    rollback_params = director.get_rollback_params()
                    if rollback_params:
                        best_params = rollback_params
                        WL(self.log,
                           f"  ⚠ [롤백] R{direction['rollback_to']} 최적 파라미터로 복원 "
                           f"(2라운드 연속 악화)", "w")
                    else:
                        WL(self.log, "  [롤백] 대상 없음 — 현재 파라미터 유지", "w")
                else:
                    # ── v6.0: 데이터 기반 파라미터 조정 (v2) ────────
                    next_params, adj_log = director.decide_next_params(best_params)
                    WL(self.log, f"  [v2조정] 파라미터 {len(adj_log)}개 항목 분석:")
                    for msg in adj_log[:6]:   # 최대 6줄만 출력
                        WL(self.log, f"    {msg}")

                    if best_profit is None or bp > best_profit:
                        best_profit = bp
                        best_params = next_params
                        if iid:
                            self.after(0, lambda i=iid: self.rt.item(i, tags=("BEST",)))
                        WL(self.log, f"  ★ BEST 업데이트: ${bp:.2f} [{grade}] {sc}pts", "o")
                    else:
                        best_params = next_params
                        WL(self.log, f"  BEST: ${best_profit:.2f} 유지 / 이번: ${bp:.2f} [{grade}]")

                # ── v6.0: round_history.json 기록 ────────────────────
                self._write_round_history(rn, r_results, ea_name, period)

                result = {'best_profit': bp, 'best_pf': bpf, 'win_rate': win,
                          'mdd': mdd, 'grade': grade, 'score': sc,
                          'recommendation': rec, 'change_summary': chg,
                          'best_params': best_params,
                          'direction': direction['status'],
                          'top_n': top_n, 'bottom_n': bot_n}
                if iid:
                    vals = (f"R{rn:02d}", "완료", str(len(sets)), f"${bp:.2f}",
                            f"{bpf:.2f}", f"{win:.1f}%", f"{mdd:.2f}",
                            f"{grade}({sc})", chg[:40])
                    tag = "BEST" if (best_profit is not None and bp >= best_profit) else "DONE"
                    self.after(0, lambda i=iid, v=vals, t=tag:
                               (self.rt.item(i, values=v), self.rt.item(i, tags=(t,))))
                self._round_data[rn]['result'] = result
            else:
                WL(self.log, f"  R{rn} 결과 없음", "e")
                if iid:
                    self.after(0, lambda i=iid: (self.rt.set(i, "상태", "실패"),
                                                  self.rt.item(i, tags=("FAIL",))))

        # ── 최종 보고서 출력 ─────────────────────────────────────────
        fin = f"${best_profit:.2f}" if best_profit else "$0"
        report_txt = director.generate_report()
        WL(self.log, f"\n{report_txt}", "o")
        WL(self.log, f"\n최적화 완료! 최고 수익: {fin}", "o")
        self.after(0, lambda: (self.r_btn.config(state="normal"),
                               self.s_btn.config(state="disabled"),
                               self.prog.config(text=f"완료 -- BEST: {fin}")))

        email_cfg = os.path.join(HERE, "email.json")
        if os.path.exists(email_cfg):
            email_results = []
            for rn2, rd in self._round_data.items():
                res2 = rd.get('result', {})
                if res2:
                    email_results.append({
                        'round': rn2,
                        'grade': res2.get('grade', '?'),
                        'score': res2.get('score', 0),
                        'profit': res2.get('best_profit', 0),
                        'pf': res2.get('best_pf', 0),
                    })
            if email_results:
                def _send():
                    ok, msg = send_email_report(email_results,
                                                f"EA AutoMaster {max_rounds}라운드 완료 -- BEST {fin}")
                    self.after(0, lambda: WL(self.log, f"[EMAIL] {msg}", "o" if ok else "e"))
                threading.Thread(target=_send, daemon=True).start()

    # -- round_history.json 기록 ------------------------------------
    def _write_round_history(self, round_num, r_results, ea_name, tf):
        """라운드 완료 후 round_history.json에 누적 기록."""
        import json as _json
        hist_path = os.path.join(HERE, "round_history.json")
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                hist = _json.load(f)
        except Exception:
            hist = []

        # 이 라운드 기존 항목 제거 (재실행 시 중복 방지)
        hist = [h for h in hist if h.get("round") != round_num]

        ranked = sorted(r_results, key=lambda x: x.get("score", 0), reverse=True)
        for rank, res in enumerate(ranked, 1):
            sc = res.get("score", 0)
            verdict = "GOOD" if sc >= 70 else ("MID" if sc >= 40 else "BAD")
            sp = res.get("set_params", {})
            # SL/TP 추출 (파라미터명 대소문자 무시)
            sl_val = next((float(v) for k, v in sp.items()
                           if "sl" in k.lower() or "stoploss" in k.lower()), 0)
            tp_val = next((float(v) for k, v in sp.items()
                           if k.lower() in ("tp", "takeprofit", "tpvalue")), 0)
            hist.append({
                "round":   round_num,
                "cat":     ea_name[:24],
                "sl":      round(sl_val, 3),
                "tp":      round(tp_val, 3),
                "lot":     next((float(v) for k, v in sp.items()
                                 if "lot" in k.lower()), 0.01),
                "tf":      tf,
                "profit":  round(res.get("net_profit", 0), 2),
                "winrate": round(res.get("win_rate", 0), 2),
                "pf":      round(res.get("profit_factor", 0), 3),
                "trades":  res.get("total_trades", 0),
                "rank":    rank,
                "verdict": verdict,
            })

        with open(hist_path, "w", encoding="utf-8") as f:
            _json.dump(hist, f, indent=2, ensure_ascii=False)
        WL(self.log, f"  [히스토리] round_history.json +{len(ranked)}개 기록")

    def _load_db(self):
        db = self.rep_v.get().strip()
        if not os.path.exists(db):
            messagebox.showwarning("알림", f"DB 없음:\n{db}")
            return
        try:
            conn = sqlite3.connect(db)
            rows = conn.execute(
                "SELECT ea_name,status,COUNT(*) FROM tasks GROUP BY ea_name,status ORDER BY ea_name"
            ).fetchall()
            conn.close()
            self.log.delete("1.0", "end")
            WL(self.log, "=== DB 태스크 현황 ===")
            for ea, st, cnt in rows:
                WL(self.log, f"  {ea} | {st} | {cnt}개")
        except Exception as e:
            WL(self.log, f"DB 조회 실패: {e}", "e")

    def _do_stop(self):
        self._stop = True
        WL(self.log, "중지 요청", "e")

    def _open_set(self):
        d = os.path.join(HERE, "round_sets")
        os.makedirs(d, exist_ok=True)
        subprocess.run(["start", "", d], shell=True)
