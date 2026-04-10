# coding: utf-8
# patch_paths.py - configs/current_config.ini 경로 자동 갱신
#
# START_WORKER_8.1.bat 에서 SOLO 실행 전에 호출됨.
# BAT 에서 아래 순서로 MT4 경로를 탐색해서 이 스크립트에 넘긴다:
#   1순위: 현재 폴더\MT4\
#   2순위: C:\NEWOPTMISER\MT4   (i 없음)
#   3순위: C:\NEWOPTIMISER\MT4  (i 있음 - 오타 폴더명도 지원)
# -> 실제 존재하는 MT4 경로를 받아서 config 에 기록
#
# [갱신 대상] 실행 위치 기준으로 자동 결정
#   terminal_path, ea_path, setfiles_path, work_folder
#
# [보존 대상] 사용자가 직접 설정 -> 절대 건드리지 않음
#   html_save_path, report_base_path
#
# Usage:
#   python patch_paths.py <BASE_DIR> <MT4_DIR>

import sys
import os
import re
from pathlib import Path


def read_ini_raw(path):
    raw = path.read_bytes()
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8', errors='replace')


def patch_ini(ini_path, base_dir, mt4_dir):
    # 슬래시 통일 (백슬래시)
    mt4  = mt4_dir.replace("/", "\\")
    base = base_dir.replace("/", "\\")

    # 갱신할 키와 값
    portable = {
        "terminal_path": mt4,
        "ea_path":       mt4 + "\\MQL4\\Experts",
        "setfiles_path": mt4 + "\\MQL4\\Files",
        "work_folder":   base,
    }

    if not ini_path.exists():
        print("[PATCH] config 없음 - 신규 생성: " + str(ini_path))
        ini_path.parent.mkdir(parents=True, exist_ok=True)
        ini_path.write_text("", encoding="utf-8")

    text = read_ini_raw(ini_path)
    lines = text.splitlines(keepends=True)
    new_lines = []
    changed = {}
    in_folders = False

    for line in lines:
        stripped = line.strip()

        if re.match(r'^\[', stripped):
            in_folders = stripped.lower().startswith("[folders]")
            new_lines.append(line)
            continue

        if in_folders and "=" in stripped and not stripped.startswith(";"):
            key = stripped.split("=", 1)[0].strip().lower()
            if key in portable:
                old_val = stripped.split("=", 1)[1].strip()
                new_val = portable[key]
                if old_val.lower() != new_val.lower():
                    changed[key] = (old_val, new_val)
                indent = line[: len(line) - len(line.lstrip())]
                new_lines.append(indent + key + " = " + new_val + "\n")
                continue

        new_lines.append(line)

    # [folders] 섹션 자체가 없을 경우 추가
    if not any("[folders]" in l.lower() for l in lines):
        new_lines.append("\n[folders]\n")
        for k, v in portable.items():
            new_lines.append(k + " = " + v + "\n")
        changed = {k: ("(없음)", v) for k, v in portable.items()}

    ini_path.write_text("".join(new_lines), encoding="utf-8")

    if changed:
        print("[PATCH] " + ini_path.name + " 경로 갱신 (" + str(len(changed)) + "개):")
        for k, (old, new) in changed.items():
            print("  " + k + ":")
            print("    전: " + old)
            print("    후: " + new)
    else:
        print("[PATCH] 변경 없음 (이미 최신)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: patch_paths.py <BASE_DIR> <MT4_DIR>")
        sys.exit(1)

    base_dir = sys.argv[1].rstrip("\\")
    mt4_dir  = sys.argv[2].rstrip("\\")
    ini_path = Path(base_dir) / "configs" / "current_config.ini"
    patch_ini(ini_path, base_dir, mt4_dir)
