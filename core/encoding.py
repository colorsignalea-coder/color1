"""
core/encoding.py — EA Auto Master v6.0
=======================================
INI / MQ4 파일 인코딩 안전 읽기/쓰기.

v6.0 크래시 원인: configparser.read(encoding="utf-8-sig") 직접 호출.
이 모듈의 read_ini()가 **유일한 INI 진입점**이어야 함.
"""
import configparser
import os
import re


def read_ini(path):
    """인코딩 자동 감지로 INI 파일 읽기 (utf-8-sig / cp949 / euc-kr / utf-16 / utf-8 순서).
    섹션이 하나라도 읽히면 성공, 모두 실패 시 빈 파서 반환.
    """
    cp = configparser.RawConfigParser(strict=False)
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-16", "utf-8"):
        try:
            cp.read(path, encoding=enc)
            if cp.sections():
                return cp
        except Exception:
            cp = configparser.RawConfigParser(strict=False)
    return cp


def write_ini(cp, path):
    """INI 파일을 utf-8-sig(BOM)로 저장. AHK IniRead/IniWrite 호환 필수."""
    with open(path, "w", encoding="utf-8-sig") as f:
        cp.write(f)


def read_mq4(path):
    """MQ4 파일 읽기. UTF-16 BOM 감지 → 다중 인코딩 폴백.
    Returns (content_str, encoding_used).
    """
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16"), "utf-16"
    for enc in ("utf-8-sig", "utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc), enc
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace"), "utf-8"


def write_mq4(path, content):
    """MQ4 파일 쓰기. UTF-8 BOM + CRLF (MetaEditor 호환)."""
    with open(path, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(content)


def fix_bom_date(path):
    """BOM 중복 제거 + 만료일 2099.12.31 패치.
    Returns True if file was modified.
    """
    with open(path, "rb") as f:
        raw = f.read()
    chg = False
    if raw[:3] == b"\xef\xbb\xbf":
        inner = raw[3:]
        if b"\xef\xbb\xbf" in inner:
            raw = b"\xef\xbb\xbf" + inner.replace(b"\xef\xbb\xbf", b"")
            chg = True
    else:
        raw = b"\xef\xbb\xbf" + raw
        chg = True
    try:
        t = raw.decode("utf-8", errors="ignore")
        t2 = re.sub(r'"20(?:2[0-9])\.\d{2}\.\d{2}"', '"2099.12.31"', t)
        if t2 != t:
            raw = t2.encode("utf-8")
            if not raw.startswith(b"\xef\xbb\xbf"):
                raw = b"\xef\xbb\xbf" + raw
            chg = True
    except Exception:
        pass
    if chg:
        with open(path, "wb") as f:
            f.write(raw)
    return chg
