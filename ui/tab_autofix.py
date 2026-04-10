"""
ui/tab_autofix.py — EA Auto Master v6.0
=========================================
EA 자동 수정 탭: 12룰 패턴 스캔 + COMPILE_V1 반복 수정.
"""
import datetime
import os
import sys
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from core.config import HERE
from core.mql4_autofix import (
    RULES, scan_rules, apply_rules,
    cv1_preprocess, cv1_compile_ea, cv1_read_log,
    cv1_parse_errors, cv1_apply_patches, cv1_apply_targeted,
)
from core.path_finder import find_me, _find_mt4_near_here
from ui.theme import (BG, FG, PANEL, PANEL2, ACCENT, BLUE, GREEN, RED,
                      MONO, LBL, TITLE, B, LB, WL)


class AutoFixTab(ttk.Frame):
    def __init__(self, nb, cfg):
        super().__init__(nb)
        self.cfg = cfg
        self._proc = None
        self._rule_vars = {}
        self._scan_src = ""
        self._last_compile_errors = []
        self._iterating = False
        self._build()

    def _build(self):
        b = tk.Frame(self, bg=BG)
        b.pack(fill="both", expand=True, padx=10, pady=8)

        pv = tk.PanedWindow(b, orient="vertical", bg=BG,
                            sashwidth=5, sashrelief="groove", sashpad=2)
        pv.pack(fill="both", expand=True)
        top_pane = tk.Frame(pv, bg=BG)
        pv.add(top_pane, height=420, minsize=200, sticky="nsew")
        bot_pane = tk.Frame(pv, bg=BG)
        pv.add(bot_pane, minsize=80, sticky="nsew")

        # ── 섹션 1: EA 컴파일 오류 분석 & 자동 수정 ──
        fa = tk.LabelFrame(
            top_pane,
            text="  \U0001f52c  EA 컴파일 오류 원인 분석 & 자동 수정",
            font=TITLE, fg="#f97316", bg=PANEL, relief="groove", bd=2)
        fa.pack(fill="x", pady=(0, 4))

        _today = datetime.date.today().strftime("%Y%m%d")
        self.ea_v = tk.StringVar()
        self.sym_v = tk.StringVar(value="BTCUSD")
        self.tf_v = tk.StringVar(value="M5")
        self.fr_v = tk.StringVar(value="2025.09.01")
        self.to_v = tk.StringVar(value="2025.09.30")
        self.it_v = tk.StringVar(value="5")
        self.py_v = tk.StringVar(
            value=os.path.join(HERE, "ea_bt_autofix.py"))

        _mt4_log_dir = ""
        _mt4d = _find_mt4_near_here()
        if _mt4d:
            _mt4_log_dir = os.path.join(os.path.dirname(_mt4d),
                                        "tester", "logs")
        if not _mt4_log_dir or not os.path.isdir(_mt4_log_dir):
            _mt4_log_dir = os.path.join(HERE, "logs")
        self.log_v = tk.StringVar(
            value=os.path.join(_mt4_log_dir, f"{_today}.log"))
        self.tail_v = tk.StringVar(value="3000")

        # EA 파일 선택
        ea_row = tk.Frame(fa, bg=PANEL)
        ea_row.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(ea_row, text="EA(.mq4):", font=LBL, fg=FG, bg=PANEL,
                 width=10, anchor="e").pack(side="left")
        tk.Entry(ea_row, textvariable=self.ea_v, font=MONO, bg=PANEL2,
                 fg="#ff6b35", insertbackground=FG, relief="flat",
                 bd=3).pack(side="left", fill="x", expand=True, padx=4)
        B(ea_row, "\U0001f4c1", PANEL2,
          lambda: self._bf(self.ea_v, [("MQ4", "*.mq4")]),
          padx=5).pack(side="left")
        B(ea_row, "\U0001f50d 패턴 스캔", "#7c3aed", self._scan_errors,
          font=("Malgun Gothic", 10, "bold"), pady=4,
          padx=10).pack(side="left", padx=(4, 0))
        B(ea_row, "\U0001f528 실제 컴파일", "#b45309", self._real_compile,
          font=("Malgun Gothic", 10, "bold"), pady=4,
          padx=10).pack(side="left", padx=(4, 0))

        # 반복수정 컨트롤
        iter_row = tk.Frame(fa, bg=PANEL)
        iter_row.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(iter_row, text="반복 최대:", font=LBL, fg="#94a3b8",
                 bg=PANEL).pack(side="left")
        self._iter_var = tk.StringVar(value="10")
        tk.Spinbox(iter_row, textvariable=self._iter_var, from_=1, to=20,
                   width=3, font=MONO, bg=PANEL2, fg="#ff6b35",
                   relief="flat", bd=2,
                   buttonbackground=PANEL).pack(side="left", padx=(2, 8))
        B(iter_row,
          "\U0001f504 컴파일\u2192수정 반복 자동실행 (COMPILE_V1)",
          "#166534", self._iterative_fix,
          font=("Malgun Gothic", 10, "bold"), pady=4,
          padx=14).pack(side="left")
        tk.Label(iter_row,
                 text="\u2190 BOM패치+유효기간+NormalizeLots+W62/43/83 자동수정",
                 font=("Consolas", 8), fg="#64748b",
                 bg=PANEL).pack(side="left", padx=8)

        # 오류 룰 목록 테이블
        tree_f = tk.Frame(fa, bg=PANEL)
        tree_f.pack(fill="both", expand=True, padx=8, pady=4)
        cols = ("\u2611", "코드", "오류 유형", "발견", "수정가능")
        self._err_tree = ttk.Treeview(
            tree_f, columns=cols, show="headings", height=8)
        for cid, w, anch in [
            ("\u2611", 30, "center"), ("코드", 44, "center"),
            ("오류 유형", 300, "w"), ("발견", 60, "center"),
            ("수정가능", 70, "center"),
        ]:
            self._err_tree.heading(cid, text=cid)
            self._err_tree.column(
                cid, width=w, anchor=anch, stretch=(cid == "오류 유형"))
        self._err_tree.tag_configure("ERR", foreground="#f85149")
        self._err_tree.tag_configure("WARN", foreground="#f59e0b")
        self._err_tree.tag_configure("OK", foreground="#3fb950")
        self._err_tree.tag_configure("AUTO", foreground="#58a6ff")
        tsb = ttk.Scrollbar(tree_f, orient="vertical",
                            command=self._err_tree.yview)
        self._err_tree.configure(yscrollcommand=tsb.set)
        self._err_tree.pack(side="left", fill="both", expand=True)
        tsb.pack(side="right", fill="y")
        self._err_tree.bind("<ButtonRelease-1>", self._toggle_err_check)

        # 초기 룰 표시
        for rule_id, name, desc, checker, fixer in RULES:
            can_fix = "\u2705 자동" if fixer else "\U0001f527 수동"
            self._err_tree.insert(
                "", "end", iid=rule_id,
                values=("\u2610", rule_id, name, "-", can_fix),
                tags=("WARN",))
            self._rule_vars[rule_id] = False

        # 버튼 행
        ab = tk.Frame(fa, bg=PANEL)
        ab.pack(fill="x", padx=8, pady=(0, 6))
        B(ab, "\u2611 전체선택", "#374151",
          lambda: self._set_all_checks(True), pady=3,
          padx=8).pack(side="left", padx=2)
        B(ab, "\u2610 전체해제", "#374151",
          lambda: self._set_all_checks(False), pady=3,
          padx=8).pack(side="left", padx=2)
        B(ab, "\u2705 선택항목 자동 수정 & 저장", "#15803d",
          self._apply_fixes, font=("Malgun Gothic", 10, "bold"),
          pady=5, padx=14).pack(side="left", padx=8)
        B(ab, "\U0001f4cb 수정 미리보기", BLUE,
          self._preview_fixes, pady=5, padx=10).pack(side="left", padx=2)
        self._fix_lbl = tk.Label(
            ab, text="", font=("Consolas", 9), fg="#3fb950", bg=PANEL)
        self._fix_lbl.pack(side="right", padx=8)

        # 오류 원인 가이드
        guide_f = tk.LabelFrame(
            top_pane,
            text="  \U0001f4d6  MQL4 컴파일 오류 원인 & 해결법 가이드",
            font=TITLE, fg="#60a5fa", bg=PANEL, relief="groove", bd=2)
        guide_f.pack(fill="x", pady=(0, 4))
        guide_text = (
            "\u2460 미선언 식별자 ('xxx' - undeclared identifier)"
            "  \u2192  변수 오타 or extern/input 전역 선언 누락\n"
            "\u2461 { } 괄호 불일치 (unexpected token / missing '}')"
            "\u2192  { } 개수 카운트 [수동]\n"
            "\u2462 타입 불일치 (cannot convert)"
            "  \u2192  int에 double 대입 시 (int) 캐스팅 추가\n"
            "\u2463 함수 미정의 ('xxx' - function not defined)"
            "  \u2192  프로토타입 추가 [수동]\n"
            "\u2464 세미콜론 누락 (';' expected)"
            "  \u2192  R09 자동수정\n"
            "\u2465 extern/input 함수 내부 선언"
            "  \u2192  전역 영역으로 이동 [수동]\n"
            "\u2466 void OnInit()"
            "  \u2192  int OnInit() + return INIT_SUCCEEDED \u2192 R05\n"
            "\u2467 #property strict 없음"
            "  \u2192  파일 맨 위에 추가 \u2192 R01\n"
            "\u2468 Sleep() 사용"
            "  \u2192  백테스트 오류 \u2192 R08 자동 주석처리\n"
            "\u2469 부동소수점 == 비교"
            "  \u2192  MathAbs(a-b)<_Point \u2192 R07\n"
            "\u246a OrderSend 반환값 미확인"
            "  \u2192  int ticket=OrderSend() \u2192 R11\n"
            "\u246b GetLastError 미호출"
            "  \u2192  R12 수동 추가"
        )
        tk.Label(guide_f, text=guide_text, font=("Consolas", 8),
                 fg="#94a3b8", bg=PANEL, justify="left",
                 anchor="w").pack(fill="x", padx=10, pady=6)

        # ── 섹션 2: 기존 자동수정 실행 ──
        fb = tk.LabelFrame(
            top_pane,
            text="  \U0001f527  EA 자동 수정 실행 (ea_bt_autofix.py)",
            font=TITLE, fg=FG, bg=PANEL, relief="groove", bd=2)
        fb.pack(fill="x", pady=(0, 4))

        def _row(parent, label, var, browse_fn=None):
            r = tk.Frame(parent, bg=PANEL)
            r.pack(fill="x", padx=8, pady=2)
            tk.Label(r, text=label + ":", font=LBL, fg=FG, bg=PANEL,
                     width=12, anchor="e").pack(side="left")
            tk.Entry(r, textvariable=var, font=MONO, bg=PANEL2,
                     fg="#ff6b35", insertbackground=FG, relief="flat",
                     bd=3).pack(side="left", fill="x", expand=True, padx=4)
            if browse_fn:
                B(r, "\U0001f4c1", PANEL2, browse_fn,
                  padx=5).pack(side="left")

        _row(fb, "심볼", self.sym_v)
        _row(fb, "TF", self.tf_v)
        _row(fb, "시작일", self.fr_v)
        _row(fb, "종료일", self.to_v)
        _row(fb, "최대반복", self.it_v)
        _row(fb, "autofix.py", self.py_v,
             lambda: self._bf(self.py_v, [("py", "*.py")]))

        log_row = tk.Frame(fb, bg=PANEL)
        log_row.pack(fill="x", padx=8, pady=2)
        tk.Label(log_row, text="로그파일:", font=LBL, fg=FG, bg=PANEL,
                 width=12, anchor="e").pack(side="left")
        tk.Entry(log_row, textvariable=self.log_v, font=MONO, bg=PANEL2,
                 fg="#ff6b35", insertbackground=FG, relief="flat",
                 bd=3).pack(side="left", fill="x", expand=True, padx=4)
        B(log_row, "\U0001f4c1", PANEL2,
          lambda: self._bf(self.log_v, [("log", "*.log"), ("all", "*")]),
          padx=5).pack(side="left")
        B(log_row, "\U0001f50d 로그 에러 수정", ACCENT,
          self._run_log_fix, pady=3, padx=8).pack(side="left", padx=4)

        bf2 = tk.Frame(fb, bg=PANEL)
        bf2.pack(fill="x", padx=8, pady=(2, 6))
        self.rb = B(bf2, "\u25b6 EA 직접 자동수정", GREEN, self._run,
                     font=("Malgun Gothic", 10, "bold"), pady=6, padx=14)
        self.rb.pack(side="left", padx=(0, 5))
        self.sb = B(bf2, "\u23f9 중지", RED, self._stop_proc, pady=6,
                     padx=10)
        self.sb.config(state="disabled")
        self.sb.pack(side="left", padx=(0, 5))
        B(bf2, "\U0001f5d1 로그", "#374151",
          lambda: self.log.delete("1.0", "end"), pady=6,
          padx=6).pack(side="left")
        self.sl = tk.Label(bf2, text="대기 중", font=LBL, fg="#94a3b8",
                           bg=PANEL)
        self.sl.pack(side="right")

        # ── 섹션 3: 로그 ──
        fl = tk.LabelFrame(bot_pane, text="  \U0001f4dc  로그",
                           font=TITLE, fg=FG, bg=PANEL, relief="groove",
                           bd=2)
        fl.pack(fill="both", expand=True)
        self.log = LB(fl, 8)
        self.log.pack(fill="both", expand=True, padx=8, pady=5)

    # ================================================================
    # 오류 스캔 (패턴 기반)
    # ================================================================

    def _scan_errors(self):
        path = self.ea_v.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("오류", "MQ4 파일을 먼저 선택하세요")
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                src = f.read()
        except Exception as e:
            WL(self.log, f"파일 읽기 오류: {e}", "e")
            return
        self._scan_src = src
        self._err_tree.delete(*self._err_tree.get_children())
        self._rule_vars.clear()

        results = scan_rules(src)
        found_cnt = 0
        for rule_id, name, found, can_fix in results:
            if found:
                found_cnt += 1
            sym = "\u274c" if found and "\u274c" in name else (
                "\u26a0\ufe0f" if found else "\u2705")
            tag = "ERR" if (found and "\u274c" in name) else (
                "WARN" if found else "OK")
            can = ("\u2705 자동" if (found and can_fix)
                   else ("\U0001f527 수동" if found else "-"))
            chk = "\u2611" if found else "\u2610"
            self._err_tree.insert(
                "", "end", iid=rule_id,
                values=(chk, rule_id, f"{sym} {name}",
                        "발견" if found else "정상", can),
                tags=(tag,))
            self._rule_vars[rule_id] = bool(found)

        self._fix_lbl.config(text=f"스캔 완료 \u2014 {found_cnt}개 발견")
        WL(self.log,
           f"[스캔] {os.path.basename(path)} \u2192 {found_cnt}개 문제 발견",
           "o" if found_cnt == 0 else "w")

    # ================================================================
    # 체크박스
    # ================================================================

    def _toggle_err_check(self, event):
        col = self._err_tree.identify_column(event.x)
        iid = self._err_tree.identify_row(event.y)
        if not iid or col != "#1":
            return
        cur = self._err_tree.set(iid, "\u2611")
        new = "\u2610" if cur == "\u2611" else "\u2611"
        self._err_tree.set(iid, "\u2611", new)
        self._rule_vars[iid] = (new == "\u2611")

    def _set_all_checks(self, state):
        for iid in self._err_tree.get_children():
            self._err_tree.set(iid, "\u2611",
                               "\u2611" if state else "\u2610")
            self._rule_vars[iid] = state

    # ================================================================
    # 수정 미리보기 / 적용
    # ================================================================

    def _preview_fixes(self):
        if not self._scan_src:
            messagebox.showinfo("알림", "먼저 오류 스캔을 실행하세요")
            return
        selected = [k for k, v in self._rule_vars.items() if v]
        fixed_src, applied, skipped = apply_rules(self._scan_src, selected)
        win = tk.Toplevel(self)
        win.title("수정 미리보기")
        win.geometry("900x600")
        win.configure(bg=BG)
        tk.Label(win, text=f"적용 수정: {applied}개, 스킵: {skipped}",
                 font=LBL, fg="#3fb950", bg=BG).pack(fill="x", padx=10,
                                                       pady=4)
        txt = scrolledtext.ScrolledText(
            win, font=("Consolas", 9), bg="#0a0e14", fg="#e2e8f0",
            relief="flat")
        txt.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        txt.insert("1.0", fixed_src)
        txt.config(state="disabled")

    def _apply_fixes(self):
        path = self.ea_v.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("오류", "MQ4 파일을 먼저 선택하세요")
            return
        if not self._scan_src:
            messagebox.showinfo("알림", "먼저 오류 스캔을 실행하세요")
            return
        selected = [k for k, v in self._rule_vars.items() if v]
        fixed_src, applied, skipped = apply_rules(self._scan_src, selected)
        if applied == 0:
            messagebox.showinfo(
                "알림",
                "자동 수정 가능한 항목이 없습니다\n수동 수정 항목은 직접 편집하세요")
            return
        bak = path + f".bak{datetime.datetime.now().strftime('%H%M%S')}"
        try:
            with open(bak, "w", encoding="utf-8") as f:
                f.write(self._scan_src)
            with open(path, "w", encoding="utf-8") as f:
                f.write(fixed_src)
        except Exception as e:
            WL(self.log, f"저장 오류: {e}", "e")
            return
        self._fix_lbl.config(text=f"\u2705 {applied}개 수정 완료")
        WL(self.log,
           f"\u2705 자동 수정 완료 ({applied}개) \u2192 "
           f"{os.path.basename(path)}", "o")
        WL(self.log, f"   백업: {os.path.basename(bak)}", "i")

    # ================================================================
    # 실제 MetaEditor 컴파일
    # ================================================================

    def _real_compile(self):
        path = self.ea_v.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("오류", "MQ4 파일을 먼저 선택하세요")
            return
        me_list = find_me(4)
        if not me_list:
            messagebox.showerror(
                "오류",
                "MetaEditor를 찾을 수 없습니다\n설정 탭에서 경로를 등록해 주세요")
            return
        me_exe = me_list[0]

        def _run():
            self.after(0, lambda: self._fix_lbl.config(
                text="\u23f3 MetaEditor 컴파일 중..."))
            WL(self.log,
               f"[실제 컴파일] {os.path.basename(path)}", "i")
            log_file = path + ".compile.log"
            try:
                patched = cv1_preprocess(path)
                if patched:
                    WL(self.log, "  \u2192 BOM/유효기간 패치 적용", "o")
            except Exception as e:
                WL(self.log, f"  전처리 오류: {e}", "w")

            cv1_compile_ea(me_exe, path, log_file)
            log_txt = cv1_read_log(log_file)
            errors = cv1_parse_errors(log_txt)
            err_cnt = sum(1 for e in errors if e['type'] == 'ERROR')
            warn_cnt = sum(1 for e in errors if e['type'] == 'WARNING')
            WL(self.log,
               f"  \u2192 오류 {err_cnt}개  경고 {warn_cnt}개",
               "e" if err_cnt else "o")
            for e in errors:
                tag = "e" if e['type'] == 'ERROR' else "w"
                WL(self.log,
                   f"    L{e['line']:4d} [{e['type']}#{e['num']}] "
                   f"{e['message']}", tag)

            def _update_tree():
                self._err_tree.delete(*self._err_tree.get_children())
                self._rule_vars.clear()
                for i, e in enumerate(errors):
                    iid = f"CE{i}"
                    tag = "ERR" if e['type'] == 'ERROR' else "WARN"
                    fixable = e['num'] in (43, 62, 83)
                    can = "\u2705 자동" if fixable else "\U0001f527 수동"
                    self._err_tree.insert(
                        "", "end", iid=iid,
                        values=(
                            "\u2611" if fixable else "\u2610",
                            f"W{e['num']}" if e['type'] == 'WARNING'
                            else f"E{e['num']}",
                            f"L{e['line']}  {e['message'][:60]}",
                            "발견", can),
                        tags=(tag,))
                    self._rule_vars[iid] = fixable
                if not errors:
                    self._err_tree.insert(
                        "", "end",
                        values=("\u2705", "OK",
                                "컴파일 성공 \u2014 오류 없음", "0", "완료"),
                        tags=("OK",))
                self._fix_lbl.config(
                    text=f"컴파일 완료 \u2014 오류 {err_cnt}개  "
                         f"경고 {warn_cnt}개")
                self._last_compile_errors = errors
            self.after(0, _update_tree)

        threading.Thread(target=_run, daemon=True).start()

    # ================================================================
    # 반복 자동수정 (COMPILE_V1)
    # ================================================================

    def _iterative_fix(self):
        path = self.ea_v.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("오류", "MQ4 파일을 먼저 선택하세요")
            return
        me_list = find_me(4)
        if not me_list:
            messagebox.showerror("오류", "MetaEditor 경로 없음")
            return
        me_exe = me_list[0]
        max_iter = int(self._iter_var.get())
        self._iterating = True
        self.rb.config(state="disabled")
        self.sb.config(state="normal")

        def _loop():
            bak = path + f".bak{datetime.datetime.now().strftime('%H%M%S')}"
            with open(path, encoding='utf-8', errors='replace') as f:
                src = f.read()
            with open(bak, 'w', encoding='utf-8') as f:
                f.write(src)
            WL(self.log,
               f"[반복수정] 시작 (최대 {max_iter}회) "
               f"백업\u2192{os.path.basename(bak)}", "i")

            src = cv1_apply_patches(src)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(src)
            WL(self.log,
               "  \u2192 글로벌 패치 적용 (BOM/유효기간/NormalizeLots)", "o")

            for iteration in range(1, max_iter + 1):
                if not self._iterating:
                    break
                self.after(0, lambda i=iteration: self._fix_lbl.config(
                    text=f"반복 {i}/{max_iter} 컴파일 중..."))
                WL(self.log,
                   f"  [Iter {iteration}/{max_iter}] 컴파일 중...", "i")

                log_file = path + f"_iter{iteration}.log"
                cv1_compile_ea(me_exe, path, log_file)
                log_txt = cv1_read_log(log_file)
                errors = cv1_parse_errors(log_txt)
                err_cnt = sum(1 for e in errors if e['type'] == 'ERROR')
                warn_cnt = sum(1 for e in errors if e['type'] == 'WARNING')

                if not errors:
                    WL(self.log,
                       f"  \u2705 성공! 오류 0 / 경고 0", "o")
                    self.after(0, lambda: self._fix_lbl.config(
                        text="\u2705 컴파일 성공!"))
                    break

                WL(self.log,
                   f"  \u2192 오류 {err_cnt}개 / 경고 {warn_cnt}개 "
                   f"\u2192 자동 수정 시도", "w")

                with open(path, encoding='utf-8', errors='replace') as f:
                    src = f.read()
                fixed_src, applied = cv1_apply_targeted(src, errors)

                if not applied:
                    WL(self.log,
                       "  \u26a0\ufe0f 자동 수정 불가 항목만 남음 "
                       "\u2014 수동 확인 필요", "e")
                    self.after(0, lambda: self._fix_lbl.config(
                        text="\u26a0\ufe0f 자동 수정 한계 도달"))
                    break

                WL(self.log,
                   f"  \u2192 {len(applied)}개 수정: "
                   f"{', '.join(applied[:3])}", "o")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(fixed_src)
                time.sleep(0.3)
            else:
                WL(self.log,
                   f"  최대 반복({max_iter}회) 도달", "w")
                self.after(0, lambda: self._fix_lbl.config(
                    text=f"최대 {max_iter}회 반복 완료"))

            self._iterating = False
            self.after(0, lambda: (
                self.rb.config(state="normal"),
                self.sb.config(state="disabled")))

        threading.Thread(target=_loop, daemon=True).start()

    # ================================================================
    # 외부 스크립트 실행
    # ================================================================

    def _run(self):
        ea = self.ea_v.get().strip()
        py = self.py_v.get().strip()
        if not os.path.exists(ea):
            messagebox.showerror("오류", "EA 파일 없음")
            return
        if not os.path.exists(py):
            messagebox.showerror("오류", f"autofix.py 없음:\n{py}")
            return
        cmd = [sys.executable, py, ea, self.sym_v.get(), self.tf_v.get(),
               self.fr_v.get(), self.to_v.get(),
               "--max-iter", self.it_v.get()]
        WL(self.log, f"실행: {' '.join(cmd)}")
        self.rb.config(state="disabled")
        self.sb.config(state="normal")
        self.sl.config(text="실행 중...")

        def _worker():
            try:
                self._proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW)
                for line in self._proc.stdout:
                    if any(k in line for k in ["ERROR", "\u274c", "실패"]):
                        t = "e"
                    elif any(k in line for k in ["\u2705", "성공", "완료"]):
                        t = "o"
                    else:
                        t = "i"
                    self.after(0, lambda l=line.rstrip(), tg=t:
                               WL(self.log, l, tg))
                rc = self._proc.wait()
                self.after(0, lambda: (
                    self.sl.config(text=f"종료({rc})"),
                    self.rb.config(state="normal"),
                    self.sb.config(state="disabled"),
                    WL(self.log, f"종료 코드: {rc}",
                       "o" if rc == 0 else "e")))
            except Exception as e:
                self.after(0, lambda: (
                    WL(self.log, f"오류: {e}", "e"),
                    self.rb.config(state="normal"),
                    self.sb.config(state="disabled"),
                    self.sl.config(text="오류")))
        threading.Thread(target=_worker, daemon=True).start()

    def _run_log_fix(self):
        log_path = self.log_v.get().strip()
        py = self.py_v.get().strip()
        if not os.path.exists(log_path):
            messagebox.showerror("오류", f"로그 파일 없음:\n{log_path}")
            return
        if not os.path.exists(py):
            messagebox.showerror("오류", f"autofix.py 없음:\n{py}")
            return
        cmd = [sys.executable, py, "--log-fix", log_path,
               self.sym_v.get(), self.tf_v.get(),
               self.fr_v.get(), self.to_v.get(),
               "--max-iter", self.it_v.get(),
               "--tail", self.tail_v.get()]
        WL(self.log, f"[로그수정] {' '.join(cmd)}")
        self.rb.config(state="disabled")
        self.sb.config(state="normal")
        self.sl.config(text="로그 스캔 중...")

        def _worker():
            try:
                self._proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW)
                for line in self._proc.stdout:
                    if any(k in line
                           for k in ["ERROR", "\u274c", "실패", "없음"]):
                        t = "e"
                    elif any(k in line
                             for k in ["\u2705", "성공", "완료", "수정"]):
                        t = "o"
                    else:
                        t = "i"
                    self.after(0, lambda l=line.rstrip(), tg=t:
                               WL(self.log, l, tg))
                rc = self._proc.wait()
                self.after(0, lambda: (
                    self.sl.config(text=f"완료({rc})"),
                    self.rb.config(state="normal"),
                    self.sb.config(state="disabled"),
                    WL(self.log, f"종료 코드: {rc}",
                       "o" if rc == 0 else "e")))
            except Exception as e:
                self.after(0, lambda: (
                    WL(self.log, f"오류: {e}", "e"),
                    self.rb.config(state="normal"),
                    self.sb.config(state="disabled"),
                    self.sl.config(text="오류")))
        threading.Thread(target=_worker, daemon=True).start()

    # ================================================================
    # 유틸
    # ================================================================

    def _stop_proc(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            WL(self.log, "종료 요청", "w")
        self.rb.config(state="normal")
        self.sb.config(state="disabled")
        self.sl.config(text="중단")
        self._iterating = False

    def _bf(self, var, filetypes):
        p = filedialog.askopenfilename(
            filetypes=filetypes + [("all", "*")])
        if p:
            var.set(p)
