"""
ui/tab_monitor.py — EA Auto Master v7.0
=========================================
프로세스 실시간 감시 + 테스트 결과 실시간 표시 탭.
"""
import glob
import json
import os
import subprocess
import tkinter as tk
from tkinter import ttk

from core.config import HERE
from core.path_finder import find_me
from ui.theme import B

# 점수별 색상
def _score_color(score):
    if score >= 80:  return "#00ff9f"   # 초록 (탁월)
    if score >= 65:  return "#22d3ee"   # 청록 (양호)
    if score >= 50:  return "#fbbf24"   # 노랑 (보통)
    if score >= 30:  return "#f97316"   # 주황 (미흡)
    return "#ef4444"                    # 빨강 (불량)

def _profit_color(profit):
    if profit > 50000: return "#00ff9f"
    if profit > 10000: return "#4ade80"
    if profit > 0:     return "#a3e635"
    return "#ef4444"


class MonitorTab(ttk.Frame):
    C_G = "#22c55e"
    C_R = "#ef4444"
    C_Y = "#f59e0b"
    BG  = "#0d1117"
    PNL = "#161b22"
    PNL2= "#1c2128"

    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self._auto_mt4   = tk.BooleanVar(value=True)
        self._running    = True
        self._seen_rows  = set()       # 중복 방지
        self._result_rows= []          # 표시된 결과 행 정보
        self._build()
        self._loop()

    # ── 프로세스 탐지 유틸 ──

    @staticmethod
    def _wmic_cmdlines(proc_name):
        try:
            r = subprocess.run(
                f'wmic process where "name=\'{proc_name}\'" get commandline',
                shell=True, capture_output=True, timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW)
            return r.stdout.decode("utf-8", "replace").lower()
        except Exception:
            return ""

    @staticmethod
    def _proc_running(name):
        r = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}"],
            capture_output=True, timeout=4,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return name.lower() in r.stdout.decode("cp949", "replace").lower()

    def _is_backtest_running(self):
        out = self._wmic_cmdlines("python.exe")
        return ("run_r1_r10" in out or "run_r3_to_r10" in out
                or "ea_optimizer_v7" in out or "g4_round_optimizer" in out)

    def _is_solo_running(self):
        out = self._wmic_cmdlines("autohotkey.exe")
        return ("solo_v5.4" in out or "solo_v5.3" in out
                or "solo_1.5" in out or "solo_nc2.3" in out)

    # ── UI 구성 ──

    def _build(self):
        self.configure(style="Dark.TFrame")

        # ── 상단: 프로세스 LED + 현재 진행 ──────────────────────
        top = tk.LabelFrame(
            self, text=" 프로세스 실시간 감시 (v7.0) ",
            font=("Malgun Gothic", 9), bg=self.PNL, fg="#94a3b8",
            relief="groove", bd=1)
        top.pack(fill="x", padx=12, pady=(8, 3))

        led_row = tk.Frame(top, bg=self.PNL)
        led_row.pack(fill="x", padx=10, pady=4)
        self._leds = {}
        for key, lbl in [
            ("GUI",    "① EA MASTER GUI"),
            ("Engine", "② 백테스트 엔진"),
            ("MT4",    "③ MT4 터미널"),
            ("SOLO",   "④ SOLO AHK"),
        ]:
            col = tk.Frame(led_row, bg=self.PNL)
            col.pack(side="left", padx=14)
            led = tk.Label(col, text="●", font=("Arial", 18),
                           bg=self.PNL, fg=self.C_R, width=2)
            led.pack()
            tk.Label(col, text=lbl, font=("Malgun Gothic", 8),
                     bg=self.PNL, fg="#94a3b8").pack()
            self._leds[key] = led

        # 진행 상태 바
        prog_f = tk.Frame(top, bg=self.PNL); prog_f.pack(fill="x", padx=10, pady=(0, 6))
        self._lbl_ea = tk.Label(prog_f, text="대기 중", font=("Consolas", 9),
                                bg=self.PNL, fg="#f472b6", anchor="w")
        self._lbl_ea.pack(side="left", fill="x", expand=True)

        ctrl = tk.Frame(top, bg=self.PNL); ctrl.pack(fill="x", padx=10, pady=(0, 6))
        tk.Checkbutton(ctrl, text="MT4 자동 복구", variable=self._auto_mt4,
                       bg=self.PNL, fg="#e0e0e0", selectcolor=self.PNL2,
                       font=("Malgun Gothic", 8), activebackground=self.PNL).pack(side="left")
        B(ctrl, "MT4 시작", self.C_G, self._start_mt4, padx=8, pady=3).pack(side="right", padx=4)
        B(ctrl, "MT4 종료", self.C_R, self._kill_mt4,  padx=8, pady=3).pack(side="right")

        # ── 요약 스코어보드 ────────────────────────────────────
        score_f = tk.LabelFrame(
            self, text=" 📊 백테스트 결과 요약 (실시간) ",
            font=("Malgun Gothic", 9, "bold"), bg=self.PNL, fg="#7eb8ff",
            relief="groove", bd=1)
        score_f.pack(fill="x", padx=12, pady=3)

        self._stats_row = tk.Frame(score_f, bg=self.PNL)
        self._stats_row.pack(fill="x", padx=10, pady=6)
        self._stat_labels = {}
        for key, lbl, color in [
            ("total",   "완료",      "#7eb8ff"),
            ("score80", "Score≥80",  "#00ff9f"),
            ("score65", "Score≥65",  "#22d3ee"),
            ("avg_sc",  "평균Score", "#fbbf24"),
            ("avg_pf",  "평균 PF",   "#a78bfa"),
            ("best_ea", "최고 EA",   "#00ff9f"),
        ]:
            sf = tk.Frame(self._stats_row, bg=self.PNL)
            sf.pack(side="left", padx=12)
            tk.Label(sf, text=lbl, bg=self.PNL, fg="#6b7280",
                     font=("Malgun Gothic", 8)).pack()
            lv = tk.Label(sf, text="—", bg=self.PNL, fg=color,
                          font=("Malgun Gothic", 12, "bold"))
            lv.pack()
            self._stat_labels[key] = lv

        # ── 결과 테이블 ────────────────────────────────────────
        tbl_f = tk.LabelFrame(
            self, text=" 📋 테스트별 결과 (최신순, 색상=Score 등급) ",
            font=("Malgun Gothic", 9, "bold"), bg=self.PNL, fg="#7eb8ff",
            relief="groove", bd=1)
        tbl_f.pack(fill="both", expand=True, padx=12, pady=(3, 8))

        # 컬럼 헤더
        hdr = tk.Frame(tbl_f, bg="#1a2535")
        hdr.pack(fill="x", padx=2, pady=(4, 1))
        for text, w in [("EA명", 36), ("심볼", 8), ("TF", 4), ("Score", 7),
                         ("수익 ($)", 11), ("DD%", 6), ("PF", 5), ("거래수", 7), ("시간", 10)]:
            tk.Label(hdr, text=text, bg="#1a2535", fg="#7eb8ff",
                     font=("Malgun Gothic", 8, "bold"),
                     width=w, anchor="w").pack(side="left", padx=2)

        # 스크롤 가능한 결과 목록
        canvas_f = tk.Frame(tbl_f, bg=self.PNL)
        canvas_f.pack(fill="both", expand=True, padx=2)
        self._canvas = tk.Canvas(canvas_f, bg=self.PNL, highlightthickness=0)
        vsb = ttk.Scrollbar(canvas_f, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._result_frame = tk.Frame(self._canvas, bg=self.PNL)
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self._result_frame, anchor="nw")
        self._result_frame.bind("<Configure>", self._on_frame_resize)
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(
                              self._canvas_win, width=e.width))

    def _on_frame_resize(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _add_result_row(self, r):
        """결과 1행을 테이블에 추가 (컬러 코딩)"""
        key = f"{r.get('ea_name','')}{r.get('symbol','')}{r.get('tf','')}"
        if key in self._seen_rows: return
        self._seen_rows.add(key)

        score  = r.get('score', 0)
        profit = r.get('profit', 0)
        dd     = r.get('drawdown_pct', 0)
        pf     = r.get('profit_factor', 0)
        trades = r.get('trades', 0)
        ea_nm  = r.get('ea_name', '').replace('.ex4', '')[-35:]
        sym    = r.get('symbol', '')
        tf     = r.get('tf', '')
        ts     = r.get('timestamp', r.get('status', ''))[:16]

        s_color = _score_color(score)
        p_color = _profit_color(profit)
        row_bg  = "#0a1020" if len(self._seen_rows) % 2 == 0 else "#0d1525"

        row_f = tk.Frame(self._result_frame, bg=row_bg)
        row_f.pack(fill="x", padx=1, pady=1)

        # Score 강조 (왼쪽 컬러 바)
        tk.Frame(row_f, bg=s_color, width=4).pack(side="left")

        # 심볼 아이콘
        sym_icon = "₿" if "BTC" in sym else "🥇" if "XAU" in sym else sym
        sym_color = "#f97316" if "BTC" in sym else "#eab308"

        for text, w, color, anchor in [
            (ea_nm,           36, "#c8d8e8", "w"),
            (sym_icon,         8, sym_color,  "c"),
            (tf,               4, "#60a5fa", "c"),
            (f"{score:.1f}",   7, s_color,   "c"),
            (f"${profit:,.0f}",11, p_color,  "e"),
            (f"{dd:.1f}%",     6, "#f97316" if dd>20 else "#fbbf24", "c"),
            (f"{pf:.2f}",      5, "#a78bfa", "c"),
            (f"{trades}",      7, "#6b7280", "c"),
            (ts[-8:],         10, "#4b5563", "c"),
        ]:
            tk.Label(row_f, text=text, bg=row_bg, fg=color,
                     font=("Consolas", 8), width=w, anchor=anchor).pack(side="left", padx=1)

        self._result_rows.append(r)
        self._on_frame_resize(None)
        # 자동 스크롤 (항상 최신 표시)
        self._canvas.after(50, lambda: self._canvas.yview_moveto(1.0))

    def _update_stats(self):
        """통계 레이블 갱신"""
        if not self._result_rows: return
        scores = [r.get('score',0) for r in self._result_rows]
        profits= [r.get('profit',0) for r in self._result_rows]
        pfs    = [r.get('profit_factor',0) for r in self._result_rows]
        n = len(scores)
        avg_s  = sum(scores)/n if n else 0
        avg_pf = sum(pfs)/n    if n else 0
        best_r = max(self._result_rows, key=lambda x: x.get('score',0))
        self._stat_labels["total"].config(text=str(n))
        self._stat_labels["score80"].config(text=str(sum(1 for s in scores if s>=80)))
        self._stat_labels["score65"].config(text=str(sum(1 for s in scores if s>=65)))
        self._stat_labels["avg_sc"].config(text=f"{avg_s:.1f}")
        self._stat_labels["avg_pf"].config(text=f"{avg_pf:.2f}")
        ea_short = best_r.get('ea_name','').replace('.ex4','')
        ea_short = ea_short[-20:] if len(ea_short)>20 else ea_short
        self._stat_labels["best_ea"].config(text=f"{ea_short} ({best_r.get('score',0):.1f})")

    # ── MT4 제어 ──

    def _start_mt4(self):
        me_cands = find_me(1)
        if me_cands:
            mt4_dir = os.path.dirname(me_cands[0])
            bat = os.path.join(mt4_dir, "Start_Portable.bat")
            if os.path.exists(bat):
                subprocess.Popen(
                    ["cmd", "/c", bat], cwd=mt4_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                exe = os.path.join(mt4_dir, "terminal.exe")
                if os.path.exists(exe):
                    subprocess.Popen([exe, "/portable"], cwd=mt4_dir)

    def _kill_mt4(self):
        subprocess.run(
            ["taskkill", "/F", "/IM", "terminal.exe"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW)

    # ── 주기적 상태 업데이트 ──

    def _update(self):
        bt_on   = self._is_backtest_running()
        mt4_on  = self._proc_running("terminal.exe")
        solo_on = self._is_solo_running()

        self._leds["GUI"].config(fg=self.C_G)
        self._leds["Engine"].config(fg=self.C_G if bt_on else self.C_Y)
        self._leds["MT4"].config(fg=self.C_G if mt4_on else self.C_R)
        self._leds["SOLO"].config(fg=self.C_G if solo_on else self.C_Y)

        if bt_on and not mt4_on and self._auto_mt4.get():
            self._start_mt4()

        # ── 진행 상태 표시 ──
        try:
            st_f = os.path.join(HERE, "configs", "status.json")
            if os.path.exists(st_f):
                with open(st_f, "r", encoding="utf-8") as f:
                    st = json.load(f)
                cur = st.get("current", 0); tot = st.get("total", 0)
                ea  = st.get("ea", "")[-40:]
                rnd = st.get("round", "")
                pct = f" ({cur/tot*100:.0f}%)" if tot else ""
                progress = f"[R{rnd}] {cur}/{tot}{pct}  {ea}" if tot else st.get("message","")
                self._lbl_ea.config(text="▶ " + progress, fg="#f472b6")
            else:
                ea_f = os.path.join(HERE, "configs", "current_ea_name.txt")
                if os.path.exists(ea_f):
                    with open(ea_f, "r", encoding="utf-8") as f:
                        self._lbl_ea.config(text="▶ " + f.read().strip(), fg="#f472b6")
        except Exception:
            pass

        # ── 완료된 결과 파일 폴링 → 테이블 추가 ──
        try:
            results_dir = os.path.join(HERE, "g4_results")
            all_files   = sorted(glob.glob(os.path.join(results_dir, "*.json")))
            # BTC_GOLD 파일 (live 포함) + 일반 최근 5개
            btc_gold_files = [f for f in all_files if "BTC_GOLD" in os.path.basename(f)]
            recent_files   = [f for f in all_files if "BTC_GOLD" not in os.path.basename(f)][-5:]
            scan_files = recent_files + btc_gold_files
            for jf in scan_files:
                try:
                    with open(jf, encoding="utf-8") as f:
                        d = json.load(f)
                    results = d.get("results", [])
                    progress = d.get("progress", "")
                    for r in results:
                        r_copy = dict(r)
                        if 'timestamp' not in r_copy:
                            r_copy['timestamp'] = os.path.basename(jf)
                        if progress:
                            r_copy['_progress'] = progress
                        self._add_result_row(r_copy)
                except Exception:
                    pass
            # BTC_GOLD live 진행 상태 → 상단 레이블
            live_f = os.path.join(results_dir, "BTC_GOLD100_live.json")
            if os.path.exists(live_f):
                try:
                    with open(live_f, encoding="utf-8") as f:
                        ld = json.load(f)
                    prog = ld.get("progress", "")
                    if prog:
                        cur_text = self._lbl_ea.cget("text")
                        if "BTC+Gold" not in cur_text:
                            self._lbl_ea.config(
                                text=f"▶ BTC+Gold 배치 [{prog}] 진행중",
                                fg="#f472b6"
                            )
                except Exception:
                    pass
            self._update_stats()
        except Exception:
            pass

    def _loop(self):
        if not self._running:
            return
        try:
            self._update()
        except Exception:
            pass
        self.after(10000, self._loop)

    def destroy(self):
        self._running = False
        super().destroy()
