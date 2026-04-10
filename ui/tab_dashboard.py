"""
ui/tab_dashboard.py — EA Auto Master v6.0
==========================================
EA별 결과 대시보드 — HTM 스캔 / HTML 로드 -> EA별 성과 비교.
v5.4 L7531-8158 추출.
"""
import glob as _g
import os
import re as _r
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox, filedialog

from core.config import HERE
from ui.theme import BG, FG, PANEL, PANEL2, BLUE, GREEN, TEAL, AMBER, B, LBL, TITLE, MONO


class EADashboardTab(ttk.Frame):
    """EA별 결과 대시보드 — HTM 스캔 / HTML 로드 -> EA별 성과 비교"""

    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        self._records  = []   # list[dict]: ea,round,profit,pf,mdd,trades,file,combo
        self._ea_names = []   # listbox 순서대로 ea 이름
        # cfg에서 기본 리포트 경로 결정
        solo_dir = cfg.get("solo_dir", HERE)
        rep_base = cfg.get("report_base", "")
        if rep_base and os.path.isdir(rep_base):
            self._default_dir = rep_base
        elif os.path.isdir(os.path.join(solo_dir, "Reports")):
            self._default_dir = os.path.join(solo_dir, "Reports")
        else:
            self._default_dir = os.path.join(HERE, "Reports")
        self._build()

    def _build(self):
        b = tk.Frame(self, bg=BG); b.pack(fill="both", expand=True, padx=8, pady=6)

        # -- 상단: 소스 선택 --
        top = tk.LabelFrame(b, text="  데이터 소스 (리포트 폴더 연결)", font=TITLE, fg=FG,
                            bg=PANEL, relief="groove", bd=2)
        top.pack(fill="x", pady=(0, 6))

        tr = tk.Frame(top, bg=PANEL); tr.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(tr, text="경로:", font=LBL, fg=FG, bg=PANEL).pack(side="left")
        self._src = tk.StringVar(value=self._default_dir)
        tk.Entry(tr, textvariable=self._src, font=MONO, bg=PANEL2, fg="#ff6b35",
                 insertbackground=FG, relief="flat", width=55).pack(side="left", padx=4)
        B(tr, "...", PANEL2, self._pick_folder, padx=5).pack(side="left")
        B(tr, "HTM 스캔", "#0369a1", self._scan_htms, pady=4, padx=10).pack(side="left", padx=4)
        B(tr, "HTML 로드", "#6d28d9", self._load_html, pady=4, padx=10).pack(side="left", padx=2)
        B(tr, "브라우저", "#065f46", self._open_html_browser, pady=4, padx=8).pack(side="left", padx=2)
        B(tr, "초기화", "#374151", self._clear, pady=4, padx=8).pack(side="left", padx=2)
        self._src_lbl = tk.Label(tr, text="데이터 없음", font=("Consolas", 9),
                                 fg="#94a3b8", bg=PANEL)
        self._src_lbl.pack(side="right", padx=8)

        # 폴더 목록
        tr2 = tk.Frame(top, bg=PANEL); tr2.pack(fill="x", padx=8, pady=(2, 6))
        tk.Label(tr2, text="폴더 목록:", font=LBL, fg="#94a3b8", bg=PANEL).pack(side="left")
        self._folder_lb = tk.Listbox(tr2, bg=PANEL2, fg="#ff6b35", font=("Consolas", 8),
                                      height=3, width=62, selectbackground="#1d4ed8",
                                      activestyle="none")
        fb_sb = ttk.Scrollbar(tr2, orient="vertical", command=self._folder_lb.yview)
        self._folder_lb.configure(yscrollcommand=fb_sb.set)
        self._folder_lb.pack(side="left", fill="x", expand=True, padx=(4, 0))
        fb_sb.pack(side="left", fill="y")
        btn_f = tk.Frame(tr2, bg=PANEL); btn_f.pack(side="left", padx=4)
        B(btn_f, "+ 추가", "#065f46", self._add_folder, pady=2, padx=6).pack(pady=1)
        B(btn_f, "- 삭제", "#7f1d1d", self._del_folder, pady=2, padx=6).pack(pady=1)
        B(btn_f, "모두 스캔", "#92400e", self._scan_all_folders, pady=2, padx=6).pack(pady=1)
        # 기본 폴더 자동 등록
        self._folder_lb.insert("end", self._default_dir)
        solo_dir = self.cfg.get("solo_dir", HERE)
        for extra in [
            os.path.join(solo_dir, "Reports"),
            self.cfg.get("report_base", ""),
            os.path.join(HERE, "Reports"),
            os.path.join(HERE, "htm_results"),
        ]:
            if extra and os.path.isdir(extra) and extra not in self._get_folders():
                self._folder_lb.insert("end", extra)

        # -- 필터 행 --
        fr = tk.Frame(b, bg=BG); fr.pack(fill="x", pady=(0, 4))
        tk.Label(fr, text="EA 검색:", font=LBL, fg=FG, bg=BG).pack(side="left")
        self._q = tk.StringVar()
        self._q.trace_add("write", lambda *_: self._refresh_ea_list())
        tk.Entry(fr, textvariable=self._q, font=MONO, bg=PANEL2, fg=FG,
                 insertbackground=FG, relief="flat", width=28).pack(side="left", padx=4)
        self._combo_v = tk.BooleanVar(value=False)
        tk.Checkbutton(fr, text="COMBO 전용", variable=self._combo_v,
                       command=self._refresh_ea_list, bg=BG, fg="#ff6b35",
                       selectcolor=PANEL, activebackground=BG).pack(side="left", padx=8)
        self._profit_v = tk.BooleanVar(value=False)
        tk.Checkbutton(fr, text="수익만", variable=self._profit_v,
                       command=self._refresh_ea_list, bg=BG, fg="#3fb950",
                       selectcolor=PANEL, activebackground=BG).pack(side="left", padx=2)
        self._total_lbl = tk.Label(fr, text="", font=("Consolas", 9), fg="#64748b", bg=BG)
        self._total_lbl.pack(side="right", padx=8)

        # -- 메인: 좌=EA 리스트 / 우=상세 --
        main = tk.PanedWindow(b, orient="horizontal", bg=BG,
                              sashwidth=5, sashrelief="groove", sashpad=2)
        main.pack(fill="both", expand=True)

        lf = tk.LabelFrame(main, text="  EA 목록  (클릭 = 상세)",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        main.add(lf, width=310, minsize=180, sticky="nsew")
        self._ea_lb = tk.Listbox(lf, bg=PANEL2, fg=FG, font=("Consolas", 9),
                                  selectbackground="#1d4ed8", width=40, activestyle="none")
        ea_sb = ttk.Scrollbar(lf, orient="vertical", command=self._ea_lb.yview)
        self._ea_lb.configure(yscrollcommand=ea_sb.set)
        self._ea_lb.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        ea_sb.pack(side="right", fill="y", pady=4)
        self._ea_lb.bind("<<ListboxSelect>>", self._on_ea_select)

        rf = tk.Frame(main, bg=BG)
        main.add(rf, minsize=200, sticky="nsew")

        self._hdr = tk.Label(rf, text="<- 왼쪽에서 EA를 선택하세요",
                             font=("Malgun Gothic", 12, "bold"), fg="#58a6ff", bg=BG)
        self._hdr.pack(fill="x", pady=(0, 2))
        self._stats_lbl = tk.Label(rf, text="", font=("Consolas", 9), fg="#94a3b8", bg=BG)
        self._stats_lbl.pack(fill="x", pady=(0, 4))

        # 상세 서브 탭
        nb2 = ttk.Notebook(rf); nb2.pack(fill="both", expand=True)

        # 탭1: 라운드별 결과
        t1 = tk.Frame(nb2, bg=BG); nb2.add(t1, text="라운드별 결과")
        det_cols = ("rno","profit","pf","mdd","trades","status","file")
        self._det = ttk.Treeview(t1, columns=det_cols, show="headings", height=16)
        for cid, hdr, w in [("rno","라운드",70),("profit","순이익",90),("pf","PF",60),
                              ("mdd","MDD%",65),("trades","거래수",65),
                              ("status","상태",80),("file","파일",220)]:
            self._det.heading(cid, text=hdr)
            self._det.column(cid, width=w, anchor="center", stretch=False)
        d_sb = ttk.Scrollbar(t1, orient="vertical", command=self._det.yview)
        self._det.configure(yscrollcommand=d_sb.set)
        self._det.pack(side="left", fill="both", expand=True)
        d_sb.pack(side="right", fill="y")
        self._det.tag_configure("ok",  background="#0d2b0d", foreground="#3fb950")
        self._det.tag_configure("bad", background="#2b0d0d", foreground="#f85149")
        self._det.tag_configure("mid", background="#1c2128", foreground="#8b949e")
        self._det.bind("<Double-Button-1>", self._on_det_dblclick)

        # 탭2: COMBO 분석
        t2 = tk.Frame(nb2, bg=BG); nb2.add(t2, text="COMBO 분석")
        cbo_cols = ("rno","ea","profit","pf","mdd","trades","status")
        self._cbo = ttk.Treeview(t2, columns=cbo_cols, show="headings", height=16)
        for cid, hdr, w in [("rno","라운드",70),("ea","EA 이름",260),("profit","순이익",90),
                              ("pf","PF",60),("mdd","DD%",60),("trades","거래수",65),("status","상태",80)]:
            self._cbo.heading(cid, text=hdr)
            self._cbo.column(cid, width=w, anchor="w" if cid == "ea" else "center", stretch=False)
        c_sb = ttk.Scrollbar(t2, orient="vertical", command=self._cbo.yview)
        self._cbo.configure(yscrollcommand=c_sb.set)
        self._cbo.pack(side="left", fill="both", expand=True)
        c_sb.pack(side="right", fill="y")
        self._cbo.tag_configure("ok",   background="#0d2b0d", foreground="#3fb950")
        self._cbo.tag_configure("warn", background="#2b2b0d", foreground="#d29922")
        self._cbo.tag_configure("bad",  background="#2b0d0d", foreground="#f85149")

        # 탭3: 전체 비교
        t3 = tk.Frame(nb2, bg=BG); nb2.add(t3, text="전체 비교")
        all_cols = ("rno","ea","profit","pf","mdd","trades","grade")
        self._all = ttk.Treeview(t3, columns=all_cols, show="headings", height=16)
        for cid, hdr, w in [("rno","라운드",70),("ea","EA",260),("profit","순이익",90),
                              ("pf","PF",60),("mdd","MDD%",60),("trades","거래수",65),("grade","등급",55)]:
            self._all.heading(cid, text=hdr)
            self._all.column(cid, width=w, anchor="w" if cid == "ea" else "center", stretch=False)
        a_sb = ttk.Scrollbar(t3, orient="vertical", command=self._all.yview)
        self._all.configure(yscrollcommand=a_sb.set)
        self._all.pack(side="left", fill="both", expand=True)
        a_sb.pack(side="right", fill="y")
        self._all.tag_configure("S", background="#0d1f0d", foreground="#3fb950")
        self._all.tag_configure("A", background="#0d2b1a", foreground="#56d364")
        self._all.tag_configure("C", background="#1c2128", foreground="#8b949e")
        self._all.tag_configure("D", background="#2b1a1a", foreground="#f85149")

    # -- 폴더 목록 관리 ------------------------------------------
    def _get_folders(self):
        return list(self._folder_lb.get(0, "end"))

    def _add_folder(self):
        p = self._src.get().strip()
        if not p:
            p = filedialog.askdirectory(initialdir=self._default_dir)
        if p and os.path.isdir(p) and p not in self._get_folders():
            self._folder_lb.insert("end", p)
            self._src_lbl.config(text=f"추가됨: {os.path.basename(p)}", fg="#4ade80")
        elif p and not os.path.isdir(p):
            messagebox.showwarning("없음", f"폴더가 존재하지 않습니다:\n{p}")

    def _del_folder(self):
        sel = self._folder_lb.curselection()
        if sel:
            self._folder_lb.delete(sel[0])

    def _scan_all_folders(self):
        folders = self._get_folders()
        if not folders:
            messagebox.showwarning("없음", "폴더 목록이 비어 있습니다.")
            return
        total_parsed = 0
        for folder in folders:
            if not os.path.isdir(folder):
                continue
            htms = _g.glob(os.path.join(folder, "**", "*.htm"), recursive=True)
            htms += _g.glob(os.path.join(folder, "**", "*.html"), recursive=True)
            for fp in htms:
                rec = self._parse_single_htm(fp)
                if rec:
                    self._records.append(rec)
                    total_parsed += 1
        self._src_lbl.config(
            text=f"전체 {total_parsed}개 파싱 ({len(folders)}개 폴더)", fg="#4ade80")
        self._refresh_all()

    # -- 소스 선택 ------------------------------------------------
    def _pick_folder(self):
        p = filedialog.askdirectory(initialdir=self._src.get() or self._default_dir)
        if not p:
            p = filedialog.askopenfilename(
                filetypes=[("HTML", "*.html *.htm"), ("All", "*")],
                initialdir=os.path.dirname(self._src.get()))
        if p:
            self._src.set(p)

    def _clear(self):
        self._records = []
        self._ea_names = []
        self._ea_lb.delete(0, "end")
        for tree in (self._det, self._cbo, self._all):
            for r in tree.get_children():
                tree.delete(r)
        self._src_lbl.config(text="데이터 초기화됨", fg="#94a3b8")
        self._total_lbl.config(text="")

    # -- HTM 폴더 스캔 -------------------------------------------
    def _scan_htms(self):
        folder = self._src.get().strip()
        if os.path.isfile(folder):
            folder = os.path.dirname(folder)
        if not os.path.isdir(folder):
            messagebox.showwarning("없음", f"폴더 없음:\n{folder}")
            return
        htms = _g.glob(os.path.join(folder, "**", "*.htm"), recursive=True)
        htms += _g.glob(os.path.join(folder, "**", "*.html"), recursive=True)
        if not htms:
            messagebox.showwarning("없음", "HTM/HTML 파일이 없습니다.")
            return
        parsed = 0
        for fp in htms:
            rec = self._parse_single_htm(fp)
            if rec:
                self._records.append(rec)
                parsed += 1
        self._src_lbl.config(text=f"{parsed}개 파싱 / {len(htms)}개 파일", fg="#4ade80")
        self._refresh_all()

    # -- HTML 로드 (4가지 포맷 자동 감지) -------------------------
    def _load_html(self):
        fp = self._src.get().strip()
        if not os.path.isfile(fp):
            fp = filedialog.askopenfilename(
                filetypes=[("HTML", "*.html *.htm"), ("All", "*")],
                initialdir=os.path.dirname(fp) if os.path.isdir(os.path.dirname(fp)) else HERE)
        if not fp or not os.path.exists(fp):
            messagebox.showwarning("없음", "파일을 선택하세요.")
            return
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                html = f.read()
        except Exception as e:
            messagebox.showerror("오류", str(e))
            return

        added = 0
        fname = os.path.basename(fp)

        # 포맷 1: ROUND_COMPARISON.html
        rows1 = _r.findall(
            r'<span[^>]*>(R\d+)</span>.*?'
            r'<td[^>]*>([^<]+)</td>\s*'
            r'<td[^>]*>([+-]?[\d,\.]+)</td>\s*'
            r'<td>([\d\.]+)</td>\s*'
            r'<td>([\d\.]+%)</td>\s*'
            r'<td>(\d+)</td>',
            html, _r.DOTALL)
        if rows1:
            for rno, ea, profit, pf, mdd, trades in rows1:
                try:
                    ea_s = ea.strip()
                    self._records.append({
                        "ea": ea_s, "round": rno,
                        "profit": float(profit.replace('+', '').replace(',', '')),
                        "pf": float(pf),
                        "mdd": float(mdd.replace('%', '')),
                        "trades": int(trades),
                        "file": fname,
                        "combo": any(x in ea_s.lower() for x in ('fc', 'combo', '_2fc', '_3fc')),
                        "grade": "C"
                    })
                    added += 1
                except Exception:
                    pass

        # 포맷 2: ROUND_ANALYSIS_V2.html
        rows2 = _r.findall(
            r'<span[^>]*>\[(R\d+)\]</span>\s*</td>\s*<td>([^<]+)</td>\s*'
            r'<td[^>]*>\s*([\d,\.]+)\s*</td>\s*'
            r'<td[^>]*>\s*([\d\.]+)\s*</td>\s*'
            r'<td[^>]*>\s*([\d\.]+%)\s*</td>\s*'
            r'<td[^>]*>\s*(\d+)\s*</td>',
            html, _r.DOTALL)
        if rows2:
            for rno, ea, profit, pf, mdd, trades in rows2:
                try:
                    ea_s = ea.strip()
                    p_val = float(profit.replace(',', ''))
                    self._records.append({
                        "ea": ea_s, "round": rno,
                        "profit": p_val, "pf": float(pf),
                        "mdd": float(mdd.replace('%', '')),
                        "trades": int(trades),
                        "file": fname, "combo": True,
                        "grade": "A" if p_val > 1000 else "C"
                    })
                    added += 1
                except Exception:
                    pass

        # 포맷 3: BB_SQUEEZE_R7_ANALYSIS.html
        rno_m = _r.search(r'R(\d+)', fname)
        rno_from_fname = f"R{rno_m.group(1).zfill(2)}" if rno_m else "R??"
        rows3 = _r.findall(
            r'<tr[^>]*>.*?<td[^>]*>#(\d+)</td>.*?'
            r'<td[^>]*>(SC\d+)</td>.*?'
            r'<td[^>]*>([\d\.]+)</td>.*?'
            r'<td[^>]*>([\d\.]+)</td>.*?'
            r'<td[^>]*>[\d\.]+x</td>.*?'
            r'<td[^>]*>[\d\.]+</td>.*?'
            r'<td[^>]*>([\-\d,\.]+)</td>.*?'
            r'<td[^>]*>([\d\.]+)</td>',
            html, _r.DOTALL)
        if rows3:
            for rank, sc, sl, tp, profit, pf in rows3:
                try:
                    p = float(profit.replace(',', ''))
                    ea_s = f"{sc}_SL{sl}_TP{tp}"
                    self._records.append({
                        "ea": ea_s, "round": rno_from_fname,
                        "profit": p, "pf": float(pf),
                        "mdd": 0.0, "trades": 0,
                        "file": fname, "combo": False,
                        "grade": "A" if p > 1000 else ("C" if p > 0 else "D")
                    })
                    added += 1
                except Exception:
                    pass

        # 포맷 4: ROUND_RESULT_CHART.html
        rows4 = _r.findall(
            r'<tr[^>]*>\s*<td[^>]*>(R\d+)</td>\s*'
            r'<td[^>]*>([^<]+)</td>\s*'
            r'<td[^>]*>([+-]?[\d,\.]+)</td>\s*'
            r'<td[^>]*>([\d\.]+)</td>\s*'
            r'<td[^>]*>([\d\.]+%)</td>\s*'
            r'<td[^>]*>(\d+)</td>\s*'
            r'<td[^>]*>([^\x00-\x7F\w]+)</td>',
            html, _r.DOTALL)
        if rows4:
            star_grade = {"S": "S", "A": "A", "B": "B"}
            for rno, ea, profit, pf, mdd, trades, grade in rows4:
                try:
                    p = float(profit.replace('+', '').replace(',', ''))
                    g = star_grade.get(grade.strip(), "C")
                    self._records.append({
                        "ea": ea.strip(), "round": rno,
                        "profit": p, "pf": float(pf),
                        "mdd": float(mdd.replace('%', '')),
                        "trades": int(trades),
                        "file": fname, "combo": False, "grade": g
                    })
                    added += 1
                except Exception:
                    pass

        if added == 0:
            messagebox.showwarning("파싱 실패",
                "인식된 포맷이 없습니다.\n"
                "지원 포맷:\n"
                "- ROUND_COMPARISON.html\n"
                "- ROUND_ANALYSIS_V2.html\n"
                "- BB_SQUEEZE_R7_ANALYSIS.html\n"
                "- ROUND_RESULT_CHART.html")
            return

        self._src_lbl.config(text=f"{added}개 로드 ({fname})", fg="#4ade80")
        self._refresh_all()

    def _open_html_browser(self):
        p = self._src.get().strip()
        if os.path.isfile(p) and p.lower().endswith(('.html', '.htm')):
            webbrowser.open(f"file:///{p.replace(os.sep, '/')}")
            return
        if os.path.isdir(p):
            htmls = sorted(_g.glob(os.path.join(p, "*.html")) + _g.glob(os.path.join(p, "*.htm")))
        else:
            htmls = []
        if not htmls:
            fp = filedialog.askopenfilename(
                title="HTML 파일 선택",
                filetypes=[("HTML", "*.html *.htm"), ("All", "*")],
                initialdir=p if os.path.isdir(p) else HERE)
            if fp:
                webbrowser.open(f"file:///{fp.replace(os.sep, '/')}")
            return
        if len(htmls) == 1:
            webbrowser.open(f"file:///{htmls[0].replace(os.sep, '/')}")
        else:
            win = tk.Toplevel(self)
            win.title("HTML 파일 선택"); win.configure(bg=BG)
            win.geometry("600x300")
            tk.Label(win, text="브라우저로 열 HTML 선택:", font=LBL, fg=FG, bg=BG).pack(pady=6)
            lb = tk.Listbox(win, bg=PANEL2, fg="#ff6b35", font=("Consolas", 9),
                            selectbackground="#1d4ed8", width=80)
            lb.pack(fill="both", expand=True, padx=10)
            for h in htmls:
                lb.insert("end", os.path.basename(h))

            def _open():
                sel = lb.curselection()
                if sel:
                    webbrowser.open(f"file:///{htmls[sel[0]].replace(os.sep, '/')}")
                win.destroy()

            lb.bind("<Double-Button-1>", lambda e: _open())
            B(win, "열기", "#065f46", _open, pady=6, padx=20).pack(pady=6)

    # -- 단일 HTM 파싱 -------------------------------------------
    def _parse_single_htm(self, fpath):
        try:
            raw = open(fpath, 'rb').read()
            if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
                html = raw.decode('utf-16', errors='replace')
            elif raw[:3] == b'\xef\xbb\xbf':
                html = raw.decode('utf-8', errors='replace')
            else:
                html = raw.decode('cp1252', errors='replace')
        except Exception:
            return None

        tm = _r.search(r'<title>(?:Strategy Tester:\s*)?([^<]+)</title>', html, _r.I)
        ea = tm.group(1).strip() if tm else os.path.splitext(os.path.basename(fpath))[0]

        rpath = fpath.replace('\\', '/')
        rm = (_r.search(r'/R(\d{1,2})/', rpath) or
              _r.search(r'_R(\d{1,2})[_\.]', os.path.basename(fpath)))
        rno = f"R{rm.group(1).zfill(2)}" if rm else "R??"

        def _parse_mt4_rows():
            rows = _r.findall(r'<tr[^>]*>(.*?)</tr>', html, _r.I | _r.S)

            def row_vals(r):
                cells = _r.findall(r'<td[^>]*>(.*?)</td>', r, _r.I | _r.S)
                return [_r.sub(r'<[^>]+>', '', c).strip() for c in cells]

            state = 0
            res = {}
            for row in rows:
                vals = row_vals(row)
                if not vals:
                    continue
                if state == 0:
                    if '10000.00' in vals:
                        state = 1
                elif state == 1:
                    if len(vals) >= 6 and _r.match(r'^-?[\d,]+\.\d+$', vals[1].replace(',', '')):
                        res['profit'] = float(vals[1].replace(',', ''))
                        state = 2
                elif state == 2:
                    if len(vals) >= 2:
                        if _r.match(r'^\d+\.\d+$', vals[1]):
                            res['pf'] = float(vals[1])
                        else:
                            res['pf'] = 0.0
                        state = 3
                elif state == 3:
                    for v in vals:
                        m = _r.search(r'(\d+\.\d+)%\s*\(', v)
                        if m:
                            res['dd'] = float(m.group(1))
                            state = 4
                            break
                elif state == 4:
                    if len(vals) >= 2 and _r.match(r'^\d+$', vals[1]):
                        res['trades'] = int(vals[1])
                        break
            return res

        def _parse_html_report():
            def _get(pats, conv):
                for p in pats:
                    m = _r.search(p, html, _r.S | _r.I)
                    if m:
                        try:
                            return conv(m.group(1).replace(',', '').replace(' ', ''))
                        except Exception:
                            pass
                return None

            return {
                'profit': _get([r'Net Profit.*?<td[^>]*>([\-\d\.]+)</td>'], float),
                'pf':     _get([r'Profit Factor.*?<td[^>]*>([\d\.]+)</td>'], float),
                'dd':     _get([r'Drawdown.*?<td[^>]*>([\d\.]+)%?</td>'], float),
                'trades': _get([r'Total Trades.*?<td[^>]*>([\d]+)</td>'], int),
            }

        is_mt4 = bool(_r.search(r'Strategy Tester', html, _r.I))
        stats = _parse_mt4_rows() if is_mt4 else _parse_html_report()

        profit = stats.get('profit')
        if profit is None:
            return None
        p = profit
        return {
            "ea": ea, "round": rno,
            "profit": p, "pf": stats.get('pf') or 0.0,
            "mdd": stats.get('dd') or 0.0, "trades": stats.get('trades') or 0,
            "file": os.path.basename(fpath),
            "combo": any(x in ea.lower() for x in ('fc', 'combo')),
            "grade": "A" if p > 1000 else ("B" if p > 500 else ("C" if p > 0 else "D"))
        }

    # -- 목록/뷰 갱신 -------------------------------------------
    def _refresh_all(self):
        self._refresh_ea_list()
        self._refresh_all_tab()
        self._refresh_combo_tab()

    def _refresh_ea_list(self):
        q = self._q.get().strip().lower()
        combo_only = self._combo_v.get()
        profit_only = self._profit_v.get()

        ea_map = {}
        for r in self._records:
            ea = r["ea"]
            if q and q not in ea.lower():
                continue
            if combo_only and not r.get("combo", False):
                continue
            if profit_only and r.get("profit", 0) <= 0:
                continue
            ea_map.setdefault(ea, []).append(r)

        ea_sorted = sorted(ea_map.items(),
                           key=lambda x: max(r["profit"] for r in x[1]), reverse=True)
        self._ea_lb.delete(0, "end")
        self._ea_names = []
        for ea, recs in ea_sorted:
            best = max(r["profit"] for r in recs)
            cnt = len(recs)
            sign = "+" if best > 0 else ""
            label = f"{ea[:26]:<26}  {sign}{best:>8.0f}  [{cnt}R]"
            self._ea_lb.insert("end", label)
            self._ea_names.append(ea)
        self._total_lbl.config(text=f"EA {len(ea_sorted)}개 / 레코드 {len(self._records)}개")

    def _refresh_all_tab(self):
        for r in self._all.get_children():
            self._all.delete(r)
        recs = sorted(self._records, key=lambda x: -x["profit"])
        for rec in recs:
            p = rec["profit"]
            g = rec.get("grade", "C")
            sign = "+" if p > 0 else ""
            self._all.insert("", "end", tags=(g,), values=(
                rec["round"], rec["ea"][:45],
                f"{sign}{p:,.1f}", f"{rec['pf']:.2f}",
                f"{rec.get('mdd', 0):.1f}%", rec.get("trades", 0), g
            ))

    def _refresh_combo_tab(self):
        for r in self._cbo.get_children():
            self._cbo.delete(r)
        combos = sorted([r for r in self._records if r.get("combo", False)],
                        key=lambda x: -x["profit"])
        for rec in combos:
            p = rec["profit"]
            if p > 0:
                tag, st = "ok", "수익"
            elif p < 0:
                tag, st = "bad", "손실"
            else:
                tag, st = "warn", "노트레이드"
            self._cbo.insert("", "end", tags=(tag,), values=(
                rec["round"], rec["ea"][:44],
                f"{'+' if p > 0 else ''}{p:,.1f}",
                f"{rec['pf']:.2f}", f"{rec.get('mdd', 0):.1f}%",
                rec.get("trades", 0), st
            ))

    def _on_det_dblclick(self, event):
        sel = self._det.selection()
        if not sel:
            return
        fname = self._det.item(sel[0], "values")[6]
        for folder in self._get_folders():
            found = _g.glob(os.path.join(folder, "**", fname), recursive=True)
            if found:
                webbrowser.open(f"file:///{found[0].replace(os.sep, '/')}")
                return
        messagebox.showwarning("없음", f"파일을 찾을 수 없습니다:\n{fname}")

    def _on_ea_select(self, event):
        sel = self._ea_lb.curselection()
        if not sel:
            return
        ea = self._ea_names[sel[0]]
        recs = sorted([r for r in self._records if r["ea"] == ea], key=lambda x: x["round"])

        profits = [r["profit"] for r in recs]
        best = max(profits) if profits else 0
        best_pf = max(r["pf"] for r in recs) if recs else 0
        won = sum(1 for p in profits if p > 0)

        self._hdr.config(text=f"  {ea[:65]}")
        self._stats_lbl.config(
            text=(f"라운드: {len(recs)}개  |  최고 수익: {'+' if best > 0 else ''}{best:,.1f}"
                  f"  |  최고 PF: {best_pf:.2f}  |  수익: {won}/{len(profits)}"),
            fg="#4ade80" if best > 0 else "#f85149")

        for r in self._det.get_children():
            self._det.delete(r)
        for rec in recs:
            p = rec["profit"]
            tag = "ok" if p > 0 else ("bad" if p < 0 else "mid")
            st = "수익" if p > 0 else ("손실" if p < 0 else "없음")
            self._det.insert("", "end", tags=(tag,), values=(
                rec["round"],
                f"{'+' if p > 0 else ''}{p:,.1f}",
                f"{rec['pf']:.2f}",
                f"{rec.get('mdd', 0):.1f}%",
                rec.get("trades", 0),
                st,
                rec.get("file", "")[:35]
            ))
