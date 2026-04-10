"""
EA Auto Master v8.0 — 13파라미터 지능형 최적화 통합 제어 시스템
======================================================
V8 신규: 경로 단순화(C:/AG TO DO/EA_AUTO_MASTER_v8.0) 및 버전 통합
"""
import datetime
import os
import subprocess
import sys
import tkinter as tk
import traceback

# --- 디버그 로그 설정 ---
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
def log_error(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{ts}] {msg}\n")

def handle_exception(exc_type, exc_value, exc_traceback):
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_error(f"CRITICAL ERROR:\n{err_msg}")
    # 콘솔에도 출력
    print(err_msg)

sys.excepthook = handle_exception
# ----------------------

# --- 중복 실행 방지 로직 (파일 락 방식) ---
# def check_single_instance():
#     try:
#         import msvcrt, os, sys
#         from tkinter import messagebox
#         lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs", "app.lock")
#         os.makedirs(os.path.dirname(lock_path), exist_ok=True)
#         
#         global _lock_file_handle
#         _lock_file_handle = open(lock_path, "w")
#         try:
#             # 파일의 첫 번째 바이트에 대해 락을 시도 (LK_NBLCK: 비차단 모드)
#             msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
#         except (IOError, OSError):
#             # 락 획득 실패 시 이미 실행 중인 것으로 간주
#             root = tk.Tk(); root.withdraw()
#             messagebox.showwarning("중복 실행 금지", "이미 프로그램이 실행 중입니다.\n\n작업 표시줄이나 트레이를 확인해 주세요.")
#             root.destroy()
#             sys.exit(0)
#     except Exception:
#         pass
# check_single_instance()
# ----------------------------------------------
# ----------------------------------------------

from tkinter import ttk, filedialog
from core.config import HERE, load_cfg, save_cfg

# ui/ 탭들
from ui.tab_bypass     import BypassTab
from ui.tab_merger     import MergerTab
from ui.tab_round_opt  import RoundOptTab
from ui.tab_autofix    import AutoFixTab
from ui.tab_launcher   import LauncherTab
from ui.tab_settings   import SettingsTab
from ui.tab_scenario   import ScenarioMasterTab
from ui.tab_run_control import RunControlTab
from ui.tab_monitor    import MonitorTab
from ui.tab_history    import RoundHistoryTab
from ui.tab_dashboard  import EADashboardTab
from ui.tab_v7control  import V7ControlTab
from ui.tab_param_analysis import ParamAnalysisTab
from ui.tab_performance import PerformanceTab
from ui.tab_ea_detail   import EADetailTab

from ui.theme import BG, PANEL, PANEL2, FG, ACCENT, MONO

class EAMaster(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EA AUTO MASTER v8.1 — 13파라미터 지능형 최적화")
        
        # --- 창 크기 복원 ---
        self._geom_file = os.path.join(HERE, "configs", "window_geometry.txt")
        geom = "1200x940"
        if os.path.exists(self._geom_file):
            try:
                with open(self._geom_file, "r") as f:
                    saved_geom = f.read().strip()
                if saved_geom:
                    geom = saved_geom
            except Exception:
                pass
        self.geometry(geom)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.resizable(True, True)
        self.configure(bg=BG)
        self._cfg = load_cfg()
        self._styles()
        self._build()
        self.after(1500, self._auto_start_solo)

    def _on_closing(self):
        """종료 시 창 크기/위치 저장"""
        try:
            os.makedirs(os.path.dirname(self._geom_file), exist_ok=True)
            with open(self._geom_file, "w") as f:
                f.write(self.geometry())
        except Exception as e:
            print(f"Geometry save error: {e}")
        self.destroy()

    def _auto_start_solo(self):
        if self._cfg.get("solo_auto", "1") == "0": return
        try:
            out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq AutoHotkey.exe", "/NH"],
                                          creationflags=subprocess.CREATE_NO_WINDOW).decode("utf-8", "ignore")
            if "AutoHotkey.exe" in out: return
        except: pass
        ahk_exe = next((p for p in [r"C:\Program Files\AutoHotkey\AutoHotkey.exe", r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"] if os.path.exists(p)), None)
        solo_ahk = os.path.join(HERE, "SOLO_nc2.3.ahk")
        if ahk_exe and os.path.exists(solo_ahk):
            subprocess.Popen([ahk_exe, solo_ahk], cwd=HERE, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def _restart_app(self):
        """본 프로그램을 종료하고 즉시 다시 실행"""
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=FG, font=("Malgun Gothic", 9, "bold"), padding=[12, 5])
        s.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "white")])
        s.configure("Treeview", background=PANEL2, foreground=FG, rowheight=22, fieldbackground=PANEL2, font=MONO)
        s.configure("Treeview.Heading", background="#bae6fd", foreground="#4c1d95", font=("Malgun Gothic", 9, "bold"))
        s.map("Treeview", background=[("selected", ACCENT)])

    def _build(self):
        hdr = tk.Frame(self, bg=ACCENT, height=48)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="EA AUTO MASTER v8.1  —  13파라미터 지능형 최적화  |  LHS → FOCUSED → GENETIC",
                 font=("Malgun Gothic", 12, "bold"), fg="white", bg=ACCENT).place(relx=0.5, rely=0.5, anchor="center")
        tk.Button(hdr, text="앱 재시작", bg="#4b5563", fg="white", command=self._restart_app).place(relx=0.95, rely=0.5, anchor="center")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        cfg = self._cfg
        
        nb.add(RunControlTab(nb, cfg),      text="실행제어")
        nb.add(V7ControlTab(nb, cfg),        text="🚀 V8최적화")
        nb.add(MonitorTab(nb, cfg),         text="모니터")
        nb.add(BypassTab(nb, cfg),          text="바이패스")
        nb.add(MergerTab(nb, cfg),          text="모듈합치기")
        nb.add(RoundOptTab(nb, cfg),        text="라운드최적화")
        nb.add(AutoFixTab(nb, cfg),         text="자동수정")
        nb.add(LauncherTab(nb, "EA 자동생성", cfg.get("builder", os.path.join(HERE, "EA_AUTO_BUILDER.py")), cfg), text="EA생성")
        nb.add(SettingsTab(nb, cfg),        text="설정")
        nb.add(ScenarioMasterTab(nb, cfg),  text="시나리오")
        def _hist():
            p = cfg.get("hist_path", ""); return p if p and os.path.exists(p) else os.path.join(HERE, "round_history.json")
        nb.add(RoundHistoryTab(nb, _hist),   text="라운드히스토리")
        nb.add(EADashboardTab(nb, cfg),     text="EA대시보드")
        nb.add(ParamAnalysisTab(nb, cfg),   text="📈 파라미터분석")
        nb.add(PerformanceTab(nb, cfg),     text="📊 BTC/GOLD성과")
        nb.add(EADetailTab(nb, cfg) ,       text="🔬 EA별분석")
        
        nb.select(0)

        sb = tk.Frame(self, bg="#12121e", height=22); sb.pack(fill="x", side="bottom"); sb.pack_propagate(False)
        self._cl = tk.Label(sb, text="", font=("Consolas", 8), fg="#475569", bg="#12121e"); self._cl.pack(side="right", padx=8)
        tk.Label(sb, text="EA AUTO MASTER v8.1 |  13파라미터 최적화 |  PORTABLE v8.0", font=("Consolas", 8), fg="#3a3a54", bg="#12121e").pack(side="left", padx=8)
        self._tick()

    def _tick(self):
        self._cl.config(text=datetime.datetime.now().strftime("[T] %Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._tick)

if __name__ == "__main__":
    EAMaster().mainloop()
