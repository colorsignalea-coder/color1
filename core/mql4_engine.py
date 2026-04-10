"""
core/mql4_engine.py — EA Auto Master v6.0
==========================================
MQL4 핵심 로직: 라이센스 바이패스, 컴파일, 상태 체크.
"""
import os
import re
import shutil
import subprocess
import datetime

from core.encoding import read_mq4, write_mq4, fix_bom_date


def chk_status(content):
    """라이센스 상태 확인."""
    if "임시 비활성화" in content and "임시로 모든 계정 허용" in content:
        return "DONE"
    if "ALLOWED_ACCOUNTS" in content:
        return "HAS_LICENSE"
    return "NO_LICENSE"


def do_bypass(src, out, log_fn=print):
    """라이센스 바이패스 처리.
    src: 원본 MQ4 경로, out: 출력 MQ4 경로.
    Returns (success: bool, message: str)
    """
    content, _ = read_mq4(src)
    lines = content.split("\n")
    acc_s = acc_e = exp = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            continue
        if re.match(r"int\s+ALLOWED_ACCOUNTS\s*\[", s):
            acc_s = i
            acc_e = i if "};" in line else next(
                (j for j in range(i + 1, min(i + 60, len(lines)))
                 if "}" in lines[j].strip() and (lines[j].strip().startswith("}") or "};" in lines[j].strip())),
                i)
            break
    if acc_s == -1:
        return False, "ALLOWED_ACCOUNTS 없음"
    for ci in range(max(0, acc_s - 6), acc_s + 1):
        if "임시 비활성화" in lines[ci]:
            return False, "이미 처리됨"
    for j in range(acc_e + 1, min(acc_e + 15, len(lines))):
        s2 = lines[j].strip()
        if re.match(r"datetime\s+ExpiryDate\s*=", s2) and not s2.startswith("//"):
            exp = j
            break
    be = exp if exp >= 0 else acc_e
    ins = acc_s
    for pi in range(max(0, acc_s - 5), acc_s):
        pl = lines[pi].strip()
        if pl.startswith("//") and any(k in pl for k in ["허용", "ALLOWED", "라이센스", "계정", "License"]):
            ins = pi
            break
    orig = "\n".join(lines[ins:be + 1])
    blk = (
        "// =============== 라이센스 설정 임시 비활성화 ===============\n"
        "/*\n" + orig + "\n*/\n\n"
        "// 임시로 모든 계정 허용 (개발/테스트용)\n"
        "int ALLOWED_ACCOUNTS[] = {0};\n"
        "datetime ExpiryDate = D'2099.12.31 23:59:59';\n"
        "bool LicenseOK = true;"
    )
    c2 = "\n".join(lines[:ins] + [blk] + lines[be + 1:])
    log_fn(f"  [변수] {ins + 1}~{be + 1}줄 주석")
    fm = re.search(r"bool\s+CheckLicense\s*\(", c2)
    if fm:
        ob = c2.find("{", fm.end())
        if ob >= 0 and "임시 비활성화" not in c2[ob + 1:ob + 150]:
            d, cb = 1, ob + 1
            while cb < len(c2) and d > 0:
                if c2[cb] == "{":
                    d += 1
                elif c2[cb] == "}":
                    d -= 1
                cb += 1
            cb -= 1
            nb = (
                "\n    // 라이센스 체크 임시 비활성화\n    return true;\n\n    /*\n"
                + c2[ob + 1:cb] + "    */\n    return true;\n"
            )
            c2 = c2[:ob + 1] + nb + c2[cb:]
            log_fn("  [CheckLicense] return true 주입")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_mq4(out, c2)
    if fix_bom_date(out):
        log_fn("  [BOM/날짜] 패치")
    log_fn(f"  [저장] {os.path.basename(out)}")
    return True, "완료"


def compile_one(me, mq4, logd):
    """MetaEditor로 MQ4 파일 컴파일.
    me: metaeditor.exe 경로, mq4: 소스 파일, logd: 로그 디렉토리.
    Returns (success: bool, message: str)
    """
    me_dir = os.path.dirname(me)
    exp = os.path.join(me_dir, "MQL4", "Experts")
    os.makedirs(exp, exist_ok=True)
    ts = datetime.datetime.now().strftime("%H%M%S_%f")
    tmp = os.path.join(exp, f"_tmp_{ts}_{os.path.basename(mq4)}")
    tex = tmp[:-4] + ".ex4"
    lp = os.path.join(logd, f"tmp_{ts}.log")
    ox = mq4[:-4] + ".ex4"
    need = not os.path.realpath(mq4).lower().startswith(os.path.realpath(me_dir).lower())
    try:
        t = mq4
        if need:
            shutil.copy2(mq4, tmp)
            t = tmp
        try:
            subprocess.run(
                f'"{me}" /compile:"{t}" /log:"{lp}" /portable',
                shell=True, timeout=25, cwd=me_dir,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            subprocess.run(
                f'taskkill /f /im "{os.path.basename(me)}"',
                shell=True, capture_output=True)
            return False, "TIMEOUT"
        rex = t[:-4] + ".ex4"
        if os.path.exists(rex):
            if need:
                shutil.copy2(rex, ox)
            try:
                os.remove(lp)
            except Exception:
                pass
            return True, "성공"
        msg = ""
        if os.path.exists(lp):
            try:
                with open(lp, "r", encoding="utf-16-le", errors="replace") as f:
                    msg = f.read(300).strip()
            except Exception:
                pass
        return False, msg or "ex4 미생성"
    finally:
        for p in [tmp, tex]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
