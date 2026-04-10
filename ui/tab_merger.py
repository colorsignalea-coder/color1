"""
ui/tab_merger.py — EA Auto Master v6.0
========================================
모듈 합치기 탭: EA A + 모듈 B/C/D 함수 주입 + 컴파일.
"""
import glob
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from core.encoding import read_mq4, write_mq4, fix_bom_date
from core.mql4_engine import compile_one
from core.mql4_merger import parse_mq4_blocks, extract_module_for_inject, inject_into_base
from core.path_finder import find_me
from ui.theme import (BG, FG, PANEL, PANEL2, ACCENT, BLUE, GREEN, RED, CYAN,
                      MONO, LBL, TITLE, B, LB, WL)


class MergerTab(ttk.Frame):
    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        self._modules = []
        self._build()

    def _build(self):
        b = tk.Frame(self, bg=BG)
        b.pack(fill="both", expand=True, padx=10, pady=8)

        main = tk.PanedWindow(b, orient="horizontal", bg=BG,
                              sashwidth=5, sashrelief="groove", sashpad=2)
        main.pack(fill="both", expand=True, pady=(0, 5))

        # ── 왼쪽: 베이스 EA ──
        lp = tk.LabelFrame(main, text="  \U0001f3af  베이스 EA", font=TITLE,
                           fg=FG, bg=PANEL, relief="groove", bd=2)
        main.add(lp, width=380, minsize=200, sticky="nsew")
        rf = tk.Frame(lp, bg=PANEL)
        rf.pack(fill="x", padx=8, pady=(6, 4))
        tk.Label(rf, text="파일:", font=LBL, fg=FG, bg=PANEL,
                 width=5, anchor="e").pack(side="left")
        self.base_v = tk.StringVar()
        tk.Entry(rf, textvariable=self.base_v, font=MONO, bg=PANEL2,
                 fg="#ff6b35", insertbackground=FG, relief="flat",
                 bd=3).pack(side="left", fill="x", expand=True, padx=(4, 4))
        B(rf, "\U0001f4c1", PANEL2, self._sel_base, padx=5).pack(side="left")
        B(lp, "\U0001f50d 분석", BLUE, self._analyze_base, pady=3,
          padx=8).pack(padx=8, pady=(0, 4), anchor="w")
        self.base_info = scrolledtext.ScrolledText(
            lp, height=12, font=MONO, bg="#12121e", fg="#a3e635",
            relief="flat", bd=2)
        self.base_info.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # ── 오른쪽: 모듈 목록 ──
        rp = tk.LabelFrame(main, text="  \U0001f9e9  주입할 모듈 파일들",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        main.add(rp, minsize=200, sticky="nsew")
        rb = tk.Frame(rp, bg=PANEL)
        rb.pack(fill="x", padx=8, pady=(6, 4))
        B(rb, "+ 모듈 추가", GREEN, self._add_mod, pady=3,
          padx=8).pack(side="left", padx=(0, 4))
        B(rb, "폴더 스캔", BLUE, self._scan_mod_folder, pady=3,
          padx=8).pack(side="left", padx=(0, 4))
        B(rb, "선택 삭제", RED, self._del_mod, pady=3,
          padx=6).pack(side="left")

        self.mod_tree = ttk.Treeview(
            rp, columns=("\u2713", "파일명", "감지", "크기"),
            show="headings", height=8)
        self.mod_tree.heading("\u2713", text="\u2713", anchor="center")
        self.mod_tree.column("\u2713", width=30, anchor="center", stretch=False)
        self.mod_tree.heading("파일명", text="파일명", anchor="w")
        self.mod_tree.column("파일명", width=200, anchor="w")
        self.mod_tree.heading("감지", text="감지 신호", anchor="w")
        self.mod_tree.column("감지", width=130, anchor="w")
        self.mod_tree.heading("크기", text="크기", anchor="center")
        self.mod_tree.column("크기", width=60, anchor="center", stretch=False)
        self.mod_tree.pack(fill="both", expand=True, padx=8, pady=5)
        self.mod_tree.bind("<ButtonRelease-1>", self._mod_click)

        B(rp, "\U0001f50d 선택 모듈 분석", CYAN, self._analyze_mod, pady=4,
          padx=10).pack(padx=8, pady=(0, 4), anchor="w")
        self.mod_info = scrolledtext.ScrolledText(
            rp, height=6, font=MONO, bg="#12121e", fg="#60a5fa",
            relief="flat", bd=2)
        self.mod_info.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # ── 함수 선택 & 합치기 ──
        f3 = tk.LabelFrame(b, text="  \u26a1  함수 선택 & 합치기",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        f3.pack(fill="x", pady=(0, 4))
        fr = tk.Frame(f3, bg=PANEL)
        fr.pack(fill="x", padx=8, pady=6)
        tk.Label(fr, text="주입할 함수 (쉼표 구분 또는 빈칸=전체):",
                 font=LBL, fg=FG, bg=PANEL).pack(side="left")
        self.fn_var = tk.StringVar()
        tk.Entry(fr, textvariable=self.fn_var, font=MONO, bg=PANEL2,
                 fg="#a3e635", insertbackground=FG, relief="flat",
                 bd=3).pack(side="left", fill="x", expand=True, padx=(8, 8))
        tk.Label(f3, text="출력 파일명:", font=LBL, fg=FG,
                 bg=PANEL).pack(side="left", padx=(8, 4))
        self.out_v = tk.StringVar(value="merged_EA.mq4")
        tk.Entry(f3, textvariable=self.out_v, font=MONO, bg=PANEL2,
                 fg="#ff6b35", insertbackground=FG, relief="flat", bd=3,
                 width=24).pack(side="left", padx=(0, 8))

        bf = tk.Frame(f3, bg=PANEL)
        bf.pack(fill="x", padx=8, pady=(4, 8))
        B(bf, "\U0001f500 합치기 실행", ACCENT, self._merge,
          font=("Malgun Gothic", 11, "bold"), pady=8,
          padx=14).pack(side="left", padx=(0, 8))
        me_list = find_me(1)
        self.me_v2 = tk.StringVar(value=me_list[0] if me_list else "")
        tk.Label(bf, text="MetaEditor:", font=LBL, fg=FG,
                 bg=PANEL).pack(side="left")
        tk.Entry(bf, textvariable=self.me_v2, font=MONO, bg=PANEL2,
                 fg="#ff6b35", insertbackground=FG, relief="flat", bd=3,
                 width=36).pack(side="left", padx=(4, 4))
        B(bf, "\U0001f4c1", PANEL2,
          lambda: self._bfme(self.me_v2), padx=5).pack(side="left",
                                                         padx=(0, 8))
        self.auto_cmp = tk.BooleanVar(value=True)
        tk.Checkbutton(bf, text="합친 후 자동컴파일", variable=self.auto_cmp,
                       font=LBL, fg="#ff6b35", bg=PANEL, selectcolor="#444",
                       activebackground=PANEL,
                       activeforeground=FG).pack(side="left")

        # 로그
        fl = tk.LabelFrame(b, text="  \U0001f4dc  로그", font=TITLE, fg=FG,
                           bg=PANEL, relief="groove", bd=2)
        fl.pack(fill="both", expand=True)
        self.log = LB(fl, 5)
        self.log.pack(fill="both", expand=True, padx=8, pady=5)

    # ================================================================
    # 베이스 EA
    # ================================================================

    def _sel_base(self):
        p = filedialog.askopenfilename(
            filetypes=[("MQ4", "*.mq4"), ("all", "*")])
        if p:
            self.base_v.set(p)
            self.out_v.set("merged_" + os.path.basename(p))

    def _bfme(self, v):
        p = filedialog.askopenfilename(
            filetypes=[("exe", "*.exe"), ("all", "*")])
        if p:
            v.set(p)

    def _analyze_base(self):
        p = self.base_v.get().strip()
        if not os.path.exists(p):
            messagebox.showerror("오류", "베이스 EA 없음")
            return
        try:
            content, _ = read_mq4(p)
            blks = parse_mq4_blocks(content)
            self.base_info.delete("1.0", "end")
            self.base_info.insert("end", f"파일: {os.path.basename(p)}\n")
            self.base_info.insert(
                "end", f"파라미터 수: {len(blks['params'])}\n")
            self.base_info.insert("end", f"함수 수: {len(blks['funcs'])}\n")
            sigs = ', '.join(blks['signals']) or '없음'
            self.base_info.insert("end", f"감지 신호: {sigs}\n\n")
            self.base_info.insert("end", "\u2500\u2500\u2500 파라미터 \u2500\u2500\u2500\n")
            for t, n, v in blks['params'][:20]:
                self.base_info.insert("end", f"  {t} {n} = {v}\n")
            self.base_info.insert("end", "\n\u2500\u2500\u2500 함수 목록 \u2500\u2500\u2500\n")
            for fn in list(blks['funcs'].keys())[:30]:
                self.base_info.insert("end", f"  {fn}()\n")
            WL(self.log,
               f"베이스 분석: 파라미터 {len(blks['params'])}개, "
               f"함수 {len(blks['funcs'])}개, 신호: {blks['signals']}")
        except Exception as e:
            WL(self.log, f"분석 오류: {e}", "e")

    # ================================================================
    # 모듈 관리
    # ================================================================

    def _add_mod(self):
        ps = filedialog.askopenfilenames(
            filetypes=[("MQ4", "*.mq4"), ("all", "*")])
        for p in ps:
            self._add_mod_file(p)

    def _scan_mod_folder(self):
        d = filedialog.askdirectory()
        if not d:
            return
        for p in sorted(glob.glob(os.path.join(d, "*.mq4"))):
            self._add_mod_file(p)

    def _add_mod_file(self, p):
        if any(m[0] == p for m in self._modules):
            return
        try:
            content, _ = read_mq4(p)
            blks = parse_mq4_blocks(content)
            sigs = ", ".join(blks['signals'][:4]) or "\u2014"
            size = f"{os.path.getsize(p) // 1024}KB"
            iid = self.mod_tree.insert(
                "", "end",
                values=("\u2610", os.path.basename(p), sigs, size))
            self._modules.append((p, blks, iid))
        except Exception as e:
            WL(self.log, f"모듈 추가 실패 {os.path.basename(p)}: {e}", "e")

    def _mod_click(self, event):
        col = self.mod_tree.identify_column(event.x)
        iid = self.mod_tree.identify_row(event.y)
        if iid and col == "#1":
            cur = self.mod_tree.set(iid, "\u2713")
            self.mod_tree.set(
                iid, "\u2713", "\u2611" if cur == "\u2610" else "\u2610")

    def _del_mod(self):
        for iid in self.mod_tree.selection():
            self.mod_tree.delete(iid)
            self._modules = [m for m in self._modules if m[2] != iid]

    def _analyze_mod(self):
        sel = [m for m in self._modules
               if self.mod_tree.set(m[2], "\u2713") == "\u2611"]
        if not sel:
            sel = self._modules[:1]
        if not sel:
            return
        self.mod_info.delete("1.0", "end")
        for path, blks, _ in sel:
            self.mod_info.insert(
                "end", f"=== {os.path.basename(path)} ===\n")
            self.mod_info.insert(
                "end", f"신호: {', '.join(blks['signals'])}\n")
            self.mod_info.insert(
                "end",
                f"함수: {', '.join(list(blks['funcs'].keys())[:15])}\n")
            self.mod_info.insert(
                "end", f"iCustom: {', '.join(blks['icustom'][:5])}\n\n")

    # ================================================================
    # 합치기 실행
    # ================================================================

    def _merge(self):
        base_p = self.base_v.get().strip()
        if not os.path.exists(base_p):
            messagebox.showerror("오류", "베이스 EA 없음")
            return
        sel_mods = [m for m in self._modules
                    if self.mod_tree.set(m[2], "\u2713") == "\u2611"]
        if not sel_mods:
            sel_mods = self._modules
        if not sel_mods:
            messagebox.showwarning("알림", "모듈 없음")
            return
        out_name = self.out_v.get().strip() or "merged_EA.mq4"
        out_path = os.path.join(os.path.dirname(base_p), out_name)
        WL(self.log,
           f"합치기 시작: {os.path.basename(base_p)} + "
           f"{len(sel_mods)}개 모듈")
        threading.Thread(target=self._merge_worker,
                         args=(base_p, sel_mods, out_path),
                         daemon=True).start()

    def _merge_worker(self, base_p, sel_mods, out_path):
        try:
            base_content, _ = read_mq4(base_p)
            base_blks = parse_mq4_blocks(base_content)
            base_funcs = set(base_blks['funcs'].keys())
            skip = {'OnInit', 'OnDeinit', 'OnTick', 'init', 'deinit', 'start'}

            inject_parts = []
            inject_params = []
            for path, blks, _ in sel_mods:
                mod_content, _ = read_mq4(path)
                fn_input = self.fn_var.get().strip()
                if fn_input:
                    wanted = set(f.strip() for f in fn_input.split(','))
                else:
                    wanted = set(blks['funcs'].keys()) - base_funcs - skip

                if wanted:
                    inj = extract_module_for_inject(mod_content, wanted)
                    inject_parts.append(
                        f"// === 모듈: {os.path.basename(path)} ===\n{inj}")
                    WL(self.log,
                       f"  모듈 {os.path.basename(path)}: "
                       f"함수 {len(wanted)}개 주입 예정")

                for t, n, v in blks['params']:
                    if not any(n == bp[1] for bp in base_blks['params']):
                        inject_params.append(
                            f"extern {t} {n} = {v}; "
                            f"// \U0001f9e9 {os.path.basename(path)}")

            inject_code = "\n\n".join(inject_parts)
            merged = inject_into_base(base_content, inject_code, inject_params)
            write_mq4(out_path, merged)
            fix_bom_date(out_path)
            WL(self.log, f"\u2705 저장: {out_path}", "o")

            if self.auto_cmp.get():
                me = self.me_v2.get().strip()
                if os.path.exists(me):
                    ld = os.path.join(os.path.dirname(out_path),
                                      "compile_logs")
                    os.makedirs(ld, exist_ok=True)
                    ok, msg = compile_one(me, out_path, ld)
                    r = '\u2705 성공' if ok else '\u274c 실패'
                    WL(self.log, f"컴파일: {r} {msg}", "o" if ok else "e")
                    if ok:
                        subprocess.run(
                            ["start", "", os.path.dirname(out_path)],
                            shell=True)
                else:
                    WL(self.log, "MetaEditor 없음 \u2014 컴파일 스킵", "w")
            else:
                subprocess.run(
                    ["start", "", os.path.dirname(out_path)], shell=True)
        except Exception as e:
            WL(self.log, f"합치기 오류: {e}", "e")
