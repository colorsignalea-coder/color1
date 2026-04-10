"""
ui/tab_v7control.py — EA Auto Master v7.0
==========================================
V7 최적화 엔진 전용 제어 & 모니터링 탭.
- 현재 라운드/시나리오 실시간 표시
- TOP 결과 테이블
- 시작/중지 버튼
- g4_results/ 자동 로드
"""
import json
import os
import subprocess
import tkinter as tk
from tkinter import ttk

from core.config import HERE
from ui.theme import B, BG, PANEL, PANEL2, FG, ACCENT, MONO

_G4_DIR  = os.path.join(HERE, 'g4_results')
_CFG_DIR = os.path.join(HERE, 'configs')
_STATUS  = os.path.join(_CFG_DIR, 'status.json')


class V7ControlTab(ttk.Frame):
    C_G = "#22c55e"
    C_R = "#ef4444"
    C_Y = "#f59e0b"
    C_B = "#3b82f6"

    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self._running = True
        self._build()
        self._loop()

    # ── UI 빌드 ──────────────────────────────────────────────────

    def _build(self):
        self.configure(style="Dark.TFrame")

        # ① 헤더 상태 패널
        top = tk.LabelFrame(self, text=" V7 최적화 엔진 상태 ",
                            font=("Malgun Gothic", 9), bg=PANEL, fg="#94a3b8",
                            relief="groove", bd=1)
        top.pack(fill="x", padx=12, pady=(10, 4))

        row1 = tk.Frame(top, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=4)

        self._lbl_round  = tk.Label(row1, text="라운드: -",
                                    font=("Malgun Gothic", 11, "bold"),
                                    bg=PANEL, fg="#166534", width=14, anchor="w")
        self._lbl_round.pack(side="left")

        self._lbl_prog = tk.Label(row1, text="진행: -/-",
                                  font=("Malgun Gothic", 11, "bold"),
                                  bg=PANEL, fg="#92400e", width=14, anchor="w")
        self._lbl_prog.pack(side="left", padx=20)

        self._lbl_strat = tk.Label(row1, text="전략: -",
                                   font=("Malgun Gothic", 10),
                                   bg=PANEL, fg="#1e40af", anchor="w")
        self._lbl_strat.pack(side="left")

        self._pb = ttk.Progressbar(top, style="green.Horizontal.TProgressbar",
                                   mode="determinate", maximum=100)
        self._pb.pack(fill="x", padx=12, pady=(0, 4))

        self._lbl_ea = tk.Label(top, text="현재 EA: -",
                                font=("Consolas", 8),
                                bg=PANEL, fg="#7c3aed", anchor="w")
        self._lbl_ea.pack(fill="x", padx=12, pady=(0, 6))

        # ② 제어 버튼
        ctrl = tk.Frame(self, bg=BG)
        ctrl.pack(fill="x", padx=12, pady=4)
        B(ctrl, "▶ START ALL", self.C_G, self._start_all, padx=14).pack(side="left", padx=(0, 6))
        B(ctrl, "■ 중지",      self.C_R, self._stop,      padx=14).pack(side="left", padx=(0, 6))
        B(ctrl, "↻ 결과 새로고침", self.C_B, self._reload_results, padx=10).pack(side="left")

        # ③ TOP 결과 테이블
        res_frame = tk.LabelFrame(self, text=" 최적화 결과 TOP (전체 라운드) ",
                                  font=("Malgun Gothic", 9), bg=PANEL, fg="#94a3b8",
                                  relief="groove", bd=1)
        res_frame.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        cols = ("round", "sc", "score", "profit", "dd", "pf", "params")
        self._tree = ttk.Treeview(res_frame, columns=cols,
                                  show="headings", height=18)
        for col, w, anchor in [
            ("round",  55,  "center"),
            ("sc",     50,  "center"),
            ("score",  60,  "center"),
            ("profit", 100, "e"),
            ("dd",     60,  "center"),
            ("pf",     55,  "center"),
            ("params", 600, "w"),
        ]:
            self._tree.heading(col, text=col.upper())
            self._tree.column(col, width=w, anchor=anchor, stretch=(col == "params"))

        sb = ttk.Scrollbar(res_frame, orient="vertical",
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # 태그 색상 — PANEL2(#bae6fd 연한 파란 배경)에서 잘 보이는 진한 색상
        self._tree.tag_configure("S",    foreground="#7c2d12")   # 진한 주황 (최고점)
        self._tree.tag_configure("A",    foreground="#14532d")   # 진한 초록
        self._tree.tag_configure("B",    foreground="#1e3a8a")   # 진한 남색
        self._tree.tag_configure("C",    foreground="#374151")   # 진한 회색
        self._tree.tag_configure("D",    foreground="#6b7280")   # 중간 회색

    # ── 제어 버튼 핸들러 ────────────────────────────────────────

    def _start_all(self):
        bat = os.path.join(HERE, "START_ALL_v7.bat")
        if os.path.exists(bat):
            subprocess.Popen(["cmd", "/c", bat], cwd=HERE,
                             creationflags=subprocess.CREATE_NEW_CONSOLE)

    def _stop(self):
        stop_file = os.path.join(_CFG_DIR, "runner_stop.signal")
        with open(stop_file, "w") as f:
            f.write("stop")
        subprocess.run(["taskkill", "/F", "/IM", "terminal.exe"],
                       capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)

    def _reload_results(self):
        self._load_results()

    # ── 결과 로드 ───────────────────────────────────────────────

    def _load_results(self):
        if not os.path.exists(_G4_DIR):
            return
        all_results = []
        for fname in os.listdir(_G4_DIR):
            if not fname.endswith('.json'):
                continue
            try:
                with open(os.path.join(_G4_DIR, fname), encoding='utf-8') as f:
                    data = json.load(f)
                for r in data.get('results', []):
                    if r.get('score', 0) > 0:
                        all_results.append(r)
            except Exception:
                pass

        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)

        self._tree.delete(*self._tree.get_children())
        for r in all_results[:100]:
            sc    = r.get('sc_id', '?')
            rnd   = r.get('round', '?')
            score = r.get('score', 0)
            prof  = r.get('profit', 0)
            dd    = r.get('drawdown_pct', 0)
            pf    = r.get('profit_factor', 0)
            ea    = r.get('ea_name', '')

            grade = ('S' if score >= 85 else 'A' if score >= 70
                     else 'B' if score >= 55 else 'C' if score >= 40 else 'D')

            # 파라미터 요약 (파일명에서 추출)
            params = ea.replace('.ex4', '') if ea else '-'

            self._tree.insert('', 'end',
                values=(
                    f"R{rnd}", f"SC{sc:03d}" if isinstance(sc, int) else sc,
                    f"{score:.1f}[{grade}]",
                    f"${prof:,.0f}",
                    f"{dd:.1f}%",
                    f"{pf:.2f}",
                    params,
                ),
                tags=(grade,))

    # ── 실시간 상태 업데이트 ────────────────────────────────────

    def _update(self):
        try:
            if os.path.exists(_STATUS):
                with open(_STATUS, 'r', encoding='utf-8') as f:
                    st = json.load(f)

                rnd  = st.get('round', '-')
                cur  = st.get('current', 0)
                tot  = st.get('total', 0)
                ea   = st.get('ea', '-')
                msg  = st.get('message', '')
                strat = st.get('strategy', '-')

                self._lbl_round.config(text=f"라운드: R{rnd}")
                self._lbl_prog.config(
                    text=f"진행: {cur}/{tot}" if tot else "대기 중")
                self._lbl_strat.config(text=f"전략: {strat}")
                self._lbl_ea.config(text=f"EA: {ea[:80]}")

                if tot and cur:
                    self._pb['value'] = cur / tot * 100
                elif st.get('status') == 'completed':
                    self._pb['value'] = 100
        except Exception:
            pass

        self._load_results()

    def _loop(self):
        if not self._running:
            return
        try:
            self._update()
        except Exception:
            pass
        self.after(8000, self._loop)

    def destroy(self):
        self._running = False
        super().destroy()
