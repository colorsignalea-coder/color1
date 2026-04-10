"""
ui/tab_bypass.py — EA Auto Master v6.0
========================================
라이센스 바이패스 탭: 체크박스 다중선택 + 4슬롯 병렬 컴파일.
"""
import glob
import os
import queue
import shutil
import threading
import time
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core.config import HERE, TODAY
from core.encoding import read_mq4
from core.mql4_engine import chk_status, do_bypass, compile_one
from core.path_finder import find_me, MAX_SLOTS
from ui.theme import (BG, FG, PANEL, PANEL2, ACCENT, BLUE, GREEN, RED, AMBER,
                      MONO, LBL, TITLE, B, LB, WL)


class BypassTab(ttk.Frame):
    CB_ON = "\u2611"
    CB_OFF = "\u2610"

    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        self.configure(style="D.TFrame")
        self._rows = []       # [(path, status, iid)]
        self._hidden = []     # detached iids for filter
        self._last_out = ""
        self._out_files = []
        self._stop = False
        self._build()

    # ================================================================
    # UI 구성
    # ================================================================

    def _build(self):
        _pv = tk.PanedWindow(self, orient="vertical", bg=BG,
                             sashwidth=5, sashrelief="groove", sashpad=2)
        _pv.pack(fill="both", expand=True, padx=10, pady=6)
        _top_b = tk.Frame(_pv, bg=BG)
        _pv.add(_top_b, height=220, minsize=100, sticky="nsew")
        _bot_b = tk.Frame(_pv, bg=BG)
        _pv.add(_bot_b, minsize=100, sticky="nsew")

        # ── 폴더 선택 ──
        f1 = tk.LabelFrame(_top_b, text="  \U0001f4c2  폴더 & 스캔",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        f1.pack(fill="x", pady=(0, 4))
        r = tk.Frame(f1, bg=PANEL)
        r.pack(fill="x", padx=8, pady=(5, 2))
        tk.Label(r, text="폴더:", font=LBL, fg=FG, bg=PANEL,
                 width=5, anchor="e").pack(side="left")
        self.folder = tk.StringVar(value=HERE)
        tk.Entry(r, textvariable=self.folder, font=MONO, bg=PANEL2,
                 fg=FG, insertbackground=FG, relief="flat",
                 bd=3).pack(side="left", fill="x", expand=True, padx=(4, 4))
        B(r, "\U0001f4c1", ACCENT, self._bfolder).pack(side="left")
        r2 = tk.Frame(f1, bg=PANEL)
        r2.pack(fill="x", padx=8, pady=(0, 5))
        self.recur = tk.BooleanVar(value=True)
        tk.Checkbutton(r2, text="하위폴더 재귀", variable=self.recur,
                       font=LBL, fg=FG, bg=PANEL, selectcolor="#444",
                       activebackground=PANEL,
                       activeforeground=FG).pack(side="left")
        self.sbn = B(r2, "\U0001f50d 스캔", BLUE, self._scan)
        self.sbn.pack(side="right")

        # ── 저장 옵션 ──
        f2 = tk.LabelFrame(_top_b, text="  \U0001f4be  저장 옵션",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        f2.pack(fill="x", pady=(0, 4))
        r3 = tk.Frame(f2, bg=PANEL)
        r3.pack(fill="x", padx=8, pady=4)
        self.mode = tk.StringVar(value="new")
        tk.Radiobutton(r3, text="새 파일", variable=self.mode, value="new",
                       font=LBL, fg=FG, bg=PANEL, selectcolor="#444",
                       activebackground=PANEL,
                       activeforeground=FG).pack(side="left", padx=(0, 10))
        tk.Radiobutton(r3, text="덮어쓰기(백업)", variable=self.mode,
                       value="overwrite", font=LBL, fg=FG, bg=PANEL,
                       selectcolor="#444", activebackground=PANEL,
                       activeforeground=FG).pack(side="left", padx=(0, 14))
        tk.Label(r3, text="접미사:", font=LBL, fg=FG,
                 bg=PANEL).pack(side="left")
        self.sfx = tk.StringVar(value=f"{TODAY}ok")
        tk.Entry(r3, textvariable=self.sfx, font=MONO, bg=PANEL2,
                 fg="#a3e635", insertbackground=FG, relief="flat", bd=3,
                 width=10).pack(side="left", padx=(4, 10))
        tk.Label(r3, text="출력폴더:", font=LBL, fg=FG,
                 bg=PANEL).pack(side="left")
        self.outf = tk.StringVar(value=f"new{TODAY}")
        tk.Entry(r3, textvariable=self.outf, font=MONO, bg=PANEL2,
                 fg="#38bdf8", insertbackground=FG, relief="flat", bd=3,
                 width=10).pack(side="left", padx=(4, 10))
        self.iso = tk.BooleanVar(value=False)
        tk.Checkbutton(r3, text="원본 격리\u2192old/", variable=self.iso,
                       font=LBL, fg="#f87171", bg=PANEL, selectcolor="#444",
                       activebackground=PANEL,
                       activeforeground=FG).pack(side="left")

        # ── MetaEditor 슬롯 ──
        f3 = tk.LabelFrame(_top_b, text="  \U0001f528  MetaEditor 슬롯",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        f3.pack(fill="x", pady=(0, 4))
        auto = find_me(MAX_SLOTS)
        self.me_v = []
        self.me_e = []
        self.me_s = []
        row_f = tk.Frame(f3, bg=PANEL)
        row_f.pack(fill="x", padx=8, pady=4)
        for i in range(MAX_SLOTS):
            p = auto[i] if i < len(auto) else ""
            ev = tk.BooleanVar(value=bool(p))
            mv = tk.StringVar(value=p)
            self.me_v.append(mv)
            self.me_e.append(ev)
            col = tk.Frame(row_f, bg=PANEL)
            col.pack(side="left", fill="x", expand=True, padx=(0, 8))
            hdr = tk.Frame(col, bg=PANEL)
            hdr.pack(fill="x")
            tk.Checkbutton(hdr, text=f"슬롯{i+1}", variable=ev,
                           font=("Malgun Gothic", 8), fg=FG, bg=PANEL,
                           selectcolor="#444", activebackground=PANEL,
                           activeforeground=FG).pack(side="left")
            sl = tk.Label(hdr, text="\u25cf", font=("Consolas", 10),
                          fg="#22c55e" if p else "#475569", bg=PANEL)
            sl.pack(side="right")
            self.me_s.append(sl)
            tk.Entry(col, textvariable=mv, font=("Consolas", 7), bg=PANEL2,
                     fg="#ff6b35", insertbackground=FG, relief="flat",
                     bd=2).pack(fill="x", pady=(2, 0))
        rc = tk.Frame(f3, bg=PANEL)
        rc.pack(fill="x", padx=8, pady=(2, 5))
        self.ac = tk.BooleanVar(value=False)
        tk.Checkbutton(rc, text="바이패스 후 자동컴파일", variable=self.ac,
                       font=LBL, fg="#ff6b35", bg=PANEL, selectcolor="#444",
                       activebackground=PANEL,
                       activeforeground=FG).pack(side="left")
        self.slbl = tk.Label(rc, text="", font=LBL, fg="#94a3b8", bg=PANEL)
        self.slbl.pack(side="left", padx=10)
        B(rc, "슬롯 검증", BLUE, self._verify, pady=3, padx=8).pack(
            side="right")

        # ── 파일 목록 ──
        f4 = tk.LabelFrame(_bot_b,
                           text="  \U0001f4cb  파일 목록 (클릭으로 선택/해제)",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        f4.pack(fill="both", expand=True, pady=(0, 4))

        tb = tk.Frame(f4, bg=PANEL)
        tb.pack(fill="x", padx=8, pady=(5, 2))
        B(tb, "\u2611 전체선택", GREEN, self._sel_all, pady=3,
          padx=8).pack(side="left", padx=(0, 4))
        B(tb, "\u2610 전체해제", "#475569", self._sel_none, pady=3,
          padx=8).pack(side="left", padx=(0, 4))
        B(tb, "\u2194 반전", "#374151", self._sel_inv, pady=3,
          padx=8).pack(side="left", padx=(0, 10))
        tk.Label(tb, text="필터:", font=LBL, fg=FG,
                 bg=PANEL).pack(side="left")
        self.flt = tk.StringVar()
        self.flt.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(tb, textvariable=self.flt, font=MONO, bg=PANEL2,
                 fg="#a3e635", insertbackground=FG, relief="flat", bd=3,
                 width=18).pack(side="left", padx=(4, 0))
        self.cnt_lbl = tk.Label(tb, text="", font=LBL, fg="#94a3b8",
                                bg=PANEL)
        self.cnt_lbl.pack(side="right")

        cols = ("\u2713", "#", "상태", "파일명", "ex4", "폴더")
        self.tree = ttk.Treeview(f4, columns=cols, show="headings", height=8)
        self.tree.heading("\u2713", text="\u2713", anchor="center")
        self.tree.heading("#", text="#", anchor="center")
        self.tree.heading("상태", text="상태", anchor="center")
        self.tree.heading("파일명", text="파일명", anchor="w")
        self.tree.heading("ex4", text=".ex4", anchor="center")
        self.tree.heading("폴더", text="폴더", anchor="w")
        self.tree.column("\u2713", width=30, anchor="center", stretch=False)
        self.tree.column("#", width=40, anchor="center", stretch=False)
        self.tree.column("상태", width=110, anchor="center", stretch=False)
        self.tree.column("파일명", width=260, anchor="w")
        self.tree.column("ex4", width=48, anchor="center", stretch=False)
        self.tree.column("폴더", width=300, anchor="w")
        for tag, clr in [
            ("DONE", "#22c55e"), ("HAS", "#f59e0b"), ("NO", "#475569"),
            ("OK", "#60a5fa"), ("FAIL", "#ef4444"), ("COK", "#a3e635"),
            ("CFAIL", "#f87171"), ("SEL", "#7c3aed"),
        ]:
            self.tree.tag_configure(tag, foreground=clr)
        vsb = ttk.Scrollbar(f4, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True,
                       padx=(8, 0), pady=5)
        vsb.pack(side="right", fill="y", pady=5)
        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.bind("<space>", lambda e: self._toggle_sel())

        # 진행바
        pf = tk.Frame(_bot_b, bg=BG)
        pf.pack(fill="x", pady=(0, 2))
        self.pb = ttk.Progressbar(pf, mode="determinate",
                                  style="green.Horizontal.TProgressbar")
        self.pb.pack(fill="x")
        self.pb_lbl = tk.Label(pf, text="대기 중",
                               font=("Malgun Gothic", 8), fg="#94a3b8", bg=BG)
        self.pb_lbl.pack(anchor="e")

        # 로그
        f5 = tk.LabelFrame(_bot_b, text="  \U0001f4dc  로그",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        f5.pack(fill="both", expand=True, pady=(0, 4))
        self.log = LB(f5, 4)
        self.log.pack(fill="both", expand=True, padx=8, pady=4)

        # 버튼
        bf = tk.Frame(_bot_b, bg=BG)
        bf.pack(fill="x")
        self.run_btn = B(bf, "\U0001f680 바이패스 실행", ACCENT, self._run,
                         font=("Malgun Gothic", 11, "bold"), pady=8, padx=14)
        self.run_btn.pack(side="left", padx=(0, 5))
        self.cmp_btn = B(bf, "\U0001f528 컴파일만", AMBER, self._conly,
                         pady=8, padx=10)
        self.cmp_btn.pack(side="left", padx=(0, 5))
        self.stp_btn = B(bf, "\u23f9 중지", RED, self._do_stop,
                         pady=8, padx=8)
        self.stp_btn.config(state="disabled")
        self.stp_btn.pack(side="left", padx=(0, 10))
        B(bf, "\U0001f5d1 로그", "#374151",
          lambda: self.log.delete("1.0", "end"), pady=8,
          padx=6).pack(side="left", padx=(0, 4))
        B(bf, "\U0001f4c2 결과", GREEN, self._open_out, pady=8,
          padx=8).pack(side="left")
        self.stat = tk.Label(bf, text="", font=LBL, fg="#94a3b8", bg=BG)
        self.stat.pack(side="right")
        self.after(100, self._verify)

    # ================================================================
    # 체크박스 토글
    # ================================================================

    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        col = self.tree.identify_column(event.x)
        if col == "#1" or region == "cell":
            iid = self.tree.identify_row(event.y)
            if iid:
                self._toggle_iid(iid)

    def _toggle_iid(self, iid):
        cur = self.tree.set(iid, "\u2713")
        self.tree.set(iid, "\u2713",
                      self.CB_ON if cur == self.CB_OFF else self.CB_OFF)
        self._update_cnt()

    def _toggle_sel(self):
        for iid in self.tree.selection():
            self._toggle_iid(iid)

    def _sel_all(self):
        for iid in self.tree.get_children():
            self.tree.set(iid, "\u2713", self.CB_ON)
        self._update_cnt()

    def _sel_none(self):
        for iid in self.tree.get_children():
            self.tree.set(iid, "\u2713", self.CB_OFF)
        self._update_cnt()

    def _sel_inv(self):
        for iid in self.tree.get_children():
            cur = self.tree.set(iid, "\u2713")
            self.tree.set(iid, "\u2713",
                          self.CB_ON if cur == self.CB_OFF else self.CB_OFF)
        self._update_cnt()

    def _update_cnt(self):
        total = len(self.tree.get_children())
        sel = sum(1 for iid in self.tree.get_children()
                  if self.tree.set(iid, "\u2713") == self.CB_ON)
        self.cnt_lbl.config(text=f"선택 {sel}/{total}")

    def _apply_filter(self):
        kw = self.flt.get().strip().lower()
        for iid in self._hidden:
            self.tree.reattach(iid, "", "end")
        self._hidden = []
        if kw:
            for iid in self.tree.get_children():
                fn = self.tree.set(iid, "파일명").lower()
                fd = self.tree.set(iid, "폴더").lower()
                if kw not in fn and kw not in fd:
                    self.tree.detach(iid)
                    self._hidden.append(iid)
        self._update_cnt()

    def _get_selected(self):
        selected = []
        for p, st, iid in self._rows:
            try:
                if self.tree.set(iid, "\u2713") == self.CB_ON:
                    selected.append((p, st, iid))
            except Exception:
                pass
        return selected

    # ================================================================
    # 슬롯 & 스캔
    # ================================================================

    def _verify(self):
        active = []
        for i in range(MAX_SLOTS):
            p = self.me_v[i].get().strip()
            ok = self.me_e[i].get() and os.path.exists(p)
            self.me_s[i].config(fg="#22c55e" if ok else "#475569")
            if ok:
                active.append(p)
        n = len(active)
        self.slbl.config(text=f"활성 {n}개" if n else "없음")
        return active

    def _active_me(self):
        return [self.me_v[i].get().strip() for i in range(MAX_SLOTS)
                if self.me_e[i].get()
                and os.path.exists(self.me_v[i].get().strip())]

    def _bfolder(self):
        d = filedialog.askdirectory(initialdir=self.folder.get())
        if d:
            self.folder.set(d)
            self._scan()

    def _wlog(self, msg, tag="i"):
        WL(self.log, msg, tag)

    def _scan(self):
        folder = self.folder.get()
        if not os.path.isdir(folder):
            messagebox.showerror("오류", f"폴더 없음:\n{folder}")
            return
        self.sbn.config(state="disabled", text="\u23f3 스캔...")
        self.run_btn.config(state="disabled")
        self.cmp_btn.config(state="disabled")
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._rows.clear()
        self._hidden = []
        self.stat.config(text="스캔 중...")
        threading.Thread(target=self._scan_worker, args=(folder,),
                         daemon=True).start()

    def _scan_worker(self, folder):
        if self.recur.get():
            files = sorted(
                os.path.join(r, f) for r, _, fs in os.walk(folder)
                for f in fs if f.lower().endswith('.mq4'))
        else:
            files = sorted(glob.glob(os.path.join(folder, '*.mq4')))

        lmap = {
            "DONE": ("\u2705 완료", "DONE"),
            "HAS_LICENSE": ("\u26a0\ufe0f 처리필요", "HAS"),
            "NO_LICENSE": ("\u2014 없음", "NO"),
            "ERROR": ("\u2716 오류", "FAIL"),
        }
        d = h = n = 0
        for idx, path in enumerate(files):
            try:
                content, _ = read_mq4(path)
                st = chk_status(content)
            except Exception:
                st = "ERROR"
            fname = os.path.basename(path)
            rel = os.path.relpath(os.path.dirname(path), folder)
            if rel == ".":
                rel = "(루트)"
            ex4 = "\u2b55" if os.path.exists(path[:-4] + ".ex4") else "\u274c"
            lbl, tag = lmap.get(st, (st, "NO"))
            num = idx + 1

            def _add(p=path, s=st, l=lbl, tg=tag, fn=fname, r=rel,
                     e4=ex4, ni=num, tot=len(files)):
                iid = self.tree.insert(
                    "", "end", values=(self.CB_OFF, ni, l, fn, e4, r),
                    tags=(tg,))
                self._rows.append((p, s, iid))
                self.pb_lbl.config(text=f"스캔 {ni}/{tot}")
            self.after(0, _add)
            if st == "DONE":
                d += 1
            elif st == "HAS_LICENSE":
                h += 1
            else:
                n += 1

        def _done(tot=len(files), h=h, d=d, n=n):
            self.stat.config(
                text=f"총 {tot} | 처리필요 {h} | 완료 {d} | 없음 {n}")
            self._wlog(
                f"스캔 완료 {tot}개 \u2014 처리필요 {h}개 / \u2611 클릭으로 선택")
            self.sbn.config(state="normal", text="\U0001f50d 스캔")
            self.run_btn.config(state="normal")
            self.cmp_btn.config(state="normal")
            self._update_cnt()
            for p, st, iid in self._rows:
                if st == "HAS_LICENSE":
                    self.tree.set(iid, "\u2713", self.CB_ON)
            self._update_cnt()
        self.after(0, _done)

    # ================================================================
    # 바이패스 실행
    # ================================================================

    def _run(self):
        targets = [(p, iid) for p, st, iid in self._get_selected()
                   if st == "HAS_LICENSE"]
        if not targets:
            targets = [(p, iid) for p, st, iid in self._rows
                       if st == "HAS_LICENSE"]
        if not targets:
            self._wlog("처리할 파일 없음 (\u26a0\ufe0f 처리필요 0개)")
            return
        self._stop = False
        self.run_btn.config(state="disabled", text="\u23f3 처리 중...")
        self.cmp_btn.config(state="disabled")
        self.stp_btn.config(state="normal")
        threading.Thread(target=self._run_worker, args=(targets,),
                         daemon=True).start()

    def _run_worker(self, targets):
        sfx = self.sfx.get().strip()
        mode = self.mode.get()
        outf = self.outf.get().strip() or f"new{TODAY}"
        do_iso = self.iso.get() and mode == "new"
        total = len(targets)
        ok = fail = iso_cnt = 0
        self._out_files = []
        self.pb["maximum"] = total
        self.pb["value"] = 0
        self._wlog(f"바이패스 시작: {total}개")
        st = time.time()
        for i, (src, iid) in enumerate(targets):
            if self._stop:
                self._wlog("\u23f9 중단", "e")
                break
            fn = os.path.basename(src)
            e = time.time() - st
            rate = (i / e) if e > 0 else 0.01
            eta = int((total - i) / rate) if rate > 0 else 0
            self.after(0, lambda v=i + 1,
                       s=f"[{i+1}/{total}] {fn}  ETA {eta//60}m{eta%60}s": (
                           self.pb.config(value=v),
                           self.pb_lbl.config(text=s)))
            self._wlog(f"[{i+1}/{total}] {fn}")
            base, ext = os.path.splitext(fn)
            if mode == "new":
                od = os.path.join(os.path.dirname(src), outf)
                os.makedirs(od, exist_ok=True)
                op = os.path.join(od, base + sfx + ext)
                self._last_out = od
            else:
                op = src
                try:
                    shutil.copy2(src, src + ".bak")
                except Exception as e2:
                    self._wlog(f"  백업실패: {e2}", "e")
            try:
                mod, msg = do_bypass(src, op, log_fn=self._wlog)
                if mod:
                    ok += 1
                    self._out_files.append(op)
                    if do_iso:
                        sd = os.path.dirname(src)
                        od2 = os.path.join(sd, "old")
                        os.makedirs(od2, exist_ok=True)
                        sx4 = src[:-4] + ".ex4"
                        try:
                            shutil.move(
                                src,
                                os.path.join(od2, os.path.basename(src)))
                            if os.path.exists(sx4):
                                shutil.move(
                                    sx4,
                                    os.path.join(od2, os.path.basename(sx4)))
                            iso_cnt += 1
                            self._wlog("  [격리] \u2192 old/")
                        except Exception as e3:
                            self._wlog(f"  [격리실패] {e3}", "e")
                    self.after(0, lambda iid=iid, n=os.path.basename(op): (
                        self.tree.set(iid, "상태", f"\u2714 {n}"),
                        self.tree.item(iid, tags=("OK",))))
                else:
                    fail += 1
                    self.after(0, lambda iid=iid, m=msg:
                               self.tree.set(iid, "상태", f"\u2014 {m}"))
                    self._wlog(f"  => {msg}")
            except Exception as e4:
                fail += 1
                self.after(0, lambda iid=iid: (
                    self.tree.set(iid, "상태", "\u2716 오류"),
                    self.tree.item(iid, tags=("FAIL",))))
                self._wlog(f"  오류: {e4}", "e")
        self.after(0, lambda: self.pb.config(value=total))
        iso_msg = f" / 격리 {iso_cnt}" if do_iso else ""
        self._wlog(f"\u2705 완료: 성공 {ok} / 실패 {fail}{iso_msg}", "o")
        if self.ac.get() and self._out_files and not self._stop:
            self._wlog("\u2500\u2500\u2500 자동 컴파일 \u2500\u2500\u2500")
            self._compile_worker(self._out_files)
        else:
            self._reset_buttons()
            if (mode == "new" and self._last_out
                    and os.path.isdir(self._last_out)):
                subprocess.run(["start", "", self._last_out], shell=True)

    # ================================================================
    # 컴파일
    # ================================================================

    def _conly(self):
        sel = self._get_selected()
        t = (list(self._out_files) if self._out_files
             else ([p for p, st, iid in sel] if sel
                   else [p for p, st, iid in self._rows]))
        if not t:
            messagebox.showwarning("알림", "파일 없음")
            return
        if not self._active_me():
            messagebox.showerror("슬롯 없음", "MetaEditor 슬롯 없음")
            return
        self._stop = False
        self.run_btn.config(state="disabled")
        self.cmp_btn.config(state="disabled", text="\u23f3 컴파일...")
        self.stp_btn.config(state="normal")
        threading.Thread(target=self._compile_worker, args=(t,),
                         daemon=True).start()

    def _compile_worker(self, mq4s):
        ame = self._active_me()
        if not ame:
            self._wlog("활성 슬롯 없음", "e")
            self._reset_buttons()
            return
        ns = len(ame)
        total = len(mq4s)
        self._wlog(f"컴파일: {total}개 / {ns}슬롯")
        self.after(0, lambda: self.pb.config(maximum=total, value=0))
        ld = os.path.join(os.path.dirname(mq4s[0]), "compile_logs")
        os.makedirs(ld, exist_ok=True)
        q_items = queue.Queue()
        for m in mq4s:
            q_items.put(m)
        res = []
        lock = threading.Lock()
        cnt = [0]
        st = time.time()
        p2i = {p: iid for p, _, iid in self._rows}

        def worker(me, si):
            while not self._stop:
                try:
                    mq4 = q_items.get_nowait()
                except queue.Empty:
                    break
                fn = os.path.basename(mq4)
                ok2, msg = compile_one(me, mq4, ld)
                with lock:
                    cnt[0] += 1
                    c = cnt[0]
                    e = time.time() - st
                    r = (c / e) if e > 0 else 0.01
                    eta2 = int((total - c) / r) if r > 0 else 0
                    res.append((fn, ok2, msg))
                tg = "o" if ok2 else "e"
                ic = "\u2705" if ok2 else "\u274c"
                log_msg = f"  슬롯{si+1} {ic} {fn}"
                if not ok2:
                    log_msg += f": {msg[:60]}"
                self.after(0, lambda s=log_msg, tgg=tg:
                           self._wlog(s, tgg))
                iid = p2i.get(mq4)
                if iid:
                    if ok2:
                        self.after(0, lambda i=iid: (
                            self.tree.set(i, "상태", "\U0001f528 완료"),
                            self.tree.set(i, "ex4", "\u2b55"),
                            self.tree.item(i, tags=("COK",))))
                    else:
                        self.after(0, lambda i=iid: (
                            self.tree.set(i, "상태", "\U0001f528 오류"),
                            self.tree.item(i, tags=("CFAIL",))))
                self.after(0, lambda v=c,
                           s=f"컴파일 [{c}/{total}] "
                             f"ETA {eta2//60}m{eta2%60}s": (
                               self.pb.config(value=v),
                               self.pb_lbl.config(text=s)))
                q_items.task_done()

        ts2 = [threading.Thread(target=worker, args=(me, i), daemon=True)
               for i, me in enumerate(ame)]
        for t in ts2:
            t.start()
        for t in ts2:
            t.join()
        ok2 = sum(1 for _, o, _ in res if o)
        fail = len(res) - ok2
        self._wlog(
            f"\U0001f528 컴파일 완료: 성공 {ok2} / 실패 {fail}  ({ns}슬롯)",
            "o")
        self._reset_buttons()
        if self._last_out and os.path.isdir(self._last_out):
            subprocess.run(["start", "", self._last_out], shell=True)

    # ================================================================
    # 유틸
    # ================================================================

    def _do_stop(self):
        self._stop = True
        self._wlog("\u23f9 중지", "e")

    def _reset_buttons(self):
        self.after(0, lambda: (
            self.run_btn.config(
                state="normal", text="\U0001f680 바이패스 실행"),
            self.cmp_btn.config(state="normal", text="\U0001f528 컴파일만"),
            self.stp_btn.config(state="disabled")))

    def _open_out(self):
        if self._last_out and os.path.isdir(self._last_out):
            subprocess.run(["start", "", self._last_out], shell=True)
        else:
            messagebox.showinfo("결과", "폴더 없음")
