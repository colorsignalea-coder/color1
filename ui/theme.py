"""
ui/theme.py — EA Auto Master v6.0
===================================
Sky Blue 테마 상수 + 공용 UI 헬퍼 (B, LB, WL, _apply_font_sz).
"""
import datetime
import tkinter as tk
from tkinter import scrolledtext

# Sky Blue Theme palette
BG = "#f0f9ff"
PANEL = "#e0f2fe"
PANEL2 = "#bae6fd"
ACCENT = "#0369a1"
BLUE = "#0284c7"
GREEN = "#16a34a"
RED = "#dc2626"
AMBER = "#b45309"
TEAL = "#0f766e"
CYAN = "#0e7490"
ROSE = "#9f1239"
FG = "#0f172a"

# 폰트
MONO = ("Consolas", 9)
TITLE = ("Malgun Gothic", 10, "bold")
LBL = ("Malgun Gothic", 9)

MAX_SLOTS = 4
_G_FONT_SZ = 9


def _apply_font_sz(root_widget, size):
    """모든 위젯 폰트 크기 재귀 변경."""
    import tkinter.font as _tkf
    size = max(7, min(20, int(size)))

    def _walk(w):
        try:
            cur = w.cget("font")
            if cur:
                if isinstance(cur, str) and cur:
                    try:
                        _tkf.nametofont(cur).configure(size=size)
                    except Exception:
                        pass
                elif isinstance(cur, (list, tuple)) and len(cur) >= 2:
                    try:
                        w.configure(font=(cur[0], size) + tuple(cur[2:]))
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            for c in w.winfo_children():
                _walk(c)
        except Exception:
            pass

    _walk(root_widget)


def B(parent, text, bg, cmd, **kw):
    """스타일 버튼 생성."""
    return tk.Button(
        parent, text=text, font=kw.pop("font", LBL), bg=bg, fg="white",
        relief="flat", bd=0, pady=kw.pop("pady", 5), padx=kw.pop("padx", 10),
        command=cmd, cursor="hand2", **kw)


def LB(parent, h=6):
    """스크롤 가능 로그 박스 생성."""
    b = scrolledtext.ScrolledText(
        parent, height=h, font=MONO,
        bg="white", fg=FG, insertbackground=FG, relief="flat", bd=4, wrap="word")
    b.tag_config("e", foreground="#ff5555")
    b.tag_config("o", foreground="#16a34a")
    b.tag_config("w", foreground="#b45309")
    b.tag_config("i", foreground="#0369a1")
    return b


def WL(box, msg, tag="i"):
    """로그 박스에 타임스탬프 메시지 추가."""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    box.insert("end", f"[{ts}] {msg}\n", tag)
    box.see("end")
