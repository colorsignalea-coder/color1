"""
EA Auto Master v8.0 ??諛고룷 寃利??ㅽ겕由쏀듃
=========================================
?ㅻⅨ PC濡?蹂듭궗?????ㅽ뻾?댁꽌 v8.0 援ъ“媛 ?щ컮瑜몄? ?뺤씤.

?ъ슜踰?
    python verify_deploy.py
"""
import os
import sys
import importlib

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))

REQUIRED_CORE = [
    "core/config.py",
    "core/encoding.py",
    "core/path_finder.py",
    "core/htm_parser.py",
    "core/scoring.py",
    "core/diagnostics.py",
    "core/email_sender.py",
    "core/mql4_engine.py",
    "core/mql4_merger.py",
    "core/mql4_autofix.py",
    "core/round_engine.py",
    "core/ipc.py",
    "core/mt4_control.py",
    "core/round_optimizer.py",
]

REQUIRED_UI = [
    "ui/theme.py",
    "ui/tab_bypass.py",
    "ui/tab_merger.py",
    "ui/tab_round_opt.py",
    "ui/tab_autofix.py",
    "ui/tab_launcher.py",
    "ui/tab_settings.py",
    "ui/tab_scenario.py",
    "ui/tab_run_control.py",
    "ui/tab_monitor.py",
    "ui/tab_history.py",
    "ui/tab_dashboard.py",
]

REQUIRED_ROOT = [
    "ea_master.py",
    "ea_optimizer_v7.py",
    "START_ALL_v7.bat",
    "SOLO_nc2.3.ahk",
    "SOLO_WATCHER.py",
]

REQUIRED_INIT = [
    "core/__init__.py",
    "ui/__init__.py",
]


def check_files():
    ok = 0
    fail = 0
    for rel in REQUIRED_ROOT + REQUIRED_CORE + REQUIRED_UI + REQUIRED_INIT:
        full = os.path.join(HERE, rel)
        if os.path.exists(full):
            print(f"  OK   {rel}")
            ok += 1
        else:
            print(f"  MISS {rel}  ???놁쓬!")
            fail += 1
    return ok, fail


def check_imports():
    sys.path.insert(0, HERE)
    modules = [
        "core.config", "core.encoding", "core.path_finder",
        "core.htm_parser", "core.scoring", "core.diagnostics",
        "core.email_sender", "core.mql4_engine", "core.mql4_merger",
        "core.mql4_autofix", "core.round_engine", "core.ipc",
        "core.mt4_control", "core.round_optimizer",
        "ui.theme",
        "ui.tab_bypass", "ui.tab_merger", "ui.tab_round_opt",
        "ui.tab_autofix", "ui.tab_launcher", "ui.tab_settings",
        "ui.tab_scenario", "ui.tab_run_control", "ui.tab_monitor",
        "ui.tab_history", "ui.tab_dashboard",
    ]
    ok = 0
    fail = 0
    for m in modules:
        try:
            importlib.import_module(m)
            print(f"  OK   {m}")
            ok += 1
        except Exception as e:
            print(f"  FAIL {m}: {e}")
            fail += 1
    return ok, fail


def check_here():
    """HERE 湲곕컲 寃쎈줈 ?숈옉 ?뺤씤."""
    from core.config import HERE as cfg_here
    ok = os.path.normcase(HERE) == os.path.normcase(cfg_here)
    if ok:
        print(f"  OK   HERE = {cfg_here}")
    else:
        print(f"  WARN HERE mismatch: script={HERE}  cfg={cfg_here}")
    return ok


def main():
    print("=" * 60)
    print("  EA Auto Master v8.0 - DEPLOY VERIFY")
    print(f"  寃쎈줈: {HERE}")
    print("=" * 60)

    print("\n[1] ?뚯씪 議댁옱 ?뺤씤")
    fok, ffail = check_files()

    print("\n[2] Import 寃利?(26紐⑤뱢)")
    iok, ifail = check_imports()

    print("\n[3] HERE 寃쎈줈 寃利?)
    here_ok = check_here()

    print("\n" + "=" * 60)
    total_ok = fok + iok + (1 if here_ok else 0)
    total_fail = ffail + ifail + (0 if here_ok else 1)
    print(f"  寃곌낵: {total_ok} OK / {total_fail} FAIL")
    if total_fail == 0:
        print("  [PASS]  Deploy OK - ready to run on another PC")
    else:
        print("  [FAIL]  Deploy FAIL - check MISS/FAIL items above")
    print("=" * 60)

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

