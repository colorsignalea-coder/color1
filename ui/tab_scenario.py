"""
ui/tab_scenario.py — EA Auto Master v6.0
=========================================
시나리오 마스터 탭 — 160개 사전설정 시나리오 자동 생성 + 컴파일.
v5.4 L3343-7117 추출.
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

from core.config import HERE
from core.encoding import read_ini
from core.mql4_autofix import cv1_preprocess, cv1_compile_ea, cv1_read_log, cv1_parse_errors
from core.mql4_merger import parse_mq4_blocks
from core.path_finder import _find_mt4_near_here
from ui.theme import (BG, FG, PANEL, PANEL2, ACCENT, BLUE, GREEN, RED, TEAL,
                      AMBER, CYAN, ROSE, TITLE, LBL, MONO, B, LB, WL)

class ScenarioMasterTab(ttk.Frame):
    """
    8가지 시나리오 카테고리 × 20개 = 160개 사전설정
    1개 EA에 전부 적용해 컴파일 횟수 최소화 → 빠른 최적화
    """

    # ── 카테고리 정의 ──────────────────────────────────────────
    CAT_META = {
        "SL_DEC":   {"color":"#ef4444","icon":"🛑","desc":"SL_DEC (50~525): tight stop"},
        "SL_INC":   {"color":"#f97316","icon":"📊","desc":"SL_INC (550~1500): wide stop"},
        "TP_INC":   {"color":"#22c55e","icon":"💚","desc":"TP_INC (90~470): big target"},
        "TF_CHG":   {"color":"#a855f7","icon":"⏱️","desc":"TF_CHG (M5/M15/M30/H1/H4 x4)"},
        "LOT_BIG":  {"color":"#3b82f6","icon":"🚀","desc":"LOT_BIG (0.20~1.91): high risk"},
        "LOT_SML":  {"color":"#8b5cf6","icon":"🔰","desc":"LOT_SML (0.01~0.105): low risk"},
        "SLTP_MIX": {"color":"#eab308","icon":"⚖️","desc":"SLTP_MIX: R:R optimize"},
        "FULL_MIX": {"color":"#06b6d4","icon":"🌈","desc":"FULL_MIX: SL+TP+Lot+TF all"},
    }

    TF_CODES = {5:"M5",15:"M15",30:"M30",60:"H1",240:"H4"}

    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        # ★v5.3: 간격 설정 변수
        self._gap_preset  = tk.StringVar(value="balanced")
        self._gap_sl_dec  = tk.IntVar(value=25)
        self._gap_sl_inc  = tk.IntVar(value=50)
        self._gap_tp_inc  = tk.IntVar(value=20)
        self._gap_lot_big = tk.DoubleVar(value=0.09)
        self._gap_lot_sml = tk.DoubleVar(value=0.005)
        # ★v5.3: 신규 변수 범위
        self._risk_min = tk.DoubleVar(value=1.0)
        self._risk_max = tk.DoubleVar(value=3.0)
        self._dd_min   = tk.DoubleVar(value=5.0)
        self._dd_max   = tk.DoubleVar(value=15.0)
        self._pos_min  = tk.IntVar(value=1)
        self._pos_max  = tk.IntVar(value=6)
        # 신규 변수 적용 여부 on/off
        self._use_risk = tk.BooleanVar(value=True)
        self._use_dd   = tk.BooleanVar(value=True)
        self._use_pos  = tk.BooleanVar(value=True)
        self._nth_var     = tk.IntVar(value=1)      # ★v5.4.1: 표시 간격 (1=전체)
        self._interval_btns = {}                    # ★간격 버튼 하이라이트용
        self._scenarios = self._gen_scenarios()
        self._chk_vars  = {}   # iid → BooleanVar
        # out_dir: INI의 ea_path(Experts 루트) 우선, 없으면 HERE\output 폴백
        # html_save_path는 Reports 폴더라 컴파일 출력 폴더로 부적합 → 제외
        _ini_path = os.path.join(HERE, "configs", "current_config.ini")
        _experts_from_ini = ""
        if os.path.exists(_ini_path):
            _cp_tmp = read_ini(_ini_path)
            _tp = _cp_tmp.get("folders", "terminal_path", fallback="").strip()
            if _tp and os.path.isdir(_tp):
                _experts_from_ini = os.path.join(_tp, "MQL4", "Experts")
        _out_default = _experts_from_ini or cfg.get("ea_path", "") or os.path.join(HERE, "output")
        self._out_dir   = tk.StringVar(value=_out_default)
        _def_ea = os.path.join(HERE, "13 ea v7 master 5.0", "output", "StochRSI_Divergence_EA_v7", "StochRSI_Divergence_EA_v7_R1_FULLMIX_01_SL544_TP87_L0.15_5m_0405FF.mq4")
        self._ea_path   = tk.StringVar(value=_def_ea if os.path.exists(_def_ea) else "")
        self._sl_var    = tk.IntVar(value=500)
        self._tp_var    = tk.IntVar(value=80)
        self._lot_var   = tk.DoubleVar(value=0.10)
        self._tf_var    = tk.IntVar(value=5)
        self._fname_var = tk.StringVar(value="MyEA_Custom")
        # 백테스트 실행 설정
        self._sym_var   = tk.StringVar(value="BTCUSD")
        # ★v5.3: 심볼 다중 선택 (시나리오 생성용)
        self._sym_checks = {
            "BTCUSD": tk.BooleanVar(value=True),
            "XAUUSD": tk.BooleanVar(value=False),
            "USDJPY": tk.BooleanVar(value=False),
            "EURUSD": tk.BooleanVar(value=False),
        }
        # ★v5.3: TF 다중 선택 (시나리오 생성용)
        self._per_checks = {
            "M5":  tk.BooleanVar(value=True),
            "M15": tk.BooleanVar(value=True),
            "M30": tk.BooleanVar(value=True),
            "H1":  tk.BooleanVar(value=True),
            "H4":  tk.BooleanVar(value=False),
        }
        self._per_var   = tk.StringVar(value="M5")
        self._fr_var    = tk.StringVar(value="2025.01.01")
        self._to_var    = tk.StringVar(value="2025.09.30")
        # 배포형: SOLO_nc2.3 자동 감지 (자기 폴더 우선)
        _solo_default = HERE
        for _sd in (HERE, os.path.dirname(HERE)):
            if os.path.exists(os.path.join(_sd, "SOLO_nc2.3.ahk")):
                _solo_default = _sd; break
            if os.path.exists(os.path.join(_sd, "SOLO_v5.3.ahk")):
                _solo_default = _sd; break
        self._solo_var  = tk.StringVar(value=_solo_default)
        self._stop_bt   = False
        self._ea_folder_paths = []   # ★v4.0: 폴더 선택 시 .mq4 경로 목록
        self._round_no  = tk.IntVar(value=1)   # 현재 라운드 번호
        self._hist_path = os.path.join(HERE, "round_history.json")
        # ★v5.4 라운드 컨트롤 변수
        self._rnd_sel      = tk.IntVar(value=1)
        self._rnd_end      = tk.IntVar(value=3)   # 범위 실행 끝 라운드
        self._rnd_proc     = None
        self._rnd_evo_tree = None
        self._rnd_status   = None
        self._rnd_stop_btn = None
        # ── G4v7 파라미터 (ATR / MA / ADX / RSI / Cooldown) ──────────────
        self._atr_period  = tk.IntVar(value=20)
        self._fast_ma     = tk.IntVar(value=12)
        self._slow_ma     = tk.IntVar(value=28)
        self._adx_period  = tk.IntVar(value=14)
        self._adx_min     = tk.DoubleVar(value=18.0)
        self._rsi_period  = tk.IntVar(value=14)
        self._rsi_lower   = tk.DoubleVar(value=35.0)
        self._rsi_upper   = tk.DoubleVar(value=70.0)
        self._cooldown    = tk.IntVar(value=6)
        self._use_atr = tk.BooleanVar(value=True)
        self._use_ma  = tk.BooleanVar(value=True)
        self._use_adx = tk.BooleanVar(value=True)
        self._use_rsi = tk.BooleanVar(value=True)
        self._use_cd  = tk.BooleanVar(value=True)
        self._build()

    # ── 시나리오 생성 ★v5.3: 간격 파라미터 지원 ──────────────────
    def _gen_scenarios(self, sl_dec_gap=25, sl_inc_gap=50, tp_inc_gap=20,
                       lot_big_gap=0.09, lot_sml_gap=0.005, tf_list=None):
        """★v5.3: 간격 조정 가능 (기본값=v4.5 호환)
        tf_list: 선택된 TF 리스트 (None이면 [5] 기본값)"""
        # 상단 TF 체크박스에서 선택된 TF 목록
        TF_MAP = {"M5":5,"M15":15,"M30":30,"H1":60,"H4":240}
        if tf_list is None:
            if hasattr(self, '_per_checks'):
                tf_list = [TF_MAP[k] for k, v in self._per_checks.items() if v.get()]
            if not tf_list:
                tf_list = [5]
        s = []
        # 기본 TF = 첫 번째 선택 TF (SL/TP/Lot 변형 시나리오용)
        base_tf = tf_list[0]
        # 1. SL 감소 (50~2000, sl_dec_gap step) × 선택 TF 수
        for tf in tf_list:
            current = 50
            for i in range(40):
                if current > 2000: break
                s.append({"cat":"SL_DEC","id":i+1,"sl":current,"tp":80,"lot":0.10,"tf":tf,
                          "note":f"tight stop TF={self.TF_CODES.get(tf,tf)}"})
                current += int(sl_dec_gap)
        # 2. SL 증가 (550~3000, sl_inc_gap step) × 선택 TF 수
        for tf in tf_list:
            current = 550
            for i in range(40):
                if current > 3000: break
                s.append({"cat":"SL_INC","id":i+1,"sl":current,"tp":80,"lot":0.10,"tf":tf,
                          "note":f"wide stop TF={self.TF_CODES.get(tf,tf)}"})
                current += int(sl_inc_gap)
        # 3. TP 증가 (90~1500, tp_inc_gap step)
        current = 90
        for i in range(40):
            if current > 1500: break
            s.append({"cat":"TP_INC","id":i+1,"sl":500,"tp":current,"lot":0.10,"tf":base_tf,"note":"big target"})
            current += int(tp_inc_gap)
        # 4. TF 변경 (5TF × 4 SL/TP 조합) = 20 (고정)
        tf_list = [5,15,30,60,240]
        sltp    = [(500,80),(544,87),(575,92),(300,60)]
        for tf in tf_list:
            for sl,tp in sltp:
                s.append({"cat":"TF_CHG","id":len([x for x in s if x["cat"]=="TF_CHG"])+1,
                          "sl":sl,"tp":tp,"lot":0.10,"tf":tf,"note":f"TF={self.TF_CODES[tf]}"})
        # 5. Lot 크게 (0.20~, lot_big_gap step) × 40
        for i in range(40):
            lot = round(0.20 + i * lot_big_gap, 2)
            s.append({"cat":"LOT_BIG","id":i+1,"sl":544,"tp":87,"lot":lot,"tf":5,"note":"high risk"})
        # 6. Lot 작게 (0.01~, lot_sml_gap step) × 40
        for i in range(40):
            lot = round(0.01 + i * lot_sml_gap, 3)
            s.append({"cat":"LOT_SML","id":i+1,"sl":544,"tp":87,"lot":lot,"tf":5,"note":"low risk"})
        # 7. SL+TP 믹스 × 40 (★확장 — SL 200~590 step 10, R:R≈0.20)
        sltp_mix = [(200+i*10, round((200+i*10)*0.20)) for i in range(40)]
        for i,(sl,tp) in enumerate(sltp_mix):
            s.append({"cat":"SLTP_MIX","id":i+1,"sl":sl,"tp":tp,"lot":0.10,"tf":5,
                      "note":f"R:R={tp/sl:.2f}"})
        # 8. 전체 믹스 × 20 (고정)
        full = [
            (544,87,0.15,5),(575,92,0.12,15),(500,100,0.10,30),(450,90,0.20,5),
            (600,80,0.08,60),(350,70,0.05,5),(557,89,0.18,15),(480,96,0.10,30),
            (520,104,0.15,5),(475,95,0.10,60),(540,108,0.12,5),(560,84,0.10,240),
            (499,79,0.10,5),(530,106,0.16,15),(510,102,0.10,5),(490,98,0.10,30),
            (570,114,0.14,5),(465,93,0.10,15),(505,101,0.10,5),(535,107,0.12,60),
        ]
        for i,(sl,tp,lot,tf) in enumerate(full):
            s.append({"cat":"FULL_MIX","id":i+1,"sl":sl,"tp":tp,"lot":lot,"tf":tf,"note":"all combo"})
        return s

    def _apply_gap_preset(self, preset=None):
        """★v5.3: 간격 프리셋 적용"""
        p = preset or self._gap_preset.get()
        presets = {
            "conservative": (25, 50, 20, 0.09, 0.005),
            "balanced":     (20, 50, 25, 0.10, 0.01),
            "aggressive":   (15, 40, 30, 0.12, 0.015),
        }
        if p in presets:
            sd, si, tp, lb, ls = presets[p]
            self._gap_sl_dec.set(sd)
            self._gap_sl_inc.set(si)
            self._gap_tp_inc.set(tp)
            self._gap_lot_big.set(lb)
            self._gap_lot_sml.set(ls)

    def _rebuild_scenarios(self):
        """★v5.3: 간격 설정 + 상단 TF/심볼 체크박스로 시나리오 재생성"""
        TF_MAP = {"M5":5,"M15":15,"M30":30,"H1":60,"H4":240}
        tf_list = [TF_MAP[k] for k, v in self._per_checks.items() if v.get()]
        if not tf_list: tf_list = [5]

        # 선택된 심볼 목록 (시나리오 노트에 반영)
        sym_list = [s for s, v in self._sym_checks.items() if v.get()]
        if not sym_list: sym_list = ["BTCUSD"]

        base_sc = self._gen_scenarios(
            sl_dec_gap  = self._gap_sl_dec.get(),
            sl_inc_gap  = self._gap_sl_inc.get(),
            tp_inc_gap  = self._gap_tp_inc.get(),
            lot_big_gap = self._gap_lot_big.get(),
            lot_sml_gap = self._gap_lot_sml.get(),
            tf_list     = tf_list,
        )
        # 다중 심볼: 각 시나리오에 symbol 필드 추가 (단일 심볼이면 그냥 저장)
        if len(sym_list) > 1:
            expanded = []
            for sym in sym_list:
                for sc in base_sc:
                    new_sc = dict(sc)
                    new_sc["symbol"] = sym
                    new_sc["note"]   = f"[{sym}] {sc['note']}"
                    expanded.append(new_sc)
            self._scenarios = expanded
        else:
            for sc in base_sc:
                sc["symbol"] = sym_list[0]
            self._scenarios = base_sc

        self._chk_vars = {}
        self._populate_tree()
        n = len(self._scenarios)
        tf_str  = "+".join(self.TF_CODES.get(t,str(t)) for t in tf_list)
        sym_str = "+".join(sym_list)
        self._cnt_lbl.config(text=f"{n}개")
        if hasattr(self, '_right_title'):
            self._right_title.config(text=f"  📋  총 {n}개 시나리오 세트 콤보 (TF선택:{len(tf_list)} X 심볼:{len(sym_list)})")
        self._status.config(text=f"✅ 시나리오 조합(콤보) 계산 완료: 총 {n}개 (TF={tf_str}, 심볼={sym_str})")

    # ── UI 빌드 ────────────────────────────────────────────────
    def _build(self):
        # ★v5.4 수직 PanedWindow: 위=라운드 컨트롤 / 아래=메인 콘텐츠
        _pv = tk.PanedWindow(self, orient="vertical", bg=BG,
                             sashwidth=5, sashrelief="groove", sashpad=2)
        _pv.pack(fill="both", expand=True)
        _top_pane = tk.Frame(_pv, bg=BG)
        _pv.add(_top_pane, height=180, minsize=100, sticky="nsew")
        _bot_pane = tk.Frame(_pv, bg=BG)
        _pv.add(_bot_pane, minsize=120, sticky="nsew")

        # ★v5.4 라운드 컨트롤 패널 (위 패널)
        self._build_round_ctrl(_top_pane)

        outer = tk.Frame(_bot_pane, bg=BG); outer.pack(fill="both", expand=True, padx=8, pady=6)

        # ── 상단: EA 선택 + 출력폴더 ─────────────────────────
        top = tk.LabelFrame(outer, text="  📁  EA 파일 & 출력 폴더",
                            font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        top.pack(fill="x", pady=(0,6))
        tf = tk.Frame(top, bg=PANEL); tf.pack(fill="x", padx=8, pady=5)
        tk.Label(tf, text="EA(.mq4):", font=LBL, fg=FG, bg=PANEL, width=10, anchor="e").pack(side="left")
        tk.Entry(tf, textvariable=self._ea_path, font=MONO, bg=PANEL2, fg="#ff6b35",
                 insertbackground=FG, relief="flat", bd=3).pack(side="left", fill="x", expand=True, padx=4)
        B(tf,"📁 선택",BLUE, self._sel_ea, pady=3).pack(side="left",padx=2)
        B(tf,"📂 폴더 스캔",TEAL, self._scan_ea, pady=3).pack(side="left",padx=2)
        B(tf,"📂 EA폴더",AMBER, self._sel_ea_folder, pady=3).pack(side="left",padx=2)
        self._folder_lbl = tk.Label(tf, text="", font=("Consolas",8), fg="#22c55e", bg=PANEL)
        self._folder_lbl.pack(side="left", padx=4)

        tf2 = tk.Frame(top, bg=PANEL); tf2.pack(fill="x", padx=8, pady=(0,5))
        tk.Label(tf2, text="저장폴더:", font=LBL, fg=FG, bg=PANEL, width=10, anchor="e").pack(side="left")
        tk.Entry(tf2, textvariable=self._out_dir, font=MONO, bg=PANEL2, fg="#a3e635",
                 insertbackground=FG, relief="flat", bd=3).pack(side="left", fill="x", expand=True, padx=4)
        B(tf2,"📁 선택",AMBER, lambda: self._out_dir.set(
            filedialog.askdirectory(initialdir=self._out_dir.get()) or self._out_dir.get()
        ), pady=3).pack(side="left",padx=2)
        B(tf2,"📂 열기",PANEL2, lambda: subprocess.run(["start","",self._out_dir.get()],shell=True),
          pady=3).pack(side="left",padx=2)

        # ── 백테스트 설정 행 ──────────────────────────────────
        tf3 = tk.Frame(top, bg=PANEL); tf3.pack(fill="x", padx=8, pady=(0,4))
        for lbl, var, w, fg_c in [
            ("심볼:",   self._sym_var, 9,  "#f472b6"),
            ("시작일:", self._fr_var,  12, "#60a5fa"),
            ("종료일:", self._to_var,  12, "#34d399"),
        ]:
            tk.Label(tf3, text=lbl, font=LBL, fg=FG, bg=PANEL, width=6, anchor="e").pack(side="left")
            tk.Entry(tf3, textvariable=var, font=MONO, bg=PANEL2, fg=fg_c,
                     insertbackground=FG, relief="flat", bd=3, width=w).pack(side="left", padx=(0,8))
        tk.Label(tf3, text="TF:", font=LBL, fg=FG, bg=PANEL, width=4, anchor="e").pack(side="left")
        _tf_cb = ttk.Combobox(tf3, textvariable=self._per_var, width=6, state="readonly",
                              values=["M1","M5","M15","M30","H1","H4","D1"])
        _tf_cb.pack(side="left", padx=(0,8))
        tf4 = tk.Frame(top, bg=PANEL); tf4.pack(fill="x", padx=8, pady=(0,5))
        tk.Label(tf4, text="SOLO폴더:", font=LBL, fg=FG, bg=PANEL, width=10, anchor="e").pack(side="left")
        tk.Entry(tf4, textvariable=self._solo_var, font=MONO, bg=PANEL2, fg="#94a3b8",
                 insertbackground=FG, relief="flat", bd=3).pack(side="left", fill="x", expand=True, padx=4)
        B(tf4,"📁 선택",PANEL2, lambda: self._solo_var.set(
            filedialog.askdirectory(initialdir=self._solo_var.get()) or self._solo_var.get()
        ), pady=3).pack(side="left",padx=2)
        B(tf4,"🔄 SOLO 동기화",GREEN, self._sync_solo_paths, pady=3).pack(side="left",padx=2)

        # ── ★v5.3: 프리셋 + 심볼 선택 + 재생성 ──────────────────
        self._init_sl  = tk.IntVar(value=500); self._init_tp  = tk.IntVar(value=80)
        self._init_lot = tk.DoubleVar(value=0.10); self._init_tf = tk.IntVar(value=5)

        tf6 = tk.Frame(top, bg=PANEL); tf6.pack(fill="x", padx=8, pady=(0,5))
        tk.Label(tf6, text="★v5.3 프리셋:", font=("Malgun Gothic",9,"bold"), fg="#a855f7", bg=PANEL).pack(side="left", padx=(0,4))
        for label, val, clr in [("보수적","conservative","#64748b"),
                                  ("균형(추천)","balanced","#16a34a"),
                                  ("공격적","aggressive","#dc2626")]:
            tk.Radiobutton(tf6, text=label, variable=self._gap_preset, value=val,
                           fg=clr, bg=PANEL, font=("Malgun Gothic",9,"bold"),
                           command=lambda v=val: self._apply_gap_preset(v)).pack(side="left", padx=3)
        # 심볼 다중 선택
        tk.Label(tf6, text="  심볼:", font=("Malgun Gothic",9,"bold"), fg="#f472b6", bg=PANEL).pack(side="left", padx=(12,2))
        _sym_colors = {"BTCUSD":"#f97316","XAUUSD":"#eab308","USDJPY":"#60a5fa","EURUSD":"#34d399"}
        for sym, var in self._sym_checks.items():
            tk.Checkbutton(tf6, text=sym, variable=var,
                           font=("Consolas",8,"bold"), fg=_sym_colors[sym], bg=PANEL,
                           selectcolor="#1e1b4b", activebackground=PANEL,
                           activeforeground=_sym_colors[sym]).pack(side="left", padx=2)
        # TF 다중 선택 (다중 시간봉 동시 테스트 — 시나리오 재생성에 반영)
        tk.Label(tf6, text="  TF:", font=("Malgun Gothic",9,"bold"), fg="#a855f7", bg=PANEL).pack(side="left", padx=(10,2))
        _tf_colors = {"M5":"#22c55e","M15":"#60a5fa","M30":"#f97316","H1":"#a855f7","H4":"#ef4444"}
        for tf_name, var in self._per_checks.items():
            tk.Checkbutton(tf6, text=tf_name, variable=var,
                           font=("Consolas",8,"bold"), fg=_tf_colors[tf_name], bg=PANEL,
                           selectcolor="#1e1b4b", activebackground=PANEL,
                           activeforeground=_tf_colors[tf_name]).pack(side="left", padx=2)
        B(tf6, "🔄 시나리오 재생성", "#7c3aed", self._rebuild_scenarios,
          font=("Malgun Gothic",9,"bold"), pady=2, padx=12).pack(side="left", padx=8)

        # ── 중단: 좌(슬라이더) + 우(시나리오 트리) — PanedWindow 드래그 리사이징 ──
        mid = tk.PanedWindow(outer, orient="horizontal", bg=BG,
                             sashwidth=6, sashrelief="groove", sashpad=2)
        mid.pack(fill="both", expand=True)

        # ─── 왼쪽: GUI 슬라이더 편집기 (스크롤 가능) ─────────
        left = tk.LabelFrame(mid, text="  🎛️  파라미터 편집기 (슬라이더)",
                             font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        mid.add(left, width=360, minsize=220, sticky="nsew")

        # 스크롤 가능한 Canvas
        _lcanvas = tk.Canvas(left, bg=PANEL, highlightthickness=0)
        _lvsb = tk.Scrollbar(left, orient="vertical", command=_lcanvas.yview)
        _lcanvas.configure(yscrollcommand=_lvsb.set)
        _lvsb.pack(side="right", fill="y")
        _lcanvas.pack(side="left", fill="both", expand=True)
        sc_frame = tk.Frame(_lcanvas, bg=PANEL)
        _lcwin = _lcanvas.create_window((0, 0), window=sc_frame, anchor="nw")
        def _lframe_cfg(e, c=_lcanvas): c.configure(scrollregion=c.bbox("all"))
        def _lcanvas_cfg(e, c=_lcanvas, w=_lcwin): c.itemconfig(w, width=e.width)
        sc_frame.bind("<Configure>", _lframe_cfg)
        _lcanvas.bind("<Configure>", _lcanvas_cfg)
        def _lwheel(e, c=_lcanvas): c.yview_scroll(int(-1*(e.delta/120)), "units")
        _lcanvas.bind("<MouseWheel>", _lwheel)
        sc_frame.bind("<MouseWheel>", _lwheel)

        # SL 슬라이더 + SL_DEC 간격 SpinBox
        self._add_slider(sc_frame, "🛑 SL (손절금액)", self._sl_var,
                         50, 2000, 10, "#ef4444",
                         "손실이 이 금액 이상이면 자동 손절\n작을수록 타이트, 클수록 여유",
                         gap_var=self._gap_sl_dec, gap_from=5, gap_to=100, gap_inc=5,
                         presets=[("🛡 보수적 300", "#0ea5e9", 300),
                                  ("⚖ 추천 500",   "#16a34a", 500),
                                  ("⚡ 공격적 800", "#dc2626", 800)])
        # TP 슬라이더 + TP_INC 간격 SpinBox
        self._add_slider(sc_frame, "💚 TP (익절금액)", self._tp_var,
                         10, 500, 5, "#22c55e",
                         "이익이 이 금액 이상이면 자동 익절\n작을수록 자주 익절, 클수록 큰 수익 노림",
                         gap_var=self._gap_tp_inc, gap_from=5, gap_to=100, gap_inc=5,
                         presets=[("🛡 보수적 60",  "#0ea5e9",  60),
                                  ("⚖ 추천 80",    "#16a34a",  80),
                                  ("⚡ 공격적 150", "#dc2626", 150)])
        # Lot 슬라이더 (×100 정수로 저장) + LOT_BIG 간격 SpinBox
        self._lot_int = tk.IntVar(value=10)
        lf = tk.LabelFrame(sc_frame, text="📦 Lot (거래크기)", font=LBL, fg="#3b82f6", bg=PANEL, bd=1)
        lf.pack(fill="x", pady=4)
        lot_top = tk.Frame(lf, bg=PANEL); lot_top.pack(fill="x", padx=8, pady=(4,0))
        self._lot_lbl = tk.Label(lot_top, text="0.10", font=("Malgun Gothic",14,"bold"),
                                 fg="#3b82f6", bg=PANEL)
        self._lot_lbl.pack(side="left")
        tk.Label(lot_top, text="LOT_BIG 간격:", font=("Consolas",8), fg="#a855f7", bg=PANEL).pack(side="right", padx=(8,2))
        tk.Spinbox(lot_top, textvariable=self._gap_lot_big,
                   from_=0.01, to=0.5, increment=0.01,
                   width=6, font=MONO, bg=PANEL2, fg="#f0abfc",
                   relief="flat", bd=2, justify="center",
                   format="%.2f", buttonbackground=PANEL).pack(side="right")
        tk.Label(lf, text="0.01이면 소액, 1.0이면 표준 계약", font=("Consolas",8),
                 fg="#475569", bg=PANEL).pack(anchor="w", padx=8)
        tk.Scale(lf, from_=1, to=200, orient="horizontal", variable=self._lot_int,
                 command=self._on_lot, bg=PANEL, fg=FG, highlightthickness=0,
                 troughcolor=PANEL2, sliderrelief="flat", length=280).pack(fill="x",padx=8,pady=4)
        # Lot 프리셋 버튼
        lot_pr = tk.Frame(lf, bg=PANEL); lot_pr.pack(fill="x", padx=8, pady=(0,4))
        for p_lbl, p_clr, p_x100 in [("🛡 보수적 0.05", "#0ea5e9",  5),
                                       ("⚖ 추천 0.10",   "#16a34a", 10),
                                       ("⚡ 공격적 0.20", "#dc2626", 20)]:
            B(lot_pr, p_lbl, p_clr,
              lambda v=p_x100: (self._lot_int.set(v), self._on_lot(v)),
              font=("Malgun Gothic",8,"bold"), pady=2, padx=6
              ).pack(side="left", padx=2)

        # TF는 상단 체크박스로 선택 (슬라이더 패널 버튼 제거)
        self._tf_btns = {}   # 참조 유지 (오류 방지)

        # ★v5.3 신규 변수: Risk%, MaxDD%, MaxPos — 기존 슬라이더와 동일한 형식
        def _add_new_slider(parent, label, fg_c, var_val, var_max, use_var,
                            from_v, to_v, res, from_max, to_max, inc, desc, presets=None):
            frame = tk.LabelFrame(parent, text=label, font=LBL, fg=fg_c, bg=PANEL, bd=1)
            frame.pack(fill="x", pady=4)
            # 상단행: 현재값(크게) + 위험범위 상한 + SET포함 체크
            top = tk.Frame(frame, bg=PANEL); top.pack(fill="x", padx=8, pady=(4,0))
            tk.Label(top, textvariable=var_val,
                     font=("Malgun Gothic",14,"bold"), fg=fg_c, bg=PANEL).pack(side="left")
            tk.Checkbutton(top, text="SET 포함", variable=use_var,
                           font=("Malgun Gothic",9,"bold"), fg=fg_c, bg=PANEL,
                           selectcolor="#1e1b4b", activebackground=PANEL,
                           activeforeground=fg_c).pack(side="right")
            tk.Spinbox(top, textvariable=var_max, from_=from_max, to=to_max, increment=inc,
                       width=5, font=MONO, bg=PANEL2, fg="#94a3b8",
                       relief="flat", bd=2, buttonbackground=PANEL).pack(side="right")
            tk.Label(top, text="위험상한:", font=("Consolas",8), fg="#64748b", bg=PANEL).pack(side="right", padx=(8,2))
            # 설명
            tk.Label(frame, text=desc, font=("Consolas",8), fg="#475569", bg=PANEL).pack(anchor="w", padx=8)
            # 슬라이더
            tk.Scale(frame, from_=from_v, to=to_v, orient="horizontal", variable=var_val,
                     resolution=res, command=lambda v: self._update_preview(),
                     bg=PANEL, fg=FG, highlightthickness=0,
                     troughcolor=PANEL2, sliderrelief="flat", length=280).pack(fill="x", padx=8, pady=4)
            # 프리셋 버튼 행
            if presets:
                pr = tk.Frame(frame, bg=PANEL); pr.pack(fill="x", padx=8, pady=(0,4))
                for p_lbl, p_clr, p_val in presets:
                    B(pr, p_lbl, p_clr,
                      lambda v=p_val: (var_val.set(v), self._update_preview()),
                      font=("Malgun Gothic",8,"bold"), pady=2, padx=6
                      ).pack(side="left", padx=2)

        _add_new_slider(sc_frame, "💹 Risk % (위험비율)",     "#22c55e",
                        self._risk_min, self._risk_max, self._use_risk,
                        0.1, 20.0, 0.5, 0.5, 20.0, 0.5,
                        "계좌 잔고 대비 손실 허용 비율\n작을수록 안전, 클수록 고수익 고위험",
                        presets=[("🛡 보수적 0.5%",  "#0ea5e9", 0.5),
                                 ("⚖ 추천 1.0%",    "#16a34a", 1.0),
                                 ("⚡ 공격적 2.5%",  "#dc2626", 2.5)])
        _add_new_slider(sc_frame, "📉 MaxDD % (최대 낙폭)",   "#f97316",
                        self._dd_min,  self._dd_max,  self._use_dd,
                        1.0, 50.0, 1.0, 5.0, 50.0, 1.0,
                        "이 낙폭(%)에 도달하면 EA 자동 정지\n작을수록 보수적, 클수록 손실 허용",
                        presets=[("🛡 보수적 5%",   "#0ea5e9",  5.0),
                                 ("⚖ 추천 10%",    "#16a34a", 10.0),
                                 ("⚡ 공격적 20%",  "#dc2626", 20.0)])
        _add_new_slider(sc_frame, "🔢 MaxPos (최대 포지션)",  "#60a5fa",
                        self._pos_min, self._pos_max, self._use_pos,
                        1, 20, 1, 2, 20, 1,
                        "동시 오픈 가능한 최대 포지션 수\n1=단일, 클수록 복수 포지션 허용",
                        presets=[("🛡 보수적 1",   "#0ea5e9", 1),
                                 ("⚖ 추천 3",     "#16a34a", 3),
                                 ("⚡ 공격적 6",   "#dc2626", 6)])

        # ── G4v7 파라미터 섹션 (ATR / MA / ADX / RSI / Cooldown) ─────────
        g4_frame = tk.LabelFrame(sc_frame, text="  🔬  G4v7 파라미터 (ATR/MA/ADX/RSI/CD)",
                                 font=("Malgun Gothic",9,"bold"), fg="#38bdf8",
                                 bg=PANEL, relief="groove", bd=1)
        g4_frame.pack(fill="x", pady=4, padx=0)

        def _add_g4_row(parent, label, var_min, var_max, use_var,
                        from_min, to_min, res_min, from_max, to_max, res_max, desc, presets_min=None, presets_max=None):
            frame = tk.Frame(parent, bg=PANEL); frame.pack(fill="x", pady=2, padx=4)
            top = tk.Frame(frame, bg=PANEL); top.pack(fill="x")
            cb = tk.Checkbutton(top, text=label, variable=use_var,
                                font=("Malgun Gothic",9,"bold"), fg="#38bdf8",
                                bg=PANEL, activebackground=PANEL, selectcolor=PANEL2, padx=0)
            cb.pack(side="left")
            tk.Label(top, text="Min:", font=("Consolas",8), fg="#64748b", bg=PANEL).pack(side="left", padx=(10,0))
            tk.Spinbox(top, textvariable=var_min, from_=from_min, to=to_min,
                       increment=res_min, width=5, font=("Consolas",9),
                       bg=PANEL2, fg=FG, relief="flat", bd=2,
                       insertbackground=FG).pack(side="left", padx=2)
            tk.Label(top, text="Max:", font=("Consolas",8), fg="#64748b", bg=PANEL).pack(side="left", padx=(6,0))
            tk.Spinbox(top, textvariable=var_max, from_=from_max, to=to_max,
                       increment=res_max, width=5, font=("Consolas",9),
                       bg=PANEL2, fg=FG, relief="flat", bd=2,
                       insertbackground=FG).pack(side="left", padx=2)
            tk.Label(frame, text=desc, font=("Consolas",7), fg="#475569", bg=PANEL).pack(anchor="w", padx=4)

        # ATR period
        self._atr_max = tk.IntVar(value=28)
        _add_g4_row(g4_frame, "📐 ATR Period",
                    self._atr_period, self._atr_max, self._use_atr,
                    5, 50, 1, 5, 50, 1,
                    "ATR 기간: SL/TP 계산 기준. 작을수록 민감, 클수록 완만 (기본 14~28)")
        # FastMA / SlowMA
        self._slow_ma_max = tk.IntVar(value=50)
        _add_g4_row(g4_frame, "📈 FastMA / SlowMA (Min=Fast, Max=Slow)",
                    self._fast_ma, self._slow_ma_max, self._use_ma,
                    3, 100, 1, 5, 200, 1,
                    "이동평균 교차 신호. Fast < Slow 필수. 예: FM=12, SM=28~50")
        # ADX Min
        self._adx_min_max = tk.DoubleVar(value=25.0)
        _add_g4_row(g4_frame, "📊 ADX Min (트렌드 강도 임계값)",
                    self._adx_min, self._adx_min_max, self._use_adx,
                    0, 50, 1, 0, 50, 1,
                    "ADX >= 이 값일 때만 진입. 높을수록 강한 추세만 포착 (기본 15~25)")
        # RSI Lower / Upper
        self._rsi_upper_max = tk.DoubleVar(value=75.0)
        _add_g4_row(g4_frame, "〰️ RSI Lower / Upper (진입 범위)",
                    self._rsi_lower, self._rsi_upper_max, self._use_rsi,
                    0, 50, 1, 50, 100, 1,
                    "RSI 진입 필터. Lower=과매도 기준, Upper=과매수 기준 (기본 30~70)")
        # Cooldown bars
        self._cd_max = tk.IntVar(value=10)
        _add_g4_row(g4_frame, "⏱️ CooldownBars (진입 쿨다운)",
                    self._cooldown, self._cd_max, self._use_cd,
                    0, 50, 1, 0, 50, 1,
                    "직전 거래 종료 후 N개 봉 대기. 클수록 거래 빈도 감소 (기본 2~10)")

        # ── 시나리오 개수 생성 버튼 ─────────────────────────────────
        cnt_frame = tk.Frame(sc_frame, bg=PANEL); cnt_frame.pack(fill="x", pady=4)
        tk.Label(cnt_frame, text="G4v7 시나리오 합:", font=("Malgun Gothic",9,"bold"),
                 fg="#fbbf24", bg=PANEL).pack(side="left", padx=(0,4))
        B(cnt_frame, "📊 100개 생성", "#1e3a5f",
          lambda: self._gen_g4v7_count(100), pady=5, padx=10,
          font=("Malgun Gothic",9,"bold")).pack(side="left", padx=2)
        B(cnt_frame, "📊 200개 생성", "#1a4a1f",
          lambda: self._gen_g4v7_count(200), pady=5, padx=10,
          font=("Malgun Gothic",9,"bold")).pack(side="left", padx=2)
        B(cnt_frame, "📊 50개 생성", "#2a1a00",
          lambda: self._gen_g4v7_count(50), pady=5, padx=10,
          font=("Malgun Gothic",9,"bold")).pack(side="left", padx=2)
        self._g4_cnt_lbl = tk.Label(cnt_frame, text="", font=("Consolas",9),
                                     fg="#94a3b8", bg=PANEL)
        self._g4_cnt_lbl.pack(side="left", padx=6)

        # 파일명
        fn_frame = tk.Frame(sc_frame, bg=PANEL); fn_frame.pack(fill="x", pady=6)
        tk.Label(fn_frame, text="파일명:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        tk.Entry(fn_frame, textvariable=self._fname_var, font=MONO, bg=PANEL2, fg="#ff6b35",
                 insertbackground=FG, relief="flat", bd=3).pack(side="left", fill="x", expand=True, padx=6)

        # 프리뷰 + 버튼 (★ _preview는 여기서 생성 — 반드시 _sel_tf 보다 먼저)
        self._preview = scrolledtext.ScrolledText(sc_frame, height=6, font=("Consolas",8),
                                                   bg="#12121e", fg="#a3e635", relief="flat", bd=2)
        self._preview.pack(fill="x", pady=4)
        self._sel_tf(5)  # _preview 생성 후 기본값 적용

        btn_row = tk.Frame(sc_frame, bg=PANEL); btn_row.pack(fill="x", pady=2)
        B(btn_row,"💾 .set 저장",GREEN, self._save_custom_set, pady=6, padx=10).pack(side="left",padx=2)
        B(btn_row,"📋 복사",BLUE, self._copy_preview, pady=6, padx=8).pack(side="left",padx=2)

        # 프리셋 버튼
        preset_frame = tk.LabelFrame(sc_frame, text="⚡ 빠른 프리셋", font=LBL, fg=FG, bg=PANEL, bd=1)
        preset_frame.pack(fill="x", pady=4)
        presets = [
            ("🥇 R01 BEST",  575, 92,  10, 5,  "#1f4068"),
            ("🛡️ R06 SAFE",  544, 87,  10, 5,  "#1a4a1f"),
            ("📊 R02 PF13",  499, 79,  10, 5,  "#2a2000"),
            ("⚖️ R08 균형",  557, 89,  10, 5,  "#1a1a4a"),
            ("🔰 보수적",    300, 60,   5, 15, "#2a1a2a"),
            ("🚀 공격적",    800, 150, 20, 60, "#1a2a1a"),
        ]
        prow1 = tk.Frame(preset_frame, bg=PANEL); prow1.pack(fill="x",padx=6,pady=(4,2))
        prow2 = tk.Frame(preset_frame, bg=PANEL); prow2.pack(fill="x",padx=6,pady=(0,4))
        for idx,(lbl,sl,tp,lotx10,tf,clr) in enumerate(presets):
            row = prow1 if idx < 3 else prow2
            B(row, lbl, clr,
              lambda sl=sl,tp=tp,lx=lotx10,tf=tf: self._apply_preset(sl,tp,lx,tf),
              pady=4, padx=6, font=("Malgun Gothic",8,"bold")).pack(side="left",padx=2)

        # ─── 오른쪽: 시나리오 트리뷰 ──────────────────────
        right = tk.LabelFrame(mid, text=f"  📋  {len(self._scenarios)}개 시나리오 (★v5.3 간격조정)",
                              font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        mid.add(right, minsize=300, sticky="nsew")
        self._right_title = right

        # 필터 바
        fbar = tk.Frame(right, bg=PANEL); fbar.pack(fill="x", padx=8, pady=4)
        tk.Label(fbar, text="필터:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        self._filter_cat = tk.StringVar(value="전체")
        cat_cb = ttk.Combobox(fbar, textvariable=self._filter_cat, width=12, state="readonly",
                              values=["전체"]+list(self.CAT_META.keys()))
        cat_cb.pack(side="left", padx=4)
        cat_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_tree())
        tk.Label(fbar, text="검색:", font=LBL, fg=FG, bg=PANEL).pack(side="left",padx=(8,0))
        self._search_var = tk.StringVar()
        tk.Entry(fbar, textvariable=self._search_var, font=MONO, bg=PANEL2, fg=FG,
                 insertbackground=FG, relief="flat", bd=3, width=14).pack(side="left",padx=4)
        self._search_var.trace_add("write", lambda *a: self._filter_tree())
        B(fbar,"전체선택",TEAL, self._sel_all, pady=3, padx=8).pack(side="left",padx=2)
        B(fbar,"전체해제",AMBER, self._desel_all, pady=3, padx=8).pack(side="left",padx=2)

        # ★ v5.4.1 간격 기능 버튼들 추가 (20, 40 포함)
        tk.Label(fbar, text=" 간격선택:", font=("Malgun Gothic",9,"bold"), fg="#a855f7", bg=PANEL).pack(side="left", padx=(10,2))
        for n_val, lbl in [(1,"전체"), (5,"5번째"), (10,"10번째"), (20,"20번째"), (40,"40번째")]:
            btn = tk.Button(fbar, text=lbl, font=("Consolas",9,"bold"), 
                            bg=PANEL2, fg=FG, relief="flat", bd=0, padx=6, pady=3, cursor="hand2",
                            command=lambda v=n_val: self._sel_nth(v))
            btn.pack(side="left", padx=2)
            self._interval_btns[n_val] = btn

        self._cnt_lbl = tk.Label(fbar, text="160개", font=LBL, fg="#94a3b8", bg=PANEL)
        self._cnt_lbl.pack(side="right",padx=4)

        # Treeview
        cols = ("✓","#","카테고리","SL","TP","Lot","TF","R:R","메모")
        self._tree = ttk.Treeview(right, columns=cols, show="headings", height=20,
                                   selectmode="browse")
        cw = {"✓":30,"#":35,"카테고리":80,"SL":55,"TP":55,"Lot":55,"TF":50,"R:R":50,"메모":140}
        for c in cols:
            self._tree.heading(c, text=c, anchor="center")
            self._tree.column(c, width=cw.get(c,80), anchor="center", stretch=(c=="메모"))
        vsb = ttk.Scrollbar(right, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(8,0), pady=4)
        vsb.pack(side="right", fill="y", pady=4)
        self._tree.bind("<ButtonRelease-1>", self._tree_click)
        self._tree.bind("<Double-Button-1>", self._tree_dbl)

        # 컬러 태그
        tag_colors = {
            "SL_DEC":"#ef4444","SL_INC":"#f97316","TP_INC":"#22c55e","TF_CHG":"#a855f7",
            "LOT_BIG":"#3b82f6","LOT_SML":"#8b5cf6","SLTP_MIX":"#eab308","FULL_MIX":"#06b6d4"
        }
        for cat,clr in tag_colors.items():
            self._tree.tag_configure(cat, foreground=clr)
        # ★ 제일 나중에 선언해야 가장 높은 우선순위로 배경색이 반영됨
        self._tree.tag_configure("CHK", background="#7c3aed", foreground="#ffffff")

        # ── 하단 버튼 (워크플로우 순서: 컴파일 → 저장 → 실행 → 결과) ──
        bot = tk.Frame(outer, bg=BG); bot.pack(fill="x", pady=(6,0))

        # ┌ STEP 1: 컴파일 ─────────────────────────────────────────
        _sep = lambda c: tk.Label(bot, text=c, font=("Malgun Gothic",9), fg="#475569", bg=BG)
        _sep("【1】컴파일").pack(side="left", padx=(4,0))
        B(bot,"🚀 하드코딩+컴파일", AMBER, self._run_hardcode_only,
          font=("Malgun Gothic",10,"bold"), pady=8, padx=12).pack(side="left", padx=2)

        _sep("  【2】저장").pack(side="left", padx=(6,0))
        B(bot,"💾 선택저장(.set)",GREEN,
          self._save_selected, font=("Malgun Gothic",10,"bold"), pady=8, padx=10).pack(side="left",padx=2)
        B(bot,"💾 전체저장",BLUE,
          self._save_all_cats, pady=8, padx=8).pack(side="left",padx=2)

        _sep("  【3】실행").pack(side="left", padx=(6,0))
        self._run_btn = B(bot,"▶ 백테스트 실행","#16a34a",
          self._start_bt_run, font=("Malgun Gothic",10,"bold"), pady=8, padx=12)
        self._run_btn.pack(side="left", padx=2)
        B(bot,"★ R1~R10 자동", "#7c3aed", self._start_r1_r10_auto,
          font=("Malgun Gothic",10,"bold"), pady=8, padx=10).pack(side="left", padx=2)
        self._stop_btn = B(bot,"⏹ 중단","#dc2626",
          self._stop_bt_run, pady=8, padx=8)
        self._stop_btn.pack(side="left", padx=2)
        self._stop_btn.config(state="disabled")

        _sep("  【4】결과").pack(side="left", padx=(6,0))
        B(bot,"📊 CSV",TEAL,
          self._export_csv, pady=8, padx=8).pack(side="left",padx=2)
        B(bot,"🌐 HTML",AMBER,
          self._open_html, pady=8, padx=8).pack(side="left",padx=2)
        B(bot,"📂 폴더",PANEL2,
          lambda: subprocess.run(["start","",self._out_dir.get()],shell=True),
          pady=8, padx=8).pack(side="left",padx=2)

        self._status = tk.Label(bot, text="대기 중", font=("Consolas",9), fg="#94a3b8", bg=BG)
        self._status.pack(side="right", padx=10)

        # ── 결과 분석 패널 ────────────────────────────────────────
        res_frame = tk.LabelFrame(outer, text="  📊  백테스트 결과 분석 & 라운드2 제안",
                                  font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        res_frame.pack(fill="both", expand=False, pady=(8,0))

        # 배포형: Reports 폴더 = HERE\Reports 또는 HERE\reports (대소문자)
        _htm_default = self._out_dir.get()
        for _rp in (os.path.join(HERE, "Reports"), os.path.join(HERE, "reports"),
                    os.path.join(HERE, "htm_results")):
            if os.path.isdir(_rp):
                _htm_default = _rp; break

        # 결과 분석 버튼 행
        rbtn = tk.Frame(res_frame, bg=PANEL); rbtn.pack(fill="x", padx=8, pady=5)
        tk.Label(rbtn, text="HTM 폴더:", font=LBL, fg=FG, bg=PANEL, width=9, anchor="e").pack(side="left")
        self._htm_dir = tk.StringVar(value=_htm_default)
        tk.Entry(rbtn, textvariable=self._htm_dir, font=MONO, bg=PANEL2, fg="#93c5fd",
                 insertbackground=FG, relief="flat", bd=3).pack(side="left", fill="x", expand=True, padx=4)
        B(rbtn,"📁 선택",AMBER, lambda: self._htm_dir.set(
            filedialog.askdirectory(initialdir=self._htm_dir.get()) or self._htm_dir.get()
        ), pady=3).pack(side="left",padx=2)
        B(rbtn,"🔍 결과 분석",GREEN, self._analyze_results,
          font=("Malgun Gothic",10,"bold"), pady=4, padx=12).pack(side="left",padx=(8,2))
        B(rbtn,"📊 BB_SQUEEZE R1~R8 로드","#0369a1", self._load_round_analysis,
          font=("Malgun Gothic",10,"bold"), pady=4, padx=12).pack(side="left",padx=2)
        B(rbtn,"🚀 라운드2 SET 생성 (TOP20+RESCUE5)",ACCENT, self._gen_round2,
          font=("Malgun Gothic",10,"bold"), pady=4, padx=12).pack(side="left",padx=2)
        B(rbtn,"✅ GOOD만 재실행","#15803d", self._rerun_good_only,
          font=("Malgun Gothic",10,"bold"), pady=4, padx=12).pack(side="left",padx=2)
        B(rbtn,"📋 결과 복사",PANEL2, self._copy_result, pady=4, padx=8).pack(side="left",padx=2)
        B(rbtn,"🧬 R1~R10 파라미터 인사이트","#7c3aed", self._gen_param_insight,
          font=("Malgun Gothic",10,"bold"), pady=4, padx=12).pack(side="left",padx=(8,2))

        # 결과 테이블 (Treeview)
        col_ids = ("rank","cat","id","sl","tp","lot","tf","profit","winrate","pf","trades","verdict")
        col_cfg = [
            ("rank","순위",42),("cat","카테고리",80),("id","ID",36),
            ("sl","SL",52),("tp","TP",52),("lot","Lot",46),("tf","TF",46),
            ("profit","순이익",80),("winrate","승률%",62),("pf","PF",54),
            ("trades","거래수",60),("verdict","판정",72),
        ]
        rt_frame = tk.Frame(res_frame, bg=PANEL); rt_frame.pack(fill="both", expand=True, padx=8, pady=(0,6))
        self._res_tree = ttk.Treeview(rt_frame, columns=col_ids, show="headings", height=8,
                                       selectmode="extended")
        for cid, hdr, w in col_cfg:
            self._res_tree.heading(cid, text=hdr)
            self._res_tree.column(cid, width=w, anchor="center", stretch=False)
        vsb = ttk.Scrollbar(rt_frame, orient="vertical", command=self._res_tree.yview)
        self._res_tree.configure(yscrollcommand=vsb.set)
        self._res_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._res_tree.tag_configure("GOOD",  background="#dcfce7", foreground="#166534")
        self._res_tree.tag_configure("BAD",   background="#fee2e2", foreground="#991b1b")
        self._res_tree.tag_configure("MID",   background="#f0f9ff", foreground="#334155")

        # 라운드2 제안 텍스트
        self._r2_text = tk.Text(res_frame, height=5, bg=PANEL2, fg="#ff6b35",
                                font=("Consolas",9), relief="flat", bd=3, state="disabled")
        self._r2_text.pack(fill="x", padx=8, pady=(0,6))

        # ★ 하드코딩 + 컴파일 전용 구역 (노란 박스 대응)
        h_frame = tk.Frame(res_frame, bg=PANEL); h_frame.pack(fill="x", padx=8, pady=(0,6))
        B(h_frame, "🔥 [결과] 기반 상위 20개 하드코딩 + 컴파일 생성", "#854d0e",
          self._run_hardcode_for_results, font=("Malgun Gothic",12,"bold"), pady=12).pack(fill="x")

        # ── Market Analysis 패널 ─────────────────────────────────
        ma_frame = tk.LabelFrame(outer, text="  📈  Market Analysis — EA방향 vs 시장방향",
                                 font=TITLE, fg="#ff6b35", bg=PANEL, relief="groove", bd=2)
        ma_frame.pack(fill="both", expand=True, pady=(8,0))

        ma_btn = tk.Frame(ma_frame, bg=PANEL); ma_btn.pack(fill="x", padx=8, pady=5)
        B(ma_btn, "🎯 EA방향 vs 시장방향 분석", "#0ea5e9",
          self._run_direction_analysis,
          font=("Malgun Gothic",10,"bold"), pady=5, padx=14).pack(side="left", padx=2)
        B(ma_btn, "🔧 EA 모듈 조정 (MQ4)", "#7c3aed",
          self._apply_ea_module_adjust,
          font=("Malgun Gothic",10,"bold"), pady=5, padx=14).pack(side="left", padx=2)
        self._ma_status = tk.Label(ma_btn, text="대기 중 — 먼저 HTM 폴더를 분석하세요",
                                   font=("Consolas",9), fg="#94a3b8", bg=PANEL)
        self._ma_status.pack(side="right", padx=10)

        ma_txt_frame = tk.Frame(ma_frame, bg=PANEL); ma_txt_frame.pack(fill="both", expand=True, padx=8, pady=(0,6))
        self._ma_text = tk.Text(ma_txt_frame, height=10, bg="#0f172a", fg="#e2e8f0",
                                font=("Consolas",9), relief="flat", bd=3, wrap="word")
        ma_vsb = ttk.Scrollbar(ma_txt_frame, orient="vertical", command=self._ma_text.yview)
        self._ma_text.configure(yscrollcommand=ma_vsb.set)
        self._ma_text.pack(side="left", fill="both", expand=True)
        ma_vsb.pack(side="right", fill="y")
        # text 색상 태그
        for tag, clr in [("header","#fbbf24"),("subheader","#93c5fd"),("info","#94a3b8"),
                         ("profit","#4ade80"),("loss","#f87171"),("warning","#fb923c")]:
            self._ma_text.tag_configure(tag, foreground=clr)
        self._ma_text.config(state="normal")
        self._ma_text.insert("end", "📊 HTM 폴더 분석 후 [EA방향 vs 시장방향 분석] 버튼을 클릭하세요.\n", "info")
        self._ma_text.config(state="disabled")

        self._sel_nth(1)      # ★v5.4.1: 초기 상태 필터 전체(1)로 선택 및 UI 갱신
        self._update_preview()

    # ── ★v5.4 R1~R10 라운드 컨트롤 ──────────────────────────────────
    def _build_round_ctrl(self, parent):
        """★v5.4: R1~R10 수동 라운드 컨트롤 패널 — 단계별 실행 & 진화 히스토리"""
        rp = tk.LabelFrame(parent, text="  🎯  R1~R10 라운드 수동 컨트롤  (단계별 실행 → 검토 → 다음 라운드)",
                           font=TITLE, fg="#ff8c42", bg=PANEL, relief="groove", bd=2)
        rp.pack(fill="x", padx=8, pady=(6, 2))

        # ── 실행 컨트롤 행 1: 단일 라운드 ──────────────────────────
        r1 = tk.Frame(rp, bg=PANEL); r1.pack(fill="x", padx=10, pady=(6,2))
        tk.Label(r1, text="【단일】 라운드:", font=("Malgun Gothic",9,"bold"), fg="#ff6b35", bg=PANEL).pack(side="left")
        tk.Spinbox(r1, textvariable=self._rnd_sel, from_=1, to=10, width=4,
                   font=("Consolas",13,"bold"), bg="#1e1b4b", fg="#ff6b35",
                   relief="flat", bd=2, justify="center", buttonbackground=PANEL,
                   wrap=True).pack(side="left", padx=(4, 8))
        B(r1, "▶ 이 라운드만 실행", "#15803d", self._run_round_only,
          font=("Malgun Gothic",10,"bold"), pady=5, padx=14).pack(side="left", padx=2)
        B(r1, "⏩ 자동(이어하기)", "#6d28d9", self._run_round_auto,
          font=("Malgun Gothic",10,"bold"), pady=5, padx=14).pack(side="left", padx=2)
        self._rnd_stop_btn = B(r1, "⏹ 중단", "#991b1b", self._stop_round,
          font=("Malgun Gothic",10,"bold"), pady=5, padx=10)
        self._rnd_stop_btn.pack(side="left", padx=4)
        self._rnd_stop_btn.config(state="disabled")
        self._rnd_status = tk.Label(r1, text="대기 중", font=("Consolas",9), fg="#94a3b8", bg=PANEL)
        self._rnd_status.pack(side="right", padx=8)

        # ── 실행 컨트롤 행 2: 범위 실행 (R시작 ~ R끝) ──────────────
        r2 = tk.Frame(rp, bg=PANEL); r2.pack(fill="x", padx=10, pady=(0,2))
        tk.Label(r2, text="【범위】 R", font=("Malgun Gothic",9,"bold"), fg="#60a5fa", bg=PANEL).pack(side="left")
        tk.Spinbox(r2, textvariable=self._rnd_sel, from_=1, to=10, width=3,
                   font=("Consolas",12,"bold"), bg="#1e1b4b", fg="#60a5fa",
                   relief="flat", bd=2, justify="center", buttonbackground=PANEL,
                   wrap=True).pack(side="left", padx=(2,4))
        tk.Label(r2, text="~ R", font=("Malgun Gothic",9,"bold"), fg="#60a5fa", bg=PANEL).pack(side="left")
        tk.Spinbox(r2, textvariable=self._rnd_end, from_=1, to=10, width=3,
                   font=("Consolas",12,"bold"), bg="#1e1b4b", fg="#60a5fa",
                   relief="flat", bd=2, justify="center", buttonbackground=PANEL,
                   wrap=True).pack(side="left", padx=(2,8))
        tk.Label(r2, text="단계 선택:", font=("Malgun Gothic",8), fg="#94a3b8", bg=PANEL).pack(side="left", padx=(0,4))
        for label, s, e in [("1단계(R1~3)",1,3),("2단계(R4~6)",4,6),("3단계(R7~10)",7,10)]:
            def _set_range(sv=s, ev=e):
                self._rnd_sel.set(sv); self._rnd_end.set(ev)
            tk.Button(r2, text=label, font=("Malgun Gothic",8), bg="#1e3a5f", fg="#60a5fa",
                      relief="flat", bd=0, padx=6, pady=3, cursor="hand2",
                      command=_set_range).pack(side="left", padx=2)
        B(r2, "▶▶ 범위 실행", "#0369a1", self._run_round_range,
          font=("Malgun Gothic",10,"bold"), pady=5, padx=14).pack(side="left", padx=(8,2))

        # ── 실행 컨트롤 행 3: 결과/다음 라운드 ─────────────────────
        r3 = tk.Frame(rp, bg=PANEL); r3.pack(fill="x", padx=10, pady=(0,4))
        B(r3, "🔄 히스토리 갱신", "#0369a1", self._refresh_evo,
          pady=5, padx=10).pack(side="left", padx=4)
        B(r3, "⏭ 다음 라운드 자동 설정", "#92400e", self._prep_next_round,
          pady=5, padx=10).pack(side="left", padx=2)
        B(r3, "📊 결과 확인", "#0e7490", self._analyze_results,
          pady=5, padx=10).pack(side="left", padx=4)
        B(r3, "⏭▶ 다음라운드 실행", "#064e3b", self._run_next_round,
          font=("Malgun Gothic",10,"bold"), pady=5, padx=12).pack(side="left", padx=2)

        # ── 진화 히스토리 테이블 ────────────────────────────────────
        evo_cols = ("rno","base_sl","base_tp","best_sl","best_tp","best_profit","best_pf","status")
        evo_cfg  = [("rno","라운드",55),("base_sl","기준SL",65),("base_tp","기준TP",65),
                    ("best_sl","BEST SL",70),("best_tp","BEST TP",70),
                    ("best_profit","순이익",80),("best_pf","PF",55),("status","상태",100)]
        evo_f = tk.Frame(rp, bg=PANEL); evo_f.pack(fill="x", padx=10, pady=(0, 6))
        self._rnd_evo_tree = ttk.Treeview(evo_f, columns=evo_cols, show="headings",
                                           height=5, selectmode="browse")
        for cid, hdr, w in evo_cfg:
            self._rnd_evo_tree.heading(cid, text=hdr)
            self._rnd_evo_tree.column(cid, width=w, anchor="center", stretch=False)
        evo_vsb = ttk.Scrollbar(evo_f, orient="vertical", command=self._rnd_evo_tree.yview)
        self._rnd_evo_tree.configure(yscrollcommand=evo_vsb.set)
        self._rnd_evo_tree.pack(side="left", fill="x", expand=True)
        evo_vsb.pack(side="right", fill="y")
        self._rnd_evo_tree.tag_configure("done",    background="#dcfce7", foreground="#166534")
        self._rnd_evo_tree.tag_configure("pending", background="#1e293b", foreground="#94a3b8")
        
        # ★ 빨간펜 연동 기능: 히스토리 클릭 시 간격(Gap) 자동 업데이트 바인딩
        self._rnd_evo_tree.bind("<ButtonRelease-1>", self._evo_tree_click)
        
        self._refresh_evo()

    def _evo_tree_click(self, event):
        """히스토리 트리 클릭 시, BEST SL/TP 값을 기반으로 슬라이더의 간격 및 값을 스윙"""
        iid = self._rnd_evo_tree.identify_row(event.y)
        if not iid: return
        vals = self._rnd_evo_tree.item(iid, "values")
        try:
            # 베스트 값 파싱 (문자열 '—' 방어)
            try: b_sl = float(vals[3])
            except: b_sl = 0
            try: b_tp = float(vals[4])
            except: b_tp = 0
            
            # 값이 있으면 슬라이더와 간격을 업데이트
            if b_sl > 0:
                self._gap_sl_dec.set(int(b_sl * 0.1) or 5) # 예: 10%를 간격으로 스마트 설정
                self._sl_var.set(int(b_sl))
            if b_tp > 0:
                self._gap_tp_inc.set(int(b_tp * 0.1) or 5) # 예: 10%를 간격으로 스마트 설정
                self._tp_var.set(int(b_tp))
                
            self._update_preview()
            self._status.config(text=f"✅ 연동 완료: BEST(SL:{b_sl}, TP:{b_tp}) -> 슬라이더 및 간격(Gap) 연동됨!")
        except Exception as e:
            print("Evo Tree Click Error:", e)

    def _run_script_thread(self, run_only_val):
        """run_r1_r10_stochrsi_v5.4.py 의 RUN_ONLY_ROUND 패치 후 subprocess 실행 (별도 스레드)"""
        script = os.path.join(HERE, "13 ea v7 master 5.0", "run_r1_r10_stochrsi_v5.4.py")
        if not os.path.exists(script):
            self.after(0, lambda: messagebox.showerror("오류", f"스크립트 없음:\n{script}")); return

        # RUN_ONLY_ROUND 라인 패치
        try:
            with open(script, "r", encoding="utf-8") as f:
                src = f.read()
            new_val = str(run_only_val) if run_only_val is not None else "None"
            patched = re.sub(r'( {4}RUN_ONLY_ROUND\s*=\s*)\S+', rf'\g<1>{new_val}', src)
            with open(script, "w", encoding="utf-8") as f:
                f.write(patched)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("패치 오류", str(e))); return

        self._rnd_proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=os.path.dirname(script)
        )
        self.after(0, lambda: self._rnd_stop_btn.config(state="normal"))
        # stdout 스트리밍 → 상태 레이블 업데이트
        try:
            for line in self._rnd_proc.stdout:
                line = line.strip()
                if not line: continue
                self.after(0, lambda l=line: self._rnd_status.config(
                    text=l[:90], fg="#ff6b35"))
        except: pass
        finally:
            self.after(0, lambda: self._rnd_stop_btn.config(state="disabled"))
            self.after(0, lambda: self._rnd_status.config(text="완료 ✅", fg="#4ade80"))
            self.after(600, self._refresh_evo)

    def _run_round_only(self):
        """선택한 라운드 하나만 실행"""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요."); return
        rno = self._rnd_sel.get()
        if not messagebox.askyesno("실행 확인", f"R{rno} 라운드만 단독 실행합니다.\n계속하시겠습니까?"):
            return
        self._rnd_status.config(text=f"R{rno} 준비 중...", fg="#ff8c42")
        threading.Thread(target=self._run_script_thread, args=(rno,), daemon=True).start()

    def _run_round_range(self):
        """범위 라운드 순차 실행 (예: R1 ~ R3)"""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요."); return
        r_start = self._rnd_sel.get()
        r_end   = self._rnd_end.get()
        if r_end < r_start:
            messagebox.showwarning("범위 오류", f"끝 라운드({r_end})가 시작({r_start})보다 작습니다."); return
        rng = list(range(r_start, r_end + 1))
        if not messagebox.askyesno("범위 실행 확인",
                f"R{r_start} ~ R{r_end} ({len(rng)}단계) 순차 실행합니다.\n계속하시겠습니까?"):
            return
        self._rnd_status.config(text=f"R{r_start}~R{r_end} 범위 실행 중...", fg="#60a5fa")
        threading.Thread(target=self._run_range_thread, args=(rng,), daemon=True).start()

    def _run_range_thread(self, rng):
        """범위 라운드 순차 실행 스레드"""
        for rno in rng:
            if not (self._rnd_proc is None or self._rnd_proc.poll() is not None):
                pass  # 이전 프로세스 대기
            self.after(0, lambda r=rno: self._rnd_status.config(
                text=f"R{r} 실행 중 ({rng.index(r)+1}/{len(rng)})...", fg="#ff8c42"))
            self._run_script_thread(rno)
            if self._rnd_proc:
                self._rnd_proc.wait()
        self.after(0, lambda: self._rnd_status.config(
            text=f"범위 실행 완료 (R{rng[0]}~R{rng[-1]})", fg="#22c55e"))

    def _run_round_auto(self):
        """진화 히스토리 이어서 자동 실행 (RUN_ONLY_ROUND=None)"""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요."); return
        if not messagebox.askyesno("자동 실행 확인",
                "진화 히스토리에서 이어서 R1~R10 자동 실행합니다.\n계속하시겠습니까?"):
            return
        self._rnd_status.config(text="자동(이어하기) 준비 중...", fg="#a855f7")
        threading.Thread(target=self._run_script_thread, args=(None,), daemon=True).start()

    def _stop_round(self):
        """실행 중인 라운드 프로세스 중단"""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            self._rnd_proc.terminate()
        self._rnd_status.config(text="중단됨", fg="#f87171")
        if self._rnd_stop_btn:
            self._rnd_stop_btn.config(state="disabled")

    def _refresh_evo(self):
        """stochrsi_evolution_history.json 읽어서 트리뷰 갱신"""
        if self._rnd_evo_tree is None: return
        for iid in self._rnd_evo_tree.get_children():
            self._rnd_evo_tree.delete(iid)
        evo_path = os.path.join(HERE, "Reports",
                                "stochrsi_evolution_history.json")
        completed = set()
        if os.path.exists(evo_path):
            try:
                with open(evo_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in sorted(data, key=lambda x: x.get("round_no", 0)):
                    rno  = item.get("round_no", "?")
                    base = item.get("base", {})
                    best = item.get("best", {})
                    def _fmt(v): return f"{v:.2f}" if isinstance(v, (int, float)) else str(v or "—")
                    self._rnd_evo_tree.insert("", "end", iid=f"R{rno}",
                        values=(f"R{rno}",
                                _fmt(base.get("sl")), _fmt(base.get("tp")),
                                _fmt(best.get("sl")), _fmt(best.get("tp")),
                                _fmt(best.get("profit")), _fmt(best.get("pf")),
                                "완료 ✅"),
                        tags=("done",))
                    completed.add(int(rno))
            except Exception as e:
                self._rnd_evo_tree.insert("", "end",
                    values=("—","—","—","—","—","읽기오류","—", str(e)[:40]))
        for rno in range(1, 11):
            if rno not in completed:
                self._rnd_evo_tree.insert("", "end",
                    values=(f"R{rno}", "—", "—", "—", "—", "—", "—", "대기 중"),
                    tags=("pending",))

    def _prep_next_round(self):
        """진화 히스토리에서 다음 실행할 라운드 번호를 Spinbox에 설정"""
        evo_path = os.path.join(HERE, "Reports",
                                "stochrsi_evolution_history.json")
        if os.path.exists(evo_path):
            try:
                with open(evo_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    max_done = max(int(item.get("round_no", 0)) for item in data)
                    next_rno = min(max_done + 1, 10)
                    self._rnd_sel.set(next_rno)
                    self._rnd_status.config(
                        text=f"R{max_done} 완료 → 다음: R{next_rno} 준비됨", fg="#4ade80")
                    self._refresh_evo()
                    return
            except Exception as e:
                self._rnd_status.config(text=f"히스토리 읽기 오류: {e}", fg="#f87171"); return
        self._rnd_sel.set(1)
        self._rnd_status.config(text="히스토리 없음 — R1부터 시작", fg="#ff8c42")

    def _run_next_round(self):
        """⏭▶ 다음 라운드 자동 설정 + 즉시 실행 (결과 확인 후 원스텝)"""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요."); return
        # 다음 라운드 번호 결정 (진화 히스토리 기반)
        evo_path = os.path.join(HERE, "Reports", "stochrsi_evolution_history.json")
        next_rno = 1
        if os.path.exists(evo_path):
            try:
                with open(evo_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    max_done = max(int(item.get("round_no", 0)) for item in data)
                    next_rno = min(max_done + 1, 10)
            except Exception as e:
                self._rnd_status.config(text=f"히스토리 오류: {e}", fg="#f87171"); return
        if next_rno > 10:
            self._rnd_status.config(text="R10 완료 — 더 이상 라운드 없음", fg="#4ade80"); return
        self._rnd_sel.set(next_rno)
        self._refresh_evo()
        self._rnd_status.config(text=f"R{next_rno} 즉시 시작 중...", fg="#ff8c42")
        threading.Thread(target=self._run_script_thread, args=(next_rno,), daemon=True).start()

    # ── 헬퍼 ──────────────────────────────────────────────────
    def _tf_period_str(self, tf):
        return {5:"5분봉",15:"15분봉",30:"30분봉",60:"1시간봉",240:"4시간봉"}.get(tf,"")

    def _add_slider(self, parent, label, var, from_, to, res, color, desc,
                    gap_var=None, gap_from=1, gap_to=100, gap_inc=1, presets=None):
        frame = tk.LabelFrame(parent, text=label, font=LBL, fg=color, bg=PANEL, bd=1)
        frame.pack(fill="x", pady=4)
        # 상단: 초기값 + 간격 SpinBox
        top_row = tk.Frame(frame, bg=PANEL); top_row.pack(fill="x", padx=8, pady=(4,0))
        val_lbl = tk.Label(top_row, textvariable=var,
                           font=("Malgun Gothic",14,"bold"), fg=color, bg=PANEL)
        val_lbl.pack(side="left")
        if gap_var is not None:
            tk.Label(top_row, text="간격:", font=("Consolas",8), fg="#a855f7", bg=PANEL).pack(side="right", padx=(8,2))
            spin = tk.Spinbox(top_row, textvariable=gap_var,
                              from_=gap_from, to=gap_to, increment=gap_inc,
                              width=6, font=MONO, bg=PANEL2, fg="#f0abfc",
                              relief="flat", bd=2, justify="center",
                              buttonbackground=PANEL, wrap=False)
            spin.pack(side="right")
        tk.Label(frame, text=desc, font=("Consolas",8), fg="#475569", bg=PANEL).pack(anchor="w",padx=8)
        tk.Scale(frame, from_=from_, to=to, orient="horizontal", variable=var,
                 resolution=res, command=lambda v: self._update_preview(),
                 bg=PANEL, fg=FG, highlightthickness=0,
                 troughcolor=PANEL2, sliderrelief="flat", length=280).pack(fill="x",padx=8,pady=4)
        # 프리셋 버튼 행 (보수적 / 추천 / 공격적)
        if presets:
            pr = tk.Frame(frame, bg=PANEL); pr.pack(fill="x", padx=8, pady=(0,4))
            for p_lbl, p_clr, p_val in presets:
                B(pr, p_lbl, p_clr,
                  lambda v=p_val: (var.set(v), self._update_preview()),
                  font=("Malgun Gothic",8,"bold"), pady=2, padx=6
                  ).pack(side="left", padx=2)
        else:
            tk.Frame(frame, bg=PANEL).pack(pady=2)

    def _on_lot(self, val):
        lot = int(val) / 100
        self._lot_lbl.config(text=f"{lot:.2f}")
        self._lot_var.set(lot)
        self._update_preview()

    def _sel_tf(self, val):
        self._tf_var.set(val)
        for tv, btn in self._tf_btns.items():  # _tf_btns가 비어있으면 아무것도 안 함
            try:
                btn.config(bg=ACCENT if tv == val else PANEL2,
                           fg="white" if tv == val else FG)
            except: pass
        self._update_preview()

    def _update_preview(self, *_):
        sl   = self._sl_var.get()
        tp   = self._tp_var.get()
        lot  = int(self._lot_int.get()) / 100
        tf   = self._tf_var.get()
        name = self._fname_var.get() or "MyEA"
        tfl  = self.TF_CODES.get(tf, str(tf))
        now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        rr   = tp / sl if sl else 0
        extra = ""
        if hasattr(self, '_use_risk') and self._use_risk.get():
            extra += f"InpRiskPercent={self._risk_min.get():.2f}\n"
        if hasattr(self, '_use_dd') and self._use_dd.get():
            extra += f"InpMaxDrawdown={self._dd_min.get():.2f}\n"
        if hasattr(self, '_use_pos') and self._use_pos.get():
            extra += f"MaxPositions={self._pos_min.get()}\n"
        content = (f"; EA SET 파일 — {name}\n"
                   f"; 생성: {now}\n"
                   f"; ─────────────────────────\n"
                   f"SLFixedAmount={sl}\n"
                   f"TPamount={tp}\n"
                   f"LotSize={lot:.2f}\n"
                   f"Period={tf}\n"
                   + (extra if extra else "")
                   + f"; ─────────────────────────\n"
                   f"; SL=${sl}  TP=${tp}  Lot={lot:.2f}  TF={tfl}\n"
                   f"; R:R 비율 = {rr:.2f}  (TP/SL)\n")
        if not hasattr(self, '_preview'): return
        self._preview.delete("1.0","end")
        self._preview.insert("1.0", content)

    def _apply_preset(self, sl, tp, lot_x10, tf):
        self._sl_var.set(sl)
        self._tp_var.set(tp)
        self._lot_int.set(lot_x10)
        self._lot_lbl.config(text=f"{lot_x10/100:.2f}")
        self._lot_var.set(lot_x10/100)
        self._sel_tf(tf)
        self._update_preview()

    def _apply_init_vals(self):
        """초기값 설정 (노란 필터) 적용"""
        sl=self._init_sl.get(); tp=self._init_tp.get()
        lot=self._init_lot.get(); tf=self._init_tf.get()
        self._apply_preset(sl, tp, int(lot*100), tf)
        self._status.config(text=f"초기값 적용 완료: SL{sl} TP{tp} Lot{lot} TF{tf}")

    def _run_hardcode_only(self):
        """백테스트 없이 '하드코딩 + 컴파일'만 수행 (★v4.0: 폴더 모드 지원)"""
        selected = [sc for iid, sc in zip(self._chk_vars, self._scenarios)
                    if self._chk_vars.get(iid, tk.BooleanVar()).get()]
        if not selected:
            sel_iids = self._tree.selection()
            iid_to_sc = {f"{sc['cat']}_{sc['id']}": sc for sc in self._scenarios}
            selected = [iid_to_sc[iid] for iid in sel_iids if iid in iid_to_sc]

        if not selected: return messagebox.showwarning("선택 없음", "대상을 선택하세요.")

        # ★v4.0: 폴더 모드 vs 단일 파일 모드
        if self._ea_folder_paths:
            ea_paths = [p for p in self._ea_folder_paths if os.path.exists(p)]
            if not ea_paths:
                return messagebox.showerror("EA 없음", "선택한 폴더의 .mq4 파일을 찾을 수 없습니다.")
        else:
            ea_path = self._ea_path.get().strip()
            if not ea_path: return messagebox.showerror("EA 없음", "EA를 선택하세요.")
            ea_paths = [ea_path]

        threading.Thread(target=self._worker_hardcode_batch,
                         args=(selected, ea_paths), daemon=True).start()

    def _worker_hardcode_batch(self, selected, ea_paths):
        """★v4.0: ea_paths 리스트의 모든 EA에 선택 시나리오 하드코딩+컴파일"""
        # 하위 호환: 단일 경로 문자열도 처리
        if isinstance(ea_paths, str):
            ea_paths = [ea_paths]

        me_exe = find_me(1)[0] if find_me(1) else ""
        if not me_exe:
            return self.after(0, lambda: self._status.config(text="⚠️ MetaEditor 없음", fg=RED))

        total_ea = len(ea_paths)
        total_sc = len(selected)
        done_count = 0

        self.after(0, lambda: self._status.config(
            text=f"🚀 일괄 생성 시작 ({total_ea}개 EA × {total_sc}개 시나리오)...", fg=AMBER))

        for ea_path in ea_paths:
            ea_base = os.path.splitext(os.path.basename(ea_path))[0]
            out_dir = self._out_dir.get()
            os.makedirs(out_dir, exist_ok=True)

            # ★v4.0: EA 폴더명에 _R1 추가
            ea_folder = os.path.join(out_dir, ea_base + "_R1")
            os.makedirs(ea_folder, exist_ok=True)

            for idx, sc in enumerate(selected, 1):
                tfl = self.TF_CODES.get(sc["tf"], str(sc["tf"]))
                # ★v4.0: 파일명에도 _R1 추가
                base_name = f"{ea_base}_{sc['cat']}_{sc['id']:02d}_SL{sc['sl']}_TP{sc['tp']}_L{sc['lot']:.2f}_{tfl}_R1"
                try:
                    content, enc = read_mq4(ea_path)
                    content = re.sub(r'((?:extern|input)\s+double\s+LotSize\s*=)\s*[\d\.]+;', f'\\g<1> {sc["lot"]:.2f};', content, flags=re.MULTILINE)
                    content = re.sub(r'((?:extern|input)\s+double\s+TPamount\s*=)\s*[\d\.]+;', f'\\g<1> {sc["tp"]:.1f};', content, flags=re.MULTILINE)
                    content = re.sub(r'((?:extern|input)\s+double\s+SLFixedAmount\s*=)\s*[\d\.]+;', f'\\g<1> {sc["sl"]:.1f};', content, flags=re.MULTILINE)
                    content = re.sub(r'((?:extern|input)\s+int\s+Period\s*=)\s*\d+;', f'\\g<1> {sc["tf"]};', content, flags=re.MULTILINE)
                    new_path = os.path.join(ea_folder, base_name + ".mq4")
                    write_mq4(new_path, content)
                    compile_one(me_exe, new_path, ea_folder)
                    done_count += 1
                except Exception as e:
                    self.after(0, lambda n=ea_base, e_=str(e):
                        self._status.config(text=f"⚠️ {n}: {e_}", fg=RED))
                self.after(0, lambda d=done_count, tot=total_ea*total_sc:
                    self._status.config(text=f"작업 중 ({d}/{tot})"))

        self.after(0, lambda t=total_ea: self._status.config(
            text=f"✅ 일괄 생성 완료! ({t}개 EA)", fg=GREEN))

    def _run_hardcode_for_results(self):
        """분석 결과 상위 20개 자동 하드코딩 생성"""
        if not hasattr(self, "_last_results"): return messagebox.showwarning("분석 필요", "먼저 결과 분석을 수행하세요.")
        top_20 = self._last_results[:20]
        ea_path = self._ea_path.get().strip()
        scs = []
        for r in top_20:
            tf_map = {"M5":5,"M15":15,"M30":30,"H1":60,"H4":240}
            scs.append({"cat":"BEST","id":top_20.index(r)+1,"sl":r["sl"],"tp":r["tp"],"lot":r["lot"],"tf":tf_map.get(r["tf"],5)})
        threading.Thread(target=self._worker_hardcode_batch, args=(scs, ea_path), daemon=True).start()

    # ── EA 선택 ────────────────────────────────────────────────
    def _sel_ea(self):
        p = filedialog.askopenfilename(filetypes=[("MQ4","*.mq4"),("all","*")])
        if p:
            self._ea_path.set(p)
            base = os.path.splitext(os.path.basename(p))[0]
            self._fname_var.set(base)
            self._update_preview()

    def _scan_ea(self):
        folder = filedialog.askdirectory()
        if not folder: return
        mq4s = glob.glob(os.path.join(folder,"**","*.mq4"), recursive=True)
        if not mq4s:
            messagebox.showinfo("스캔", "MQ4 파일 없음"); return
        # 가장 최근 파일 자동 선택
        latest = max(mq4s, key=os.path.getmtime)
        self._ea_path.set(latest)
        base = os.path.splitext(os.path.basename(latest))[0]
        self._fname_var.set(base)
        self._status.config(text=f"스캔: {len(mq4s)}개 발견, 최신 자동 선택")
        self._update_preview()

    def _sel_ea_folder(self):
        """★v4.0: 폴더 선택 → 하위 모든 .mq4 일괄 처리 모드"""
        folder = filedialog.askdirectory(title="EA .mq4 파일이 있는 폴더 선택")
        if not folder: return
        mq4s = glob.glob(os.path.join(folder, "*.mq4"))  # 직접 하위만 (재귀 제외)
        if not mq4s:
            # 직접 하위에 없으면 재귀 검색
            mq4s = glob.glob(os.path.join(folder, "**", "*.mq4"), recursive=True)
        if not mq4s:
            messagebox.showinfo("EA폴더", "선택한 폴더에 .mq4 파일이 없습니다."); return
        mq4s.sort()
        self._ea_folder_paths = mq4s
        # 첫 번째 파일을 단일 선택 필드에도 표시 (미리보기용)
        self._ea_path.set(mq4s[0])
        base = os.path.splitext(os.path.basename(mq4s[0]))[0]
        self._fname_var.set(base)
        self._folder_lbl.config(text=f"📂 {len(mq4s)}개 EA 로드됨")
        self._status.config(text=f"[EA폴더] {len(mq4s)}개 .mq4 선택 — 실행 시 전체 처리")
        self._update_preview()

    # ── 트리뷰 ────────────────────────────────────────────────
    def _make_set_content(self, sc, ea_name="MyEA"):
        tfl = self.TF_CODES.get(sc["tf"], str(sc["tf"]))
        rr  = sc["tp"] / sc["sl"] if sc["sl"] else 0
        lines = [
            f"; EA SET — {ea_name} [{sc['cat']} #{sc['id']}]",
            f"; {sc['note']}",
            f"; ─────────────────────────",
            f"SLFixedAmount={sc['sl']}",
            f"TPamount={sc['tp']}",
            f"LotSize={sc['lot']:.2f}",
            f"Period={sc['tf']}",
        ]
        # ★v5.3 신규 파라미터 — 적용 체크 시에만 포함 (기존 파라미터와 동일 형식)
        if hasattr(self, '_use_risk') and self._use_risk.get():
            lines.append(f"InpRiskPercent={self._risk_min.get():.2f}")
        if hasattr(self, '_use_dd') and self._use_dd.get():
            lines.append(f"InpMaxDrawdown={self._dd_min.get():.2f}")
        if hasattr(self, '_use_pos') and self._use_pos.get():
            lines.append(f"MaxPositions={self._pos_min.get()}")
        lines += [
            f"; SL=${sc['sl']}  TP=${sc['tp']}  Lot={sc['lot']:.2f}  TF={tfl}",
            f"; R:R={rr:.2f}",
        ]
        return "\n".join(lines) + "\n"

    def _populate_tree(self, items=None):
        if items is None:
            items = self._scenarios
        self._tree.delete(*self._tree.get_children())
        self._chk_vars.clear()
        
        for sc in items:
            tfl = self.TF_CODES.get(sc["tf"], str(sc["tf"]))
            rr  = f"{sc['tp']/sc['sl']:.2f}" if sc["sl"] else "-"
            # 새로 생성 시 기본은 미체크 (단, _filter_tree에서 n>1 시 전체선택 호출 예정)
            iid = self._tree.insert("", "end",
                values=("☐", sc["id"], sc["cat"], sc["sl"], sc["tp"],
                        f"{sc['lot']:.2f}", tfl, rr, sc.get("note","")),
                tags=(sc["cat"],))
            var = tk.BooleanVar(value=False)
            self._chk_vars[iid] = var
        
        self._cnt_lbl.config(text=f"{len(items)}개")

    def _tree_click(self, event):
        iid = self._tree.identify_row(event.y)
        col = self._tree.identify_column(event.x)
        if not iid: return
        if col == "#1":  # 체크박스 토글
            var = self._chk_vars.get(iid)
            if var:
                var.set(not var.get())
                chk = "☑" if var.get() else "☐"
                vals = list(self._tree.item(iid,"values"))
                vals[0] = chk; self._tree.item(iid, values=vals)
                if var.get():
                    self._tree.item(iid, tags=("CHK", vals[2])) # CHK를 앞에 두어 우선순위 확보
                else:
                    self._tree.item(iid, tags=(vals[2],))

    def _sel_nth(self, nth):
        """★v5.4.1: nth 간격 시나리오 선택 (나머지는 해제)"""
        if hasattr(self, '_interval_btns'):
            for n_val, btn in self._interval_btns.items():
                if n_val == nth: btn.config(bg="#7c3aed", fg="white")
                else: btn.config(bg=PANEL2, fg=FG)
        if hasattr(self, '_nth_var'): self._nth_var.set(nth)
            
        count = 0
        for i, iid in enumerate(self._tree.get_children()):
            var = self._chk_vars.get(iid)
            if not var: continue
            vals = list(self._tree.item(iid, "values"))
            if (i % nth) == 0:
                var.set(True)
                vals[0] = "☑"
                self._tree.item(iid, values=vals, tags=("CHK", vals[2]))  # 우선순위 교정
                count += 1
            else:
                var.set(False)
                vals[0] = "☐"
                self._tree.item(iid, values=vals, tags=(vals[2],))
        self._status.config(text=f"간격 필터링: {count}개 선택됨 (미선택 제외)")

    def _tree_dbl(self, event):
        """더블클릭 → 슬라이더에 값 자동 적용"""
        iid = self._tree.identify_row(event.y)
        if not iid: return
        vals = self._tree.item(iid,"values")
        # vals: (chk, id, cat, sl, tp, lot, tf_label, rr, note)
        try:
            sl = int(vals[3]); tp = int(vals[4])
            lot_x10 = int(float(vals[5]) * 100)
            tf_map = {"M5":5,"M15":15,"M30":30,"H1":60,"H4":240}
            tf = tf_map.get(vals[6], 5)
            self._apply_preset(sl, tp, lot_x10, tf)
            self._status.config(text=f"적용: {vals[2]} #{vals[1]}  SL={sl} TP={tp} Lot={float(vals[5]):.2f} TF={vals[6]}")
        except Exception as e:
            self._status.config(text=f"오류: {e}")

    def _filter_tree(self):
        cat  = self._filter_cat.get()
        kw   = self._search_var.get().lower()
        filt = [s for s in self._scenarios
                if (cat == "전체" or s["cat"] == cat)
                and (not kw or kw in str(s["sl"]) or kw in str(s["tp"])
                     or kw in s["cat"] or kw in s["note"])]
        self._populate_tree(filt)

    def _sel_all(self):
        for iid, var in self._chk_vars.items():
            var.set(True)
            vals = list(self._tree.item(iid,"values"))
            vals[0] = "☑"; self._tree.item(iid, values=vals)
            self._tree.item(iid, tags=("CHK", vals[2]))  # 우선순위 교정

    def _desel_all(self):
        for iid, var in self._chk_vars.items():
            var.set(False)
            vals = list(self._tree.item(iid,"values"))
            vals[0] = "☐"; self._tree.item(iid, values=vals)
            self._tree.item(iid, tags=(vals[2],))

    # ── G4v7 시나리오 N개 생성 ──────────────────────────────────
    def _gen_g4v7_count(self, n: int):
        """G4v7 파라미터 범위 기반으로 n개 시나리오를 균등 생성하고 트리뷰에 추가."""
        import itertools, random as _rnd
        try:
            from core.ea_template_v7 import generate_mq4_v7, make_ea_filename
            has_template = True
        except ImportError:
            has_template = False

        # ── 파라미터 범위 읽기 ──
        atr_min  = self._atr_period.get()
        atr_max  = getattr(self, '_atr_max', tk.IntVar(value=28)).get()
        fm_min   = self._fast_ma.get()
        sm_max   = getattr(self, '_slow_ma_max', tk.IntVar(value=50)).get()
        adx_min  = self._adx_min.get()
        adx_max  = getattr(self, '_adx_min_max', tk.DoubleVar(value=25.0)).get()
        rl_min   = self._rsi_lower.get()
        ru_max   = getattr(self, '_rsi_upper_max', tk.DoubleVar(value=75.0)).get()
        cd_min   = self._cooldown.get()
        cd_max   = getattr(self, '_cd_max', tk.IntVar(value=10)).get()
        dd_min   = self._dd_min.get()
        dd_max   = self._dd_max.get()
        pos_min  = self._pos_min.get()
        pos_max  = self._pos_max.get()
        sl_base  = self._sl_var.get()
        tp_base  = self._tp_var.get()

        # ── 파라미터 공간 ──
        def _linspace(lo, hi, steps):
            if steps <= 1 or lo == hi:
                return [lo]
            step = (hi - lo) / (steps - 1)
            return [lo + i * step for i in range(steps)]

        atr_vals = [int(round(v)) for v in _linspace(atr_min, atr_max, 4)]
        fm_vals  = [int(round(v)) for v in _linspace(fm_min, sm_max // 2, 4)]
        sm_vals  = [int(round(v)) for v in _linspace(max(fm_min+5, 21), sm_max, 5)]
        adx_vals = [round(v,1) for v in _linspace(adx_min, adx_max, 4)]
        rl_vals  = [int(round(v)) for v in _linspace(rl_min, 45, 3)]
        ru_vals  = [int(round(v)) for v in _linspace(55, ru_max, 3)]
        dd_vals  = [round(v,1) for v in _linspace(dd_min, dd_max, 4)]
        pos_vals = list(range(max(1,pos_min), min(6,pos_max)+1))
        cd_vals  = [int(round(v)) for v in _linspace(cd_min, cd_max, 4)]

        # SL×TP 변형 (sl_base±30%, tp_base±30% in 5 steps)
        sl_f = sl_base / 1000.0  # pixels→ multiplier 변환 (sl_base=500 → 0.5)
        tp_f = tp_base / 100.0   # pixels→ multiplier (tp_base=80 → 0.8... use raw)
        sl_mults = [round(sl_f * m, 3) for m in [0.5, 0.7, 1.0, 1.3, 1.6]]
        tp_mults = [round(tp_f * m, 3) for m in [0.5, 0.7, 1.0, 1.3, 1.6]]
        # Ensure reasonable ranges
        sl_mults = [max(0.1, min(1.0, v)) for v in sl_mults]
        tp_mults = [max(1.0, min(20.0, v)) for v in tp_mults]

        # ── 조합 생성 ──
        all_combos = []
        for sl, tp, atr, fm, sm_v, adx, rl, ru, dd, mp, cd in itertools.product(
            sl_mults[:3], tp_mults[:3],
            atr_vals[:2], fm_vals[:2], sm_vals[:2],
            adx_vals[:2], rl_vals[:2], ru_vals[:2],
            dd_vals[:2], pos_vals[:2], cd_vals[:2]
        ):
            if fm >= sm_v:
                continue
            all_combos.append((sl, tp, atr, fm, sm_v, adx, rl, ru, dd, mp, cd))
            if len(all_combos) >= n * 5:
                break

        if len(all_combos) < n:
            all_combos = all_combos * (n // max(1, len(all_combos)) + 1)
        _rnd.shuffle(all_combos)
        selected = all_combos[:n]

        # ── 기존 시나리오 목록에 추가 ──
        start_id = len(self._scenarios) + 1
        added = []
        for i, (sl, tp, atr, fm, sm_v, adx, rl, ru, dd, mp, cd) in enumerate(selected, 1):
            sc_id = start_id + i - 1
            params = {
                'InpSLMultiplier': sl, 'InpTPMultiplier': tp,
                'InpATRPeriod': atr, 'InpFastMA': fm, 'InpSlowMA': sm_v,
                'InpADXPeriod': 14, 'InpADXMin': adx,
                'InpRSIPeriod': 14, 'InpRSILower': rl, 'InpRSIUpper': ru,
                'InpMaxDD': dd, 'InpMaxPositions': mp, 'InpCooldownBars': cd,
            }
            note = f"G4v7 SL{int(sl*100):03d} TP{int(tp*10):04d} FM{fm:02d}/SM{sm_v:02d} AX{int(adx):02d}"
            self._scenarios.append({
                "cat": "G4V7", "id": i,
                "sl": int(sl*1000), "tp": int(tp*10), "lot": 0.10, "tf": 5,
                "note": note, "g4params": params
            })
            added.append(params)

        # ── 트리뷰 갱신 ──
        self._filter_tree()
        total = len(self._scenarios)
        if hasattr(self, '_cnt_lbl'):
            self._cnt_lbl.config(text=f"{total}개")
        if hasattr(self, '_right_title'):
            self._right_title.config(text=f"  📋  {total}개 시나리오")
        if hasattr(self, '_g4_cnt_lbl'):
            self._g4_cnt_lbl.config(text=f"✅ +{n}개 추가 (총 {total}개)")

        # ── MQ4 파일 생성 (Experts 폴더) ──
        if has_template:
            out_dir = self._out_dir.get()
            if out_dir and os.path.isdir(out_dir):
                round_num = self._round_no.get()
                written = 0
                for i, params in enumerate(added, start_id):
                    fname = make_ea_filename(i, round_num, params) + ".mq4"
                    fpath = os.path.join(out_dir, fname)
                    if not os.path.exists(fpath):
                        try:
                            with open(fpath, 'w', encoding='utf-8') as f:
                                f.write(generate_mq4_v7(i, round_num, params))
                            written += 1
                        except Exception:
                            pass
                if hasattr(self, '_g4_cnt_lbl'):
                    self._g4_cnt_lbl.config(
                        text=f"✅ +{n}개 추가 | mq4 {written}개 생성")

    # ── .set 파일 저장 ────────────────────────────────────────
    def _ensure_out_dir(self):
        d = self._out_dir.get().strip()
        if not d:
            messagebox.showerror("오류", "저장 폴더가 설정되지 않았습니다!\n저장폴더를 입력하거나 SOLO 폴더를 선택 후 [SOLO 동기화] 버튼을 누르세요.")
            return ""
        os.makedirs(d, exist_ok=True)
        return d

    def _save_custom_set(self):
        """슬라이더 현재 값으로 .set 저장"""
        sl   = self._sl_var.get()
        tp   = self._tp_var.get()
        lot  = int(self._lot_int.get()) / 100
        tf   = self._tf_var.get()
        tfl  = self.TF_CODES.get(tf, str(tf))
        name = self._fname_var.get() or "MyEA"
        d    = self._ensure_out_dir()
        fname = f"{name}_SL{sl}_TP{tp}_{tfl}.set"
        fpath = os.path.join(d, fname)
        content = self._preview.get("1.0","end")
        with open(fpath,"w",encoding="utf-8") as f: f.write(content)
        self._status.config(text=f"✅ 저장: {fname}")
        subprocess.run(["start","",d],shell=True)

    def _copy_preview(self):
        self.clipboard_clear()
        self.clipboard_append(self._preview.get("1.0","end"))
        self._status.config(text="클립보드 복사 완료")

    def _save_selected(self):
        """선택된 시나리오들 .set 파일 배치 저장"""
        ea_name = os.path.splitext(os.path.basename(self._ea_path.get()))[0] if self._ea_path.get() else "MyEA"
        selected = [(iid, var) for iid, var in self._chk_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("저장", "먼저 체크박스로 시나리오를 선택하세요"); return
        d = self._ensure_out_dir()
        if not d: return
        saved = 0
        for iid, _ in selected:
            vals = self._tree.item(iid,"values")
            # vals: (chk, id, cat, sl, tp, lot, tf_label, rr, note)
            try:
                cat   = vals[2]; sid = vals[1]
                sl    = int(vals[3]); tp = int(vals[4])
                lot   = float(vals[5])
                tfl   = vals[6]
                tf_map = {"M5":5,"M15":15,"M30":30,"H1":60,"H4":240}
                tf    = tf_map.get(tfl, 5)
                note  = vals[8] if len(vals)>8 else ""
                sc    = {"cat":cat,"id":sid,"sl":sl,"tp":tp,"lot":lot,"tf":tf,"note":note}
                content = self._make_set_content(sc, ea_name)
                cat_safe = cat.replace("+","_").replace(" ","_")
                fname    = f"{ea_name}_{cat_safe}_{sid:02d}_SL{sl}_TP{tp}_{tfl}.set"
                with open(os.path.join(d,fname),"w",encoding="utf-8") as f: f.write(content)
                saved += 1
            except Exception as e:
                self._status.config(text=f"오류: {e}")
        self._status.config(text=f"✅ {saved}개 시나리오 저장 완료 → {d}")
        subprocess.run(["start","",d],shell=True)

    def _save_all_cats(self):
        """카테고리별 서브폴더에 전체 160개 저장"""
        ea_name = os.path.splitext(os.path.basename(self._ea_path.get()))[0] if self._ea_path.get() else "MyEA"
        root    = self._ensure_out_dir()
        total   = 0
        for sc in self._scenarios:
            cat_safe = sc["cat"].replace("+","_").replace(" ","_")
            sub = os.path.join(root, cat_safe); os.makedirs(sub, exist_ok=True)
            tfl  = self.TF_CODES.get(sc["tf"],str(sc["tf"]))
            fname = f"{ea_name}_{cat_safe}_{sc['id']:02d}_SL{sc['sl']}_TP{sc['tp']}_{tfl}.set"
            content = self._make_set_content(sc, ea_name)
            with open(os.path.join(sub,fname),"w",encoding="utf-8") as f: f.write(content)
            total += 1
        self._status.config(text=f"✅ 카테고리별 전체 {total}개 저장 → {root}")
        subprocess.run(["start","",root],shell=True)

    def _export_csv(self):
        d = self._ensure_out_dir()
        fpath = os.path.join(d,"EA_160_Scenarios.csv")
        with open(fpath,"w",encoding="utf-8-sig") as f:
            f.write("Category,ID,SL,TP,Lot,TF,RR,Note\n")
            for sc in self._scenarios:
                tfl = self.TF_CODES.get(sc["tf"],str(sc["tf"]))
                rr  = f"{sc['tp']/sc['sl']:.2f}" if sc["sl"] else "-"
                f.write(f"{sc['cat']},{sc['id']},{sc['sl']},{sc['tp']},{sc['lot']:.2f},"
                        f"{tfl},{rr},{sc['note']}\n")
        self._status.config(text=f"✅ CSV 저장: EA_160_Scenarios.csv")
        subprocess.run(["start","",d],shell=True)

    def _open_html(self):
        html_path = os.path.join(HERE,"EA_SCENARIO_MASTER_GUI.html")
        if os.path.exists(html_path):
            os.startfile(html_path)
        else:
            messagebox.showinfo("HTML","EA_SCENARIO_MASTER_GUI.html 파일 없음\n먼저 생성 필요")

    # ── 결과 분석 ──────────────────────────────────────────────
    def _parse_htm_report(self, fpath):
        """MT4 HTM 리포트에서 순이익/승률/PF/거래수 + 거래 상세(진입시간/방향) 파싱. 실패 시 None."""
        try:
            raw = open(fpath, 'rb').read()
            enc = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
            html = raw.decode(enc, errors='replace')
        except Exception:
            try:
                html = open(fpath, 'r', encoding='cp949', errors='ignore').read()
            except Exception:
                return None
        import re
        from datetime import datetime as _dt

        # ── 파일명에서 심볼 추출 ──────────────────────────────
        fname = os.path.basename(fpath)
        sym_m = re.search(r'(BTCUSD|ETHUSD|XAUUSD|EURUSD|GBPUSD|USDJPY|AUDUSD|USDCHF)', fname, re.I)
        symbol = sym_m.group(1).upper() if sym_m else 'Unknown'

        # ── 통계 파싱 ─────────────────────────────────────────
        profit = None
        for pat in [r'Total Net Profit.*?<td[^>]*>([\-\d\., ]+)</td>',
                    r'순이익.*?<td[^>]*>([\-\d\., ]+)</td>',
                    r'<b>Net Profit:</b></td>\s*<td[^>]*>([\-\d\., ]+)']:
            m = re.search(pat, html, re.S | re.I)
            if m:
                try: profit = float(m.group(1).replace(',','').replace(' ','').strip()); break
                except: pass

        pf = None
        for pat in [r'Profit Factor.*?<td[^>]*>([\d\., ]+)</td>',
                    r'프로핏 팩터.*?<td[^>]*>([\d\., ]+)</td>',
                    r'<b>Profit Factor:</b></td>\s*<td[^>]*>([\d\., ]+)']:
            m = re.search(pat, html, re.S | re.I)
            if m:
                try: pf = float(m.group(1).replace(',','').replace(' ','').strip()); break
                except: pass

        winrate = None
        for pat in [r'of winning trades.*?<td[^>]*>([\d\., ]+)%?</td>',
                    r'이익 거래.*?<td[^>]*>([\d\., ]+)%?</td>',
                    r'<b>Win Rate:</b></td>\s*<td[^>]*>([\d\.]+)']:
            m = re.search(pat, html, re.S | re.I)
            if m:
                try: winrate = float(m.group(1).replace(',','').replace(' ','').strip()); break
                except: pass

        trades_count = None
        for pat in [r'Total Trades.*?<td[^>]*>([\d ]+)</td>',
                    r'전체 거래수.*?<td[^>]*>([\d ]+)</td>',
                    r'<b>Total Trades:</b></td>\s*<td[^>]*>(\d+)']:
            m = re.search(pat, html, re.S | re.I)
            if m:
                try: trades_count = int(m.group(1).replace(' ','')); break
                except: pass

        if profit is None and pf is None:
            return None

        # ── 거래 상세 파싱 (진입시간 + 방향) ─────────────────
        # Format A: MT4 기본 HTM (align=right 숫자행 + buy/sell 텍스트)
        # Format C: DETAILED 커스텀 (<tr class="buy">/<tr class="sell">)
        trade_list = []

        # Format C 시도
        rows_c = re.findall(
            r'<tr\s+class="(buy|sell)"[^>]*>.*?'
            r'<td[^>]*>([\d]{4}\.[\d]{2}\.[\d]{2}\s+[\d]{2}:[\d]{2})',
            html, re.I | re.S)
        for direction, dt_str in rows_c:
            try:
                trade_list.append({
                    'date': _dt.strptime(dt_str.strip(), '%Y.%m.%d %H:%M'),
                    'direction': direction.lower()
                })
            except Exception: pass

        # Format A 시도 (기본 MT4 HTM)
        if not trade_list:
            rows_a = re.findall(
                r'<td[^>]*>(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})</td>\s*<td[^>]*>(buy|sell)</td>',
                html, re.I)
            for dt_str, direction in rows_a:
                try:
                    trade_list.append({
                        'date': _dt.strptime(dt_str.strip(), '%Y.%m.%d %H:%M'),
                        'direction': direction.lower()
                    })
                except Exception: pass

        return {
            "profit":   profit or 0.0,
            "pf":       pf or 0.0,
            "winrate":  winrate or 0.0,
            "trades":   trades_count or len(trade_list),
            "total_trades": trades_count or len(trade_list),
            "trade_list": trade_list,   # 방향분석용 상세 리스트
            "symbol":   symbol,
        }

    def _load_round_analysis(self):
        """★v5.3: BB_SQUEEZE_R*_ANALYSIS.html JS 데이터 파싱 → 결과 테이블 로드"""
        import glob as _glob, re as _re
        htm_dir = self._htm_dir.get().strip()
        if not os.path.isdir(htm_dir):
            messagebox.showwarning("폴더 없음", f"Reports 폴더를 선택하세요:\n{htm_dir}"); return

        # R1~R10 분석 HTML 수집
        pattern = os.path.join(htm_dir, "*_R*_ANALYSIS.html")
        files = sorted(_glob.glob(pattern))
        if not files:
            messagebox.showwarning("파일 없음",
                f"BB_SQUEEZE_R*_ANALYSIS.html 파일이 없습니다.\n폴더: {htm_dir}"); return

        all_rows = []
        for fpath in files:
            fname = os.path.basename(fpath)
            round_m = _re.search(r'_R(\d+)_ANALYSIS', fname, _re.I)
            rno = round_m.group(1) if round_m else "?"
            try:
                html = open(fpath, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            # JS data array: {sc:'SC10', sl:3.0, tp:6.0, rr:2.00, profit:1844.80, trades:456, wr:68.2}
            entries = _re.findall(
                r'\{sc\s*:\s*[\'"]([^"\']+)[\'"]'
                r'.*?sl\s*:\s*([\d\.]+)'
                r'.*?tp\s*:\s*([\d\.]+)'
                r'.*?rr\s*:\s*([\d\.]+)'
                r'.*?profit\s*:\s*([\-\d\.]+)'
                r'.*?trades\s*:\s*(\d+)'
                r'.*?wr\s*:\s*([\d\.]+)',
                html, _re.S
            )
            for sc, sl, tp, rr, profit, trades, wr in entries:
                all_rows.append({
                    "round": rno, "sc": sc,
                    "sl": float(sl), "tp": float(tp), "rr": float(rr),
                    "profit": float(profit), "trades": int(trades), "wr": float(wr),
                })

        if not all_rows:
            messagebox.showwarning("파싱 실패", "JS 데이터를 찾지 못했습니다."); return

        # 순이익 내림차순 정렬
        all_rows.sort(key=lambda x: x["profit"], reverse=True)
        self._last_results = [{
            "cat": f"R{r['round']}_{r['sc']}", "sl": r["sl"], "tp": r["tp"],
            "lot": 0.10, "tf": "M5",
            "profit": r["profit"], "winrate": r["wr"], "pf": r["rr"],
            "trades": r["trades"],
        } for r in all_rows]

        # GOOD/BAD 기준
        n = len(all_rows)
        good_thresh = all_rows[max(0, int(n*0.3)-1)]["profit"] if n >= 3 else float("inf")
        bad_thresh  = all_rows[min(n-1, int(n*0.7))]["profit"]  if n >= 3 else float("-inf")

        # 트리 초기화 후 채우기
        for row in self._res_tree.get_children():
            self._res_tree.delete(row)
        for rank, r in enumerate(all_rows, 1):
            if r["profit"] >= good_thresh:
                tag, verdict = "GOOD", "✅ TOP"
            elif r["profit"] <= bad_thresh:
                tag, verdict = "BAD",  "❌ LOW"
            else:
                tag, verdict = "MID",  "➖ MID"
            self._res_tree.insert("", "end", tags=(tag,), values=(
                rank,
                f"R{r['round']}",
                r["sc"],
                r["sl"], r["tp"],
                "0.10", "M5",
                f"{r['profit']:.1f}",
                f"{r['wr']:.1f}",
                f"{r['rr']:.2f}",
                r["trades"],
                verdict,
            ))

        self._status.config(
            text=f"✅ BB_SQUEEZE R1~R8 로드 완료: {n}개 시나리오 ({len(files)}개 라운드)",
            fg="#4ade80"
        )
        # 컬럼명 업데이트 (PF → RR)
        self._res_tree.heading("pf", text="RR")
        self._res_tree.heading("cat", text="라운드")
        self._res_tree.heading("id", text="SC")

    def _analyze_results(self):
        """HTM 폴더 스캔 → 시나리오별 결과 파싱 → 테이블 출력"""
        htm_dir = self._htm_dir.get().strip()
        if not htm_dir or not os.path.isdir(htm_dir):
            messagebox.showwarning("폴더 없음", "HTM 리포트가 있는 폴더를 선택하세요."); return

        import glob as _glob, re as _re
        htm_files = _glob.glob(os.path.join(htm_dir, "**", "*.htm"), recursive=True)
        htm_files += _glob.glob(os.path.join(htm_dir, "**", "*.html"), recursive=True)
        if not htm_files:
            messagebox.showwarning("파일 없음", f"HTM 파일이 없습니다:\n{htm_dir}"); return

        # 파일명에서 시나리오 파라미터 파싱: *_SL{n}_TP{n}_*
        results = []
        for fp in htm_files:
            fname = os.path.basename(fp)
            res = self._parse_htm_report(fp)
            if res is None: continue
            # 파일명에서 SL/TP/Lot/TF 추출
            sl_m  = _re.search(r'SL(\d+)', fname)
            tp_m  = _re.search(r'TP(\d+)', fname)
            lot_m = _re.search(r'Lot([\d\.]+)', fname)
            tf_m  = _re.search(r'_(M5|M15|M30|H1|H4)', fname)
            cat_m = _re.search(r'_(SL_DEC|SL_INC|TP_INC|TF_CHG|LOT_BIG|LOT_SML|SLTP_MIX|FULL_MIX)_\d+_SL', fname)
            sl  = int(sl_m.group(1))  if sl_m  else 0
            tp  = int(tp_m.group(1))  if tp_m  else 0
            lot = float(lot_m.group(1)) if lot_m else 0.0
            tf  = tf_m.group(1)       if tf_m  else "?"
            cat = cat_m.group(1)      if cat_m else "?"
            results.append({
                "fname": fname, "cat": cat, "sl": sl, "tp": tp,
                "lot": lot, "tf": tf,
                **res
            })

        if not results:
            messagebox.showwarning("파싱 실패",
                "HTM 파일은 있지만 결과를 파싱하지 못했습니다.\n"
                "MT4에서 'Save as Report (Full)'로 저장했는지 확인하세요."); return

        # 순이익 기준 내림차순 정렬
        results.sort(key=lambda x: x["profit"], reverse=True)
        self._last_results = results  # 라운드2 제안에 사용

        # 상위/하위 기준 (상위 30% = GOOD, 하위 30% = BAD)
        n = len(results)
        good_thresh = results[max(0, int(n*0.3)-1)]["profit"] if n >= 3 else float("inf")
        bad_thresh  = results[min(n-1, int(n*0.7))]["profit"] if n >= 3 else float("-inf")

        # 트리 초기화 후 채우기
        for row in self._res_tree.get_children():
            self._res_tree.delete(row)
        for rank, r in enumerate(results, 1):
            if r["profit"] >= good_thresh:
                tag = "GOOD"; verdict = "✅ 좋음"
            elif r["profit"] <= bad_thresh:
                tag = "BAD";  verdict = "❌ 나쁨"
            else:
                tag = "MID";  verdict = "➖ 보통"
            self._res_tree.insert("", "end", tags=(tag,), values=(
                rank, r["cat"], "-", r["sl"], r["tp"], f"{r['lot']:.2f}", r["tf"],
                f"{r['profit']:.1f}", f"{r['winrate']:.1f}",
                f"{r['pf']:.2f}", r["trades"], verdict,
            ))

        self._status.config(text=f"✅ {n}개 리포트 분석 완료 (상위 GOOD / 하위 BAD)", fg="#4ade80")

        # ── 라운드 히스토리 JSON 자동 저장 ──────────────────
        self._save_round_history(results, n, good_thresh, bad_thresh)

    def _save_round_history(self, results, n, good_thresh, bad_thresh):
        """결과를 round_history.json에 누적 저장 (최대 10라운드)"""
        rno = self._round_no.get()
        try:
            existing = []
            if os.path.exists(self._hist_path):
                with open(self._hist_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
        except Exception:
            existing = []

        for rank, r in enumerate(results, 1):
            if r["profit"] >= good_thresh:
                verdict = "GOOD"
            elif r["profit"] <= bad_thresh:
                verdict = "BAD"
            else:
                verdict = "MID"
            existing.append({
                "round":   rno,
                "cat":     r.get("cat","?"),
                "sl":      r.get("sl",0),
                "tp":      r.get("tp",0),
                "lot":     r.get("lot",0.0),
                "tf":      r.get("tf","?"),
                "profit":  r.get("profit",0.0),
                "winrate": r.get("winrate",0.0),
                "pf":      r.get("pf",0.0),
                "trades":  r.get("trades",0),
                "rank":    rank,
                "verdict": verdict,
            })

        try:
            with open(self._hist_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            # 다음 라운드 번호 자동 증가 (최대 10)
            next_rno = min(rno + 1, 10)
            self._round_no.set(next_rno)
        except Exception as e:
            self._status.config(text=f"⚠️ 히스토리 저장 실패: {e}", fg="#f87171")

    def _gen_round2(self):
        """
        라운드2 SET 생성:
          - 상위 1~20위  → 직접 사용 (20개, TOP_N 태그)
          - 하위 1~5위   → 상위 1~5위 파라미터로 조정하여 개선 테스트 (5개, RESCUE 태그)
          총 25개 SET 생성 + HTML 비교 리포트 출력
        """
        if not hasattr(self, "_last_results") or not self._last_results:
            messagebox.showwarning("분석 먼저", "먼저 '🔍 결과 분석'을 실행하세요."); return

        results  = self._last_results
        n        = len(results)
        if n < 5:
            messagebox.showwarning("결과 부족", f"결과가 {n}개입니다. 최소 5개 이상 필요합니다."); return

        from collections import Counter

        # ── 상위 20개 / 하위 5개 ────────────────────────────────
        top20    = results[:min(20, n)]          # 상위 1~20위
        bottom5  = results[max(0, n-5):]         # 하위 1~5위 (worst5[0]=최하위)

        # 상위 1~5위 평균 파라미터 (RESCUE 기준값)
        top5     = results[:min(5, n)]
        def avg(lst, key):
            vals = [r[key] for r in lst if r.get(key) is not None and r[key] != 0]
            return sum(vals)/len(vals) if vals else 0

        top5_sl  = avg(top5, "sl")
        top5_tp  = avg(top5, "tp")
        top5_lot = avg(top5, "lot")
        best_tf  = Counter(r["tf"] for r in top5).most_common(1)[0][0] if top5 else "M5"

        tf_map   = {"M5":5,"M15":15,"M30":30,"H1":60,"H4":240}
        tf_int   = tf_map.get(best_tf, 5)

        ea_name  = os.path.splitext(os.path.basename(self._ea_path.get()))[0] \
                   if self._ea_path.get() else "MyEA"
        d        = self._ensure_out_dir()
        r2_dir   = os.path.join(d, "Round2_SET"); os.makedirs(r2_dir, exist_ok=True)

        created_sets = []   # {type, rank, sl, tp, lot, tf, fname, origin_profit}

        # ── 상위 20개 SET 그대로 저장 ────────────────────────────
        for i, r in enumerate(top20):
            sc = {"cat":"TOP_N","id":i+1,
                  "sl": r["sl"],"tp": r["tp"],"lot": r["lot"],
                  "tf": tf_map.get(r["tf"], 5),"note":f"TOP{i+1}직접사용"}
            content = self._make_set_content(sc, ea_name)
            fname   = f"{ea_name}_R2_TOP{i+1:02d}_SL{r['sl']}_TP{r['tp']}_{r['tf']}.set"
            with open(os.path.join(r2_dir, fname), "w", encoding="utf-8") as f:
                f.write(content)
            created_sets.append({
                "type":"TOP","rank":i+1,"sl":r["sl"],"tp":r["tp"],"lot":r["lot"],
                "tf":r["tf"],"fname":fname,"origin_profit":r["profit"],
                "cat":r.get("cat","?"),"origin_winrate":r.get("winrate",0),
                "origin_pf":r.get("pf",0),"origin_trades":r.get("trades",0),
            })

        # ── 하위 5개 → RESCUE: 상위 1~5위 평균값으로 SET 교체 ──
        # 각 하위 EA의 SL/TP/Lot를 상위1~5 평균으로 치환 (±5% 미세변동 포함)
        rescue_offsets = [
            (1.00, 1.00, 1.00),   # 정확히 평균
            (0.95, 1.05, 1.00),   # SL -5%, TP +5%
            (1.05, 0.95, 1.00),   # SL +5%, TP -5%
            (0.97, 1.03, 0.95),   # SL -3%, TP +3%, Lot -5%
            (1.03, 0.97, 1.05),   # SL +3%, TP -3%, Lot +5%
        ]
        for j, (r_bot, (sl_f, tp_f, lot_f)) in enumerate(zip(bottom5, rescue_offsets)):
            r_sl  = max(50,   int(top5_sl  * sl_f))
            r_tp  = max(10,   int(top5_tp  * tp_f))
            r_lot = max(0.01, round(top5_lot * lot_f, 2))
            sc = {"cat":"RESCUE","id":j+1,
                  "sl":r_sl,"tp":r_tp,"lot":r_lot,"tf":tf_int,
                  "note":f"RESCUE하위{n-len(bottom5)+j+1}위→TOP5평균조정"}
            content = self._make_set_content(sc, ea_name)
            fname   = f"{ea_name}_R2_RESCUE{j+1:02d}_SL{r_sl}_TP{r_tp}_{best_tf}.set"
            with open(os.path.join(r2_dir, fname), "w", encoding="utf-8") as f:
                f.write(content)
            created_sets.append({
                "type":"RESCUE","rank":n-len(bottom5)+j+1,
                "sl":r_sl,"tp":r_tp,"lot":r_lot,"tf":best_tf,
                "fname":fname,"origin_profit":r_bot["profit"],
                "cat":r_bot.get("cat","?"),"origin_winrate":r_bot.get("winrate",0),
                "origin_pf":r_bot.get("pf",0),"origin_trades":r_bot.get("trades",0),
                "rescue_sl_offset":f"{sl_f:.0%}","rescue_tp_offset":f"{tp_f:.0%}",
            })

        # ── 텍스트 요약 ─────────────────────────────────────────
        top5_avg_profit = avg(top5, "profit")
        bot5_avg_profit = avg(bottom5, "profit")
        lines = [
            f"═══ 라운드2 생성 완료 ({n}개 기준) ═══",
            f"",
            f"[TOP 20] 상위 1~20위 → SET 직접 사용 (20개)",
            f"  1위 순이익: {top20[0]['profit']:,.1f}  SL={top20[0]['sl']} TP={top20[0]['tp']} {top20[0]['tf']}",
            f"  20위 순이익: {top20[-1]['profit']:,.1f}  SL={top20[-1]['sl']} TP={top20[-1]['tp']}",
            f"",
            f"[RESCUE 5] 하위 1~5위 → 상위 1~5위 평균값으로 조정 (5개)",
            f"  TOP5 평균: SL={top5_sl:.0f} TP={top5_tp:.0f} Lot={top5_lot:.2f} TF={best_tf}",
            f"  하위 평균 순이익: {bot5_avg_profit:,.1f}  →  TOP5 평균: {top5_avg_profit:,.1f}",
            f"  (±5% 미세변동 5세트로 개선 확인)",
            f"",
            f"총 25개 SET → {r2_dir}",
        ]
        self._r2_text.config(state="normal")
        self._r2_text.delete("1.0","end")
        self._r2_text.insert("1.0", "\n".join(lines))
        self._r2_text.config(state="disabled")
        self._status.config(text=f"🚀 라운드2 25개 SET 생성 완료 (TOP20+RESCUE5)", fg="#ff6b35")
        subprocess.run(["start","",r2_dir],shell=True)

        # ── HTML 비교 리포트 생성 ────────────────────────────────
        self._gen_round2_html(results, top20, bottom5, top5, created_sets,
                              top5_sl, top5_tp, top5_lot, best_tf, r2_dir, ea_name)

    def _gen_round2_html(self, all_results, top20, bottom5, top5,
                         created_sets, top5_sl, top5_tp, top5_lot, best_tf,
                         r2_dir, ea_name):
        """라운드2 전략 비교 HTML 리포트 생성"""
        from datetime import datetime as _dt

        n   = len(all_results)
        now = _dt.now().strftime("%Y-%m-%d %H:%M")

        def profit_color(v):
            if v > 0:   return "#4ade80"
            elif v < 0: return "#f87171"
            return "#94a3b8"

        def star_bar(rank, total):
            pct = max(0, 1 - rank/total)
            filled = int(pct * 5)
            return "★"*filled + "☆"*(5-filled)

        # 상위20 행
        top20_rows = ""
        for i, r in enumerate(top20):
            pc = profit_color(r["profit"])
            stars = star_bar(i, 20)
            top20_rows += f"""
            <tr class="{'rescue-row' if i<5 else ''}">
              <td><span class="rank-badge top">TOP {i+1}</span></td>
              <td>{r.get('cat','?')}</td>
              <td>{r['sl']}</td><td>{r['tp']}</td>
              <td>{r['lot']:.2f}</td><td>{r['tf']}</td>
              <td style="color:{pc};font-weight:bold">${r['profit']:,.1f}</td>
              <td>{r.get('winrate',0):.1f}%</td>
              <td>{r.get('pf',0):.2f}</td>
              <td>{r.get('trades',0)}</td>
              <td style="color:#fbbf24">{stars}</td>
            </tr>"""

        # 하위5 → RESCUE 비교 행
        rescue_rows = ""
        rescue_sets = [s for s in created_sets if s["type"]=="RESCUE"]
        for j, (r_bot, rs) in enumerate(zip(bottom5, rescue_sets)):
            pc_orig  = profit_color(r_bot["profit"])
            rank_orig = n - len(bottom5) + j + 1
            rescue_rows += f"""
            <tr>
              <td><span class="rank-badge bottom">BOT {rank_orig}</span></td>
              <td>{r_bot.get('cat','?')}</td>
              <td>SL={r_bot['sl']} TP={r_bot['tp']}</td>
              <td style="color:{pc_orig};font-weight:bold">${r_bot['profit']:,.1f}</td>
              <td>{r_bot.get('winrate',0):.1f}%</td>
              <td>{r_bot.get('pf',0):.2f}</td>
              <td>→</td>
              <td><span class="rescue-label">RESCUE {j+1}</span></td>
              <td>SL={rs['sl']} TP={rs['tp']}</td>
              <td style="color:#60a5fa">미실행 (대기)</td>
              <td style="color:#94a3b8">{rs.get('rescue_sl_offset','?')} / {rs.get('rescue_tp_offset','?')}</td>
            </tr>"""

        # 전체 랭킹 테이블 (접을 수 있게)
        all_rows = ""
        good_n  = max(1, int(n*0.3))
        bad_n   = max(1, int(n*0.3))
        for i, r in enumerate(all_results):
            if i < good_n:      cls, label = "good-row", "GOOD"
            elif i >= n-bad_n:  cls, label = "bad-row",  "BAD"
            else:               cls, label = "",          "MID"
            pc = profit_color(r["profit"])
            all_rows += f"""
            <tr class="{cls}">
              <td>{i+1}</td><td>{r.get('cat','?')}</td>
              <td>{r['sl']}</td><td>{r['tp']}</td>
              <td>{r['lot']:.2f}</td><td>{r['tf']}</td>
              <td style="color:{pc}">${r['profit']:,.1f}</td>
              <td>{r.get('winrate',0):.1f}%</td>
              <td>{r.get('pf',0):.2f}</td>
              <td>{r.get('trades',0)}</td>
              <td><span class="verdict-{label.lower()}">{label}</span></td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>R2 Round2 전략 비교 — {ea_name}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f172a;color:#e2e8f0;font-family:'Malgun Gothic',Consolas,sans-serif;font-size:13px}}
.hdr{{background:linear-gradient(135deg,#1e3a8a,#7c3aed);padding:20px 30px;display:flex;justify-content:space-between;align-items:center}}
.hdr h1{{font-size:22px;font-weight:700;color:#fff}}
.hdr .meta{{color:#bfdbfe;font-size:12px;text-align:right}}
.tabs{{display:flex;background:#1e293b;border-bottom:2px solid #334155}}
.tab{{padding:10px 22px;cursor:pointer;color:#94a3b8;font-weight:600;border-bottom:3px solid transparent;transition:.2s}}
.tab.active,.tab:hover{{color:#60a5fa;border-bottom-color:#60a5fa}}
.content{{display:none;padding:20px 24px}}
.content.active{{display:block}}
.stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.stat-card{{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;text-align:center}}
.stat-card .val{{font-size:22px;font-weight:700;color:#60a5fa}}
.stat-card .lbl{{font-size:11px;color:#64748b;margin-top:4px}}
.stat-card.green .val{{color:#4ade80}}
.stat-card.red .val{{color:#f87171}}
.stat-card.yellow .val{{color:#fbbf24}}
.stat-card.purple .val{{color:#a78bfa}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#1e293b;color:#94a3b8;padding:8px 10px;text-align:center;border-bottom:1px solid #334155;position:sticky;top:0}}
td{{padding:7px 10px;text-align:center;border-bottom:1px solid #1e293b}}
tr:hover td{{background:#1e293b}}
.good-row td{{background:#0a1f0f}}
.bad-row td{{background:#1f0a0a}}
.rescue-row td{{background:#0f1f35}}
.rank-badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700}}
.rank-badge.top{{background:#1e3a8a;color:#60a5fa}}
.rank-badge.bottom{{background:#3b0764;color:#c084fc}}
.rescue-label{{background:#0c4a6e;color:#38bdf8;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700}}
.verdict-good{{background:#166534;color:#4ade80;padding:2px 8px;border-radius:10px;font-size:11px}}
.verdict-bad{{background:#7f1d1d;color:#f87171;padding:2px 8px;border-radius:10px;font-size:11px}}
.verdict-mid{{background:#1e293b;color:#94a3b8;padding:2px 8px;border-radius:10px;font-size:11px}}
.section-title{{color:#fbbf24;font-size:15px;font-weight:700;margin:18px 0 10px;padding-left:10px;border-left:3px solid #fbbf24}}
.info-box{{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px 18px;margin-bottom:16px;line-height:1.8}}
.info-box .hl{{color:#60a5fa;font-weight:700}}
.info-box .green{{color:#4ade80;font-weight:700}}
.info-box .red{{color:#f87171;font-weight:700}}
.info-box .yellow{{color:#fbbf24;font-weight:700}}
.rescue-explain{{background:#0c1a2e;border:1px solid #1d4ed8;border-radius:8px;padding:14px 18px;margin-bottom:16px;line-height:1.9}}
.arrow{{color:#fbbf24;font-size:16px}}
.scroll-table{{max-height:400px;overflow-y:auto;border:1px solid #334155;border-radius:6px}}
details summary{{cursor:pointer;padding:10px 14px;background:#1e293b;color:#94a3b8;border-radius:6px;margin-bottom:8px}}
details[open] summary{{color:#60a5fa}}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <h1>🚀 Round 2 — 전략 비교 리포트</h1>
    <div style="color:#bfdbfe;margin-top:4px">EA: <b>{ea_name}</b> | 생성: {now} | 총 {n}개 라운드1 결과 분석</div>
  </div>
  <div class="meta">
    TOP 20 → 직접 사용<br>
    RESCUE 5 → 하위를 상위 파라미터로 교체<br>
    총 25개 SET → Round2_SET/
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('overview')">📊 라운드2 전략</div>
  <div class="tab" onclick="showTab('rescue')">🔬 RESCUE 분석</div>
  <div class="tab" onclick="showTab('allrank')">📋 전체 랭킹 ({n}개)</div>
  <div class="tab" onclick="showTab('guide')">📖 사용 가이드</div>
</div>

<!-- TAB 1: OVERVIEW -->
<div id="overview" class="content active">
  <div class="stats-grid">
    <div class="stat-card green">
      <div class="val">${all_results[0]['profit']:,.0f}</div>
      <div class="lbl">1위 순이익 (TOP1)</div>
    </div>
    <div class="stat-card">
      <div class="val">{len(top20)}</div>
      <div class="lbl">TOP SET 수</div>
    </div>
    <div class="stat-card purple">
      <div class="val">5</div>
      <div class="lbl">RESCUE SET 수</div>
    </div>
    <div class="stat-card yellow">
      <div class="val">{top5_sl:.0f}/{top5_tp:.0f}</div>
      <div class="lbl">TOP5 평균 SL/TP</div>
    </div>
  </div>

  <div class="section-title">🏆 TOP 20 — 상위 1~20위 직접 사용</div>
  <div class="info-box">
    <span class="hl">TOP 20</span>은 라운드1에서 순이익 기준 상위 20개 시나리오입니다.
    라운드2에서 동일 파라미터로 다른 기간/조건에서 재검증합니다.<br>
    <span class="green">1위</span>: SL={top20[0]['sl']} TP={top20[0]['tp']} Lot={top20[0]['lot']:.2f} {top20[0]['tf']} → ${top20[0]['profit']:,.1f}
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <span style="color:#94a3b8">20위</span>: SL={top20[-1]['sl']} TP={top20[-1]['tp']} → ${top20[-1]['profit']:,.1f}
  </div>
  <div class="scroll-table">
  <table>
    <thead><tr>
      <th>순위</th><th>카테고리</th><th>SL</th><th>TP</th><th>Lot</th><th>TF</th>
      <th>순이익</th><th>승률</th><th>PF</th><th>거래수</th><th>평점</th>
    </tr></thead>
    <tbody>{top20_rows}</tbody>
  </table>
  </div>
</div>

<!-- TAB 2: RESCUE -->
<div id="rescue" class="content">
  <div class="section-title">🔬 RESCUE 5 — 하위 5개를 TOP5 평균값으로 교체</div>
  <div class="rescue-explain">
    <b style="color:#38bdf8">RESCUE 전략이란?</b><br>
    라운드1에서 <span class="red">최하위 5개</span>의 EA는 SL/TP 파라미터가 시장과 맞지 않아 성적이 나쁩니다.<br>
    이 5개에 <span class="green">상위 1~5위 평균 파라미터</span>를 적용하면 성적이 개선되는지 테스트합니다.<br><br>
    <b>TOP5 기준값:</b>
    SL=<span class="hl">{top5_sl:.0f}</span> &nbsp;
    TP=<span class="hl">{top5_tp:.0f}</span> &nbsp;
    Lot=<span class="hl">{top5_lot:.2f}</span> &nbsp;
    TF=<span class="hl">{best_tf}</span><br><br>
    <b>5세트 변동:</b> 정확히 평균값 / SL-5%TP+5% / SL+5%TP-5% / SL-3%TP+3%Lot-5% / SL+3%TP-3%Lot+5%<br>
    → 라운드2 백테스트 후 <span class="yellow">순이익이 원래보다 올라가면 파라미터 개선 확인</span>
  </div>
  <div class="scroll-table">
  <table>
    <thead><tr>
      <th>원래 순위</th><th>카테고리</th><th>원래 파라미터</th><th>원래 순이익</th>
      <th>원래 승률</th><th>원래 PF</th><th></th>
      <th>RESCUE 세트</th><th>조정 파라미터</th><th>예상 결과</th><th>SL/TP 변동률</th>
    </tr></thead>
    <tbody>{rescue_rows}</tbody>
  </table>
  </div>

  <div class="info-box" style="margin-top:16px">
    <b style="color:#fbbf24">라운드2 실행 후 확인 방법:</b><br>
    1. Round2_SET/ 폴더의 RESCUE_*.set을 MT4 백테스트에 적용<br>
    2. 결과 HTM을 '결과 분석' 버튼으로 다시 파싱<br>
    3. RESCUE 세트의 순이익이 <span class="green">원래 하위 성적보다 높으면</span> → 파라미터 개선 성공<br>
    4. TOP과 RESCUE의 순이익 차이가 <span class="yellow">10% 이내</span>이면 → RESCUE 채택 고려
  </div>
</div>

<!-- TAB 3: ALL RANK -->
<div id="allrank" class="content">
  <div class="section-title">📋 라운드1 전체 랭킹 ({n}개)</div>
  <div class="info-box">
    <span class="green">GOOD</span> (상위 {good_n}개) &nbsp;|&nbsp;
    <span class="red">BAD</span> (하위 {bad_n}개) &nbsp;|&nbsp;
    MID (중간 {n-good_n-bad_n}개)
  </div>
  <details>
    <summary>▼ 전체 랭킹 테이블 펼치기 ({n}개)</summary>
    <div class="scroll-table">
    <table>
      <thead><tr>
        <th>순위</th><th>카테고리</th><th>SL</th><th>TP</th><th>Lot</th><th>TF</th>
        <th>순이익</th><th>승률</th><th>PF</th><th>거래수</th><th>판정</th>
      </tr></thead>
      <tbody>{all_rows}</tbody>
    </table>
    </div>
  </details>
</div>

<!-- TAB 4: GUIDE -->
<div id="guide" class="content">
  <div class="section-title">📖 라운드2 사용 가이드</div>
  <div class="info-box">
    <b style="color:#fbbf24">Step 1. SET 파일 확인</b><br>
    → <code style="color:#60a5fa">{r2_dir}</code><br>
    → TOP01~TOP20 (상위20), RESCUE01~RESCUE05 (하위5 개선테스트)<br><br>
    <b style="color:#fbbf24">Step 2. 백테스트 실행</b><br>
    → 25개 SET을 MT4 Strategy Tester에서 순차 실행<br>
    → 또는 SOLO AHK 자동화로 배치 실행<br><br>
    <b style="color:#fbbf24">Step 3. 결과 분석</b><br>
    → 완료된 HTM 폴더를 '🔍 결과 분석' 버튼으로 파싱<br>
    → RESCUE 세트가 원래 하위 성적보다 높으면 파라미터 개선 성공<br><br>
    <b style="color:#fbbf24">Step 4. 판정 기준</b><br>
    → <span class="green">ADOPT</span>: RESCUE 순이익 > 원래 하위 순이익 + 10%<br>
    → <span class="yellow">REVIEW</span>: 차이가 ±10% 이내<br>
    → <span class="red">RESTORE</span>: RESCUE 성적이 더 나쁨 → 원래 TOP 파라미터만 유지
  </div>
</div>

<script>
function showTab(id) {{
  document.querySelectorAll('.content').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>"""

        html_path = os.path.join(r2_dir, f"ROUND2_COMPARISON_{ea_name}.html")
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            subprocess.run(["start","",html_path],shell=True)
        except Exception as e:
            self._status.config(text=f"⚠️ HTML 저장 실패: {e}", fg="#f87171")

    def _rerun_good_only(self):
        """GOOD 판정 시나리오만 골라서 백테스트 재실행 (BAD 제외)"""
        if not hasattr(self, "_last_results") or not self._last_results:
            messagebox.showwarning("분석 먼저", "먼저 '🔍 결과 분석'을 실행하세요."); return

        results  = self._last_results
        n        = len(results)
        top_n    = max(3, int(n * 0.3))
        good_res = results[:top_n]

        if not good_res:
            messagebox.showinfo("없음", "GOOD 시나리오가 없습니다."); return

        # GOOD 결과에서 시나리오 파라미터 복원
        import re as _re
        good_scenarios = []
        tf_map_inv = {"M5":5,"M15":15,"M30":30,"H1":60,"H4":240}
        for r in good_res:
            sc = {
                "cat":  r.get("cat","GOOD"),
                "id":   len(good_scenarios)+1,
                "sl":   r.get("sl",500),
                "tp":   r.get("tp",80),
                "lot":  r.get("lot",0.10),
                "tf":   tf_map_inv.get(r.get("tf","M5"), 5),
                "note": f"GOOD재실행 원래순위{results.index(r)+1}",
            }
            good_scenarios.append(sc)

        ea_path = self._ea_path.get().strip()
        if not ea_path or not os.path.exists(ea_path):
            messagebox.showerror("EA 없음", "EA(.mq4) 파일을 선택하세요."); return

        paths = self._get_bt_paths()
        if not os.path.exists(paths["ahk"]):
            messagebox.showerror("AHK 없음",
                f"AHK 스크립트를 찾을 수 없습니다:\n{paths['ahk']}"); return
        if not os.path.exists(paths["ahk_exe"]):
            messagebox.showerror("AutoHotkey 없음",
                "AutoHotkey.exe를 찾을 수 없습니다."); return

        confirm = messagebox.askyesno(
            "GOOD만 재실행",
            f"BAD/MID {n - top_n}개 제외\n"
            f"GOOD {top_n}개만 백테스트 재실행합니다.\n\n"
            f"계속 진행하시겠습니까?"
        )
        if not confirm: return

        self._stop_bt = False
        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._status.config(text=f"▶ GOOD {top_n}개 재실행 중...", fg="#22c55e")
        threading.Thread(target=self._run_scenario_bt,
                         args=(good_scenarios, paths, ea_path), daemon=True).start()

    def _copy_result(self):
        txt = self._r2_text.get("1.0","end")
        self.clipboard_clear()
        self.clipboard_append(txt)
        self._status.config(text="📋 결과 복사됨")

    # ── R1~R10 파라미터 인사이트 엔진 ──────────────────────────
    def _gen_param_insight(self):
        """
        round_history.json (R1~R10 누적 데이터)를 분석하여
        파라미터별 수익 영향력, 최적 구간, GOOD/BAD 패턴을 추출하고
        HTML 인사이트 리포트를 생성한다.
        """
        path = self._hist_path if not callable(self._hist_path) else self._hist_path()
        if not os.path.exists(path):
            messagebox.showwarning("히스토리 없음",
                "round_history.json이 없습니다.\n"
                "먼저 각 라운드 결과를 '🔍 결과 분석'으로 저장하세요."); return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("로드 오류", str(e)); return

        if len(data) < 3:
            messagebox.showwarning("데이터 부족",
                f"현재 {len(data)}개 기록뿐입니다.\n"
                "최소 10개 이상 누적 후 분석하면 더 정확합니다."); return

        from collections import defaultdict
        import math

        # ── 1. 기본 집계 ─────────────────────────────────────────
        rounds    = sorted(set(d["round"] for d in data))
        total_ea  = len(data)
        profits   = [d["profit"] for d in data]
        good_data = [d for d in data if d.get("verdict") == "GOOD"]
        bad_data  = [d for d in data if d.get("verdict") == "BAD"]

        def safe_avg(lst): return sum(lst)/len(lst) if lst else 0
        def safe_std(lst):
            if len(lst) < 2: return 0
            m = safe_avg(lst)
            return math.sqrt(sum((x-m)**2 for x in lst)/(len(lst)-1))

        # ── 2. 파라미터 구간별 수익 분포 ─────────────────────────
        def bucket_analysis(records, key, buckets):
            """records를 key 값 기준으로 buckets 구간에 넣어 avg profit 계산"""
            result = []
            for lo, hi, label in buckets:
                sub = [r for r in records if lo <= r.get(key,0) < hi]
                if not sub:
                    result.append((label, 0, 0, 0)); continue
                ps = [r["profit"] for r in sub]
                result.append((label, safe_avg(ps), len(sub), safe_std(ps)))
            return result

        # SL 구간
        sl_buckets = [
            (0,   200,  "50~199"),
            (200, 350,  "200~349"),
            (350, 500,  "350~499"),
            (500, 650,  "500~649"),
            (650, 850,  "650~849"),
            (850, 1100, "850~1099"),
            (1100,9999, "1100+"),
        ]
        tp_buckets = [
            (0,   60,  "10~59"),
            (60,  90,  "60~89"),
            (90,  120, "90~119"),
            (120, 160, "120~159"),
            (160, 220, "160~219"),
            (220, 9999,"220+"),
        ]
        lot_buckets = [
            (0,     0.06, "0.01~0.05"),
            (0.06,  0.12, "0.06~0.11"),
            (0.12,  0.20, "0.12~0.19"),
            (0.20,  0.40, "0.20~0.39"),
            (0.40,  0.80, "0.40~0.79"),
            (0.80,  9.99, "0.80+"),
        ]

        sl_dist  = bucket_analysis(data, "sl",  sl_buckets)
        tp_dist  = bucket_analysis(data, "tp",  tp_buckets)
        lot_dist = bucket_analysis(data, "lot", lot_buckets)

        # TF별 분포
        tf_groups = defaultdict(list)
        for d in data: tf_groups[d.get("tf","?")].append(d["profit"])
        tf_dist = [(tf, safe_avg(ps), len(ps), safe_std(ps))
                   for tf, ps in sorted(tf_groups.items())]

        # 카테고리별 분포
        cat_groups = defaultdict(list)
        for d in data: cat_groups[d.get("cat","?")].append(d["profit"])
        cat_dist = sorted([(cat, safe_avg(ps), len(ps))
                           for cat, ps in cat_groups.items()],
                          key=lambda x: x[1], reverse=True)

        # ── 3. GOOD vs BAD 파라미터 차이 ─────────────────────────
        g_sl  = safe_avg([d["sl"]  for d in good_data]) if good_data else 0
        g_tp  = safe_avg([d["tp"]  for d in good_data]) if good_data else 0
        g_lot = safe_avg([d["lot"] for d in good_data]) if good_data else 0
        b_sl  = safe_avg([d["sl"]  for d in bad_data])  if bad_data  else 0
        b_tp  = safe_avg([d["tp"]  for d in bad_data])  if bad_data  else 0
        b_lot = safe_avg([d["lot"] for d in bad_data])  if bad_data  else 0

        from collections import Counter
        g_tf  = Counter(d.get("tf","?") for d in good_data).most_common(3)
        b_tf  = Counter(d.get("tf","?") for d in bad_data).most_common(3)
        g_cat = Counter(d.get("cat","?") for d in good_data).most_common(5)
        b_cat = Counter(d.get("cat","?") for d in bad_data).most_common(5)

        # ── 4. 라운드별 트렌드 ───────────────────────────────────
        round_stats = {}
        for rno in rounds:
            rs = [d for d in data if d["round"] == rno]
            ps = [d["profit"] for d in rs]
            round_stats[rno] = {
                "count":  len(rs),
                "avg":    safe_avg(ps),
                "max":    max(ps) if ps else 0,
                "min":    min(ps) if ps else 0,
                "good":   sum(1 for d in rs if d.get("verdict")=="GOOD"),
                "bad":    sum(1 for d in rs if d.get("verdict")=="BAD"),
                "best_sl": max(rs, key=lambda x: x["profit"])["sl"] if rs else 0,
                "best_tp": max(rs, key=lambda x: x["profit"])["tp"] if rs else 0,
                "best_tf": max(rs, key=lambda x: x["profit"]).get("tf","?") if rs else "?",
            }

        # ── 5. 파라미터 상관 점수 (단순 스피어만 근사) ───────────
        def rank_corr_approx(records, key):
            """key값과 profit의 단순 방향 상관 (양수=높을수록 좋음, 음수=낮을수록 좋음)"""
            pairs = [(r.get(key,0), r["profit"]) for r in records if r.get(key) is not None]
            if len(pairs) < 4: return 0.0
            pairs.sort(key=lambda x: x[0])
            n = len(pairs)
            lo_avg = safe_avg([p[1] for p in pairs[:n//3]])
            hi_avg = safe_avg([p[1] for p in pairs[n*2//3:]])
            rng = max(abs(lo_avg), abs(hi_avg), 1)
            return (hi_avg - lo_avg) / rng

        corr_sl  = rank_corr_approx(data, "sl")
        corr_tp  = rank_corr_approx(data, "tp")
        corr_lot = rank_corr_approx(data, "lot")

        # 최적 구간 (평균 수익 최고 bucket)
        best_sl_bucket  = max(sl_dist,  key=lambda x: x[1])
        best_tp_bucket  = max(tp_dist,  key=lambda x: x[1])
        best_lot_bucket = max(lot_dist, key=lambda x: x[1])
        best_tf_item    = max(tf_dist,  key=lambda x: x[1]) if tf_dist else ("?",0,0,0)

        # ── 6. HTML 생성 ─────────────────────────────────────────
        from datetime import datetime as _dt
        now = _dt.now().strftime("%Y-%m-%d %H:%M")

        def bar_html(val, max_val, color="#60a5fa", width=160):
            pct = max(0, min(100, (val / max_val * 100) if max_val else 0))
            return (f'<div style="display:inline-block;background:{color};'
                    f'height:12px;width:{int(pct*width/100)}px;'
                    f'border-radius:3px;vertical-align:middle"></div>'
                    f'<span style="margin-left:6px;color:#e2e8f0">'
                    f'{"+" if val>=0 else ""}{val:,.0f}</span>')

        def dist_rows(dist_list, color_pos="#4ade80", color_neg="#f87171"):
            max_abs = max(abs(r[1]) for r in dist_list) if dist_list else 1
            rows = ""
            for label, avg_p, cnt, std in dist_list:
                if cnt == 0:
                    rows += f'<tr><td>{label}</td><td colspan="3" style="color:#475569">데이터 없음</td></tr>'
                    continue
                clr = color_pos if avg_p >= 0 else color_neg
                rows += (f'<tr><td style="color:#94a3b8">{label}</td>'
                         f'<td>{bar_html(avg_p, max_abs if max_abs>0 else 1, clr)}</td>'
                         f'<td style="color:#64748b">{cnt}건</td>'
                         f'<td style="color:#475569">σ={std:,.0f}</td></tr>')
            return rows

        sl_rows  = dist_rows(sl_dist)
        tp_rows  = dist_rows(tp_dist)
        lot_rows = dist_rows(lot_dist)

        tf_rows = ""
        max_tf = max(abs(r[1]) for r in tf_dist) if tf_dist else 1
        for tf, avg_p, cnt, std in tf_dist:
            clr = "#4ade80" if avg_p >= 0 else "#f87171"
            tf_rows += (f'<tr><td style="color:#a78bfa;font-weight:700">{tf}</td>'
                        f'<td>{bar_html(avg_p, max_tf if max_tf>0 else 1, clr)}</td>'
                        f'<td style="color:#64748b">{cnt}건</td>'
                        f'<td style="color:#475569">σ={std:,.0f}</td></tr>')

        cat_rows = ""
        max_cat = max(abs(r[1]) for r in cat_dist) if cat_dist else 1
        for cat, avg_p, cnt in cat_dist:
            clr = "#4ade80" if avg_p >= 0 else "#f87171"
            cat_rows += (f'<tr><td style="color:#fbbf24">{cat}</td>'
                         f'<td>{bar_html(avg_p, max_cat if max_cat>0 else 1, clr)}</td>'
                         f'<td style="color:#64748b">{cnt}건</td></tr>')

        round_rows = ""
        for rno, rs in round_stats.items():
            clr = "#4ade80" if rs["avg"] >= 0 else "#f87171"
            round_rows += (
                f'<tr>'
                f'<td style="color:#60a5fa;font-weight:700">R{rno}</td>'
                f'<td style="color:#64748b">{rs["count"]}</td>'
                f'<td style="color:{clr}">${rs["avg"]:,.0f}</td>'
                f'<td style="color:#4ade80">${rs["max"]:,.0f}</td>'
                f'<td style="color:#f87171">${rs["min"]:,.0f}</td>'
                f'<td style="color:#4ade80">{rs["good"]}</td>'
                f'<td style="color:#f87171">{rs["bad"]}</td>'
                f'<td style="color:#94a3b8">SL={rs["best_sl"]} TP={rs["best_tp"]} {rs["best_tf"]}</td>'
                f'</tr>')

        def corr_badge(v):
            if v > 0.3:  return f'<span style="color:#4ade80;font-weight:700">↑ 높을수록 유리 (+{v:.2f})</span>'
            if v < -0.3: return f'<span style="color:#f87171;font-weight:700">↓ 낮을수록 유리 ({v:.2f})</span>'
            return f'<span style="color:#94a3b8">→ 영향 중립 ({v:.2f})</span>'

        # 최적 추천 섹션
        opt_sl  = best_sl_bucket[0]
        opt_tp  = best_tp_bucket[0]
        opt_lot = best_lot_bucket[0]
        opt_tf  = best_tf_item[0]

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>R1~R10 파라미터 인사이트 리포트</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f172a;color:#e2e8f0;font-family:'Malgun Gothic',Consolas,sans-serif;font-size:13px;line-height:1.6}}
.hdr{{background:linear-gradient(135deg,#4c1d95,#1e3a8a);padding:22px 30px}}
.hdr h1{{font-size:24px;font-weight:700;color:#fff}}
.hdr .sub{{color:#c4b5fd;margin-top:6px;font-size:13px}}
.tabs{{display:flex;background:#1e293b;border-bottom:2px solid #334155;flex-wrap:wrap}}
.tab{{padding:10px 20px;cursor:pointer;color:#94a3b8;font-weight:600;border-bottom:3px solid transparent;transition:.2s;font-size:13px}}
.tab.active,.tab:hover{{color:#a78bfa;border-bottom-color:#a78bfa}}
.content{{display:none;padding:22px 26px}}
.content.active{{display:block}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}}
.grid2{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:20px}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;text-align:center}}
.card .val{{font-size:24px;font-weight:700}}
.card .lbl{{font-size:11px;color:#64748b;margin-top:4px}}
.card.green .val{{color:#4ade80}}
.card.red   .val{{color:#f87171}}
.card.blue  .val{{color:#60a5fa}}
.card.purple .val{{color:#a78bfa}}
.card.yellow .val{{color:#fbbf24}}
.sec{{color:#fbbf24;font-size:15px;font-weight:700;margin:20px 0 10px;padding-left:10px;border-left:3px solid #fbbf24}}
.info{{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px 18px;margin-bottom:14px;line-height:1.9}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#0f172a;color:#64748b;padding:8px 10px;text-align:center;border-bottom:1px solid #334155;position:sticky;top:0;font-size:11px;text-transform:uppercase;letter-spacing:.5px}}
td{{padding:8px 10px;text-align:center;border-bottom:1px solid #1e293b}}
tr:hover td{{background:#1e293b}}
.scroll{{max-height:380px;overflow-y:auto;border:1px solid #334155;border-radius:6px}}
.opt-box{{background:linear-gradient(135deg,#1e1b4b,#0f172a);border:2px solid #6d28d9;border-radius:10px;padding:18px 22px;margin-bottom:16px}}
.opt-box h3{{color:#a78bfa;font-size:15px;margin-bottom:12px}}
.opt-row{{display:flex;align-items:center;gap:16px;margin-bottom:10px}}
.opt-key{{color:#94a3b8;width:80px;font-size:12px}}
.opt-val{{color:#fbbf24;font-size:20px;font-weight:700;width:120px}}
.opt-bar-wrap{{flex:1;background:#1e293b;height:10px;border-radius:5px;overflow:hidden}}
.opt-bar{{height:10px;background:linear-gradient(90deg,#7c3aed,#60a5fa);border-radius:5px}}
.opt-note{{color:#64748b;font-size:11px}}
.corr-row{{display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid #1e293b}}
.corr-key{{color:#e2e8f0;font-weight:700;width:60px}}
.corr-bar-wrap{{flex:1;height:8px;background:#1e293b;border-radius:4px;position:relative}}
.corr-bar-pos{{height:8px;background:#4ade80;border-radius:4px;position:absolute;left:50%}}
.corr-bar-neg{{height:8px;background:#f87171;border-radius:4px;position:absolute;right:50%}}
.warn{{background:#1c1917;border:1px solid #78350f;border-radius:8px;padding:12px 16px;color:#fcd34d;margin-top:12px;font-size:12px}}
.hl-green{{color:#4ade80;font-weight:700}}
.hl-red{{color:#f87171;font-weight:700}}
.hl-yellow{{color:#fbbf24;font-weight:700}}
.hl-blue{{color:#60a5fa;font-weight:700}}
.hl-purple{{color:#a78bfa;font-weight:700}}
</style>
</head>
<body>

<div class="hdr">
  <h1>🧬 R1~R10 파라미터 인사이트 리포트</h1>
  <div class="sub">
    누적 {total_ea}개 EA 기록 | {len(rounds)}개 라운드 (R{min(rounds)}~R{max(rounds)}) | 생성: {now}<br>
    <span style="color:#c4b5fd">집단 데이터로 파악한 수익/손실에 영향을 주는 핵심 변수 분석</span>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('summary')">🎯 핵심 인사이트</div>
  <div class="tab" onclick="showTab('sl')">📏 SL 분석</div>
  <div class="tab" onclick="showTab('tp')">🎯 TP 분석</div>
  <div class="tab" onclick="showTab('lot')">💰 Lot 분석</div>
  <div class="tab" onclick="showTab('tf')">⏱ TF / 카테고리</div>
  <div class="tab" onclick="showTab('rounds')">📊 라운드 트렌드</div>
  <div class="tab" onclick="showTab('goodbad')">✅ GOOD vs BAD</div>
</div>

<!-- ═══ TAB 1: SUMMARY ═══ -->
<div id="summary" class="content active">
  <div class="grid4">
    <div class="card blue"><div class="val">{len(rounds)}</div><div class="lbl">분석 라운드 수</div></div>
    <div class="card"><div class="val">{total_ea}</div><div class="lbl">총 EA 기록 수</div></div>
    <div class="card green"><div class="val">{len(good_data)}</div><div class="lbl">GOOD 판정 수</div></div>
    <div class="card red"><div class="val">{len(bad_data)}</div><div class="lbl">BAD 판정 수</div></div>
  </div>

  <div class="sec">🔬 파라미터 영향력 (높을수록 / 낮을수록 유리 판단)</div>
  <div class="info">
    <div class="corr-row">
      <span class="corr-key">SL</span>
      {corr_badge(corr_sl)}
      <span class="opt-note">&nbsp;| 최적 구간: <b class="hl-yellow">{opt_sl}</b> (평균 ${best_sl_bucket[1]:,.0f})</span>
    </div>
    <div class="corr-row">
      <span class="corr-key">TP</span>
      {corr_badge(corr_tp)}
      <span class="opt-note">&nbsp;| 최적 구간: <b class="hl-yellow">{opt_tp}</b> (평균 ${best_tp_bucket[1]:,.0f})</span>
    </div>
    <div class="corr-row">
      <span class="corr-key">Lot</span>
      {corr_badge(corr_lot)}
      <span class="opt-note">&nbsp;| 최적 구간: <b class="hl-yellow">{opt_lot}</b> (평균 ${best_lot_bucket[1]:,.0f})</span>
    </div>
    <div class="corr-row" style="border:none">
      <span class="corr-key">TF</span>
      <span style="color:#a78bfa;font-weight:700">최다 GOOD: {g_tf[0][0] if g_tf else '?'} ({g_tf[0][1] if g_tf else 0}건)</span>
      <span class="opt-note">&nbsp;| 최고 평균: <b class="hl-yellow">{opt_tf}</b> (평균 ${best_tf_item[1]:,.0f})</span>
    </div>
  </div>

  <div class="opt-box">
    <h3>🏆 집단 데이터 기반 최적 파라미터 추천</h3>
    <div class="opt-row">
      <span class="opt-key">SL 구간</span>
      <span class="opt-val">{opt_sl}</span>
      <div class="opt-bar-wrap"><div class="opt-bar" style="width:{min(100,max(10,int(best_sl_bucket[1]/max(abs(p) for p in profits)*100) if profits else 50))}%"></div></div>
      <span class="opt-note">평균 ${best_sl_bucket[1]:,.0f} | {best_sl_bucket[2]}건 샘플</span>
    </div>
    <div class="opt-row">
      <span class="opt-key">TP 구간</span>
      <span class="opt-val">{opt_tp}</span>
      <div class="opt-bar-wrap"><div class="opt-bar" style="width:{min(100,max(10,int(best_tp_bucket[1]/max(abs(p) for p in profits)*100) if profits else 50))}%"></div></div>
      <span class="opt-note">평균 ${best_tp_bucket[1]:,.0f} | {best_tp_bucket[2]}건 샘플</span>
    </div>
    <div class="opt-row">
      <span class="opt-key">Lot 구간</span>
      <span class="opt-val">{opt_lot}</span>
      <div class="opt-bar-wrap"><div class="opt-bar" style="width:{min(100,max(10,int(best_lot_bucket[1]/max(abs(p) for p in profits)*100) if profits else 50))}%"></div></div>
      <span class="opt-note">평균 ${best_lot_bucket[1]:,.0f} | {best_lot_bucket[2]}건 샘플</span>
    </div>
    <div class="opt-row" style="margin-bottom:0">
      <span class="opt-key">TF</span>
      <span class="opt-val" style="color:#a78bfa">{opt_tf}</span>
      <div class="opt-bar-wrap"><div class="opt-bar" style="width:{min(100,max(10,int(best_tf_item[1]/max(abs(p) for p in profits)*100) if profits else 50))}%"></div></div>
      <span class="opt-note">평균 ${best_tf_item[1]:,.0f} | {best_tf_item[2]}건 샘플</span>
    </div>
  </div>

  <div class="warn">
    ⚠️ 이 추천은 {total_ea}개 과거 백테스트 집단 통계 기반입니다.
    라운드가 많아질수록 정확도가 올라갑니다.
    현재 {len(rounds)}라운드 → 목표 10라운드 후 재분석하면 더 신뢰도가 높아집니다.
  </div>
</div>

<!-- ═══ TAB 2: SL ═══ -->
<div id="sl" class="content">
  <div class="sec">📏 SL(손절폭) 구간별 평균 수익</div>
  <div class="info">
    SL이 <b class="hl-yellow">{opt_sl}</b> 구간일 때 평균 수익 최고 (${best_sl_bucket[1]:,.0f}).<br>
    방향성: {corr_badge(corr_sl)}<br>
    <span style="color:#64748b;font-size:12px">
      * σ(표준편차)가 클수록 결과 편차가 크다 = 안정성 낮음<br>
      * σ가 작으면서 평균이 높은 구간이 가장 이상적
    </span>
  </div>
  <div class="scroll">
  <table>
    <thead><tr><th>SL 구간</th><th>평균 순이익</th><th>샘플 수</th><th>표준편차</th></tr></thead>
    <tbody>{sl_rows}</tbody>
  </table>
  </div>

  <div class="sec" style="margin-top:20px">GOOD vs BAD SL 평균</div>
  <div class="grid2">
    <div class="card green">
      <div class="val">{g_sl:.0f}</div>
      <div class="lbl">GOOD 평균 SL ({len(good_data)}건)</div>
    </div>
    <div class="card red">
      <div class="val">{b_sl:.0f}</div>
      <div class="lbl">BAD 평균 SL ({len(bad_data)}건)</div>
    </div>
  </div>
  {"<div class='warn'>⚠️ GOOD SL이 BAD SL보다 " + ("낮습니다 → 타이트한 손절이 유리한 패턴" if g_sl < b_sl else "높습니다 → 넓은 손절이 유리한 패턴") + "</div>" if good_data and bad_data else ""}
</div>

<!-- ═══ TAB 3: TP ═══ -->
<div id="tp" class="content">
  <div class="sec">🎯 TP(익절폭) 구간별 평균 수익</div>
  <div class="info">
    TP가 <b class="hl-yellow">{opt_tp}</b> 구간일 때 평균 수익 최고 (${best_tp_bucket[1]:,.0f}).<br>
    방향성: {corr_badge(corr_tp)}<br>
    <span style="color:#64748b;font-size:12px">R:R 비율 = TP/SL. 최적 SL {opt_sl} + 최적 TP {opt_tp} 조합이 집단 데이터 기준 최고 성과</span>
  </div>
  <div class="scroll">
  <table>
    <thead><tr><th>TP 구간</th><th>평균 순이익</th><th>샘플 수</th><th>표준편차</th></tr></thead>
    <tbody>{tp_rows}</tbody>
  </table>
  </div>
  <div class="grid2" style="margin-top:16px">
    <div class="card green"><div class="val">{g_tp:.0f}</div><div class="lbl">GOOD 평균 TP</div></div>
    <div class="card red"><div class="val">{b_tp:.0f}</div><div class="lbl">BAD 평균 TP</div></div>
  </div>
</div>

<!-- ═══ TAB 4: LOT ═══ -->
<div id="lot" class="content">
  <div class="sec">💰 Lot(거래량) 구간별 평균 수익</div>
  <div class="info">
    Lot이 <b class="hl-yellow">{opt_lot}</b> 구간일 때 평균 수익 최고 (${best_lot_bucket[1]:,.0f}).<br>
    방향성: {corr_badge(corr_lot)}<br>
    <span style="color:#64748b;font-size:12px">Lot이 커질수록 수익도 크지만 손실도 커짐. 최적 구간이 리스크 대비 기대값이 가장 높은 지점</span>
  </div>
  <div class="scroll">
  <table>
    <thead><tr><th>Lot 구간</th><th>평균 순이익</th><th>샘플 수</th><th>표준편차</th></tr></thead>
    <tbody>{lot_rows}</tbody>
  </table>
  </div>
  <div class="grid2" style="margin-top:16px">
    <div class="card green"><div class="val">{g_lot:.2f}</div><div class="lbl">GOOD 평균 Lot</div></div>
    <div class="card red"><div class="val">{b_lot:.2f}</div><div class="lbl">BAD 평균 Lot</div></div>
  </div>
</div>

<!-- ═══ TAB 5: TF / CAT ═══ -->
<div id="tf" class="content">
  <div class="grid2">
    <div>
      <div class="sec">⏱ TF(타임프레임)별 평균 수익</div>
      <div class="scroll">
      <table>
        <thead><tr><th>TF</th><th>평균 순이익</th><th>샘플 수</th><th>표준편차</th></tr></thead>
        <tbody>{tf_rows}</tbody>
      </table>
      </div>
      <div class="info" style="margin-top:12px">
        GOOD에서 많이 나온 TF: <b class="hl-purple">{", ".join(f"{t}({c}건)" for t,c in g_tf[:3])}</b><br>
        BAD에서 많이 나온 TF: <b class="hl-red">{", ".join(f"{t}({c}건)" for t,c in b_tf[:3])}</b>
      </div>
    </div>
    <div>
      <div class="sec">🏷 카테고리별 평균 수익</div>
      <div class="scroll">
      <table>
        <thead><tr><th>카테고리</th><th>평균 순이익</th><th>샘플 수</th></tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>
      </div>
      <div class="info" style="margin-top:12px">
        GOOD 상위 카테고리: <b class="hl-green">{", ".join(f"{c}({n}건)" for c,n in g_cat[:3])}</b><br>
        BAD 상위 카테고리: <b class="hl-red">{", ".join(f"{c}({n}건)" for c,n in b_cat[:3])}</b>
      </div>
    </div>
  </div>
</div>

<!-- ═══ TAB 6: ROUNDS ═══ -->
<div id="rounds" class="content">
  <div class="sec">📊 라운드별 성과 트렌드 (R1→R{max(rounds)})</div>
  <div class="info">
    라운드가 진행될수록 평균 수익이 <b class="hl-green">개선</b>되고 있다면 최적화가 올바른 방향입니다.<br>
    최고 평균 수익 라운드: <b class="hl-yellow">R{max(round_stats, key=lambda x: round_stats[x]["avg"])}</b>
    (${max(rs["avg"] for rs in round_stats.values()):,.0f})
  </div>
  <div class="scroll">
  <table>
    <thead><tr>
      <th>라운드</th><th>EA수</th><th>평균순이익</th><th>최고</th><th>최저</th>
      <th>GOOD수</th><th>BAD수</th><th>최고 파라미터</th>
    </tr></thead>
    <tbody>{round_rows}</tbody>
  </table>
  </div>

  <div class="sec" style="margin-top:20px">📈 라운드별 평균수익 트렌드 (텍스트 차트)</div>
  <div class="info" style="font-family:Consolas,monospace;font-size:12px">
    {"".join(
        f'R{rno}: {"█" * max(1, min(40, int(max(0, rs["avg"]) / max(1, max(rs2["avg"] for rs2 in round_stats.values())) * 40)))} ${rs["avg"]:,.0f}<br>'
        for rno, rs in round_stats.items()
    )}
  </div>
</div>

<!-- ═══ TAB 7: GOOD vs BAD ═══ -->
<div id="goodbad" class="content">
  <div class="sec">✅ GOOD vs BAD 파라미터 패턴 비교</div>
  <div class="grid3">
    <div class="card">
      <div class="val" style="color:#4ade80">{len(good_data)}</div>
      <div class="lbl">GOOD 총 건수</div>
    </div>
    <div class="card">
      <div class="val" style="color:#94a3b8">{total_ea - len(good_data) - len(bad_data)}</div>
      <div class="lbl">MID 총 건수</div>
    </div>
    <div class="card">
      <div class="val" style="color:#f87171">{len(bad_data)}</div>
      <div class="lbl">BAD 총 건수</div>
    </div>
  </div>

  <div class="grid3">
    <div class="info">
      <b class="hl-green">GOOD 평균 파라미터</b><br>
      SL: <b class="hl-yellow">{g_sl:.0f}</b><br>
      TP: <b class="hl-yellow">{g_tp:.0f}</b><br>
      Lot: <b class="hl-yellow">{g_lot:.3f}</b><br>
      TF: <b class="hl-purple">{g_tf[0][0] if g_tf else "?"}</b> ({g_tf[0][1] if g_tf else 0}건 최다)<br>
      카테고리: <b class="hl-green">{g_cat[0][0] if g_cat else "?"}</b>
    </div>
    <div class="info" style="border-color:#475569">
      <b style="color:#94a3b8">차이 (GOOD - BAD)</b><br>
      SL 차: <b class="hl-yellow">{g_sl-b_sl:+.0f}</b>
              {"(낮음 유리)" if g_sl < b_sl else "(높음 유리)"}<br>
      TP 차: <b class="hl-yellow">{g_tp-b_tp:+.0f}</b>
              {"(낮음 유리)" if g_tp < b_tp else "(높음 유리)"}<br>
      Lot 차: <b class="hl-yellow">{g_lot-b_lot:+.3f}</b>
               {"(낮음 유리)" if g_lot < b_lot else "(높음 유리)"}<br><br>
      <span style="color:#64748b;font-size:11px">집단 {total_ea}개 기반</span>
    </div>
    <div class="info" style="border-color:#7f1d1d">
      <b class="hl-red">BAD 평균 파라미터</b><br>
      SL: <b style="color:#f87171">{b_sl:.0f}</b><br>
      TP: <b style="color:#f87171">{b_tp:.0f}</b><br>
      Lot: <b style="color:#f87171">{b_lot:.3f}</b><br>
      TF: <b class="hl-purple">{b_tf[0][0] if b_tf else "?"}</b> ({b_tf[0][1] if b_tf else 0}건 최다)<br>
      카테고리: <b class="hl-red">{b_cat[0][0] if b_cat else "?"}</b>
    </div>
  </div>

  <div class="opt-box">
    <h3>💡 손실 줄이기 위한 피해야 할 구간</h3>
    <div class="info" style="background:transparent;border:none;padding:0">
      BAD에서 자주 나오는 파라미터 조합을 피하세요:<br>
      SL: <b class="hl-red">{b_sl:.0f}</b> 근처 (GOOD보다 {"높음" if b_sl > g_sl else "낮음"} → {"줄이기" if b_sl > g_sl else "높이기"} 방향)<br>
      TP: <b class="hl-red">{b_tp:.0f}</b> 근처 (GOOD보다 {"높음" if b_tp > g_tp else "낮음"} → {"줄이기" if b_tp > g_tp else "높이기"} 방향)<br>
      TF: <b class="hl-red">{b_tf[0][0] if b_tf else "?"}</b> 사용 시 BAD 빈도 높음<br>
      카테고리: <b class="hl-red">{b_cat[0][0] if b_cat else "?"}</b> 전략은 이 EA에 적합하지 않을 수 있음
    </div>
  </div>
</div>

<script>
function showTab(id) {{
  document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>"""

        # 저장 & 오픈
        out_dir   = self._ensure_out_dir()
        html_path = os.path.join(out_dir, "PARAM_INSIGHT_R1toR10.html")
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            subprocess.run(["start","",html_path], shell=True)
            self._status.config(text=f"🧬 파라미터 인사이트 리포트 생성 완료", fg="#a78bfa")
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))

    # ── Market Analysis ─────────────────────────────────────────
    # 배포형: MT4 history 동적 탐색 (HERE 기준 MT4 형제 폴더)
    MT4_HISTORY_DIRS = []
    _mt4_hist = _find_mt4_near_here()
    if _mt4_hist:
        _hd = os.path.join(_mt4_hist, "history")
        if os.path.isdir(_hd):
            MT4_HISTORY_DIRS.append(_hd)
            for _sub in os.listdir(_hd):
                _sp = os.path.join(_hd, _sub)
                if os.path.isdir(_sp):
                    MT4_HISTORY_DIRS.append(_sp)
    _MT4_TF_INFO = {
        'M5':  (5,   '5m',  5),
        'M15': (15,  '15m', 15),
        'M30': (30,  '30m', 30),
        'H1':  (60,  '1h',  60),
        'H4':  (240, '4h',  240),
        'D1':  (1440,'1d',  1440),
    }

    def _ma_log(self, text, tag="info"):
        """Market Analysis 텍스트박스에 로그 출력 (thread-safe)"""
        def _do():
            self._ma_text.config(state="normal")
            self._ma_text.insert("end", text, tag)
            self._ma_text.see("end")
            self._ma_text.config(state="disabled")
        self.after(0, _do)

    def _load_hst(self, symbol, tf_minutes=60):
        """MT4 로컬 HST 파일 파싱 → pandas DataFrame"""
        import struct as _st
        fname = f"{symbol.upper()}{tf_minutes}.hst"
        hst_path = None
        for d in self.MT4_HISTORY_DIRS:
            cand = os.path.join(d, fname)
            if os.path.exists(cand):
                hst_path = cand; break
        if not hst_path:
            return None
        try:
            with open(hst_path, 'rb') as f:
                raw = f.read()
            header_size = 148
            rec = raw[header_size:]
            for rec_size in (48, 60, 44):
                if len(rec) % rec_size == 0 and len(rec) >= rec_size:
                    ts_test = _st.unpack_from('<q', rec, 0)[0]
                    if 0 < ts_test < 2e9:
                        break
            else:
                return None
            n = len(rec) // rec_size
            rows = []
            for i in range(n):
                off = i * rec_size
                ts = _st.unpack_from('<q', rec, off)[0]
                o, h, l, c = _st.unpack_from('<dddd', rec, off + 8)
                rows.append((ts, o, h, l, c))
            if not rows:
                return None
            import pandas as pd
            df = pd.DataFrame(rows, columns=['ts','Open','High','Low','Close'])
            df.index = pd.to_datetime(df['ts'], unit='s')
            df = df.drop(columns=['ts'])
            return df
        except Exception as e:
            print(f"HST load error {fname}: {e}")
            return None

    def _download_price_data(self, symbol, start_date, end_date, interval='1h'):
        """MT4 HST 우선, 없으면 yfinance 폴백"""
        from datetime import datetime as _dt, timedelta as _td
        if isinstance(start_date, str): start_date = _dt.strptime(start_date, '%Y%m%d')
        if isinstance(end_date, str):   end_date   = _dt.strptime(end_date,   '%Y%m%d')
        tf_map = {'1m':1,'5m':5,'15m':15,'30m':30,'1h':60,'4h':240,'1d':1440}
        tf_min = tf_map.get(interval, 60)
        df_hst = self._load_hst(symbol, tf_min)
        if df_hst is not None and not df_hst.empty:
            mask = (df_hst.index >= start_date - _td(days=2)) & \
                   (df_hst.index <= end_date   + _td(days=2))
            sl = df_hst[mask]
            if not sl.empty:
                return sl.copy()
        try:
            import yfinance as yf
            sym_map = {'BTCUSD':'BTC-USD','ETHUSD':'ETH-USD','XAUUSD':'GC=F',
                       'EURUSD':'EURUSD=X','GBPUSD':'GBPUSD=X','USDJPY':'USDJPY=X'}
            yf_sym = sym_map.get(symbol.upper(), symbol)
            df = yf.download(yf_sym, start=start_date.strftime('%Y-%m-%d'),
                             end=(end_date + _td(days=1)).strftime('%Y-%m-%d'),
                             interval=interval, progress=False, auto_adjust=True)
            return df if df is not None and not df.empty else None
        except Exception:
            return None

    def _detect_tf_from_results(self):
        """_last_results에서 가장 많이 등장하는 TF 감지"""
        from collections import Counter
        results = getattr(self, '_last_results', [])
        tf_counter = Counter(r.get('tf','').upper().strip() for r in results
                             if r.get('tf','').upper().strip() in self._MT4_TF_INFO)
        if not tf_counter:
            return 60, '1h', 60, 'H1'
        best = tf_counter.most_common(1)[0][0]
        tf_min, interval, window = self._MT4_TF_INFO[best]
        return tf_min, interval, window, best

    def _run_direction_analysis(self):
        """EA 매매방향 vs 실제 시장방향 분석 (백그라운드)"""
        results = getattr(self, '_last_results', [])
        if not results:
            messagebox.showwarning("분석 먼저", "먼저 '🔍 결과 분석'을 실행하여 HTM을 로드하세요.")
            return

        self._ma_text.config(state="normal")
        self._ma_text.delete("1.0","end")
        self._ma_text.config(state="disabled")
        self._ma_log("🎯 EA 매매방향 vs 실제 시장방향 분석\n" + "="*60 + "\n\n", "header")

        tf_min, interval, window_min, tf_label = self._detect_tf_from_results()
        self._ma_log(f"📐 감지된 TF: {tf_label} ({tf_min}분봉, 매칭 윈도우 ±{window_min}분)\n\n", "info")
        self._ma_status.config(text=f"분석 중... TF={tf_label}")

        self._direction_results = {}

        def _analyze():
            try:
                from collections import defaultdict
                from datetime import timedelta as _td
                all_trades = defaultdict(list)
                for r in results:
                    sym = r.get('symbol','Unknown')
                    for t in r.get('trade_list', r.get('trades', [])):
                        if isinstance(t, dict) and 'date' in t:
                            all_trades[sym].append(t)

                if not any(all_trades.values()):
                    self._ma_log(
                        "⚠️ 트레이드 상세 데이터가 없습니다.\n"
                        "HTM 리포트에 거래내역 테이블이 포함된 파일이 필요합니다.\n\n"
                        "💡 MT4 Strategy Tester → Report (Full) 형식으로 저장하세요.\n", "warning")
                    self.after(0, lambda: self._ma_status.config(text="⚠️ 거래내역 없음"))
                    return

                direction_summary = {}
                for symbol, trades in all_trades.items():
                    if not trades: continue
                    self._ma_log(f"\n📊 {symbol} — {len(trades)}개 트레이드 분석 중...\n", "subheader")

                    from datetime import datetime as _dt
                    dates = [t['date'] for t in trades if isinstance(t.get('date'), _dt)]
                    if not dates: continue
                    start_str = min(dates).strftime('%Y%m%d')
                    end_str   = max(dates).strftime('%Y%m%d')

                    df = self._download_price_data(symbol, start_str, end_str, interval=interval)
                    if df is None or df.empty:
                        self._ma_log(f"  ✗ {symbol}: 시장 데이터 로드 실패\n", "loss")
                        continue

                    df = df.copy()
                    actual_gap = int((df.index[1]-df.index[0]).total_seconds()/60) if len(df)>1 else tf_min
                    self._ma_log(f"  시장데이터: {len(df)}봉 ({tf_label},{actual_gap}분봉) {start_str}~{end_str}\n","info")
                    df['market_dir'] = (df['Close'] > df['Close'].shift(1)).map({True:'up',False:'down'})

                    matched=0; mismatched=0; no_data=0
                    mismatch_details=[]
                    _window = _td(minutes=window_min)
                    _is_daily = (actual_gap >= 1440)

                    for t in trades:
                        trade_dt = t.get('date')
                        if not isinstance(trade_dt, _dt): no_data+=1; continue
                        if not _is_daily:
                            mask = (df.index >= trade_dt-_window) & (df.index <= trade_dt+_window)
                            row = df[mask]
                            if row.empty:
                                row = df[df.index.date == trade_dt.date()]
                        else:
                            row = df[df.index.date == trade_dt.date()]
                        if row.empty: no_data+=1; continue
                        market_dir = row.iloc[0]['market_dir']
                        ea_dir = t.get('direction','')
                        if (ea_dir=='buy') == (market_dir=='up'):
                            matched+=1
                        else:
                            mismatched+=1
                            if len(mismatch_details)<5:
                                mismatch_details.append(
                                    f"    {trade_dt.strftime('%Y-%m-%d %H:%M')} {ea_dir.upper()} "
                                    f"← 시장: {'↑UP' if market_dir=='up' else '↓DOWN'}")

                    total = matched+mismatched
                    if total==0:
                        self._ma_log(f"  ⚠️ {symbol}: 매칭 가능한 날짜 없음\n","warning"); continue

                    pct = matched/total*100
                    direction_summary[symbol] = pct
                    tag = 'profit' if pct>=55 else ('warning' if pct>=45 else 'loss')
                    self._ma_log(f"\n  ✅ 일치: {matched}건  ❌ 역방향: {mismatched}건  ⬜ 데이터없음: {no_data}건\n","info")
                    self._ma_log(f"  📈 시장방향 일치율: {pct:.1f}%\n", tag)
                    if pct < 50:
                        self._ma_log("  ⚠️ EA가 시장방향과 반대로 매매하는 경우 多 → 역추세 EA이거나 진입 로직 점검 필요\n","warning")
                    elif pct >= 60:
                        self._ma_log("  ✅ EA가 시장방향과 잘 일치합니다\n","profit")
                    if mismatch_details:
                        self._ma_log("\n  역방향 진입 샘플 (최대5건):\n","warning")
                        for d in mismatch_details:
                            self._ma_log(d+"\n","loss")

                self._ma_log("\n\n💡 일치율 60%↑: 추세추종 EA  |  일치율 40%↓: 역추세 EA  |  50%±: 혼합형\n","warning")
                self._ma_log("🔧 [EA 모듈 조정] 버튼으로 MQ4 파일의 추세필터 파라미터를 자동 조정할 수 있습니다.\n","info")
                self._direction_results = direction_summary
                self.after(0, lambda: self._ma_status.config(text=f"✅ 분석 완료 ({len(direction_summary)}개 심볼)"))
            except Exception as e:
                self._ma_log(f"\n❌ 분석 실패: {e}\n","loss")
                self.after(0, lambda: self._ma_status.config(text=f"❌ 오류: {e}"))

        threading.Thread(target=_analyze, daemon=True).start()

    def _apply_ea_module_adjust(self):
        """방향 분석 결과 기반 MQ4 파라미터 자동 조정"""
        import re as _re, shutil as _sh
        direction_results = getattr(self, '_direction_results', {})
        if not direction_results:
            messagebox.showwarning("EA 모듈 조정","먼저 [🎯 EA방향 vs 시장방향 분석]을 실행하세요.")
            return

        mq4_path = filedialog.askopenfilename(
            title="수정할 MQ4 파일 선택",
            filetypes=[("MQ4 files","*.mq4"),("All files","*.*")])
        if not mq4_path: return

        avg_pct = sum(direction_results.values()) / len(direction_results)

        try:
            raw = open(mq4_path,'rb').read()
            enc = 'utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8'
            text = raw.decode(enc, errors='replace')
        except Exception as e:
            messagebox.showerror("오류",f"파일 읽기 실패:\n{e}"); return

        changes = []
        modified = text

        if avg_pct < 45:
            patterns = [
                (r'(extern\s+bool\s+)(EnableTrendFilter\s*=\s*)true',  r'\g<1>\g<2>false'),
                (r'(extern\s+bool\s+)(UseTrendConfirm\s*=\s*)true',    r'\g<1>\g<2>false'),
                (r'(extern\s+bool\s+)(EnableAdvancedTrend\s*=\s*)true',r'\g<1>\g<2>false'),
                (r'(extern\s+bool\s+)(EnableBraidFilter\s*=\s*)true',  r'\g<1>\g<2>false'),
            ]
            msg_type="역추세 EA"; suggestion="추세필터 비활성화 적용"
        elif avg_pct > 60:
            patterns = [
                (r'(extern\s+bool\s+)(EnableTrendFilter\s*=\s*)false', r'\g<1>\g<2>true'),
                (r'(extern\s+bool\s+)(UseTrendConfirm\s*=\s*)false',   r'\g<1>\g<2>true'),
                (r'(extern\s+bool\s+)(EnableAdvancedTrend\s*=\s*)false',r'\g<1>\g<2>true'),
                (r'(extern\s+bool\s+)(UseBraidFilter\s*=\s*)false',    r'\g<1>\g<2>true'),
            ]
            msg_type="추세추종 EA"; suggestion="추세필터 활성화 적용"
        else:
            patterns = []
            msg_type="혼합형 EA"; suggestion="일치율 45~60% — 수동 검토 권장"
            changes = ["수정 없음 (혼합형 EA)"]

        for pat, repl in patterns:
            new_text = _re.sub(pat, repl, modified, flags=_re.IGNORECASE)
            if new_text != modified:
                m = _re.search(pat, modified, _re.IGNORECASE)
                if m: changes.append(m.group(0).strip())
                modified = new_text
        if patterns and not changes:
            changes.append("(추세필터 파라미터 미발견 — 수동 확인 필요)")

        changes_str = "\n".join(f"  • {c}" for c in changes)
        confirm = messagebox.askyesno("EA 모듈 조정 확인",
            f"분석 결과: {msg_type} (일치율 {avg_pct:.1f}%)\n\n"
            f"조정:\n{changes_str}\n\n적용: {suggestion}\n\n"
            f"백업 파일(.bak)을 생성하고 수정하시겠습니까?")
        if not confirm: return

        bak_path = mq4_path + ".bak"
        _sh.copy2(mq4_path, bak_path)

        if modified != text:
            with open(mq4_path,'wb') as f:
                f.write(modified.encode(enc, errors='replace'))

        self._ma_log(f"\n{'='*60}\n","header")
        self._ma_log(f"🔧 EA 모듈 조정: {os.path.basename(mq4_path)}\n","header")
        self._ma_log(f"  유형: {msg_type}  일치율: {avg_pct:.1f}%\n","info")
        self._ma_log(f"  백업: {bak_path}\n","info")
        for c in changes:
            self._ma_log(f"  {c}\n","profit" if "없음" not in c and "미발견" not in c else "warning")
        if modified == text:
            self._ma_log("  ⚠️ 내용 변경 없음 — 수동 확인 필요\n","warning")
        else:
            self._ma_log("  ✅ 저장 완료 — MetaEditor에서 재컴파일 필요\n","profit")

        # 수정 전 통계 수집
        results = getattr(self, '_last_results', [])
        valid = [r for r in results if r.get('total_trades',0)>0]
        if not valid: return
        before = {
            'net_profit': sum(r.get('profit',r.get('net_profit',0)) for r in valid)/len(valid),
            'win_rate':   sum(r.get('winrate',r.get('win_rate',0)) for r in valid)/len(valid),
            'profit_factor': sum(r.get('pf',r.get('profit_factor',1)) for r in valid)/len(valid),
            'total_trades': int(sum(r.get('trades',r.get('total_trades',0)) for r in valid)/len(valid)),
        }
        run_bt = messagebox.askyesno("실제 백테스트 비교",
            f"수정된 EA를 동일 조건으로 백테스트하여 수정 전/후 비교하시겠습니까?\n\n"
            f"(MetaEditor에서 먼저 재컴파일 후 실행)\n\n"
            f"수정 전: 순이익 ${before['net_profit']:,.0f}  승률 {before['win_rate']:.1f}%  PF {before['profit_factor']:.2f}")
        if run_bt:
            self._run_bt_compare_ma(mq4_path, bak_path, before, msg_type)

    def _run_bt_compare_ma(self, mq4_path, bak_path, before_stats, ea_type):
        """수정 전/후 백테스트 결과 폴더 선택 → 비교"""
        import shutil as _sh
        self._ma_log("\n⏳ 수정 후 백테스트 결과 폴더를 선택하세요...\n","warning")
        new_folder = filedialog.askdirectory(title="수정 후 백테스트 결과 폴더 선택 (HTM 파일 있는 폴더)")
        if not new_folder:
            self._ma_log("  비교 취소됨\n","warning"); return

        new_results = []
        for root_d, _, files in os.walk(new_folder):
            for fname in files:
                if fname.lower().endswith('.htm'):
                    r = self._parse_htm_simple(os.path.join(root_d, fname))
                    if r and r.get('total_trades',0)>0:
                        new_results.append(r)

        if not new_results:
            self._ma_log("  ⚠️ 유효한 백테스트 리포트를 찾지 못했습니다.\n","warning"); return

        valid = [r for r in new_results if r.get('total_trades',0)>0]
        after = {
            'net_profit': sum(r.get('profit',r.get('net_profit',0)) for r in valid)/len(valid),
            'win_rate':   sum(r.get('winrate',r.get('win_rate',0)) for r in valid)/len(valid),
            'profit_factor': sum(r.get('pf',r.get('profit_factor',1)) for r in valid)/len(valid),
            'total_trades': int(sum(r.get('trades',r.get('total_trades',0)) for r in valid)/len(valid)),
        }

        self._ma_log(f"\n{'='*60}\n","header")
        self._ma_log(f"📊 수정 전/후 비교 ({ea_type})\n","header")
        self._ma_log(f"  {'항목':15} {'수정 전':>12} {'수정 후':>12} {'변화':>10}\n","subheader")
        self._ma_log(f"  {'-'*52}\n","info")

        def _row(label, b, a, fmt):
            diff = a-b; sign='+' if diff>=0 else ''
            tag = 'profit' if diff>0 else ('loss' if diff<0 else 'info')
            self._ma_log(f"  {label:15} {b:{fmt}} {a:{fmt}} {sign}{diff:{fmt}}\n", tag)

        _row('순이익($)',    before_stats['net_profit'],    after['net_profit'],    '12,.0f')
        _row('승률(%)',      before_stats['win_rate'],      after['win_rate'],      '12.1f')
        _row('PF',          before_stats['profit_factor'], after['profit_factor'], '12.2f')
        _row('트레이드(건)', before_stats['total_trades'],  after['total_trades'],  '12.0f')

        improved = sum([after['net_profit']>before_stats['net_profit'],
                        after['win_rate']>before_stats['win_rate'],
                        after['profit_factor']>before_stats['profit_factor']])
        self._ma_log(f"\n  {'='*52}\n","info")
        if improved >= 2:
            self._ma_log(f"  ✅ 성능 향상 ({improved}/3 지표 개선) — 수정 버전 채택 권장\n","profit")
        elif improved == 0:
            self._ma_log(f"  ❌ 성능 저하 — 백업(.bak) 복원 권장\n  백업: {bak_path}\n","loss")
            if messagebox.askyesno("성능 저하 감지","수정 후 성능이 저하되었습니다.\n백업으로 복원하시겠습니까?"):
                _sh.copy2(bak_path, mq4_path)
                self._ma_log("  🔄 원본 복원 완료\n","warning")
        else:
            self._ma_log(f"  ➖ 부분 개선 ({improved}/3) — 상황에 따라 판단하세요\n","warning")

    def _parse_htm_simple(self, fpath):
        """백테스트 HTM에서 핵심 통계만 빠르게 파싱"""
        import re as _re
        try:
            raw = open(fpath,'rb').read()
            enc = 'utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'cp949'
            html = raw.decode(enc, errors='replace')
        except Exception:
            return None
        result = {'fname': os.path.basename(fpath), 'trades':[], 'total_trades':0}
        # Net profit
        m = _re.search(r'Net\s+[Pp]rofit[:\s<>td/]*?([-\d,\.]+)', html)
        if m: result['profit'] = float(m.group(1).replace(',',''))
        else:
            m2 = _re.search(r'<b>Net Profit:</b></td>\s*<td[^>]*>([-\d,\.]+)', html)
            if m2: result['profit'] = float(m2.group(1).replace(',',''))
        # Total trades
        m = _re.search(r'Total\s+[Tt]rades?[:\s<>td/]*?(\d+)', html)
        if m: result['total_trades'] = int(m.group(1)); result['trades_count'] = result['total_trades']
        # Win rate
        m = _re.search(r'Win\s+[Rr]ate?[:\s<>td/]*?([\d\.]+)', html)
        if not m: m = _re.search(r'Profit\s+[Tt]rades?.*?([\d\.]+)%', html)
        if m: result['winrate'] = float(m.group(1))
        else: result['winrate'] = 0.0
        # PF
        m = _re.search(r'Profit\s+[Ff]actor[:\s<>td/]*?([\d\.]+)', html)
        if m: result['pf'] = float(m.group(1))
        else: result['pf'] = 1.0
        result.setdefault('profit', 0.0)
        result['net_profit'] = result['profit']
        result['win_rate']   = result['winrate']
        result['profit_factor'] = result['pf']
        return result

    # ── 백테스트 실행 ──────────────────────────────────────────
    def _get_bt_paths(self):
        """SOLO 경로 구조 반환 — SOLO_*.ahk 자동 탐색 (버전무관)"""
        solo = self._solo_var.get().strip() or HERE
        ini  = os.path.join(solo, "configs", "current_config.ini")
        # ★ SOLO_*.ahk 버전무관 탐색 (11_0, 12_0, 1.4, 1.5 등 모두 지원)
        import glob as _g
        _ahk_cands = (
            _g.glob(os.path.join(solo, "SOLO_*.ahk")) +
            _g.glob(os.path.join(solo, "scripts", "SOLO_*.ahk"))
        )
        # 버전 번호 내림차순 (최신 버전 우선)
        _ahk_cands.sort(key=lambda p: os.path.basename(p), reverse=True)
        ahk = _ahk_cands[0] if _ahk_cands else os.path.join(solo, "SOLO_1.4.ahk")
        # 완료 플래그: configs\test_completed.flag
        flag    = os.path.join(solo, "configs", "test_completed.flag")
        ahk_exe = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
        if not os.path.exists(ahk_exe):
            ahk_exe = r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
        ea_path = ""; mt4_files = ""
        if os.path.exists(ini):
            cp = read_ini(ini)
            ea_path   = cp.get("folders", "ea_path",       fallback="").strip()
            mt4_files = cp.get("folders", "setfiles_path", fallback="").strip()
            if not mt4_files:
                tp = cp.get("folders", "terminal_path", fallback="").strip()
                if tp: mt4_files = os.path.join(tp, "MQL4", "Files")
            # ★ SOLO 저장폴더(html_save_path) → _out_dir 자동 동기화
            html_save = cp.get("folders", "html_save_path", fallback="").strip()
            if html_save and not self._out_dir.get().strip():
                self.after(0, lambda p=html_save: self._out_dir.set(p))
        if not ea_path or not os.path.isdir(ea_path):
            # 동적 탐색
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
                        if not os.path.isdir(d): continue
                        if os.path.exists(os.path.join(d, "terminal.exe")):
                            ea_path   = os.path.join(d, "MQL4", "Experts")
                            mt4_files = os.path.join(d, "MQL4", "Files")
                            break
                    if ea_path: break
                except Exception:
                    continue
        return {"solo": solo, "ini": ini, "ahk": ahk, "flag": flag,
                "ahk_exe": ahk_exe, "ea_path": ea_path, "mt4_files": mt4_files}

    def _sync_solo_paths(self):
        """SOLO_nc2.3 양방향 완전 동기화 (배포형 상대경로 기반).
        GUI → INI: 현재 GUI 설정을 INI에 기록 (SOLO_nc2.3이 읽을 수 있도록)
        INI → GUI: SOLO가 변경한 값을 GUI에 반영
        모든 경로는 HERE 기준 상대경로로 자동 변환 (폴더명 변경 대비)"""
        solo = self._solo_var.get().strip() or HERE
        ini  = os.path.join(solo, "configs", "current_config.ini")
        sys_json = os.path.join(solo, "configs", "system_paths.json")
        msg_parts = []

        # ── Phase 1: INI에서 읽기 (INI → GUI) ──
        html_save = ""
        ea_p      = ""
        terminal_p = ""
        cp = None
        if os.path.exists(ini):
            cp = read_ini(ini)
            html_save  = cp.get("folders", "html_save_path", fallback="").strip()
            ea_p       = cp.get("folders", "ea_path",        fallback="").strip()
            terminal_p = cp.get("folders", "terminal_path",  fallback="").strip()

        # system_paths.json 폴백
        if not html_save and os.path.exists(sys_json):
            try:
                sp = json.load(open(sys_json, encoding="utf-8"))
                html_save = sp.get("report_base", "").strip()
            except Exception:
                pass

        # 배포형 폴백: HERE 기준 상대 경로
        if not html_save:
            html_save = os.path.join(HERE, "Reports")
        if not ea_p:
            # MT4 형제 폴더 자동 탐색
            mt4d = self._find_mt4_dir() if hasattr(self, '_find_mt4_dir') else ""
            if mt4d:
                ea_p = os.path.join(mt4d, "MQL4", "Experts")
                terminal_p = mt4d

        # GUI에 적용
        if html_save:
            self._out_dir.set(html_save)
            if hasattr(self, '_htm_dir'):
                self._htm_dir.set(html_save)
            msg_parts.append(f"Reports={os.path.basename(html_save)}")
        if ea_p:
            msg_parts.append(f"EA={os.path.basename(ea_p)}")

        # ── Phase 2: GUI → INI 기록 (SOLO_nc2.3이 읽을 수 있도록) ──
        if cp is None:
            cp = read_ini(ini) if os.path.exists(ini) else __import__('configparser').RawConfigParser(strict=False)
        for sec in ("folders", "current_backtest", "test_date"):
            if not cp.has_section(sec):
                cp.add_section(sec)

        # 배포형: 모든 경로를 HERE 기준으로 작성
        cp.set("folders", "html_save_path", html_save)
        cp.set("folders", "work_folder", HERE)
        if ea_p:
            cp.set("folders", "ea_path", ea_p)
        if terminal_p:
            cp.set("folders", "terminal_path", terminal_p)
            mt4_files = os.path.join(terminal_p, "MQL4", "Files")
            cp.set("folders", "setfiles_path", mt4_files)

        # GUI에서 설정된 심볼/TF/날짜가 있으면 INI에도 기록
        for attr, sec, key in [
            ("_sym_var",  "current_backtest", "symbol"),
            ("_tf_var",   "current_backtest", "period"),
            ("_from_var", "test_date",        "from_date"),
            ("_to_var",   "test_date",        "to_date"),
        ]:
            val = getattr(self, attr, None)
            if val:
                v = val.get().strip() if hasattr(val, 'get') else str(val)
                if v:
                    cp.set(sec, key, v)

        # INI 저장 (UTF-8 BOM — AHK 호환)
        try:
            write_ini(cp, ini)
            msg_parts.append("INI 저장 OK")
        except Exception as e:
            msg_parts.append(f"INI 저장 실패: {e}")

        self._status.config(
            text="SOLO 동기화 완료: " + " | ".join(msg_parts) if msg_parts else "SOLO 동기화 완료",
            fg="#22c55e"
        )

    def _start_bt_run(self):
        """선택된 시나리오에 대해 백테스트 순차 실행 (별도 스레드)"""
        # 체크된 시나리오 수집
        selected = [sc for iid, sc in zip(self._chk_vars, self._scenarios)
                    if self._chk_vars.get(iid, tk.BooleanVar()).get()]
        # 체크 없으면 트리에서 선택된 항목으로 폴백
        if not selected:
            sel_iids = self._tree.selection()
            if not sel_iids:
                messagebox.showwarning("선택 없음", "실행할 시나리오를 체크하거나 선택하세요.")
                return
            iid_to_sc = {f"{sc['cat']}_{sc['id']}": sc for sc in self._scenarios}
            selected = [iid_to_sc[iid] for iid in sel_iids if iid in iid_to_sc]

        # selected 가 비어있으면 경고 후 중단
        if not selected:
            messagebox.showwarning("시나리오 없음", "실행할 시나리오를 체크(☑)하거나 선택하세요.")
            return

        # ★v4.0: 폴더 모드 (여러 EA) vs 단일 파일 모드
        if self._ea_folder_paths:
            ea_list = [p for p in self._ea_folder_paths if os.path.exists(p)]
            if not ea_list:
                messagebox.showerror("EA 없음", "선택한 폴더의 .mq4 파일을 찾을 수 없습니다."); return
            # 확인 팝업 (폴더 모드)
            names = "\n".join(os.path.basename(p) for p in ea_list)
            if not messagebox.askyesno("EA 폴더 모드 확인",
                f"📂 폴더 모드: {len(ea_list)}개 EA × {len(selected)}개 시나리오 실행\n\n{names}\n\n계속하시겠습니까?"):
                return
        else:
            ea_path = self._ea_path.get().strip()
            if not ea_path or not os.path.exists(ea_path):
                messagebox.showerror("EA 없음", "EA(.mq4) 파일을 선택하세요."); return
            ea_list = [ea_path]

        paths = self._get_bt_paths()
        if not os.path.exists(paths["ahk"]):
            messagebox.showerror("AHK 없음",
                f"AHK 스크립트를 찾을 수 없습니다:\n{paths['ahk']}\n\nSOLO 폴더를 확인하세요.")
            return
        if not os.path.exists(paths["ahk_exe"]):
            messagebox.showerror("AutoHotkey 없음",
                "AutoHotkey.exe를 찾을 수 없습니다.\nAutoHotkey를 설치하세요.")
            return

        self._stop_bt = False
        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        folder_info = f" ({len(ea_list)}개 EA)" if len(ea_list) > 1 else ""
        self._status.config(text=f"▶ 백테스트 실행 중...{folder_info}", fg="#22c55e")
        threading.Thread(target=self._run_folder_bt,
                         args=(selected, paths, ea_list), daemon=True).start()

    def _stop_bt_run(self):
        self._stop_bt = True
        self._status.config(text="⏹ 중단 요청...", fg="#f87171")

    def _run_folder_bt(self, selected, paths, ea_list):
        """★v4.0: ea_list 의 모든 EA에 대해 순차적으로 _run_scenario_bt 호출"""
        total_ea = len(ea_list)
        success = 0
        log_path = os.path.join(HERE, "folder_run.log")
        results = []

        def log(msg):
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {msg}"
            try:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(line + "\n")
            except Exception:
                pass

        log(f"=== 폴더 실행 시작: {total_ea}개 EA, {len(selected)}개 시나리오 ===")
        for p in ea_list:
            log(f"  EA파일: {p}")

        for ea_idx, ea_path in enumerate(ea_list, 1):
            if self._stop_bt: break
            ea_name = os.path.splitext(os.path.basename(ea_path))[0]
            log(f"[{ea_idx}/{total_ea}] 시작: {ea_name}")
            self.after(0, lambda n=ea_name, i=ea_idx, t=total_ea:
                self._status.config(text=f"[EA {i}/{t}] {n} 처리 중...", fg="#ff6b35"))
            try:
                self._run_scenario_bt(selected, paths, ea_path)
                success += 1
                log(f"[{ea_idx}/{total_ea}] 완료: {ea_name}")
                results.append(f"✅ {ea_name}")
            except Exception as e:
                log(f"[{ea_idx}/{total_ea}] 에러: {ea_name} → {e}")
                results.append(f"❌ {ea_name}: {e}")
                self.after(0, lambda n=ea_name, e_=str(e):
                    self._status.config(text=f"⚠️ [{n}] 에러: {e_}", fg="#f87171"))
                time.sleep(0.5)  # 다음 EA 계속 진행

        log(f"=== 완료: {success}/{total_ea} 성공 ===")
        summary = "\n".join(results) if results else "(없음)"
        if not self._stop_bt:
            self.after(0, lambda s=success, t=total_ea, sm=summary: (
                self._status.config(text=f"✅ 폴더 완료 ({s}/{t}개 EA)", fg="#22c55e"),
                messagebox.showinfo("폴더 실행 완료",
                    f"총 {t}개 EA 중 {s}개 성공\n\n{sm}\n\n로그: {log_path}")
            ))
        self.after(0, lambda: (
            self._run_btn.config(state="normal"),
            self._stop_btn.config(state="disabled"),
        ))

    def _restart_mt4(self, paths):
        """MT4 종료 후 재시작 (새 .ex4 파일 인식)"""
        # 1) MT4 종료
        subprocess.run(
            ["taskkill", "/F", "/IM", "terminal.exe"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(3)

        # 2) terminal_path 탐색 (INI → ea_path 상위 폴더 순)
        terminal_path = ""
        ini = paths.get("ini", "")
        if os.path.exists(ini):
            cp = read_ini(ini)
            terminal_path = cp.get("folders", "terminal_path", fallback="").strip()

        if not terminal_path or not os.path.isdir(terminal_path):
            ea_p = paths.get("ea_path", "")
            if ea_p:
                p = ea_p
                for _ in range(5):
                    p = os.path.dirname(p)
                    if not p: break
                    if os.path.exists(os.path.join(p, "terminal.exe")):
                        terminal_path = p
                        break

        if not terminal_path or not os.path.isdir(terminal_path):
            self.after(0, lambda: self._status.config(
                text="⚠️ MT4 경로 없음 — 15초 후 계속", fg="#f87171"))
            time.sleep(15)
            return False

        # 3) MT4 재시작
        start_bat = os.path.join(terminal_path, "Start_Portable.bat")
        term_exe  = os.path.join(terminal_path, "terminal.exe")
        if os.path.exists(start_bat):
            subprocess.Popen(
                ["cmd", "/c", start_bat],
                cwd=terminal_path,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        elif os.path.exists(term_exe):
            subprocess.Popen(
                [term_exe, "/portable"],
                cwd=terminal_path
            )
        else:
            self.after(0, lambda: self._status.config(
                text="⚠️ terminal.exe 없음 — 수동 재시작 후 계속", fg="#f87171"))
            time.sleep(15)
            return False

        # 4) 로딩 대기 (20초 카운트다운)
        for i in range(20, 0, -1):
            if self._stop_bt: return False
            self.after(0, lambda t=i: self._status.config(
                text=f"[2/3] MT4 로딩 대기 ({t}초)...", fg="#f97316"))
            time.sleep(1)
        return True

    # ── ★v5.3: R1~R10 자동 실행 (5개 대간격 시나리오 × 10라운드) ──────────
    # 배포형: HERE 기준 StochRSI EA 자동 탐색
    _STOCH_EA = ""
    for _sd in (os.path.join(HERE, "13 ea v7 master 5.0", "output"),
                os.path.join(HERE, "output")):
        if os.path.isdir(_sd):
            for _root, _dirs, _files in os.walk(_sd):
                for _fn in _files:
                    if _fn.startswith("StochRSI") and _fn.endswith(".mq4"):
                        _STOCH_EA = os.path.join(_root, _fn); break
                if _STOCH_EA: break
        if _STOCH_EA: break

    def _start_r1_r10_auto(self):
        """★v5.3: 5개 대간격 시나리오 × R1~R10 자동 백테스트"""
        ea_path = self._ea_path.get().strip()
        if not ea_path or not os.path.exists(ea_path):
            if os.path.exists(self._STOCH_EA):
                self._ea_path.set(self._STOCH_EA)
                ea_path = self._STOCH_EA
            else:
                messagebox.showerror("EA 없음",
                    f"EA 파일을 선택하거나 아래 경로를 확인하세요:\n{self._STOCH_EA}")
                return

        paths = self._get_bt_paths()
        if not os.path.exists(paths["ahk"]):
            messagebox.showerror("AHK 없음", f"SOLO AHK 스크립트 없음:\n{paths['ahk']}"); return
        if not os.path.exists(paths["ahk_exe"]):
            messagebox.showerror("AutoHotkey 없음", "AutoHotkey.exe를 찾을 수 없습니다."); return

        if not messagebox.askyesno("R1~R10 자동 실행 확인",
            f"EA: {os.path.basename(ea_path)}\n\n"
            "5개 시나리오 × 10라운드 = 50회 실제 백테스트\n"
            "각 라운드마다 최적값으로 간격을 좁혀 수렴합니다.\n\n"
            "시작하시겠습니까?"):
            return

        self._stop_bt = False
        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._status.config(text="★ R1~R10 자동 실행 준비 중...", fg="#a855f7")
        threading.Thread(target=self._run_r1_r10_thread,
                         args=(ea_path, paths), daemon=True).start()

    def _run_r1_r10_thread(self, ea_path, paths):
        """R1~R10 루프: 5개 시나리오 → 백테스트 → 최적값 추출 → 간격 수렴"""
        import re as _re, glob as _glob

        # ── 기본 파라미터: 파일명에서 SL/TP/Lot 파싱 ──────────
        fname = os.path.basename(ea_path)
        sl_m   = _re.search(r'SL(\d+)', fname)
        tp_m   = _re.search(r'TP(\d+)', fname)
        lot_m  = _re.search(r'L([\d\.]+)', fname)
        base_sl  = int(sl_m.group(1))   if sl_m  else 544
        base_tp  = int(tp_m.group(1))   if tp_m  else 87
        base_lot = float(lot_m.group(1)) if lot_m else 0.15

        sl_gap = 150   # R1 대간격
        tp_gap = 30

        htm_dir = self._htm_dir.get().strip()

        for rno in range(1, 11):
            if self._stop_bt: break

            self.after(0, lambda r=rno, sg=sl_gap:
                self._status.config(
                    text=f"★ R{r}/10 — SL={base_sl} TP={base_tp} gap=±{sg}",
                    fg="#a855f7"))

            # ── 5개 시나리오 생성: 중심 ±2 step ──────────────
            scenarios = []
            for i in range(5):
                offset = i - 2   # -2, -1, 0, +1, +2
                sl = max(50,  base_sl + offset * sl_gap)
                tp = max(10,  base_tp + offset * tp_gap)
                scenarios.append({
                    "cat": "FULL_MIX", "id": i + 1,
                    "sl": sl, "tp": tp, "lot": base_lot, "tf": 5,
                    "note": f"R{rno}_auto_gap{sl_gap}",
                })

            # ── HTM 이전 목록 스냅샷 ─────────────────────────
            before = set(_glob.glob(os.path.join(htm_dir, "*.htm")) +
                         _glob.glob(os.path.join(htm_dir, "*.html")))

            # ── 5개 백테스트 실행 (기존 로직 재사용) ──────────
            self._run_scenario_bt(scenarios, paths, ea_path)

            if self._stop_bt: break

            # ── 새 HTM 파일 파싱 ─────────────────────────────
            after = set(_glob.glob(os.path.join(htm_dir, "*.htm")) +
                        _glob.glob(os.path.join(htm_dir, "*.html")))
            new_htms = after - before

            results = []
            for fp in new_htms:
                res = self._parse_htm_report(fp)
                if res is None: continue
                fn = os.path.basename(fp)
                sm = _re.search(r'SL(\d+)', fn);  tm = _re.search(r'TP(\d+)', fn)
                results.append({
                    "sl":     int(sm.group(1)) if sm else base_sl,
                    "tp":     int(tm.group(1)) if tm else base_tp,
                    "profit": res.get("profit", 0),
                    "winrate":res.get("winrate", 0),
                    "trades": res.get("trades", 0),
                })

            # ── 결과 없으면 중단 ──────────────────────────────
            if not results:
                self.after(0, lambda r=rno:
                    self._status.config(
                        text=f"⚠️ R{r}: HTM 결과 없음 — 중단",
                        fg="#f87171"))
                break

            results.sort(key=lambda x: x["profit"], reverse=True)
            best = results[0]
            base_sl = best["sl"]
            base_tp = best["tp"]

            # ── r2_text 로그 업데이트 ─────────────────────────
            log_line = (
                f"R{rno:02d}: {len(results)}개 완료  "
                f"BEST SL={base_sl} TP={base_tp}  "
                f"Profit={best['profit']:.1f}  WR={best['winrate']:.1f}%  "
                f"다음 gap=±{max(10, int(sl_gap*0.7))}\n"
            )
            def _upd_log(txt=log_line):
                self._r2_text.config(state="normal")
                self._r2_text.insert("end", txt)
                self._r2_text.see("end")
                self._r2_text.config(state="disabled")
            self.after(0, _upd_log)

            # ── 간격 수렴: 매 라운드 30% 축소 ───────────────
            sl_gap = max(10, int(sl_gap * 0.7))
            tp_gap = max(5,  int(tp_gap * 0.7))

        # ── 완료 처리 ─────────────────────────────────────────
        self.after(0, lambda: self._status.config(
            text="✅ R1~R10 자동 실행 완료", fg="#4ade80"))
        self.after(0, lambda: self._run_btn.config(state="normal"))
        self.after(0, lambda: self._stop_btn.config(state="disabled"))

    def _run_scenario_bt(self, selected, paths, ea_path):
        """선택 시나리오 순차 백테스트 (워커 스레드)
        Phase1: 전체 하드코딩+컴파일 → Phase2: MT4 재시작 → Phase3: 순차 백테스트
        """
        ea_name     = os.path.splitext(os.path.basename(ea_path))[0]
        default_sym = self._sym_var.get().strip()   # 기본 심볼 (sc에 symbol 없을 때 폴백)
        fr_date  = self._fr_var.get().strip()
        to_date  = self._to_var.get().strip()
        out_dir  = self._out_dir.get().strip()
        total    = len(selected)

        me_cands = find_me(1)
        me_exe = me_cands[0] if me_cands else ""

        # ── Phase 1: 전체 하드코딩 + 컴파일 ──────────────────────
        compiled = []  # (bt_ea_name, ea_folder, set_mt4, sc, tfl)

        # ★ 1개 공유 폴더 (모든 시나리오 EA를 같은 폴더에)
        ea_folder = os.path.join(out_dir, ea_name)
        os.makedirs(ea_folder, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        for idx, sc in enumerate(selected, 1):
            if self._stop_bt:
                self.after(0, lambda: self._status.config(text="⏹ 중단됨", fg="#f87171"))
                return

            # ★ 시나리오별 심볼 사용 (다중 심볼 선택 시 각 sc에 symbol 필드 있음)
            symbol = sc.get("symbol", default_sym)

            tfl        = self.TF_CODES.get(sc["tf"], str(sc["tf"]))
            sym_tag    = f"_{symbol}" if symbol != default_sym else ""
            bt_ea_name = f"{ea_name}_{sc['cat']}_{sc['id']:02d}_SL{sc['sl']}_TP{sc['tp']}_Lot{sc['lot']:.2f}_{tfl}{sym_tag}_R1"
            set_name   = f"{bt_ea_name}.set"
            set_params = {
                "SLFixedAmount": sc["sl"],
                "TPamount":      sc["tp"],
                "LotSize":       f"{sc['lot']:.2f}",
                "Period":        sc["tf"],
            }

            # .set 저장
            set_local = os.path.join(out_dir, set_name)
            lines = [f"{k}={v}||0||0" for k, v in set_params.items()]
            try:
                with open(set_local, "w", encoding="utf-8-sig") as f:
                    f.write("\n".join(lines) + "\n")
            except Exception as e:
                self.after(0, lambda e_=str(e): self._status.config(text=f"⚠️ set파일 저장실패: {e_}", fg="#f87171"))

            # MT4 Files 복사
            if paths["mt4_files"]:
                try:
                    os.makedirs(paths["mt4_files"], exist_ok=True)
                    set_mt4 = os.path.join(paths["mt4_files"], set_name)
                    with open(set_mt4, "w", encoding="utf-8-sig") as f:
                        f.write("\n".join(lines) + "\n")
                except Exception:
                    set_mt4 = set_local
            else:
                set_mt4 = set_local

            # 하드코딩 + 컴파일 (★ 공유 폴더에 모두 저장)
            if me_exe and os.path.exists(ea_path):
                try:
                    import re
                    content, enc = read_mq4(ea_path)
                    content = re.sub(r'((?:extern|input)\s+double\s+LotSize\s*=)\s*[\d\.]+;',       f'\\g<1> {sc["lot"]:.2f};', content, flags=re.MULTILINE)
                    content = re.sub(r'((?:extern|input)\s+double\s+TPamount\s*=)\s*[\d\.]+;',      f'\\g<1> {sc["tp"]:.1f};',  content, flags=re.MULTILINE)
                    content = re.sub(r'((?:extern|input)\s+double\s+SLFixedAmount\s*=)\s*[\d\.]+;', f'\\g<1> {sc["sl"]:.1f};',  content, flags=re.MULTILINE)
                    content = re.sub(r'((?:extern|input)\s+int\s+Period\s*=)\s*\d+;',               f'\\g<1> {sc["tf"]};',       content, flags=re.MULTILINE)
                    new_mq4 = os.path.join(ea_folder, bt_ea_name + ".mq4")
                    write_mq4(new_mq4, content)
                    self.after(0, lambda i=idx, t=total, n=bt_ea_name[:50]:
                        self._status.config(text=f"[1/3] 컴파일 ({i}/{t}): {n}", fg="#ff6b35"))
                    ok, msg = compile_one(me_exe, new_mq4, ea_folder)
                    if not ok:
                        self.after(0, lambda m=msg: self._status.config(text=f"⚠️ 컴파일 실패: {m}", fg="#f87171"))
                except Exception as e:
                    self.after(0, lambda e_=str(e): self._status.config(text=f"⚠️ 하드코딩 실패: {e_}", fg="#f87171"))

            compiled.append((bt_ea_name, ea_folder, set_mt4, sc, tfl))

        if not compiled or self._stop_bt:
            return

        # ── Phase 2: MT4 재시작 (새 .ex4 파일 인식) ─────────────
        self.after(0, lambda: self._status.config(text="[2/3] MT4 재시작 중...", fg="#f97316"))
        self._restart_mt4(paths)

        if self._stop_bt:
            return

        # ── Phase 3: 순차 백테스트 ────────────────────────────────
        for idx, (bt_ea_name, ea_folder, set_mt4, sc, tfl) in enumerate(compiled, 1):
            if self._stop_bt:
                self.after(0, lambda: self._status.config(text="⏹ 중단됨", fg="#f87171"))
                break

            bt_period = tfl
            # INI 업데이트 — ea_path는 공유 폴더, ea_name만 시나리오별로 교체
            cp = read_ini(paths["ini"]) if os.path.exists(paths["ini"]) else __import__("configparser").ConfigParser(strict=False)
            if not cp.has_section("folders"):          cp.add_section("folders")
            if not cp.has_section("current_backtest"): cp.add_section("current_backtest")
            if not cp.has_section("test_date"):        cp.add_section("test_date")
            cp.set("folders",          "ea_path",        ea_folder)
            cp.set("current_backtest", "ea_name",        bt_ea_name)
            cp.set("current_backtest", "symbol",         symbol)
            cp.set("current_backtest", "period",         bt_period)
            cp.set("current_backtest", "from_date",      fr_date)
            cp.set("current_backtest", "to_date",        to_date)
            cp.set("current_backtest", "set_file_path",  set_mt4)
            cp.set("current_backtest", "has_set",        "1")
            cp.set("test_date",        "enable",         "1")
            cp.set("test_date",        "from_date",      fr_date)
            cp.set("test_date",        "to_date",        to_date)
            os.makedirs(os.path.dirname(paths["ini"]), exist_ok=True)
            with open(paths["ini"], "w", encoding="utf-8-sig") as f:
                cp.write(f)
            ea_txt = os.path.join(os.path.dirname(paths["ini"]), "current_ea_name.txt")
            with open(ea_txt, "w", encoding="utf-8") as f:
                f.write(bt_ea_name + ".ex4\n")

            # AHK 실행 → 완료 플래그 대기
            flag = paths["flag"]
            if os.path.exists(flag): os.remove(flag)
            cmd = [paths["ahk_exe"], paths["ahk"], bt_ea_name, symbol, bt_period, str(idx)]
            status_txt = f"[3/3 {idx}/{total}] {sc['cat']}#{sc['id']} SL{sc['sl']} TP{sc['tp']} {tfl}"
            self.after(0, lambda t=status_txt: self._status.config(text=t, fg="#ff6b35"))
            proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            start = time.time()
            done = False
            while time.time() - start < 300:
                if self._stop_bt:
                    proc.terminate()
                    break
                if os.path.exists(flag):
                    try:
                        if open(flag, "r").read().strip() == "DONE":
                            done = True
                            break
                    except Exception:
                        pass
                time.sleep(2)
            if not done and not self._stop_bt:
                proc.terminate()
                self.after(0, lambda s=bt_ea_name: self._status.config(
                    text=f"⚠️ 타임아웃: {s}", fg="#f87171"))

        # 버튼 상태 복원은 _run_folder_bt 에서 처리


# ============================================================
# Tab 10 — 📈 라운드 히스토리 (성적표 + 그래프)
# ============================================================
