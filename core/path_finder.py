"""
core/path_finder.py — EA Auto Master v6.0
==========================================
배포형 동적 경로 탐색. 모든 경로는 HERE 기준.
절대경로 하드코딩 금지.
"""
import os
from core.config import HERE


def _find_metaeditor_candidates():
    """HERE 기준 동적 탐색 + 일반 설치 경로 폴백."""
    cands = [os.path.join(os.path.dirname(HERE), "MT4", "metaeditor.exe")]
    for depth in range(3):
        base = HERE
        for _ in range(depth):
            base = os.path.dirname(base)
        if not base or not os.path.isdir(base):
            continue
        try:
            for name in os.listdir(base):
                d = os.path.join(base, name)
                me = os.path.join(d, "metaeditor.exe")
                if os.path.exists(me) and me not in cands:
                    cands.append(me)
                me2 = os.path.join(d, "MT4", "metaeditor.exe")
                if os.path.exists(me2) and me2 not in cands:
                    cands.append(me2)
        except OSError:
            pass
    cands += [
        r"C:\Program Files (x86)\MetaTrader 4\metaeditor.exe",
        r"C:\Program Files\MetaTrader 4\metaeditor.exe",
    ]
    return cands


ME_CANDS = _find_metaeditor_candidates()
_ME_CANDS = ME_CANDS   # v5.4 호환 alias
MAX_SLOTS = 4


def _find_mt4_near_here():
    """HERE 기준 상위 3단계에서 terminal.exe 있는 MT4 폴더 탐색."""
    p = HERE
    for _ in range(4):
        p = os.path.dirname(p)
        if not p or not os.path.isdir(p):
            break
        try:
            for name in sorted(os.listdir(p)):
                d = os.path.join(p, name)
                if os.path.isdir(d) and os.path.exists(os.path.join(d, "terminal.exe")):
                    me = os.path.join(d, "metaeditor.exe")
                    if os.path.exists(me):
                        return me
        except Exception:
            continue
    return ""


def find_me(n=4):
    """metaeditor.exe 탐색: 인접 MT4 우선, 폴백으로 ME_CANDS."""
    r = []
    nearby = _find_mt4_near_here()
    if nearby and nearby not in r:
        r.append(nearby)
    for p in ME_CANDS:
        if os.path.exists(p) and p not in r and len(r) < n:
            r.append(p)
    return r


def find_builder_file(name):
    """EA_AUTO_BUILDER.py / EA_OPTIMIZER_GUI.py 자동 탐색 (다른 PC 호환)."""
    candidates = [
        os.path.join(HERE, name),
        os.path.join(HERE, "EA_BUILDER_7.4", name),
        os.path.join(os.path.dirname(HERE), "EA_BUILDER_7.4", name),
        os.path.join(os.path.dirname(HERE), "Server", "EA_BUILDER_7.4", name),
        os.path.join(os.path.dirname(os.path.dirname(HERE)), "Server", "EA_BUILDER_7.4", name),
    ]
    p = HERE
    for _ in range(5):
        p = os.path.dirname(p)
        if not p or not os.path.isdir(p):
            break
        for sub in ["Server/EA_BUILDER_7.4", "EA_BUILDER_7.4"]:
            c = os.path.join(p, sub.replace("/", os.sep), name)
            if c not in candidates:
                candidates.append(c)
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(HERE, name)


def _find_db_path():
    """solo_worker.db 자동 탐색."""
    candidates = []
    p = HERE
    for _ in range(5):
        p = os.path.dirname(p)
        if not p or not os.path.isdir(p):
            break
        for sub in ["Server/EA_BUILDER_6.0/configs", "Server/EA_BUILDER_7.4/configs",
                     "configs", "3_SOLO_Local/configs"]:
            c = os.path.join(p, sub.replace("/", os.sep), "solo_worker.db")
            candidates.append(c)
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(os.path.dirname(HERE), "Server", "EA_BUILDER_7.4", "configs", "solo_worker.db")


def find_dashboard_file():
    """round_dashboard_v3.3.py 자동 탐색."""
    names = ["round_dashboard_v3.3.py", "round_dashboard_v3.31.py", "round_dashboard.py"]
    search_dirs = []
    p = HERE
    for _ in range(5):
        p = os.path.dirname(p)
        if not p or not os.path.isdir(p):
            break
        for sub in ["DASH Board3.3 pack", "Dashboard", "DASHBOARD"]:
            d = os.path.join(p, sub)
            if os.path.isdir(d):
                search_dirs.append(d)
    for d in search_dirs:
        for n in names:
            c = os.path.join(d, n)
            if os.path.exists(c):
                return c
    return os.path.join(os.path.dirname(HERE), "Dashboard", "round_dashboard_v3.3.py")


def verify_all_paths():
    """통합 경로 검증. {항목: (경로, 존재여부)} 반환."""
    result = {}
    me_list = find_me(1)
    result["metaeditor"] = (me_list[0] if me_list else "", bool(me_list))
    db = _find_db_path()
    result["solo_worker_db"] = (db, os.path.exists(db))
    dash = find_dashboard_file()
    result["dashboard"] = (dash, os.path.exists(dash))
    return result
