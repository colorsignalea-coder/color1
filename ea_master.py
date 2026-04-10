"""
EA Auto Master v8.0 ??13?뚮씪誘명꽣 吏?ν삎 理쒖쟻???쒖뒪??======================================================
V7 ?좉퇋: ea_optimizer_v7.py ?곕룞 + V7ControlTab 異붽?
援ъ“:
  ea_master.py (吏꾩엯??
    -> ui/ (??12媛?
       -> core/ (14媛?紐⑤뱢, tkinter 湲덉?)
"""
import datetime
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

# core/ ?좏떥由ы떚
from core.config import HERE, load_cfg, save_cfg

# ui/ ??11媛?from ui.tab_bypass     import BypassTab
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
        self.title("EA AUTO MASTER v8.0 ??13?뚮씪誘명꽣 吏?ν삎 理쒖쟻??)
        self.geometry("1200x940")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._cfg = load_cfg()
        self._styles()
        self._build()
        # SOLO PACK ?먮룞 ?쒖옉 (1.5珥??쒕젅????GUI ?덉젙????
        self.after(1500, self._auto_start_solo)

    def _auto_start_solo(self):
        """???쒖옉 1.5珥???SOLO_nc2.3.ahk ?먮룞 ?ㅽ뻾.
        START_ALL_v7.bat ? ?숈씪?섍쾶 SOLO_nc2.3.ahk 瑜?吏곸젒 ?ㅽ뻾.
        """
        if self._cfg.get("solo_auto", "1") == "0":
            print("[SOLO] ?먮룞?쒖옉 OFF (?ㅼ젙 ??뿉??蹂寃?媛??")
            return

        # AutoHotkey ?대? ?ㅽ뻾 以묒씠硫??ㅽ궢 (tasklist ?ъ슜 ??PowerShell 蹂대떎 ?덉젙??
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq AutoHotkey.exe", "/NH"],
                creationflags=subprocess.CREATE_NO_WINDOW
            ).decode("utf-8", "ignore")
            if "AutoHotkey.exe" in out:
                print("[SOLO] AutoHotkey already running ??skip")
                return
        except Exception:
            pass

        # AutoHotkey ?ㅽ뻾 ?뚯씪 ?먯깋
        ahk_candidates = [
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
            r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe",
        ]
        ahk_exe = next((p for p in ahk_candidates if os.path.exists(p)), None)
        if not ahk_exe:
            print("[SOLO] AutoHotkey.exe not found ??skip")
            return

        # SOLO_nc2.3.ahk 吏곸젒 ?ㅽ뻾 (START_ALL_v7.bat ? ?숈씪)
        solo_ahk = os.path.join(HERE, "SOLO_nc2.3.ahk")
        if not os.path.exists(solo_ahk):
            print(f"[SOLO] SOLO_nc2.3.ahk not found at: {solo_ahk}")
            return

        subprocess.Popen([ahk_exe, solo_ahk], cwd=HERE,
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        print(f"[SOLO] started: SOLO_nc2.3.ahk")

    def _styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=FG,
                    font=("Malgun Gothic", 9, "bold"), padding=[12, 5])
        s.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", "white")])
        s.configure("D.TFrame", background=BG)
        s.configure("Treeview", background=PANEL2, foreground=FG,
                    rowheight=22, fieldbackground=PANEL2, font=MONO)
        s.configure("Treeview.Heading", background="#bae6fd",
                    foreground="#4c1d95", font=("Malgun Gothic", 9, "bold"))
        s.map("Treeview.Heading", background=[("active", "#93c5fd")])
        s.map("Treeview", background=[("selected", ACCENT)])
        s.configure("green.Horizontal.TProgressbar",
                    troughcolor=PANEL2, background="#22c55e", thickness=10)

    def _build(self):
        # ?ㅻ뜑 諛?        hdr = tk.Frame(self, bg=ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr,
                 text="EA AUTO MASTER v8.0  ?? 13?뚮씪誘명꽣 吏?ν삎 理쒖쟻?? |  LHS ??FOCUSED ??GENETIC",
                 font=("Malgun Gothic", 12, "bold"), fg="white", bg=ACCENT
                 ).place(relx=0.5, rely=0.5, anchor="center")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        cfg = self._cfg

        nb.add(V7ControlTab(nb, cfg),        text="?? V7理쒖쟻??)
        nb.add(MonitorTab(nb, cfg),         text="紐⑤땲??)
        nb.add(BypassTab(nb, cfg),          text="諛붿씠?⑥뒪")
        nb.add(MergerTab(nb, cfg),          text="紐⑤뱢?⑹튂湲?)
        nb.add(RoundOptTab(nb, cfg),        text="?쇱슫?쒖턀?곹솕")
        nb.add(AutoFixTab(nb, cfg),         text="?먮룞?섏젙")
        nb.add(LauncherTab(
                   nb, "EA ?먮룞?앹꽦",
                   cfg.get("builder", os.path.join(HERE, "EA_AUTO_BUILDER.py")),
                   cfg),                    text="EA?앹꽦")
        nb.add(SettingsTab(nb, cfg),        text="?ㅼ젙")
        nb.add(ScenarioMasterTab(nb, cfg),  text="?쒕굹由ъ삤")
        nb.add(RunControlTab(nb, cfg),      text="?ㅽ뻾?쒖뼱")
        def _hist_path():
            # 1) cfg??寃쎈줈 ?ㅼ젙 ?덉쑝硫??곗꽑
            p = cfg.get("hist_path", "")
            if p and os.path.exists(p):
                return p
            # 2) RUNTIME ?대뜑 ?먮룞 ?먯깋 (EA MASTER 6.0\RUNTIME\)
            candidates = [
                os.path.join(HERE, "round_history.json"),
                os.path.join(os.path.dirname(HERE), "round_history.json"),
                os.path.join(os.path.dirname(HERE), "RUNTIME", "round_history.json"),
                r"os.path.join(HERE, "RUNTIME")\round_history.json",
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c
            return candidates[0]  # ?놁쑝硫?湲곕낯
        nb.add(RoundHistoryTab(nb, _hist_path),
                                            text="?쇱슫?쒗엳?ㅽ넗由?)
        nb.add(EADashboardTab(nb, cfg),     text="EA??쒕낫??)
        nb.add(ParamAnalysisTab(nb, cfg),   text="?뱢 ?뚮씪誘명꽣遺꾩꽍")
        nb.add(PerformanceTab(nb, cfg),     text="?뱤 BTC/GOLD?깃낵")
        nb.add(EADetailTab(nb, cfg),        text="?뵮 EA蹂꾨텇??)

        # ?섎떒 ?곹깭諛?        sb = tk.Frame(self, bg="#12121e", height=22)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self._cl = tk.Label(sb, text="", font=("Consolas", 8),
                            fg="#475569", bg="#12121e")
        self._cl.pack(side="right", padx=8)
        tk.Label(sb,
                 text="EA AUTO MASTER v8.0 |  13?뚮씪誘명꽣 理쒖쟻?? |  LHS?묯OCUSED?묰ENETIC  |  ui/ 13??,
                 font=("Consolas", 8), fg="#3a3a54", bg="#12121e").pack(side="left", padx=8)
        self._tick()

    def _tick(self):
        self._cl.config(text=datetime.datetime.now().strftime("[T] %Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._tick)


# ?? core/ 紐⑤뱢 import 寃利??????????????????????????????????????????
def _verify_all():
    """core/ + ui/ ?꾩껜 import 寃利?"""
    import io
    results = []

    core_modules = [
        "core.config", "core.encoding", "core.path_finder",
        "core.htm_parser", "core.scoring", "core.diagnostics",
        "core.email_sender", "core.mql4_engine", "core.mql4_merger",
        "core.mql4_autofix", "core.round_engine", "core.ipc",
        "core.mt4_control", "core.round_optimizer",
    ]
    ui_modules = [
        "ui.theme",
        "ui.tab_bypass", "ui.tab_merger", "ui.tab_round_opt",
        "ui.tab_autofix", "ui.tab_launcher", "ui.tab_settings",
        "ui.tab_scenario", "ui.tab_run_control", "ui.tab_monitor",
        "ui.tab_history", "ui.tab_dashboard", "ui.tab_param_analysis",
        "ui.tab_performance",
        "ui.tab_ea_detail",
    ]

    ok = 0
    fail = 0
    for m in core_modules + ui_modules:
        try:
            __import__(m)
            results.append(f"  OK  {m}")
            ok += 1
        except Exception as e:
            results.append(f"  FAIL {m}: {e}")
            fail += 1

    print("\n".join(results))
    print(f"\n[v6.0] ?꾩껜 寃利? {ok} OK / {fail} FAIL")
    return fail == 0


if __name__ == "__main__":
    if "--verify" in sys.argv:
        success = _verify_all()
        sys.exit(0 if success else 1)

    EAMaster().mainloop()

