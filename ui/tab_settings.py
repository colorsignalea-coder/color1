"""
ui/tab_settings.py — EA Auto Master v6.0
==========================================
경로 설정 + 공용 폰트 크기 조정 탭.
"""
import datetime
import tkinter as tk
from tkinter import ttk, filedialog

from core.config import save_cfg
from core.path_finder import find_me, find_builder_file, _find_db_path, find_dashboard_file, _ME_CANDS
from ui.theme import (BG, FG, PANEL, PANEL2, BLUE, GREEN,
                      MONO, LBL, TITLE, B, _apply_font_sz)


class SettingsTab(ttk.Frame):
    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        self._build()

    def _build(self):
        b = tk.Frame(self, bg=BG)
        b.pack(fill="both", expand=True, padx=14, pady=12)

        f1 = tk.LabelFrame(b, text="  \u2699\ufe0f  경로 설정", font=TITLE,
                           fg=FG, bg=PANEL, relief="groove", bd=2)
        f1.pack(fill="x", pady=(0, 8))

        # 배포형 기본 SOLO 경로
        from core.config import HERE
        import os
        _def_solo = HERE
        _candidates = [
            HERE,
            os.path.join(os.path.dirname(HERE), "SOLO_PACK_V1.2"),
            os.path.join(os.path.dirname(HERE), "2026 MUST TODO", "SOLO_PACK_V1.2"),
            os.path.join(os.path.dirname(os.path.dirname(HERE)), "SOLO_PACK_V1.2"),
        ]
        for c in _candidates:
            if os.path.exists(os.path.join(c, "configs", "current_config.ini")):
                _def_solo = c
                break

        fields = [
            ("SOLO PACK 폴더", "solo_dir", _def_solo),
            ("SOLO START.bat", "solo_bat",
             os.path.join(_def_solo, "START_SOLO.bat")),
            ("자동시작 ON/OFF", "solo_auto", "1"),
            ("MetaEditor #1", "me1", _ME_CANDS[0] if _ME_CANDS else ""),
            ("MetaEditor #2", "me2", _ME_CANDS[1] if len(_ME_CANDS) > 1 else ""),
            ("MetaEditor #3", "me3", ""),
            ("MetaEditor #4", "me4", ""),
            ("EA_AUTO_BUILDER", "builder",
             find_builder_file("EA_AUTO_BUILDER.py")),
            ("EA_OPTIMIZER_GUI", "optgui",
             find_builder_file("EA_OPTIMIZER_GUI.py")),
            ("ea_bt_autofix", "autofix",
             find_builder_file("ea_bt_autofix.py")),
            ("solo_worker DB", "db_path", _find_db_path()),
            ("round_dashboard", "dashboard", find_dashboard_file()),
        ]

        self._v = {}
        for lbl, key, default in fields:
            r = tk.Frame(f1, bg=PANEL)
            r.pack(fill="x", padx=8, pady=3)
            tk.Label(r, text=lbl + ":", font=LBL, fg=FG, bg=PANEL,
                     width=18, anchor="e").pack(side="left")
            v = tk.StringVar(value=self.cfg.get(key, default))
            self._v[key] = v
            tk.Entry(r, textvariable=v, font=MONO, bg=PANEL2,
                     fg="#ff6b35", insertbackground=FG, relief="flat",
                     bd=3).pack(side="left", fill="x", expand=True, padx=(4, 4))
            B(r, "\U0001f4c1", PANEL2, lambda k=key: self._browse_file(k),
              padx=5).pack(side="left")

        bf = tk.Frame(b, bg=BG)
        bf.pack(fill="x", pady=8)
        B(bf, "\U0001f4be 저장", GREEN, self._save,
          font=("Malgun Gothic", 11, "bold"), pady=8, padx=16).pack(
            side="left", padx=(0, 8))
        B(bf, "\U0001f50d MetaEditor 자동탐색", BLUE, self._detect,
          pady=8, padx=10).pack(side="left")
        self.sl = tk.Label(bf, text="", font=LBL, fg="#22c55e", bg=BG)
        self.sl.pack(side="left", padx=12)

        # 공용 폰트 크기 조정
        ff = tk.LabelFrame(b, text="  \U0001f524  공용 폰트 크기 조정 (모든 탭 한번에)",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        ff.pack(fill="x", pady=(4, 0))
        fr2 = tk.Frame(ff, bg=PANEL)
        fr2.pack(fill="x", padx=10, pady=8)
        tk.Label(fr2, text="폰트 pt:", font=LBL, fg=FG, bg=PANEL,
                 width=9, anchor="e").pack(side="left")
        self._fsz = tk.IntVar(value=9)
        tk.Spinbox(fr2, textvariable=self._fsz, from_=7, to=18, width=4,
                   font=MONO, bg=PANEL2, fg="#ff6b35", relief="flat", bd=2,
                   buttonbackground=PANEL2).pack(side="left", padx=(4, 8))
        B(fr2, "\u25c0 작게", "#374151",
          lambda: (self._fsz.set(max(7, self._fsz.get() - 1)),
                   self._apply_fsz()),
          pady=4, padx=8).pack(side="left", padx=2)
        B(fr2, "\u25b6 크게", BLUE,
          lambda: (self._fsz.set(min(18, self._fsz.get() + 1)),
                   self._apply_fsz()),
          pady=4, padx=8).pack(side="left", padx=2)
        B(fr2, "\u2705 적용", GREEN, self._apply_fsz,
          font=("Malgun Gothic", 10, "bold"), pady=4, padx=14).pack(
            side="left", padx=8)
        B(fr2, "\U0001f504 9pt 초기화", "#475569",
          lambda: (self._fsz.set(9), self._apply_fsz()),
          pady=4, padx=8).pack(side="left", padx=2)
        tk.Label(fr2, text="\u203b 적용 후 창 크기 살짝 드래그하면 레이아웃 갱신",
                 font=("Malgun Gothic", 8), fg="#94a3b8",
                 bg=PANEL).pack(side="left", padx=10)

    def _apply_fsz(self):
        _apply_font_sz(self.winfo_toplevel(), self._fsz.get())

    def _browse_file(self, key):
        p = filedialog.askopenfilename(filetypes=[("all", "*")])
        if p:
            self._v[key].set(p)

    def _save(self):
        d = {k: v.get() for k, v in self._v.items()}
        self.cfg.update(d)
        save_cfg(d)
        self.sl.config(
            text=f"\u2705 {datetime.datetime.now().strftime('%H:%M:%S')}")

    def _detect(self):
        found = find_me(4)
        for i, k in enumerate(["me1", "me2", "me3", "me4"]):
            if i < len(found):
                self._v[k].set(found[i])
        self.sl.config(text=f"탐색 {len(found)}개")
