"""
ui/tab_run_control.py — EA Auto Master v8.1
============================================
실행제어 + 모니터 통합 탭 — LED 상태 + 실시간 stdout 로그.
v5.4 L8162-8499 추출.
"""
import glob as _g
import glob
import os
import re as _r
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core.config import HERE
from core.path_finder import find_me
from core.folder_queue import FolderQueue
from core.reset_engine import reset_all
from ui.theme import B


class RunControlTab(ttk.Frame):
    """실행제어 + 모니터 통합 탭 — LED 상태 + 실시간 stdout 로그"""

    C_G = "#16a34a"; C_R = "#dc2626"; C_Y = "#ca8a04"
    PNL = "#ffffff"; BG2 = "#f1f5f9"

    # V7 Optimizer 경로 (HERE 기반 동적 설정)
    G4_SOLO_DIR   = HERE
    G4_OPTIMIZER  = os.path.join(HERE, 'ea_optimizer_v7.py')
    G4_CONFIGS    = os.path.join(HERE, 'configs')
    G4_RESULTS    = os.path.join(HERE, 'g4_results')

    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self._proc         = None
        self._running      = True
        self._auto_mt4     = tk.BooleanVar(value=True)
        solo_dir = cfg.get("solo_dir", HERE)
        self._solo_log     = os.path.join(solo_dir, "scripts", "simple_loop_log.txt")
        self._solo_pos     = 0
        self._htm_folder   = ""
        self._htm_seen     = set()
        self._stats        = {"win": 0, "loss": 0, "total": 0, "profit": 0.0}
        # SOLO CATCHER 모니터링 상태
        self._status_ts    = ""   # 마지막으로 표시한 status.json timestamp
        self._live_mtime   = 0    # live_latest.json mtime
        self._fq           = FolderQueue()
        self._fq_proc      = None  # 폴더 큐 서브프로세스
        self._queue_start_time = None   # 큐 시작 시각 (경과시간 측정)

        # -- 신규: 파일 리스트 변수 --
        self._queue_vars     = {}   # {foldername: BooleanVar}
        self._queue_labels   = {}   # {foldername: Label}
        self._file_vars      = {}   # {filename: BooleanVar}
        self._file_labels    = {}   # {filename: Frame}
        self._last_sel_folder = ""   # 최근 클릭한 폴더명

        # 세션 저장/불러오기
        self._sessions_dir = os.path.join(HERE, 'configs', 'queue_sessions')
        os.makedirs(self._sessions_dir, exist_ok=True)
        # 라운드 컨트롤 변수
        self._rnd_sel      = tk.IntVar(value=1)
        self._rnd_end      = tk.IntVar(value=3)
        self._rnd_proc     = None
        self._rnd_stop_btn = None
        self._rnd_status   = None
        self._rnd_evo_tree = None
        self._build()
        self._load_htm_path()
        self._mon_loop()

    # -- UI 빌드 -------------------------------------------------
    def _build(self):
        self.configure(style="Dark.TFrame")

        _pv = tk.PanedWindow(self, orient="vertical", bg=self.BG2,
                             sashwidth=5, sashrelief="groove", sashpad=2)
        _pv.pack(fill="both", expand=True)

        # ── 상단 패널: 스크롤 가능한 Canvas 컨테이너 ──────────────
        _top_outer = tk.Frame(_pv, bg=self.BG2)
        _pv.add(_top_outer, height=560, minsize=200, sticky="nsew")

        _top_canvas = tk.Canvas(_top_outer, bg=self.BG2, highlightthickness=0)
        _top_vsb    = ttk.Scrollbar(_top_outer, orient="vertical",
                                    command=_top_canvas.yview)
        _top_canvas.configure(yscrollcommand=_top_vsb.set)
        _top_vsb.pack(side="right", fill="y")
        _top_canvas.pack(side="left", fill="both", expand=True)

        _top_pane = tk.Frame(_top_canvas, bg=self.BG2)
        _top_win  = _top_canvas.create_window((0, 0), window=_top_pane, anchor="nw")

        def _on_top_configure(e):
            _top_canvas.configure(scrollregion=_top_canvas.bbox("all"))
        def _on_top_canvas_resize(e):
            _top_canvas.itemconfig(_top_win, width=e.width)
        _top_pane.bind("<Configure>", _on_top_configure)
        _top_canvas.bind("<Configure>", _on_top_canvas_resize)

        # 마우스 휠 스크롤 (Windows)
        def _on_mousewheel(e):
            _top_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        _top_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        _bot_pane = tk.Frame(_pv, bg=self.BG2)
        _pv.add(_bot_pane, minsize=80, sticky="nsew")

        # 프로세스 상태 LED
        led_f = tk.LabelFrame(_top_pane, text="  프로세스 상태 (10초 갱신)",
                              font=("Malgun Gothic", 9), bg=self.PNL, fg="#94a3b8",
                              relief="groove", bd=1)
        led_f.pack(fill="x", padx=10, pady=(8, 4))

        self._leds = {}
        leds_row = tk.Frame(led_f, bg=self.PNL); leds_row.pack(fill="x", padx=10, pady=4)
        for key, lbl in [("GUI", "EA MASTER GUI"), ("Engine", "백테스트 엔진 (Python)"),
                          ("MT4", "MT4 (terminal.exe)"), ("SOLO", "SOLO 제어 (AHK)")]:
            col = tk.Frame(leds_row, bg=self.PNL); col.pack(side="left", padx=16)
            led = tk.Label(col, text="●", font=("Arial", 20), bg=self.PNL,
                           fg=self.C_R, width=2); led.pack()
            tk.Label(col, text=lbl, font=("Malgun Gothic", 8), bg=self.PNL,
                     fg="#94a3b8").pack()
            self._leds[key] = led

        info_row = tk.Frame(led_f, bg=self.PNL); info_row.pack(fill="x", padx=10, pady=(0, 6))
        self._lbl_status = tk.Label(info_row, text="대기 중", font=("Consolas", 9),
                                    bg=self.PNL, fg="#f472b6", anchor="w")
        self._lbl_status.pack(side="left", fill="x", expand=True)
        tk.Checkbutton(info_row, text="MT4 다운 시 자동 복구", variable=self._auto_mt4,
                       bg=self.PNL, fg="#e0e0e0", selectcolor=self.BG2,
                       font=("Malgun Gothic", 8), activebackground=self.PNL).pack(side="right", padx=6)
        B(info_row, "MT4 시작", self.C_G, self._start_mt4,
          pady=3, padx=8).pack(side="right", padx=4)
        B(info_row, "MT4 종료", self.C_R, self._kill_mt4,
          pady=3, padx=8).pack(side="right")
        B(info_row, "SOLO 시작", self.C_G, self._start_solo,
          pady=3, padx=8).pack(side="right", padx=4)
        B(info_row, "SOLO 종료", self.C_R, self._kill_solo,
          pady=3, padx=8).pack(side="right")

        # ── R1~R10 라운드 수동 컨트롤 패널 (LED 바로 아래 최상단) ──
        self._build_round_ctrl(_top_pane)

        # ── 폴더 큐 패널 ───────────────────────────────────────────
        queue_f = tk.LabelFrame(
            _top_pane,
            text="  폴더 큐 (READY_FOR_TEST/ 하위 폴더)  ─ 번호순 정렬",
            font=("Malgun Gothic", 9, "bold"), bg=self.PNL, fg="#a78bfa",
            relief="groove", bd=1
        )
        queue_f.pack(fill="x", padx=10, pady=(0, 4))

        # 좌우 분할 프레임 (폴더 리스트 | 파일 리스트)
        list_split_f = tk.Frame(queue_f, bg=self.PNL)
        list_split_f.pack(fill="x", padx=8, pady=(4, 2))

        # [좌측계] 폴더 목록
        fold_col = tk.Frame(list_split_f, bg=self.PNL)
        fold_col.pack(side="left", fill="both", expand=True)
        tk.Label(fold_col, text="📂 폴더 목록", font=("Malgun Gothic", 8, "bold"), bg=self.PNL, fg="#94a3b8").pack(anchor="w")

        self._chk_canvas = tk.Canvas(fold_col, bg="#ffffff", height=150, highlightthickness=1, highlightbackground="#e2e8f0")
        self._chk_canvas.pack(side="left", fill="both", expand=True)
        _ck_vsb = ttk.Scrollbar(fold_col, orient="vertical", command=self._chk_canvas.yview)
        _ck_vsb.pack(side="right", fill="y")
        self._chk_canvas.configure(yscrollcommand=_ck_vsb.set)

        self._chk_inner = tk.Frame(self._chk_canvas, bg="#ffffff")
        self._chk_win_id = self._chk_canvas.create_window((0, 0), window=self._chk_inner, anchor="nw")
        self._chk_inner.bind(
            "<Configure>",
            lambda e: self._chk_canvas.configure(
                scrollregion=self._chk_canvas.bbox("all")
            )
        )
        self._chk_canvas.bind(
            "<Configure>",
            lambda e: self._chk_canvas.itemconfig(self._chk_win_id, width=e.width)
        )

        # [우측계] 파일 목록
        file_col = tk.Frame(list_split_f, bg=self.PNL)
        file_col.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(file_col, text="📄 파일 목록 (폴더 클릭하여 로드)", font=("Malgun Gothic", 8, "bold"), bg=self.PNL, fg="#94a3b8").pack(anchor="w")

        self._file_canvas = tk.Canvas(file_col, bg="#ffffff", height=150, highlightthickness=1, highlightbackground="#e2e8f0")
        self._file_canvas.pack(side="left", fill="both", expand=True)
        _file_vsb = ttk.Scrollbar(file_col, orient="vertical", command=self._file_canvas.yview)
        _file_vsb.pack(side="right", fill="y")
        self._file_canvas.configure(yscrollcommand=_file_vsb.set)

        self._file_inner = tk.Frame(self._file_canvas, bg="#ffffff")
        self._file_win_id = self._file_canvas.create_window((0, 0), window=self._file_inner, anchor="nw")
        self._file_inner.bind(
            "<Configure>",
            lambda e: self._file_canvas.configure(
                scrollregion=self._file_canvas.bbox("all")
            )
        )
        self._file_canvas.bind(
            "<Configure>",
            lambda e: self._file_canvas.itemconfig(self._file_win_id, width=e.width)
        )

        # 버튼행 1: 폴더 제어
        ctrl_row1 = tk.Frame(queue_f, bg=self.PNL)
        ctrl_row1.pack(fill="x", padx=8, pady=(2, 1))
        tk.Label(ctrl_row1, text="[폴더]:", font=("Malgun Gothic", 8, "bold"), bg=self.PNL, fg="#a78bfa").pack(side="left", padx=(0, 4))
        B(ctrl_row1, "전체 선택", "#1e3a5f", self._queue_select_all,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 2))
        B(ctrl_row1, "전체 해제", "#374151", self._queue_deselect_all,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 8))
        B(ctrl_row1, "새로고침", "#1e3a5f", self._refresh_queue_list,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 8))
        B(ctrl_row1, "초기화", "#7f1d1d", self._reset_progress,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 4))
        B(ctrl_row1, "🗑 완전삭제", "#450a0a", self._delete_json_only,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 4))
        B(ctrl_row1, "🗑 폴더 삭제", "#7f1d1d", self._delete_selected_folders,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 8))
        B(ctrl_row1, "📁 찾기", "#0369a1", self._find_folders_manually,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 2))
        B(ctrl_row1, "🚀 큐 자동 검증", "#d97706", self._run_auto_test_setup,
          pady=2, padx=10, font=("Malgun Gothic", 8, "bold")).pack(side="left", padx=(0, 2))

        # 버튼행 2: 파일 제어 (N번째 선택 포함)
        ctrl_row_file = tk.Frame(queue_f, bg=self.PNL)
        ctrl_row_file.pack(fill="x", padx=8, pady=(1, 2))
        tk.Label(ctrl_row_file, text="[파일]:", font=("Malgun Gothic", 8, "bold"), bg=self.PNL, fg="#34d399").pack(side="left", padx=(0, 4))
        B(ctrl_row_file, "전체 선택", "#065f46", self._file_select_all,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 2))
        B(ctrl_row_file, "전체 해제", "#3c3c3c", self._file_deselect_all,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=(0, 10))

        tk.Label(ctrl_row_file, text="간격 선택:", font=("Malgun Gothic", 8), bg=self.PNL, fg="#a78bfa").pack(side="left", padx=(0, 4))
        B(ctrl_row_file, "전체", "#7c3aed", self._file_select_all,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="left", padx=1)
        for n in [5, 10, 20, 40, 50, 100]:
            B(ctrl_row_file, f"{n}번째", "#0ea5e9", lambda v=n: self._file_select_nth(v),
              pady=2, padx=6, font=("Malgun Gothic", 8)).pack(side="left", padx=1)
        B(ctrl_row_file, "📄 찾기", "#0e7490", self._find_files_manually,
          pady=2, padx=8, font=("Malgun Gothic", 8)).pack(side="right", padx=(0, 2))

        # 버튼행 2: 큐 시작 + 상태
        ctrl_row2 = tk.Frame(queue_f, bg=self.PNL)
        ctrl_row2.pack(fill="x", padx=8, pady=(1, 6))
        self.btn_queue = B(ctrl_row2, "▶  선택 폴더 큐 시작", "#7c3aed",
                           self._run_folder_queue,
                           font=("Malgun Gothic", 10, "bold"), pady=4, padx=16)
        self.btn_queue.pack(side="left")
        self._paused = False
        self._btn_pause = tk.Button(ctrl_row2, text="⏸ 일시정지",
                                    font=("Malgun Gothic", 9, "bold"),
                                    bg="#92400e", fg="white",
                                    relief="flat", bd=0, padx=10, pady=4,
                                    cursor="hand2",
                                    command=self._toggle_pause)
        self._btn_pause.pack(side="left", padx=(6, 0))
        self._lbl_queue_status = tk.Label(
            ctrl_row2, text="대기 중", bg=self.PNL, fg="#6b7280",
            font=("Malgun Gothic", 9)
        )
        self._lbl_queue_status.pack(side="left", padx=10)

        # (데이터 새로고침 호출부 하단으로 이동됨)

        # ── 세션 저장/불러오기 패널 ────────────────────────────────
        sess_f = tk.LabelFrame(
            _top_pane,
            text="  💾  작업 세션 저장 / 불러오기",
            font=("Malgun Gothic", 9, "bold"), bg=self.PNL, fg="#34d399",
            relief="groove", bd=1
        )
        sess_f.pack(fill="x", padx=10, pady=(0, 4))

        # 저장 행: 이름 입력 + 메모 + 저장 버튼
        save_row = tk.Frame(sess_f, bg=self.PNL)
        save_row.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(save_row, text="이름:", bg=self.PNL, fg="#94a3b8",
                 font=("Malgun Gothic", 9)).pack(side="left")
        self._sess_name = tk.Entry(
            save_row, width=20, bg="#1a2535", fg="#e2e8f0",
            insertbackground="white", font=("Consolas", 9),
            relief="flat", highlightthickness=1, highlightbackground="#2a3a4a"
        )
        self._sess_name.insert(0, time.strftime("세션_%m%d_%H%M"))
        self._sess_name.pack(side="left", padx=(4, 8))
        tk.Label(save_row, text="메모:", bg=self.PNL, fg="#94a3b8",
                 font=("Malgun Gothic", 9)).pack(side="left")
        self._sess_memo = tk.Entry(
            save_row, width=30, bg="#1a2535", fg="#e2e8f0",
            insertbackground="white", font=("Consolas", 9),
            relief="flat", highlightthickness=1, highlightbackground="#2a3a4a"
        )
        self._sess_memo.pack(side="left", padx=(4, 8))
        B(save_row, "💾 저장", "#065f46", self._save_session,
          pady=3, padx=10).pack(side="left")

        # 불러오기 행: 세션 목록 콤보 + 불러오기 + 삭제
        load_row = tk.Frame(sess_f, bg=self.PNL)
        load_row.pack(fill="x", padx=8, pady=(2, 6))
        tk.Label(load_row, text="저장 세션:", bg=self.PNL, fg="#94a3b8",
                 font=("Malgun Gothic", 9)).pack(side="left")
        self._sess_combo = ttk.Combobox(
            load_row, width=36, state="readonly",
            font=("Consolas", 9)
        )
        self._sess_combo.pack(side="left", padx=(4, 8))
        B(load_row, "📂 불러오기", "#1e3a5f", self._load_session,
          pady=3, padx=10).pack(side="left", padx=(0, 4))
        B(load_row, "🗑 삭제", "#7f1d1d", self._delete_session,
          pady=3, padx=10).pack(side="left")
        self._lbl_sess_info = tk.Label(
            load_row, text="", bg=self.PNL, fg="#6b7280",
            font=("Malgun Gothic", 8)
        )
        self._lbl_sess_info.pack(side="left", padx=8)
        self._sess_combo.bind("<<ComboboxSelected>>", self._on_session_select)
        # self._refresh_session_list() # (하단으로 이동됨)

        # 실행 버튼
        btn_f = tk.Frame(_top_pane, bg=self.BG2); btn_f.pack(fill="x", padx=10, pady=6)
        self.btn_all = B(btn_f, "전체 시작 (MT4+SOLO+OPT)", "#7c3aed",
                         self._start_all,
                         font=("Malgun Gothic", 12, "bold"), pady=12, padx=20)
        self.btn_all.pack(side="left", padx=(0, 8))
        self.btn_r1 = B(btn_f, "R1 단일 검증", "#1d4ed8",
                        lambda: self._run_master(True),
                        font=("Malgun Gothic", 11, "bold"), pady=12, padx=20)
        self.btn_r1.pack(side="left", padx=(0, 8))
        self.btn_run = B(btn_f, "R1~R10 전자동 루프", "#166534",
                         lambda: self._run_master(False),
                         font=("Malgun Gothic", 12, "bold"), pady=12, padx=28)
        self.btn_run.pack(side="left")
        B(btn_f, "전체 중지", "#7f1d1d", self._stop_all,
          pady=12, padx=16).pack(side="left", padx=8)
        B(btn_f, "로그 삭제", "#374151",
          lambda: (self.log.config(state="normal"),
                   self.log.delete("1.0", "end"),
                   self.log.config(state="disabled")),
          pady=12, padx=10).pack(side="right")

        # ── BTC+Gold 100 배치 패널 ──────────────────────────────
        batch_f = tk.LabelFrame(
            _top_pane,
            text="  🟠 BTC+Gold 100 배치 백테스트",
            font=("Malgun Gothic", 9, "bold"), bg=self.PNL, fg="#f97316",
            relief="groove", bd=1
        )
        batch_f.pack(fill="x", padx=10, pady=(0, 6))

        # 1행: 기간
        row1 = tk.Frame(batch_f, bg=self.PNL); row1.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(row1, text="기간 시작:", bg=self.PNL, fg="#94a3b8",
                 font=("Malgun Gothic", 9)).pack(side="left")
        self._btc_from = tk.Entry(row1, width=12, bg="#1a2535", fg="#e2e8f0",
                                  insertbackground="white", font=("Consolas", 9),
                                  relief="flat", highlightthickness=1,
                                  highlightbackground="#2a3a4a")
        self._btc_from.insert(0, "2025.04.01")
        self._btc_from.pack(side="left", padx=(4, 12))

        tk.Label(row1, text="종료:", bg=self.PNL, fg="#94a3b8",
                 font=("Malgun Gothic", 9)).pack(side="left")
        self._btc_to = tk.Entry(row1, width=12, bg="#1a2535", fg="#e2e8f0",
                                insertbackground="white", font=("Consolas", 9),
                                relief="flat", highlightthickness=1,
                                highlightbackground="#2a3a4a")
        self._btc_to.insert(0, "2026.04.01")
        self._btc_to.pack(side="left", padx=(4, 20))

        # 2행: 종목 + 주기
        row2 = tk.Frame(batch_f, bg=self.PNL); row2.pack(fill="x", padx=10, pady=2)
        tk.Label(row2, text="종목:", bg=self.PNL, fg="#94a3b8",
                 font=("Malgun Gothic", 9)).pack(side="left")
        self._sym_btc  = tk.BooleanVar(value=True)
        self._sym_xau  = tk.BooleanVar(value=True)
        for var, lbl, color in [(self._sym_btc, "BTCUSD", "#f97316"),
                                 (self._sym_xau, "XAUUSD", "#eab308")]:
            tk.Checkbutton(row2, text=lbl, variable=var,
                           bg=self.PNL, fg=color, selectcolor=self.BG2,
                           activebackground=self.PNL, activeforeground=color,
                           font=("Malgun Gothic", 9)).pack(side="left", padx=4)

        tk.Label(row2, text="  주기:", bg=self.PNL, fg="#94a3b8",
                 font=("Malgun Gothic", 9)).pack(side="left", padx=(10, 0))
        self._tf_m5  = tk.BooleanVar(value=True)
        self._tf_m15 = tk.BooleanVar(value=True)
        self._tf_m30 = tk.BooleanVar(value=True)
        for var, lbl in [(self._tf_m5, "M5"), (self._tf_m15, "M15"), (self._tf_m30, "M30")]:
            tk.Checkbutton(row2, text=lbl, variable=var,
                           bg=self.PNL, fg="#60a5fa", selectcolor=self.BG2,
                           activebackground=self.PNL, activeforeground="#60a5fa",
                           font=("Malgun Gothic", 9)).pack(side="left", padx=3)

        # 3행: 버튼
        row3 = tk.Frame(batch_f, bg=self.PNL); row3.pack(fill="x", padx=10, pady=(4, 8))
        self.btn_btc_batch = B(
            row3, "▶  BTC+Gold 100 배치 시작", "#c2410c",
            self._run_btc_gold_batch,
            font=("Malgun Gothic", 11, "bold"), pady=10, padx=24
        )
        self.btn_btc_batch.pack(side="left")
        self._lbl_batch_status = tk.Label(
            row3, text="대기 중", bg=self.PNL, fg="#6b7280",
            font=("Malgun Gothic", 9)
        )
        self._lbl_batch_status.pack(side="left", padx=12)

        # 실시간 로그
        log_f = tk.LabelFrame(_bot_pane, text="  실시간 로그",
                              font=("Malgun Gothic", 9), bg=self.PNL, fg="#94a3b8",
                              relief="groove", bd=1)
        log_f.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.log = tk.Text(log_f, bg="#0a0e14", fg="#e2e8f0",
                           font=("Consolas", 9), relief="flat",
                           state="disabled", wrap="word")
        vsb = ttk.Scrollbar(log_f, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=vsb.set)
        self.log.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=5)
        vsb.pack(side="right", fill="y", pady=5)

        self.log.tag_configure("ok",    foreground="#3fb950")
        self.log.tag_configure("err",   foreground="#f85149")
        self.log.tag_configure("warn",  foreground="#f59e0b")
        self.log.tag_configure("info",  foreground="#8b949e")
        self.log.tag_configure("ts",    foreground="#484f58")
        self.log.tag_configure("rpt",   foreground="#58a6ff")
        self.log.tag_configure("score", foreground="#d2a8ff")

        # ── 데이터 초기 로드 (창이 먼저 열린 뒤 비동기로 수행) ────────
        self.after(500, self._refresh_queue_list)
        self.after(600, self._refresh_session_list)

    # -- BTC+Gold 100 배치 실행 -----------------------------------
    def _run_btc_gold_batch(self):
        """BTC+Gold 100 배치 런처 실행 (run_btc_gold_100.py)"""
        script = os.path.join(self.G4_SOLO_DIR, 'run_btc_gold_100.py')
        if not os.path.exists(script):
            return messagebox.showerror("오류", f"배치 런처 없음:\n{script}")

        from_date = self._btc_from.get().strip() or "2025.04.01"
        to_date   = self._btc_to.get().strip()   or "2026.04.01"
        syms = []
        if self._sym_btc.get(): syms.append('BTCUSD')
        if self._sym_xau.get(): syms.append('XAUUSD')
        tfs  = []
        if self._tf_m5.get():  tfs.append('M5')
        if self._tf_m15.get(): tfs.append('M15')
        if self._tf_m30.get(): tfs.append('M30')
        if not syms or not tfs:
            return messagebox.showwarning("경고", "종목과 주기를 최소 1개 이상 선택하세요.")

        # run_btc_gold_100.py 파라미터 패치 (임시 env 변수 전달)
        import json as _json
        patch = {
            'from_date': from_date, 'to_date': to_date,
            'symbols': syms, 'timeframes': tfs
        }
        patch_path = os.path.join(self.G4_SOLO_DIR, 'configs', '_btc_batch_patch.json')
        os.makedirs(os.path.dirname(patch_path), exist_ok=True)
        with open(patch_path, 'w', encoding='utf-8') as f:
            _json.dump(patch, f)

        self.btn_btc_batch.config(state="disabled")
        self._lbl_batch_status.config(text=f"실행 중... ({from_date}~{to_date})", fg="#f97316")
        self._append(
            f"\n▶ BTC+Gold 100 배치 시작\n"
            f"  기간: {from_date} ~ {to_date}\n"
            f"  종목: {'+'.join(syms)}  주기: {'+'.join(tfs)}\n", "ok"
        )
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["BTC_BATCH_PATCH"]  = patch_path
        self._btc_proc = subprocess.Popen(
            [sys.executable, "-u", script],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=self.G4_SOLO_DIR, env=env
        )
        threading.Thread(target=self._stream_btc_batch, daemon=True).start()

    def _stream_btc_batch(self):
        try:
            for line in self._btc_proc.stdout:
                self.after(0, lambda l=line.rstrip(): self._append_line(l))
        except Exception:
            pass
        finally:
            self.after(0, lambda: self.btn_btc_batch.config(state="normal"))
            self.after(0, lambda: self._lbl_batch_status.config(
                text="완료", fg="#22c55e"))
            self.after(0, lambda: self._append("== BTC+Gold 배치 완료 ==\n", "ok"))

    # -- 실행 제어 -----------------------------------------------
    def _run_master(self, r1_only=False):
        # V7 Optimizer 사용
        script = self.G4_OPTIMIZER
        if not os.path.exists(script):
            return messagebox.showerror("오류", f"V7 옵티마이저 없음:\n{script}")
        self.btn_run.config(state="disabled")
        self.btn_r1.config(state="disabled")
        label = "1라운드 실행" if r1_only else "V7 전자동 루프"
        self._append(f"▶ {label} 시작 → ea_optimizer_v7.py\n", "ok")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        self._proc = subprocess.Popen(
            [sys.executable, "-u", script],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=self.G4_SOLO_DIR, env=env)
        threading.Thread(target=self._stream_log, daemon=True).start()

    def _stop_master(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._append("중단됨.\n", "warn")
        self.btn_run.config(state="normal")
        self.btn_r1.config(state="normal")

    def _stream_log(self):
        try:
            for line in self._proc.stdout:
                self.after(0, lambda l=line.rstrip(): self._append_line(l))
        except Exception:
            pass
        finally:
            self.after(0, lambda: self.btn_run.config(state="normal"))
            self.after(0, lambda: self.btn_r1.config(state="normal"))
            self.after(0, lambda: self._append("== 프로세스 종료 ==\n", "info"))

    def _append_line(self, line):
        if any(k in line for k in ["리포트", ".htm", "Reports", "report"]):
            tag = "rpt"
        elif any(k in line for k in ["점수", "수익", "$", "최고", "평균"]):
            tag = "score"
        elif any(k in line for k in ["완료", "성공", "OK", "DONE"]):
            tag = "ok"
        elif any(k in line for k in ["오류", "Error", "FAIL", "실패", "WARN"]):
            tag = "err"
        elif any(k in line for k in ["경고", "RETRY", "재시도"]):
            tag = "warn"
        else:
            tag = "info"
        self._append(line + "\n", tag)

    def _append(self, txt, tag="info"):
        """최신 로그가 항상 상단에 오도록 1.0 위치에 삽입."""
        if not hasattr(self, 'log') or self.log is None:
            return  # 빌드 중에는 로그 위젯이 아직 없으므로 무시
        ts = time.strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("1.0", txt, tag)
        self.log.insert("1.0", f"[{ts}] ", "ts")
        self.log.config(state="disabled")

    # -- 모니터 루프 (10초마다 LED 갱신) -------------------------
    @staticmethod
    def _proc_running(name):
        try:
            r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}"],
                               capture_output=True, timeout=4,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            return name.lower() in r.stdout.decode("cp949", "replace").lower()
        except Exception:
            return False

    @staticmethod
    def _cmdline_contains(proc, keyword):
        try:
            r = subprocess.run(
                f'wmic process where "name=\'{proc}\'" get commandline',
                shell=True, capture_output=True, timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW)
            return keyword.lower() in r.stdout.decode("utf-8", "replace").lower()
        except Exception:
            return False

    def _mon_loop(self):
        if not self._running:
            return
        try:
            # ea_optimizer_v7 또는 기존 g4 스크립트 감지
            bt_on   = (self._cmdline_contains("python.exe", "ea_optimizer_v7") or
                       self._cmdline_contains("python.exe", "g4_round_optimizer") or
                       self._cmdline_contains("python.exe", "run_r"))
            mt4_on  = self._proc_running("terminal.exe")
            solo_on = self._cmdline_contains("autohotkey.exe", "solo")
            # 내부 프로세스도 체크
            if self._proc and self._proc.poll() is None:
                bt_on = True
            self._leds["GUI"].config(fg=self.C_G)
            self._leds["Engine"].config(fg=self.C_G if bt_on else self.C_Y)
            self._leds["MT4"].config(fg=self.C_G if mt4_on else self.C_R)
            self._leds["SOLO"].config(fg=self.C_G if solo_on else self.C_Y)
            if bt_on and not mt4_on and self._auto_mt4.get():
                self._start_mt4()
            self._poll_solo_status()    # SOLO CATCHER 상태
            self._poll_live_results()   # G4 라운드 진행 현황
            self._tail_solo_log()
            self._scan_new_htms()
        except Exception:
            pass
        self.after(5000, self._mon_loop)   # 5초 갱신

    def _poll_solo_status(self):
        """V7 status.json 폴링 → 현재 진행 상황 표시."""
        status_f = os.path.join(self.G4_CONFIGS, "status.json")
        if not os.path.exists(status_f):
            return
        try:
            import json as _json
            with open(status_f, "r", encoding="utf-8", errors="replace") as f:
                d = _json.load(f)
            ts   = d.get("timestamp", "")
            ea   = d.get("ea", "")
            msg  = d.get("message", "")
            stat = d.get("status", "")
            rnd  = d.get("round", "")
            cur  = d.get("current", "")
            tot  = d.get("total", "")
            if ts != self._status_ts:
                self._status_ts = ts
                color = "ok" if stat in ("done", "completed") else ("warn" if stat == "busy" else "info")
                if ea:
                    label = f"R{rnd} [{cur}/{tot}] {ea}" if rnd else msg
                    self._append(f"[V7] {label}\n", color)
                    self._lbl_status.config(text=label[:80])
                elif msg:
                    self._append(f"[V7] {msg}\n", color)
        except Exception:
            pass

    def _poll_live_results(self):
        """V7 g4_results/*.json 폴링 → 최신 완료 라운드 TOP 결과 표시."""
        try:
            import json as _json
            result_files = sorted(
                glob.glob(os.path.join(self.G4_RESULTS, 'V7_R*.json')),
                key=os.path.getmtime)
            if not result_files:
                return
            latest = result_files[-1]
            mtime = os.path.getmtime(latest)
            if mtime <= self._live_mtime:
                return
            self._live_mtime = mtime
            with open(latest, "r", encoding="utf-8", errors="replace") as f:
                d = _json.load(f)
            rnd = d.get("round", "?")
            results = d.get("results", [])
            valid = [r for r in results if r.get("score", 0) > 0]
            if valid:
                top = max(valid, key=lambda x: x.get("score", 0))
                nm  = top.get("ea_name", "").replace(".ex4", "")[-35:]
                self._append(
                    f"[V7 R{rnd}] {len(results)}개 완료  "
                    f"TOP: {nm}  "
                    f"점수:{top.get('score',0):.1f}  "
                    f"${top.get('profit',0):,.0f}  "
                    f"DD:{top.get('drawdown_pct',0):.1f}%\n",
                    "score")
        except Exception:
            pass

    def _load_htm_path(self):
        try:
            import configparser as _cp
            ini = os.path.join(HERE, "configs", "current_config.ini")
            c = _cp.RawConfigParser()
            c.read(ini, encoding="utf-8-sig")
            if c.has_option("folders", "html_save_path"):
                p = c.get("folders", "html_save_path").strip()
                if os.path.isdir(p):
                    self._htm_folder = p
                    return
                parent = os.path.dirname(p)
                if os.path.isdir(parent):
                    self._htm_folder = parent
        except Exception:
            pass

    def _tail_solo_log(self):
        if not os.path.exists(self._solo_log):
            return
        try:
            with open(self._solo_log, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                size = f.tell()
                if size < self._solo_pos:
                    self._solo_pos = 0
                f.seek(self._solo_pos)
                new = f.read()
                self._solo_pos = f.tell()
            for line in new.splitlines():
                line = line.strip()
                if not line:
                    continue
                if any(k in line for k in ["[EA ", "[COMPLETED", "=== ", "[SKIP]", "[NO_TRADE"]):
                    self._append(f"[SOLO] {line}\n", "info")
                elif any(k in line for k in ["[WARN]", "Timed Out"]):
                    self._append(f"[SOLO] {line}\n", "warn")
        except Exception:
            pass

    def _scan_new_htms(self):
        if not self._htm_folder:
            self._load_htm_path()
        if not self._htm_folder:
            return
        try:
            htms = _g.glob(os.path.join(self._htm_folder, "**", "*.htm"), recursive=True)
            htms += _g.glob(os.path.join(self._htm_folder, "**", "*.HTM"), recursive=True)
        except Exception:
            return

        for path in sorted(htms, key=os.path.getmtime):
            fname = os.path.basename(path)
            if fname in self._htm_seen:
                continue
            self._htm_seen.add(fname)
            try:
                profit = self._parse_htm_profit(path)
                if profit is None:
                    continue
                self._stats["total"] += 1
                if profit > 0:
                    self._stats["win"] += 1
                    self._stats["profit"] += profit
                    icon = "OK"
                else:
                    self._stats["loss"] += 1
                    icon = "LOSS"
                s = self._stats
                self._append(
                    f"{icon} {fname[:50]}  ${profit:+,.2f}  "
                    f"[누계 W{s['win']}/L{s['loss']}  합계 ${s['profit']:+,.2f}]\n",
                    "ok" if profit > 0 else "err")
                self._lbl_status.config(
                    text=f"최근: {fname[:40]}  W{s['win']} L{s['loss']} 합계 ${s['profit']:+,.2f}")
            except Exception:
                pass

    def _parse_htm_profit(self, fpath):
        try:
            raw = open(fpath, "rb").read()
            if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
                html = raw.decode("utf-16", errors="replace")
            elif raw[:3] == b'\xef\xbb\xbf':
                html = raw.decode("utf-8", errors="replace")
            else:
                html = raw.decode("cp1252", errors="replace")
        except Exception:
            return None

        rows = _r.findall(r'<tr[^>]*>(.*?)</tr>', html, _r.I | _r.S)

        def row_vals(r):
            cells = _r.findall(r'<td[^>]*>(.*?)</td>', r, _r.I | _r.S)
            return [_r.sub(r'<[^>]+>', '', c).strip() for c in cells]

        state = 0
        for row in rows:
            vals = row_vals(row)
            if not vals:
                continue
            if state == 0:
                if '10000.00' in vals:
                    state = 1
            elif state == 1:
                if len(vals) >= 6 and _r.match(r'^-?[\d,]+\.\d+$', vals[1].replace(',', '')):
                    return float(vals[1].replace(',', ''))
        return None

    def _start_solo(self):
        ahk_paths = [
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
            r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe",
        ]
        ahk_exe = next((p for p in ahk_paths if os.path.exists(p)), None)
        solo_ahk = os.path.join(HERE, "SOLO_nc2.3.ahk")
        if not ahk_exe:
            self._append("[SOLO] AutoHotkey not found\n", "err"); return
        if not os.path.exists(solo_ahk):
            self._append(f"[SOLO] SOLO_nc2.3.ahk not found: {solo_ahk}\n", "err"); return
        subprocess.Popen([ahk_exe, solo_ahk], cwd=HERE)
        self._append(f"[SOLO] Started: {solo_ahk}\n", "ok")

    def _kill_solo(self):
        subprocess.run(["taskkill", "/F", "/IM", "AutoHotkey.exe", "/T"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self._append("[SOLO] Killed AutoHotkey\n", "warn")

    def _start_all(self):
        """MT4 → 10s → SOLO → 5s → Optimizer 순서로 전체 시작."""
        self._append("=== 전체 시작: MT4 + SOLO + Optimizer ===\n", "ok")
        self._kill_mt4()
        self._kill_solo()
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        # configs runner_stop.signal 삭제 (있으면 제거)
        sig = os.path.join(self.G4_CONFIGS, "runner_stop.signal")
        try:
            if os.path.exists(sig):
                os.remove(sig)
        except Exception:
            pass
        def _do_start():
            time.sleep(1)
            self.after(0, lambda: self._append("[1] MT4 시작...\n", "info"))
            self.after(0, self._start_mt4)
            time.sleep(10)
            self.after(0, lambda: self._append("[2] SOLO 시작...\n", "info"))
            self.after(0, self._start_solo)
            time.sleep(5)
            self.after(0, lambda: self._append("[3] Optimizer 시작...\n", "info"))
            self.after(0, lambda: self._run_master(False))
        threading.Thread(target=_do_start, daemon=True).start()

    def _stop_all(self):
        """Optimizer + SOLO + MT4 전체 중지."""
        self._stop_master()
        self._kill_solo()
        self._kill_mt4()
        subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self._append("=== 전체 중지 완료 ===\n", "warn")

    def _start_mt4(self):
        me = find_me(1)
        if me:
            mt4_dir = os.path.dirname(me[0])
            bat = os.path.join(mt4_dir, "Start_Portable.bat")
            if os.path.exists(bat):
                subprocess.Popen(["cmd", "/c", bat], cwd=mt4_dir,
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                exe = os.path.join(mt4_dir, "terminal.exe")
                if os.path.exists(exe):
                    subprocess.Popen([exe, "/portable"], cwd=mt4_dir)

    def _kill_mt4(self):
        subprocess.run(["taskkill", "/F", "/IM", "terminal.exe"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    # -- 폴더 큐 UI 메서드 -----------------------------------------------
    def _refresh_queue_list(self):
        """READY_FOR_TEST 폴더 스캔 → 체크박스 목록 갱신 (번호순)."""
        try:
            self._fq = FolderQueue()
            folders  = self._fq.scan_folders()
            done_set = set(self._fq._state.get('completed_folders', []))
            cur      = self._fq.get_current_folder()
            self._append(f"[QUEUE] 폴더 리스트 갱신 완료 ({len(folders)}개 발견)\n", "ok")

            for w in self._chk_inner.winfo_children():
                w.destroy()
            old_names = set(self._queue_vars.keys())
            new_names = {fd['name'] for fd in folders}
            for gone in old_names - new_names:
                del self._queue_vars[gone]
            self._queue_labels = {}

            if not folders:
                tk.Label(self._chk_inner,
                         text="  (READY_FOR_TEST/ 에 하위 폴더 없음)",
                         bg="#ffffff", fg="#94a3b8",
                         font=("Malgun Gothic", 9)).pack(anchor="w", pady=4)
                self._lbl_queue_status.config(text="폴더 없음", fg="#6b7280")
                return

            for idx, fd in enumerate(folders):
                name  = fd['name']
                count = fd['count']
                if name not in self._queue_vars:
                    self._queue_vars[name] = tk.BooleanVar(value=False)
                if name in done_set:
                    state_txt, color = "[완료]",   "#3fb950"
                elif name == cur:
                    state_txt, color = "[실행중]", "#f59e0b"
                else:
                    state_txt, color = "[대기]",   "#e2e8f0"

                _var = self._queue_vars[name]

                row = tk.Frame(self._chk_inner, bg="#ffffff", cursor="hand2")
                row.pack(fill="x", padx=2, pady=1)

                tk.Label(row, text="%2d." % (idx + 1),
                         bg="#ffffff", fg="#94a3b8",
                         font=("Consolas", 9), width=3).pack(side="left")

                def _on_chk():
                    self._update_queue_status_label()
                    self._refresh_file_list(name)

                chk = tk.Checkbutton(
                    row, variable=_var,
                    bg="#ffffff", activebackground="#f1f5f9",
                    selectcolor="white",  # 체크박스 배경 흰색
                    fg="#16a34a",         # 체크 활성화 시 녹색
                    activeforeground="#16a34a",
                    bd=1,
                    relief="flat",
                    command=_on_chk
                )
                chk.pack(side="left", padx=(0, 4))

                lbl = tk.Label(
                    row,
                    text="%s  %s  (%d개 EA)" % (state_txt, name, count),
                    bg="#ffffff", fg=color,
                    font=("Consolas", 9, "bold"), anchor="w", cursor="hand2"
                )
                lbl.pack(side="left", fill="x", expand=True)

                def _fold_click(e, name=name):
                    self._append(f"[QUEUE] 폴더 선택: {name}\n", "info")
                    self._refresh_file_list(name)
                
                lbl.bind("<Button-1>", _fold_click)
                row.bind("<Button-1>", _fold_click)

                self._queue_labels[name] = lbl

            self._update_queue_status_label()
            
            # 레이아웃 강제 갱신 (비표시 방지)
            self._chk_inner.update_idletasks()
            self._chk_canvas.configure(scrollregion=self._chk_canvas.bbox("all"))

        except Exception as e:
            print(f"[QUEUE] 새로고침 실패: {e}")
            try:
                self._append("[QUEUE] 새로고침 실패: %s\n" % e, "err")
            except Exception:
                pass  # 빌드 중 로그 위젯 미생성 시 무시

    def _refresh_file_list(self, folder_name):
        """특정 폴더의 .ex4 파일 목록을 우측 캔버스에 표시 (현재 선택 폴더 강조)."""
        # 하이라이트 처리
        for name, lbl in self._queue_labels.items():
            if name == folder_name:
                lbl.config(bg="#f1f5f9", fg="#1e293b") # 하이라이트 (연한 회색 배경)
            else:
                # 기본 색상 복원
                done_set = set(self._fq._state.get('completed_folders', []))
                cur      = self._fq.get_current_folder()
                color = "#16a34a" if name in done_set else ("#ca8a04" if name == cur else "#1e293b")
                lbl.config(bg="#ffffff", fg=color)

        self._last_sel_folder = folder_name
        for w in self._file_inner.winfo_children():
            w.destroy()
        
        # 이전 선택 값 보관을 위해, 폴더별로 관리할 수도 있지만 일단은 현재 로드된 파일들만 관리
        self._file_vars = {}
        files = self._fq.get_ex4_files(folder_name)
        
        if not files:
            tk.Label(self._file_inner, text=" (파일 없음)", bg="#ffffff", fg="#94a3b8", font=("Malgun Gothic", 9)).pack(anchor="w", pady=4)
            return

        for idx, fpath in enumerate(files):
            fname = os.path.basename(fpath)
            var = tk.BooleanVar(value=True)
            self._file_vars[fname] = var

            row = tk.Frame(self._file_inner, bg="#ffffff", cursor="hand2")
            row.pack(fill="x", padx=2, pady=1)

            tk.Label(row, text="%d." % (idx + 1), bg="#ffffff", fg="#94a3b8", font=("Consolas", 8), width=4).pack(side="left")

            chk = tk.Checkbutton(row, variable=var, bg="#ffffff", activebackground="#f1f5f9", selectcolor="white", fg="#16a34a", relief="flat")
            chk.pack(side="left")

            lbl = tk.Label(row, text=fname, bg="#ffffff", fg="#1e293b", font=("Consolas", 8), anchor="w")
            lbl.pack(side="left", fill="x", expand=True)

            def _toggle_file(e, v=var):
                v.set(not v.get())
            lbl.bind("<Button-1>", _toggle_file)
            row.bind("<Button-1>", _toggle_file)

        # 렌더링 강제 갱신 (500개 이상의 대량 파일 대응)
        self._file_inner.update_idletasks()
        self._file_canvas.configure(scrollregion=self._file_canvas.bbox("all"))
        self._file_canvas.yview_moveto(0)

    def _file_select_all(self):
        for v in self._file_vars.values():
            v.set(True)

    def _file_deselect_all(self):
        for v in self._file_vars.values():
            v.set(False)

    def _file_select_nth(self, n):
        """n번째 간격으로 선택 (1, n+1, 2n+1 ...)."""
        idx = 0
        for name, var in self._file_vars.items():
            if idx % n == 0:
                var.set(True)
            else:
                var.set(False)
            idx += 1

    def _queue_select_all(self):
        for v in self._queue_vars.values():
            v.set(True)
        self._update_queue_status_label()

    def _queue_deselect_all(self):
        for v in self._queue_vars.values():
            v.set(False)
        self._update_queue_status_label()

    def _toggle_pause(self):
        """일시정지 / 재개 토글."""
        pause_file = os.path.join(self.G4_CONFIGS, 'runner_pause.signal')
        if not self._paused:
            # 일시정지
            open(pause_file, 'w').close()
            self._paused = True
            self._btn_pause.config(text="▶ 재개", bg="#15803d")
            self._lbl_queue_status.config(text="⏸ 일시정지 중", fg="#f59e0b")
            self._append("⏸ 일시정지 — 현재 파일 완료 후 대기\n", "warn")
        else:
            # 재개
            if os.path.exists(pause_file):
                os.remove(pause_file)
            self._paused = False
            self._btn_pause.config(text="⏸ 일시정지", bg="#92400e")
            self._lbl_queue_status.config(text="실행 중...", fg="#f97316")
            self._append("▶ 재개\n", "ok")

    def _update_queue_status_label(self):
        try:
            done, total = self._fq.get_progress()
            sel_cnt = sum(1 for v in self._queue_vars.values() if v.get())
            self._lbl_queue_status.config(
                text="%d/%d 완료  |  선택: %d개" % (done, total, sel_cnt),
                fg="#94a3b8")
        except Exception:
            pass

    # -- 세션 저장/불러오기 ------------------------------------------
    def _session_file(self, name):
        safe = name.replace("/", "_").replace("\\", "_").replace(":", "-")
        return os.path.join(self._sessions_dir, safe + ".json")

    def _save_session(self):
        import json as _json
        name = self._sess_name.get().strip()
        if not name:
            name = time.strftime("세션_%m%d_%H%M")
        memo = self._sess_memo.get().strip()

        # 경과 시간 계산
        if self._queue_start_time:
            elapsed_sec = int(time.time() - self._queue_start_time)
            elapsed_str = "%d분 %d초" % (elapsed_sec // 60, elapsed_sec % 60)
        else:
            elapsed_str = "-"

        selected  = [n for n, v in self._queue_vars.items() if v.get()]
        all_folds = list(self._queue_vars.keys())

        data = {
            "name":        name,
            "memo":        memo,
            "saved_at":    time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_time":   elapsed_str,
            "selected":    selected,
            "all_folders": all_folds,
        }
        fpath = self._session_file(name)
        with open(fpath, "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, indent=2)

        self._refresh_session_list()
        self._lbl_sess_info.config(
            text="저장 완료: %s  (%s)" % (name, time.strftime("%H:%M:%S")),
            fg="#34d399")
        self._append("💾 세션 저장: %s  선택=%d개  시간=%s\n" % (
            name, len(selected), elapsed_str), "ok")

    def _refresh_session_list(self):
        import json as _json
        sessions = []
        for f in sorted(os.listdir(self._sessions_dir), reverse=True):
            if not f.endswith(".json"): continue
            fpath = os.path.join(self._sessions_dir, f)
            try:
                with open(fpath, encoding="utf-8") as fh:
                    d = _json.load(fh)
                label = "[%s]  %s  (%s)  시간: %s" % (
                    d.get("saved_at", "")[:16],
                    d.get("name", f[:-5]),
                    d.get("memo", "")[:20],
                    d.get("test_time", "-"))
                sessions.append((label, fpath))
            except Exception:
                pass
        self._sess_sessions = sessions  # [(label, fpath), ...]
        self._sess_combo["values"] = [s[0] for s in sessions]
        if sessions:
            self._sess_combo.current(0)
            self._on_session_select()

    def _on_session_select(self, event=None):
        import json as _json
        idx = self._sess_combo.current()
        if idx < 0 or not hasattr(self, "_sess_sessions"): return
        try:
            fpath = self._sess_sessions[idx][1]
            with open(fpath, encoding="utf-8") as f:
                d = _json.load(f)
            self._lbl_sess_info.config(
                text="선택: %d개 폴더  |  메모: %s" % (
                    len(d.get("selected", [])), d.get("memo", "")),
                fg="#6b7280")
        except Exception:
            pass

    def _load_session(self):
        import json as _json
        idx = self._sess_combo.current()
        if idx < 0 or not hasattr(self, "_sess_sessions"):
            return
        try:
            fpath = self._sess_sessions[idx][1]
            with open(fpath, encoding="utf-8") as f:
                d = _json.load(f)
        except Exception as e:
            return self._append("[세션] 불러오기 실패: %s\n" % e, "err")

        name     = d.get("name", "")
        memo     = d.get("memo", "")
        selected = set(d.get("selected", []))

        # 이름/메모 복원
        self._sess_name.delete(0, "end")
        self._sess_name.insert(0, name)
        self._sess_memo.delete(0, "end")
        self._sess_memo.insert(0, memo)

        # 체크박스 상태 복원
        self._refresh_queue_list()  # 최신 폴더 목록으로 갱신
        for n, v in self._queue_vars.items():
            v.set(n in selected)
        self._update_queue_status_label()

        self._lbl_sess_info.config(
            text="불러옴: %s  (%s)" % (name, d.get("saved_at", "")[:16]),
            fg="#34d399")
        self._append("📂 세션 불러오기: %s  선택=%d개  저장시간=%s\n" % (
            name, len(selected), d.get("saved_at", "")), "ok")

    def _delete_session(self):
        idx = self._sess_combo.current()
        if idx < 0 or not hasattr(self, "_sess_sessions"):
            return messagebox.showwarning("경고", "삭제할 세션을 선택하세요.")
        fpath = self._sess_sessions[idx][1]
        name  = os.path.basename(fpath)[:-5]
        if not messagebox.askyesno("삭제 확인", "세션 '%s' 을 삭제합니까?" % name):
            return
        try:
            os.remove(fpath)
            self._refresh_session_list()
            self._lbl_sess_info.config(text="삭제 완료: %s" % name, fg="#f85149")
            self._append("🗑 세션 삭제 완료: %s\n" % name, "warn")
        except Exception as e:
            self._append("[세션] 삭제 실패: %s\n" % e, "err")

    def _delete_selected_folders(self):
        """선택된 폴더들을 READY_FOR_TEST 에서 실제 삭제 (원본 파일 삭제)."""
        selected = [n for n, v in self._queue_vars.items() if v.get()]
        if not selected:
            return messagebox.showwarning("경고", "삭제할 폴더를 선택하세요.")

        if not messagebox.askyesno(
                "폴더 삭제 확인",
                f"선택한 {len(selected)}개 폴더를 파일 시스템에서 영구히 삭제합니다.\n"
                "※ .ex4 파일 등 모든 내용물이 사라집니다.\n"
                "※ 이 작업은 되돌릴 수 없습니다.\n\n"
                "정말로 삭제하시겠습니까?"):
            return

        import shutil
        cnt = 0
        deleted_names = []
        cur = self._fq.get_current_folder()
        for name in selected:
            if name == cur:
                self._append(f"[QUEUE] 현재 실행 중인 폴더는 삭제할 수 없습니다: {name}\n", "warn")
                continue
            path = os.path.join(self._fq._ready_dir, name)
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    cnt += 1
                    deleted_names.append(name)
                except Exception as e:
                    self._append(f"[QUEUE] 폴더 삭제 실패 ({name}): {e}\n", "err")
        
        if cnt > 0:
            self._append("=== 선택 폴더 삭제 완료: %d개 (%s) ===\n" % (cnt, ", ".join(deleted_names)), "ok")
        self._refresh_queue_list()

    def _run_auto_test_setup(self):
        """scripts/setup_test_queue.py를 실행하여 3개 테스트 폴더 자동 생성"""
        script = os.path.join(HERE, "scripts", "setup_test_queue.py")
        if not os.path.exists(script):
            return messagebox.showerror("오류", f"스크립트가 없습니다: {script}")
        
        try:
            import subprocess
            subprocess.run([sys.executable, script], check=True, capture_output=True, text=True)
            self._append("✅ 큐 자동 검증 테스트 폴더(3개) 생성 완료!\n", "ok")
            self._refresh_queue_list()
            messagebox.showinfo("완료", "검증용 테스트 폴더 3개가 생성되었습니다.\n목록에서 확인 후 '폴더 큐 시작'을 눌러보세요.")
        except Exception as e:
            self._append(f"❌ 검증 테스트 세업 실패: {e}\n", "err")

    def _find_folders_manually(self):
        """직접 폴더를 탐색하여 큐에서 선택함"""
        ready_dir = os.path.abspath(r"reports\READY_FOR_TEST")
        if not os.path.exists(ready_dir): os.makedirs(ready_dir, exist_ok=True)
        
        target = filedialog.askdirectory(initialdir=ready_dir, title="백테스트 폴더 선택")
        if not target: return
        
        rel = os.path.relpath(target, ready_dir).replace('\\', '/')
        if rel == "." or ".." in rel:
            messagebox.showwarning("주의", "READY_FOR_TEST 폴더 내부의 폴더를 선택해주세요.")
            return

        self._refresh_queue_list() # 목록 갱신
        
        # 만약 선택한 폴더가 부모 폴더일 경우, 해당 폴더로 시작하는 모든 하위 큐 항목을 선택!
        matched = False
        for q_name in self._queue_vars.keys():
            if q_name == rel or q_name.startswith(rel + '/'):
                self._queue_vars[q_name].set(True)
                self._append(f"📁 큐 폴더 일괄 선택됨: {q_name}\n", "ok")
                matched = True
        
        if matched:
            self._update_queue_status_label()
        else:
            messagebox.showinfo("알림", f"리스트에서 '{rel}' 관련 하위 테스트 폴더를 찾을 수 없습니다.")

    def _find_files_manually(self):
        """직접 파일을 탐색하여 해당 폴더를 큐에서 선택함"""
        ready_dir = os.path.abspath(r"reports\READY_FOR_TEST")
        if not os.path.exists(ready_dir): os.makedirs(ready_dir, exist_ok=True)
        
        fpath = filedialog.askopenfilename(
            initialdir=ready_dir, title="백테스트 EA 파일 선택",
            filetypes=[("EA Files", "*.ex4"), ("All Files", "*.*")]
        )
        if not fpath: return
        
        target_dir = os.path.dirname(fpath)
        rel = os.path.relpath(target_dir, ready_dir).replace('\\', '/')
        
        if rel == "." or ".." in rel:
            messagebox.showwarning("주의", "폴더에 정리된 파일을 선택하거나,\n루트 파일은 먼저 폴더로 분류해주세요.")
            return

        self._refresh_queue_list()
        if rel in self._queue_vars:
            self._queue_vars[rel].set(True)
            self._update_queue_status_label()
            self._append(f"📄 파일 기반 폴더 선택됨: {rel}\n", "ok")
        else:
            messagebox.showinfo("알림", f"'{rel}' 폴더를 큐 리스트에서 찾을 수 없습니다.")

    def _reset_progress(self):
        """progress/status/flag 초기화 — g4_results는 백업 보관."""
        if not messagebox.askyesno(
                "초기화 확인",
                "round_*_progress.json, command.json, flag 파일을 초기화합니다.\n"
                "g4_results는 백업 후 보관됩니다. (레포트/JSON 모두 안전)\n\n"
                "계속하시겠습니까?"):
            return
        cnt, msgs = reset_all(backup_results=True)
        for m in msgs:
            self._append(m + "\n", "warn")
        self._append("=== 초기화 완료: %d개 파일 정리 ===\n" % cnt, "ok")
        self._refresh_queue_list()

    def _delete_json_only(self):
        """JSON 파일만 완전 삭제 — HTML/CSV 레포트는 보존."""
        if not messagebox.askyesno(
                "JSON 완전삭제 확인",
                "progress.json, command.json, flag 파일 및\n"
                "g4_results 폴더의 JSON 파일을 모두 삭제합니다.\n\n"
                "※ HTML/CSV 레포트 파일은 그대로 보존됩니다.\n"
                "※ 이 작업은 되돌릴 수 없습니다.\n\n"
                "계속하시겠습니까?"):
            return
        from core.reset_engine import delete_json_only
        cnt, msgs = delete_json_only()
        for m in msgs:
            self._append(m + "\n", "warn")
        self._append("=== JSON 완전삭제 완료: %d개 파일 삭제 (레포트 보존) ===\n" % cnt, "ok")
        self._refresh_queue_list()

    def _run_folder_queue(self):
        """선택된 폴더만 큐 모드로 optimizer 실행."""
        import json as _json
        script = self.G4_OPTIMIZER
        if not os.path.exists(script):
            return messagebox.showerror("오류", "V7 옵티마이저 없음:\n%s" % script)

        selected = [n for n, v in self._queue_vars.items() if v.get()]
        if not selected:
            return messagebox.showwarning("경고", "선택된 폴더가 없습니다.\n체크박스를 선택하세요.")

        # 선택 목록을 configs/queue_selected.json 에 저장 → optimizer 가 읽음
        # 파일 필터링 추가: 현재 로드된 폴더에 대해 선택된 파일이 있다면 그것도 저장
        file_filter = [fn for fn, v in self._file_vars.items() if v.get()]
        
        sel_file = os.path.join(self.G4_CONFIGS, "queue_selected.json")
        os.makedirs(self.G4_CONFIGS, exist_ok=True)
        with open(sel_file, "w", encoding="utf-8") as f:
            _json.dump({
                "selected": selected,
                "file_filter": file_filter,
                "filter_folder": self._last_sel_folder
            }, f, ensure_ascii=False)

        self._queue_start_time = time.time()
        self.btn_queue.config(state="disabled")
        self._lbl_queue_status.config(text="실행 중... (%d개)" % len(selected), fg="#f97316")
        msg = "▶ 폴더 큐 모드 시작 (%d개 선택)\n" % len(selected)
        if file_filter and len(file_filter) < len(self._file_vars):
            msg += "  ※ 파일 필터 적용됨: %d/%d개\n" % (len(file_filter), len(self._file_vars))
        self._append(msg, "ok")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        self._fq_proc = subprocess.Popen(
            [sys.executable, "-u", script, "--folder-queue"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=self.G4_SOLO_DIR, env=env
        )
        threading.Thread(target=self._stream_folder_queue, daemon=True).start()

    def _stream_folder_queue(self):
        try:
            for line in self._fq_proc.stdout:
                self.after(0, lambda l=line.rstrip(): self._append_line(l))
                # 큐 상태 갱신 (QUEUE 로그 줄마다)
                if '[QUEUE]' in line or 'FOLDER' in line:
                    self.after(0, self._refresh_queue_list)
        except Exception:
            pass
        finally:
            self.after(0, lambda: self.btn_queue.config(state="normal"))
            self.after(0, lambda: self._lbl_queue_status.config(
                text="완료", fg="#22c55e"))
            self.after(0, lambda: self._append("== 폴더 큐 완료 ==\n", "ok"))
            self.after(0, self._refresh_queue_list)

    # -- R1~R10 라운드 수동 컨트롤 -----------------------------------
    def _build_round_ctrl(self, parent):
        """R1~R10 수동 라운드 컨트롤 패널 — 단계별 실행 & 진화 히스토리."""
        rp = tk.LabelFrame(
            parent,
            text="  🎯  R1~R10 라운드 수동 컨트롤  (단계별 실행 → 검토 → 다음 라운드)",
            font=("Malgun Gothic", 9, "bold"), fg="#ff8c42", bg=self.PNL,
            relief="groove", bd=2
        )
        rp.pack(fill="x", padx=10, pady=(0, 4))

        # 행1: 단일 라운드
        r1 = tk.Frame(rp, bg=self.PNL); r1.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(r1, text="【단일】 라운드:", font=("Malgun Gothic", 9, "bold"),
                 fg="#ff6b35", bg=self.PNL).pack(side="left")
        tk.Spinbox(r1, textvariable=self._rnd_sel, from_=1, to=10, width=4,
                   font=("Consolas", 13, "bold"), bg="#1e1b4b", fg="#ff6b35",
                   relief="flat", bd=2, justify="center",
                   buttonbackground=self.PNL, wrap=True).pack(side="left", padx=(4, 8))
        B(r1, "▶ 이 라운드만 실행", "#15803d", self._run_round_only,
          font=("Malgun Gothic", 10, "bold"), pady=5, padx=14).pack(side="left", padx=2)
        B(r1, "⏩ 자동(이어하기)", "#6d28d9", self._run_round_auto,
          font=("Malgun Gothic", 10, "bold"), pady=5, padx=14).pack(side="left", padx=2)
        self._rnd_stop_btn = B(r1, "⏹ 중단", "#991b1b", self._stop_round,
                               font=("Malgun Gothic", 10, "bold"), pady=5, padx=10)
        self._rnd_stop_btn.pack(side="left", padx=4)
        self._rnd_stop_btn.config(state="disabled")
        self._rnd_status = tk.Label(r1, text="대기 중", font=("Consolas", 9),
                                    fg="#94a3b8", bg=self.PNL)
        self._rnd_status.pack(side="right", padx=8)

        # 행2: 범위 실행
        r2 = tk.Frame(rp, bg=self.PNL); r2.pack(fill="x", padx=10, pady=(0, 2))
        tk.Label(r2, text="【범위】 R", font=("Malgun Gothic", 9, "bold"),
                 fg="#60a5fa", bg=self.PNL).pack(side="left")
        tk.Spinbox(r2, textvariable=self._rnd_sel, from_=1, to=10, width=3,
                   font=("Consolas", 12, "bold"), bg="#1e1b4b", fg="#60a5fa",
                   relief="flat", bd=2, justify="center",
                   buttonbackground=self.PNL, wrap=True).pack(side="left", padx=(2, 4))
        tk.Label(r2, text="~ R", font=("Malgun Gothic", 9, "bold"),
                 fg="#60a5fa", bg=self.PNL).pack(side="left")
        tk.Spinbox(r2, textvariable=self._rnd_end, from_=1, to=10, width=3,
                   font=("Consolas", 12, "bold"), bg="#1e1b4b", fg="#60a5fa",
                   relief="flat", bd=2, justify="center",
                   buttonbackground=self.PNL, wrap=True).pack(side="left", padx=(2, 8))
        tk.Label(r2, text="단계 선택:", font=("Malgun Gothic", 8),
                 fg="#94a3b8", bg=self.PNL).pack(side="left", padx=(0, 4))
        for label, s, e in [("1단계(R1~3)", 1, 3), ("2단계(R4~6)", 4, 6), ("3단계(R7~10)", 7, 10)]:
            def _set_range(sv=s, ev=e):
                self._rnd_sel.set(sv); self._rnd_end.set(ev)
            tk.Button(r2, text=label, font=("Malgun Gothic", 8),
                      bg="#1e3a5f", fg="#60a5fa", relief="flat", bd=0,
                      padx=6, pady=3, cursor="hand2",
                      command=_set_range).pack(side="left", padx=2)
        B(r2, "▶▶ 범위 실행", "#0369a1", self._run_round_range,
          font=("Malgun Gothic", 10, "bold"), pady=5, padx=14).pack(side="left", padx=(8, 2))

        # 행3: 결과/다음 라운드
        r3 = tk.Frame(rp, bg=self.PNL); r3.pack(fill="x", padx=10, pady=(0, 4))
        B(r3, "🔄 히스토리 갱신", "#0369a1", self._refresh_evo,
          pady=5, padx=10).pack(side="left", padx=4)
        B(r3, "⏭ 다음 라운드 자동 설정", "#92400e", self._prep_next_round,
          pady=5, padx=10).pack(side="left", padx=2)
        B(r3, "📊 결과 확인", "#0e7490", self._analyze_results,
          pady=5, padx=10).pack(side="left", padx=4)
        B(r3, "⏭▶ 다음라운드 실행", "#064e3b", self._run_next_round,
          font=("Malgun Gothic", 10, "bold"), pady=5, padx=12).pack(side="left", padx=2)

        # 히스토리 테이블
        evo_cols = ("rno", "best_sl", "best_tp", "best_profit", "best_pf", "sc_cnt", "status")
        evo_cfg  = [("rno", "라운드", 55), ("best_sl", "BEST SL", 70),
                    ("best_tp", "BEST TP", 70), ("best_profit", "순이익", 85),
                    ("best_pf", "PF", 55), ("sc_cnt", "SC수", 50), ("status", "상태", 100)]
        evo_f = tk.Frame(rp, bg=self.PNL); evo_f.pack(fill="x", padx=10, pady=(0, 6))
        self._rnd_evo_tree = ttk.Treeview(evo_f, columns=evo_cols, show="headings",
                                           height=5, selectmode="browse")
        for cid, hdr, w in evo_cfg:
            self._rnd_evo_tree.heading(cid, text=hdr)
            self._rnd_evo_tree.column(cid, width=w, anchor="center", stretch=False)
        evo_vsb = ttk.Scrollbar(evo_f, orient="vertical",
                                 command=self._rnd_evo_tree.yview)
        self._rnd_evo_tree.configure(yscrollcommand=evo_vsb.set)
        self._rnd_evo_tree.pack(side="left", fill="x", expand=True)
        evo_vsb.pack(side="right", fill="y")
        self._rnd_evo_tree.tag_configure("done",    background="#0d2818", foreground="#3fb950")
        self._rnd_evo_tree.tag_configure("pending", background="#0d1117", foreground="#6b7280")
        self._refresh_evo()

    def _run_round_only(self):
        """선택한 라운드 하나만 실행."""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요.")
            return
        rno = self._rnd_sel.get()
        if not messagebox.askyesno("실행 확인",
                "R%d 라운드만 단독 실행합니다.\n계속하시겠습니까?" % rno):
            return
        self._rnd_status.config(text="R%d 준비 중..." % rno, fg="#ff8c42")
        threading.Thread(target=self._run_round_thread, args=(rno, rno), daemon=True).start()

    def _run_round_range(self):
        """범위 라운드 순차 실행."""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요.")
            return
        r_start = self._rnd_sel.get()
        r_end   = self._rnd_end.get()
        if r_end < r_start:
            messagebox.showwarning("범위 오류",
                "끝 라운드(%d)가 시작(%d)보다 작습니다." % (r_end, r_start))
            return
        if not messagebox.askyesno("범위 실행 확인",
                "R%d ~ R%d (%d단계) 순차 실행합니다.\n계속하시겠습니까?" % (
                    r_start, r_end, r_end - r_start + 1)):
            return
        self._rnd_status.config(
            text="R%d~R%d 범위 실행 중..." % (r_start, r_end), fg="#60a5fa")
        threading.Thread(target=self._run_round_thread,
                         args=(r_start, r_end), daemon=True).start()

    def _run_round_auto(self):
        """자동(이어하기): auto_round 감지 후 R10까지 실행."""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요.")
            return
        if not messagebox.askyesno("자동 실행 확인",
                "이어서 R1~R10 자동 실행합니다.\n계속하시겠습니까?"):
            return
        self._rnd_status.config(text="자동(이어하기) 준비 중...", fg="#a855f7")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        self._rnd_proc = subprocess.Popen(
            [sys.executable, "-u", self.G4_OPTIMIZER],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=self.G4_SOLO_DIR, env=env
        )
        self.after(0, lambda: self._rnd_stop_btn.config(state="normal"))
        threading.Thread(target=self._stream_round, daemon=True).start()

    def _run_round_thread(self, r_start, r_end):
        """단일/범위 라운드를 --round R [--to M] 으로 실행."""
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [sys.executable, "-u", self.G4_OPTIMIZER,
               "--round", str(r_start), "--to", str(r_end)]
        self.after(0, lambda: self._rnd_stop_btn.config(state="normal"))
        self._rnd_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=self.G4_SOLO_DIR, env=env
        )
        self._stream_round()

    def _stream_round(self):
        try:
            for line in self._rnd_proc.stdout:
                line = line.strip()
                if not line: continue
                self.after(0, lambda l=line: self._append_line(l))
                self.after(0, lambda l=line: self._rnd_status.config(
                    text=l[:80], fg="#ff6b35"))
        except Exception:
            pass
        finally:
            self.after(0, lambda: self._rnd_stop_btn.config(state="disabled"))
            self.after(0, lambda: self._rnd_status.config(text="완료 ✅", fg="#3fb950"))
            self.after(600, self._refresh_evo)

    def _stop_round(self):
        """실행 중인 라운드 프로세스 중단."""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            self._rnd_proc.terminate()
        self._rnd_status.config(text="중단됨", fg="#f85149")
        if self._rnd_stop_btn:
            self._rnd_stop_btn.config(state="disabled")

    def _refresh_evo(self):
        """g4_results/ V7_R*.json → 히스토리 트리뷰 갱신."""
        if not self._rnd_evo_tree:
            return
        import json as _json
        for iid in self._rnd_evo_tree.get_children():
            self._rnd_evo_tree.delete(iid)
        completed = {}
        for rjson in sorted(_g.glob(os.path.join(self.G4_RESULTS, "V7_R*.json"))):
            try:
                with open(rjson, encoding="utf-8") as f:
                    d = _json.load(f)
                rno     = d.get("round", 0)
                results = d.get("results", [])
                if not results: continue
                best    = max(results, key=lambda x: x.get("score", 0))
                completed[rno] = {
                    "best_sl":     best.get("params", {}).get("InpSLMultiplier", 0),
                    "best_tp":     best.get("params", {}).get("InpTPMultiplier", 0),
                    "best_profit": best.get("profit", 0),
                    "best_pf":     best.get("profit_factor", 0),
                    "sc_cnt":      len(results),
                }
            except Exception:
                pass
        for rno in range(1, 11):
            if rno in completed:
                c = completed[rno]
                self._rnd_evo_tree.insert("", "end", iid="R%d" % rno,
                    values=("R%d" % rno,
                            "%.2f" % c["best_sl"], "%.1f" % c["best_tp"],
                            "$%.0f" % c["best_profit"], "%.2f" % c["best_pf"],
                            c["sc_cnt"], "완료 ✅"),
                    tags=("done",))
            else:
                self._rnd_evo_tree.insert("", "end", iid="R%d" % rno,
                    values=("R%d" % rno, "—", "—", "—", "—", "—", "대기 중"),
                    tags=("pending",))

    def _prep_next_round(self):
        """g4_results 에서 다음 실행 라운드 번호를 Spinbox에 설정."""
        completed = set()
        for rjson in _g.glob(os.path.join(self.G4_RESULTS, "V7_R*.json")):
            try:
                import json as _json
                with open(rjson, encoding="utf-8") as f:
                    d = _json.load(f)
                if len(d.get("results", [])) > 0:
                    completed.add(d.get("round", 0))
            except Exception:
                pass
        if completed:
            max_done = max(completed)
            next_rno = min(max_done + 1, 10)
            self._rnd_sel.set(next_rno)
            self._rnd_status.config(
                text="R%d 완료 → 다음: R%d 준비됨" % (max_done, next_rno),
                fg="#3fb950")
        else:
            self._rnd_sel.set(1)
            self._rnd_status.config(text="이력 없음 — R1부터 시작", fg="#f59e0b")
        self._refresh_evo()

    def _analyze_results(self):
        """g4_results 폴더를 탐색기로 열기."""
        if os.path.exists(self.G4_RESULTS):
            subprocess.Popen(["explorer", self.G4_RESULTS])
        else:
            messagebox.showinfo("결과 없음", "g4_results/ 폴더가 없습니다.")

    def _run_next_round(self):
        """다음 라운드 자동 설정 + 즉시 실행."""
        if self._rnd_proc and self._rnd_proc.poll() is None:
            messagebox.showwarning("실행 중", "현재 라운드 실행 중입니다. 먼저 중단하세요.")
            return
        self._prep_next_round()
        rno = self._rnd_sel.get()
        if rno > 10:
            self._rnd_status.config(text="R10 완료 — 더 이상 라운드 없음", fg="#3fb950")
            return
        self._rnd_status.config(text="R%d 즉시 시작 중..." % rno, fg="#ff8c42")
        threading.Thread(target=self._run_round_thread, args=(rno, rno), daemon=True).start()

    def destroy(self):
        self._running = False
        super().destroy()
