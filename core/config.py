"""
core/config.py — EA Auto Master v6.0
=====================================
배포형 경로 설정 + JSON 설정 관리.
모든 모듈이 이 파일의 HERE를 경로 기준으로 사용.
"""
import os
import sys
import json
import datetime

# HERE = ea_master.py (진입점)가 있는 폴더
# sys.argv[0] 기반이므로 어디서 실행해도 동일
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
TODAY = datetime.datetime.now().strftime("%m%d")
CFG = os.path.join(HERE, "ea_master.json")


def load_cfg():
    """ea_master.json 설정 로드. 없거나 파싱 실패 시 빈 dict."""
    try:
        if os.path.exists(CFG):
            with open(CFG, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_cfg(d):
    """ea_master.json 설정 저장."""
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
