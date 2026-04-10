"""
ui/tab_history.py — EA Auto Master v6.0
=======================================
라운드별 전체 성적 누적 + 비교 그래프 (최대 10라운드).
v5.4 L7118-7435 추출.
"""
import json
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

from ui.theme import BG, FG, PANEL, GREEN, BLUE, TEAL, AMBER, PANEL2, B, LBL


class RoundHistoryTab(ttk.Frame):
    """라운드별 전체 성적 누적 + 비교 그래프 (최대 10라운드)"""

    COLS = ("round","cat","sl","tp","lot","tf","profit","winrate","pf","trades","rank","verdict")
    COL_CFG = [
        ("round","라운드",56),("cat","카테고리",80),("sl","SL",52),("tp","TP",52),
        ("lot","Lot",46),("tf","TF",44),("profit","순이익",80),
        ("winrate","승률%",60),("pf","PF",54),("trades","거래수",58),
        ("rank","전체순위",66),("verdict","판정",60),
    ]

    def __init__(self, nb, hist_path_ref):
        super().__init__(nb)
        self._hist_path = hist_path_ref   # callable -> 경로 문자열 반환
        self._auto_refresh = True
        self._last_mtime = 0
        self._build()
        self._schedule_refresh()

    # -- UI -------------------------------------------------------
    def _build(self):
        outer = tk.Frame(self, bg=BG); outer.pack(fill="both", expand=True, padx=8, pady=6)

        # 상단 버튼
        top = tk.Frame(outer, bg=BG); top.pack(fill="x", pady=(0,6))
        B(top, "새로고침", GREEN, self._load, pady=6, padx=12,
          font=("Malgun Gothic",10,"bold")).pack(side="left", padx=4)
        B(top, "그래프 보기", BLUE, self._show_graph, pady=6, padx=12,
          font=("Malgun Gothic",10,"bold")).pack(side="left", padx=2)
        B(top, "라운드별 요약", TEAL, self._show_summary, pady=6, padx=12,
          font=("Malgun Gothic",10,"bold")).pack(side="left", padx=2)
        B(top, "기록 초기화", PANEL2, self._clear_history, pady=6, padx=10
          ).pack(side="left", padx=2)
        B(top, "CSV 내보내기", AMBER, self._export_csv, pady=6, padx=10
          ).pack(side="left", padx=2)
        B(top, "📂 경로변경", PANEL2, self._change_path, pady=6, padx=8
          ).pack(side="left", padx=2)
        B(top, "🌐 HTML 리포트", "#7c3aed", self._make_html_report, pady=6, padx=8,
          font=("Malgun Gothic",9,"bold")).pack(side="left", padx=2)
        self._auto_v = tk.BooleanVar(value=True)
        tk.Checkbutton(top, text="자동새로고침", variable=self._auto_v,
                       bg=BG, fg="#94a3b8", selectcolor=PANEL2,
                       activebackground=BG, font=("Malgun Gothic",9),
                       command=lambda: setattr(self, '_auto_refresh', self._auto_v.get())
                       ).pack(side="left", padx=6)
        self._info = tk.Label(top, text="", font=("Consolas",9), fg="#94a3b8", bg=BG)
        self._info.pack(side="right", padx=10)

        # 경로 표시
        self._path_lbl = tk.Label(outer, text="", font=("Consolas",8),
                                   fg="#475569", bg=BG, anchor="w")
        self._path_lbl.pack(fill="x", pady=(0,2))

        # 필터
        flt = tk.Frame(outer, bg=BG); flt.pack(fill="x", pady=(0,4))
        tk.Label(flt, text="라운드 필터:", font=LBL, fg=FG, bg=BG).pack(side="left")
        self._flt_round = tk.StringVar(value="전체")
        self._flt_cb = ttk.Combobox(flt, textvariable=self._flt_round,
                                     values=["전체"]+[f"R{i}" for i in range(1,11)],
                                     width=8, state="readonly")
        self._flt_cb.pack(side="left", padx=4)
        self._flt_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())
        tk.Label(flt, text="판정:", font=LBL, fg=FG, bg=BG).pack(side="left", padx=(12,0))
        self._flt_verdict = tk.StringVar(value="전체")
        ttk.Combobox(flt, textvariable=self._flt_verdict,
                     values=["전체","GOOD","MID","BAD"], width=7, state="readonly"
                     ).pack(side="left", padx=4)
        self._flt_verdict.trace_add("write", lambda *_: self._apply_filter())

        # 메인 테이블
        tf_frame = tk.Frame(outer, bg=BG); tf_frame.pack(fill="both", expand=True)
        self._tree = ttk.Treeview(tf_frame, columns=self.COLS, show="headings",
                                   selectmode="extended")
        for cid, hdr, w in self.COL_CFG:
            self._tree.heading(cid, text=hdr)
            self._tree.column(cid, width=w, anchor="center", stretch=False)
        vsb = ttk.Scrollbar(tf_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tf_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tf_frame.rowconfigure(0, weight=1); tf_frame.columnconfigure(0, weight=1)
        self._tree.tag_configure("GOOD", background="#14261a", foreground="#4ade80")
        self._tree.tag_configure("BAD",  background="#261414", foreground="#f87171")
        self._tree.tag_configure("MID",  background="#1e1e2e", foreground="#c9d1d9")
        for i in range(1,11):
            clr = ["#1a1a2e","#1a2040","#1a2a1a","#2a1a1a","#1a2a2a",
                   "#2a2a1a","#1a1a40","#2a1a2a","#1a2a20","#20201a"][i-1]
            self._tree.tag_configure(f"R{i}", background=clr)

        # 하단 요약 라벨
        self._summary_lbl = tk.Label(outer, text="", font=("Consolas",9),
                                      fg="#94a3b8", bg=BG, anchor="w", justify="left")
        self._summary_lbl.pack(fill="x", pady=(4,0))

        self._all_rows = []
        self._load()

    # -- 자동새로고침 스케줄 ----------------------------------------
    def _schedule_refresh(self):
        try:
            if self._auto_refresh:
                path = self._hist_path() if callable(self._hist_path) else self._hist_path
                if os.path.exists(path):
                    mtime = os.path.getmtime(path)
                    if mtime != self._last_mtime:
                        self._last_mtime = mtime
                        self._load()
        except Exception:
            pass
        self.after(5000, self._schedule_refresh)

    def _change_path(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(
            title="round_history.json 선택",
            filetypes=[("JSON", "*.json"), ("모두", "*")]
        )
        if p:
            self._hist_path = p
            self._last_mtime = 0
            self._load()

    # -- 데이터 로드 ----------------------------------------------
    def _load(self):
        path = self._hist_path() if callable(self._hist_path) else self._hist_path
        self._path_lbl.config(text=f"경로: {path}")
        if not os.path.exists(path):
            self._info.config(text="기록 없음 — 백테스트 후 자동 저장됩니다")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self._info.config(text=f"로드 오류: {e}"); return

        rows = []
        for entry in data:
            rno     = entry.get("round", 1)
            verdict = entry.get("verdict", "MID")
            tag     = verdict
            tag_r   = f"R{min(rno, 10)}"
            rows.append({
                "round":   f"R{rno}",
                "cat":     entry.get("cat", "?"),
                "sl":      entry.get("sl", 0),
                "tp":      entry.get("tp", 0),
                "lot":     f"{entry.get('lot', 0.0):.2f}",
                "tf":      entry.get("tf", "?"),
                "profit":  f"{entry.get('profit', 0):.1f}",
                "winrate": f"{entry.get('winrate', 0):.1f}",
                "pf":      f"{entry.get('pf', 0):.2f}",
                "trades":  entry.get("trades", 0),
                "rank":    entry.get("rank", "-"),
                "verdict": {"GOOD": "GOOD", "BAD": "BAD", "MID": "MID"}.get(verdict, "?"),
                "_tags":   (tag, tag_r),
            })
        self._all_rows = rows
        self._apply_filter()
        n_rounds = len(set(r["round"] for r in rows))
        import datetime as _dt
        now = _dt.datetime.now().strftime("%H:%M:%S")
        self._info.config(text=f"총 {len(rows)}개 결과 / {n_rounds}라운드  [{now}]")

    def _apply_filter(self):
        flt_r = self._flt_round.get()
        flt_v = self._flt_verdict.get()
        for row in self._tree.get_children():
            self._tree.delete(row)
        for r in self._all_rows:
            if flt_r != "전체" and r["round"] != flt_r:
                continue
            v_key = r["verdict"]
            if flt_v != "전체" and v_key != flt_v:
                continue
            self._tree.insert("", "end", tags=r["_tags"], values=(
                r["round"], r["cat"], r["sl"], r["tp"], r["lot"], r["tf"],
                r["profit"], r["winrate"], r["pf"], r["trades"], r["rank"], r["verdict"],
            ))
        self._update_summary()

    def _update_summary(self):
        if not self._all_rows:
            return
        by_round = {}
        for r in self._all_rows:
            rk = r["round"]
            by_round.setdefault(rk, []).append(float(r["profit"]))
        parts = []
        for rk in sorted(by_round.keys()):
            vals = by_round[rk]
            best = max(vals)
            avg = sum(vals) / len(vals)
            parts.append(f"{rk}: 최고={best:.0f}  평균={avg:.0f}  ({len(vals)}개)")
        self._summary_lbl.config(text="  |  ".join(parts))

    # -- 그래프 ---------------------------------------------------
    def _show_graph(self):
        if not self._all_rows:
            messagebox.showinfo("없음", "기록이 없습니다. 먼저 백테스트를 실행하세요.")
            return
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            for fp in ["C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/gulim.ttc"]:
                if os.path.exists(fp):
                    fm.fontManager.addfont(fp)
                    plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
                    break
            plt.rcParams["axes.facecolor"]   = "#161b22"
            plt.rcParams["figure.facecolor"] = "#0d1117"
            plt.rcParams["text.color"]       = "#c9d1d9"
            plt.rcParams["axes.labelcolor"]  = "#c9d1d9"
            plt.rcParams["xtick.color"]      = "#8b949e"
            plt.rcParams["ytick.color"]      = "#8b949e"
            plt.rcParams["axes.edgecolor"]   = "#30363d"
            plt.rcParams["grid.color"]       = "#21262d"
        except ImportError:
            messagebox.showerror("matplotlib 없음",
                "pip install matplotlib 을 실행한 후 다시 시도하세요.")
            return

        by_round = {}
        for r in self._all_rows:
            rk = r["round"]
            by_round.setdefault(rk, {"profits": [], "cats": []})
            by_round[rk]["profits"].append(float(r["profit"]))
            by_round[rk]["cats"].append(r["cat"])
        rounds_sorted = sorted(by_round.keys())

        colors = ["#3b82f6","#22c55e","#f59e0b","#ef4444","#a855f7",
                  "#06b6d4","#ec4899","#84cc16","#f97316","#8b5cf6"]

        fig, axes = plt.subplots(2, 2, figsize=(14, 9))
        fig.suptitle("EA 시나리오 라운드별 성적표", fontsize=15,
                     fontweight="bold", color="#58a6ff")

        # 그래프 1: 라운드별 최고 순이익 막대
        ax1 = axes[0][0]
        best_list = [max(by_round[r]["profits"]) for r in rounds_sorted]
        bars = ax1.bar(rounds_sorted, best_list,
                       color=[colors[i % 10] for i in range(len(rounds_sorted))],
                       edgecolor="#30363d", linewidth=0.5)
        ax1.set_title("라운드별 최고 순이익", color="#ffa657")
        ax1.set_ylabel("순이익 ($)")
        ax1.axhline(0, color="#f85149", linewidth=0.8, linestyle="--")
        for bar, val in zip(bars, best_list):
            ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5,
                     f"{val:.0f}", ha="center", va="bottom", fontsize=8, color="#c9d1d9")
        ax1.grid(axis="y", alpha=0.3)

        # 그래프 2: 라운드별 평균 순이익 추이선
        ax2 = axes[0][1]
        avg_list = [sum(by_round[r]["profits"])/len(by_round[r]["profits"])
                    for r in rounds_sorted]
        ax2.plot(rounds_sorted, avg_list, marker="o", color="#58a6ff",
                 linewidth=2, markersize=7, markerfacecolor="#1f6feb")
        ax2.fill_between(rounds_sorted, avg_list, alpha=0.15, color="#58a6ff")
        ax2.set_title("라운드별 평균 순이익 추이", color="#ffa657")
        ax2.set_ylabel("평균 순이익 ($)")
        ax2.axhline(0, color="#f85149", linewidth=0.8, linestyle="--")
        for x, y in zip(rounds_sorted, avg_list):
            ax2.annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                         xytext=(0, 8), ha="center", fontsize=8, color="#c9d1d9")
        ax2.grid(alpha=0.3)

        # 그래프 3: 라운드별 GOOD/MID/BAD 분포 쌓음 막대
        ax3 = axes[1][0]
        good_cnt = []; mid_cnt = []; bad_cnt = []
        for r in rounds_sorted:
            profits = sorted(by_round[r]["profits"], reverse=True)
            n = len(profits)
            top_n = max(1, int(n * 0.3))
            bot_n = max(1, int(n * 0.3))
            good_cnt.append(top_n)
            bad_cnt.append(bot_n)
            mid_cnt.append(n - top_n - bot_n)
        ax3.bar(rounds_sorted, good_cnt, label="GOOD", color="#22c55e", alpha=0.8)
        ax3.bar(rounds_sorted, mid_cnt, label="MID", color="#475569", alpha=0.8,
                bottom=good_cnt)
        ax3.bar(rounds_sorted, bad_cnt, label="BAD", color="#ef4444", alpha=0.8,
                bottom=[g+m for g, m in zip(good_cnt, mid_cnt)])
        ax3.set_title("라운드별 GOOD/MID/BAD 분포", color="#ffa657")
        ax3.set_ylabel("시나리오 수")
        ax3.legend(facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9")
        ax3.grid(axis="y", alpha=0.3)

        # 그래프 4: 전체 순이익 분포 (히스토그램)
        ax4 = axes[1][1]
        all_profits = [float(r["profit"]) for r in self._all_rows]
        ax4.hist(all_profits, bins=20, color="#3b82f6", edgecolor="#30363d",
                 alpha=0.8, linewidth=0.5)
        ax4.axvline(0, color="#f85149", linewidth=1, linestyle="--", label="손익분기")
        median_p = sorted(all_profits)[len(all_profits)//2]
        ax4.axvline(median_p, color="#22c55e", linewidth=1, linestyle="--",
                    label=f"중앙값 {median_p:.0f}")
        ax4.set_title("전체 순이익 분포", color="#ffa657")
        ax4.set_xlabel("순이익 ($)"); ax4.set_ylabel("빈도")
        ax4.legend(facecolor="#21262d", edgecolor="#30363d", labelcolor="#c9d1d9")
        ax4.grid(alpha=0.3)

        plt.tight_layout()
        plt.show()

    # -- 라운드별 텍스트 요약 -------------------------------------
    def _show_summary(self):
        if not self._all_rows:
            messagebox.showinfo("없음", "기록이 없습니다.")
            return
        by_round = {}
        for r in self._all_rows:
            rk = r["round"]
            by_round.setdefault(rk, []).append(r)
        lines = ["=" * 62, f"  라운드별 성적표  ({len(self._all_rows)}개 전체 결과)", "=" * 62]
        for rk in sorted(by_round.keys()):
            rows = by_round[rk]
            profits = [float(r["profit"]) for r in rows]
            best_r  = max(rows, key=lambda x: float(x["profit"]))
            worst_r = min(rows, key=lambda x: float(x["profit"]))
            good_n  = sum(1 for r in rows if r["verdict"] == "GOOD")
            bad_n   = sum(1 for r in rows if r["verdict"] == "BAD")
            lines += [
                f"\n  {rk}  ({len(rows)}개 시나리오)",
                f"  {'─' * 41}",
                f"  최고: {max(profits):>8.1f}$   [{best_r['cat']} SL{best_r['sl']} TP{best_r['tp']} {best_r['tf']}]",
                f"  최저: {min(profits):>8.1f}$   [{worst_r['cat']} SL{worst_r['sl']} TP{worst_r['tp']} {worst_r['tf']}]",
                f"  평균: {sum(profits)/len(profits):>8.1f}$",
                f"  GOOD: {good_n}개   BAD: {bad_n}개   MID: {len(rows)-good_n-bad_n}개",
            ]
        lines.append("\n" + "=" * 62)
        txt = "\n".join(lines)
        win = tk.Toplevel(self)
        win.title("라운드별 성적표"); win.geometry("560x480"); win.configure(bg=BG)
        txt_w = tk.Text(win, bg=PANEL, fg="#e2e8f0", font=("Consolas",10),
                        relief="flat", bd=0, wrap="none")
        txt_w.pack(fill="both", expand=True, padx=8, pady=8)
        txt_w.insert("1.0", txt); txt_w.config(state="disabled")
        B(win, "복사", BLUE, lambda: (win.clipboard_clear(), win.clipboard_append(txt)),
          pady=4).pack(pady=(0,8))

    # -- 기타 -----------------------------------------------------
    def _clear_history(self):
        if not messagebox.askyesno("초기화", "전체 라운드 기록을 삭제할까요?\n되돌릴 수 없습니다."):
            return
        path = self._hist_path() if callable(self._hist_path) else self._hist_path
        if os.path.exists(path):
            os.remove(path)
        self._all_rows = []
        for row in self._tree.get_children():
            self._tree.delete(row)
        self._info.config(text="기록 초기화됨")
        self._summary_lbl.config(text="")

    def _export_csv(self):
        if not self._all_rows:
            messagebox.showinfo("없음", "기록이 없습니다.")
            return
        path = self._hist_path() if callable(self._hist_path) else self._hist_path
        csv_path = path.replace(".json", "_export.csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("라운드,카테고리,SL,TP,Lot,TF,순이익,승률,PF,거래수,전체순위,판정\n")
            for r in self._all_rows:
                f.write(f"{r['round']},{r['cat']},{r['sl']},{r['tp']},"
                        f"{r['lot']},{r['tf']},{r['profit']},{r['winrate']},"
                        f"{r['pf']},{r['trades']},{r['rank']},{r['verdict']}\n")
        messagebox.showinfo("저장", f"CSV 저장: {csv_path}")
        subprocess.run(["start", "", os.path.dirname(csv_path)], shell=True)

    def _make_html_report(self):
        if not self._all_rows:
            messagebox.showinfo("없음", "기록이 없습니다. 먼저 백테스트를 실행하세요.")
            return
        # make_round_report.py 탐색 (RUNTIME 폴더 우선)
        path = self._hist_path() if callable(self._hist_path) else self._hist_path
        candidates = [
            os.path.join(os.path.dirname(path), "make_round_report.py"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "make_round_report.py"),
            r"C:\AG TO DO\EA MASTER 6.0\RUNTIME\make_round_report.py",
        ]
        script = None
        for c in candidates:
            if os.path.exists(c):
                script = os.path.abspath(c)
                break
        if not script:
            messagebox.showerror("오류", "make_round_report.py 를 찾을 수 없습니다.\n"
                                         r"C:\AG TO DO\EA MASTER 6.0\RUNTIME\ 에 있는지 확인하세요.")
            return
        import sys, datetime
        import threading
        def _run():
            try:
                result = subprocess.run(
                    [sys.executable, script, path],
                    capture_output=True, text=True, encoding="utf-8", errors="replace"
                )
                out = result.stdout.strip()
                # 생성된 HTML 경로 파싱 후 브라우저 오픈
                for line in out.splitlines():
                    if ".html" in line:
                        html_path = line.replace("생성:", "").replace("생성 :", "").strip()
                        if os.path.exists(html_path):
                            subprocess.Popen(["cmd", "/c", "start", "", html_path], shell=False)
                            return
                # fallback: g4_results 폴더에서 최신 HTML
                g4_dir = os.path.join(os.path.dirname(script), "g4_results")
                if os.path.isdir(g4_dir):
                    htmls = sorted(
                        [f for f in os.listdir(g4_dir) if f.startswith("ROUND_CHART") and f.endswith(".html")],
                        reverse=True
                    )
                    if htmls:
                        subprocess.Popen(["cmd", "/c", "start", "", os.path.join(g4_dir, htmls[0])], shell=False)
            except Exception as e:
                messagebox.showerror("오류", str(e))
        threading.Thread(target=_run, daemon=True).start()
        self._info.config(text="HTML 리포트 생성 중...")
