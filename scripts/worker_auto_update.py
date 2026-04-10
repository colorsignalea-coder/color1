# coding: utf-8
"""
worker_auto_update.py
=====================
서버 /update/* 엔드포인트에서 변경된 파일만 다운로드 후 교체
워커 시작 전, 또는 단독으로 실행 가능

사용법:
    python worker_auto_update.py --server http://100.80.221.25:9001
"""

import sys, os, base64, hashlib, argparse, configparser
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SOLO_DIR   = SCRIPT_DIR.parent  # 워커 루트 (WORKER_008_v12_9001/)
INI_PATH   = SOLO_DIR / "configs" / "current_config.ini"


def get_server_url():
    """current_config.ini에서 서버 URL 읽기"""
    try:
        if INI_PATH.exists():
            raw = INI_PATH.read_bytes()
            content = raw.decode('utf-16', errors='ignore') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8', errors='ignore')
            cfg = configparser.ConfigParser()
            cfg.read_string(content)
            url = cfg.get('server', 'server_url', fallback='').strip()
            if url:
                return url
    except Exception:
        pass
    return None


def run_update(server_url: str, dry_run=False):
    try:
        import requests
    except ImportError:
        print("[ERROR] requests 모듈 없음: pip install requests")
        return False

    print(f"[UPDATE] 서버 연결: {server_url}/update/list")
    try:
        resp = requests.get(f"{server_url}/update/list", timeout=5)
    except Exception as e:
        print(f"[ERROR] 서버 연결 실패: {e}")
        return False

    if resp.status_code != 200:
        print(f"[ERROR] /update/list 응답 오류: {resp.status_code}")
        return False

    files = resp.json().get('files', [])
    if not files:
        print("[UPDATE] 배포 파일 없음.")
        return True

    print(f"[UPDATE] 서버 파일 {len(files)}개 확인")
    updated = []
    for item in files:
        rel   = item['path']
        md5   = item['md5']
        size  = item['size']
        dest  = SOLO_DIR / rel

        # 로컬 해시 비교
        if dest.exists():
            local_md5 = hashlib.md5(dest.read_bytes()).hexdigest()
            if local_md5 == md5:
                print(f"  [SKIP] {rel} (동일)")
                continue

        status = "신규" if not dest.exists() else "변경"
        print(f"  [{status}] {rel}  ({size} bytes)")
        if dry_run:
            updated.append(rel)
            continue

        # 다운로드
        dl = requests.get(f"{server_url}/update/file/{rel}", timeout=30)
        if dl.status_code != 200:
            print(f"  [ERROR] 다운로드 실패: {rel}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(dl.json()['content_b64']))
        print(f"  [OK] {rel} 교체 완료")
        updated.append(rel)

    if updated:
        print(f"\n[UPDATE] {len(updated)}개 파일 업데이트 완료.")
        return True
    else:
        print("[UPDATE] 모두 최신 상태.")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Worker 파일 자동 업데이트')
    parser.add_argument('--server', default=None, help='서버 URL (기본: config에서 읽기)')
    parser.add_argument('--dry-run', action='store_true', help='변경사항만 확인 (실제 교체 안 함)')
    args = parser.parse_args()

    server_url = args.server or get_server_url()
    if not server_url:
        print("[ERROR] 서버 URL을 찾을 수 없습니다. --server 옵션으로 지정하세요.")
        sys.exit(1)

    server_url = server_url.rstrip('/')
    changed = run_update(server_url, dry_run=args.dry_run)
    sys.exit(0 if changed else 0)
