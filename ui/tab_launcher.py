"""
ui/tab_launcher.py — EA Auto Master v6.0
=========================================
외부 스크립트 실행 탭 (EA_AUTO_BUILDER, EA_OPTIMIZER_GUI 런처).
"""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ui.theme import BG, FG, PANEL, PANEL2, ACCENT, RED, MONO, LBL, TITLE, B, LB, WL


class LauncherTab(ttk.Frame):
    def __init__(self, nb, label, script, cfg):
        super().__init__(nb)
        self.label = label
        self._proc = None
        self._build(script)

    def _build(self, script):
        b = tk.Frame(self, bg=BG)
        b.pack(fill="both", expand=True, padx=10, pady=8)

        # 경로 입력
        pf = tk.Frame(b, bg=BG)
        pf.pack(fill="x", pady=(0, 8))
        tk.Label(pf, text="스크립트:", font=LBL, fg=FG, bg=BG,
                 width=9, anchor="e").pack(side="left")
        self.path = tk.StringVar(value=script)
        tk.Entry(pf, textvariable=self.path, font=MONO, bg=PANEL2,
                 fg="#ff6b35", insertbackground=FG, relief="flat",
                 bd=3).pack(side="left", fill="x", expand=True, padx=(4, 4))
        B(pf, "\U0001f4c1", PANEL2, self._browse, padx=5).pack(side="left")

        # 상태
        sf = tk.Frame(b, bg=BG)
        sf.pack(fill="x", pady=(0, 6))
        self.dot = tk.Label(sf, text="\u25cf", font=("Consolas", 16),
                            fg="#475569", bg=BG)
        self.dot.pack(side="left")
        self.slbl = tk.Label(sf, text="미실행",
                             font=("Malgun Gothic", 10, "bold"),
                             fg="#94a3b8", bg=BG)
        self.slbl.pack(side="left", padx=6)
        self.plbl = tk.Label(sf, text="", font=LBL, fg="#64748b", bg=BG)
        self.plbl.pack(side="left", padx=10)

        # 버튼
        bf = tk.Frame(b, bg=BG)
        bf.pack(fill="x", pady=(0, 8))
        self.lb = B(bf, f"\U0001f680 {self.label} 실행", ACCENT, self._launch,
                     font=("Malgun Gothic", 11, "bold"), pady=8, padx=16)
        self.lb.pack(side="left", padx=(0, 8))
        self.sb = B(bf, "\u23f9 종료", RED, self._stop, pady=8, padx=10)
        self.sb.config(state="disabled")
        self.sb.pack(side="left", padx=(0, 8))
        B(bf, "\U0001f5d1 로그", "#374151",
          lambda: self.log.delete("1.0", "end"), pady=8, padx=6).pack(side="right")

        # 로그
        fl = tk.LabelFrame(b, text="  \U0001f4dc  로그", font=TITLE, fg=FG,
                           bg=PANEL, relief="groove", bd=2)
        fl.pack(fill="both", expand=True)
        self.log = LB(fl, 18)
        self.log.pack(fill="both", expand=True, padx=8, pady=5)

    def _browse(self):
        p = filedialog.askopenfilename(filetypes=[("py", "*.py"), ("all", "*")])
        if p:
            self.path.set(p)

    def _launch(self):
        p = self.path.get().strip()
        if not os.path.exists(p):
            messagebox.showerror("오류", f"없음:\n{p}")
            return
        if self._proc and self._proc.poll() is None:
            messagebox.showinfo("알림", "이미 실행 중")
            return
        try:
            self._proc = subprocess.Popen(
                [sys.executable, p],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                cwd=os.path.dirname(p),
                creationflags=subprocess.CREATE_NO_WINDOW)
            self._update_status(True)
            WL(self.log, f"PID: {self._proc.pid}", "o")
            threading.Thread(target=self._read_output, daemon=True).start()
        except Exception as e:
            WL(self.log, f"실패: {e}", "e")

    def _read_output(self):
        try:
            for line in self._proc.stdout:
                if any(k in line for k in ["Error", "error", "실패"]):
                    t = "e"
                elif any(k in line for k in ["\u2705", "성공", "OK"]):
                    t = "o"
                else:
                    t = "i"
                self.after(0, lambda l=line.rstrip(), tg=t: WL(self.log, l, tg))
        except Exception:
            pass
        rc = self._proc.wait() if self._proc else -1
        self.after(0, lambda: (
            self._update_status(False),
            WL(self.log, f"종료({rc})", "o" if rc == 0 else "e")))

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            WL(self.log, "종료 요청", "w")
        self._update_status(False)

    def _update_status(self, on):
        self.dot.config(fg="#22c55e" if on else "#475569")
        self.slbl.config(text="실행 중" if on else "미실행",
                         fg="#22c55e" if on else "#94a3b8")
        self.plbl.config(
            text=f"PID:{self._proc.pid}" if on and self._proc else "")
        self.lb.config(state="disabled" if on else "normal")
        self.sb.config(state="normal" if on else "disabled")
