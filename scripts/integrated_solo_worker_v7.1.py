# coding: utf-8
# =============================================================================
# ⚠️  수정 전 반드시 MUST_READ.html 을 먼저 읽을 것!
#    경로: C:\NEWOPTMISER\MUST_READ.html
#
#  워커 핵심 규칙:
#  1. 서버 주소: current_config.ini [worker] server_url = http://100.80.221.25:9001
#  2. 태스크 폯링: GET /worker/{id}/next (5초 간격)
#  3. 결과 전송: POST /results/submit
#  4. EA 다운로드: GET /ea/source/{ea_name} (.ex4 우선)
#  5. IPC: configs/command.json → AHK 감지 → configs/test_completed.flag → Python
#  6. current_config.ini 본인코딩: UTF-16/UTF-8/CP949 순서 시도
#  7. 수정 시 배포 폴더(worker_updates/scripts/) 선 수정 후 배포
# =============================================================================
"""
Integrated SOLO Worker v7.11
SOLO 7.0 + MT4 Portable + 자동 분석 + HTTP 통신 통합 워커

기능:
- SOLO 7.0 AHK로 백테스트 실행
- 백테스트 완료 즉시 자동 분석 (ReportAnalyzer)
- 중간 정지 상황에서도 분석 시도
- 서버로 결과 자동 전송
- 서버에서 SET 값 조정 받아 재테스트
- 수십~수백 회 반복 최적화

변경 (v7.1):
- all_done.flag 생성 버그 수정: 매 태스크 후 생성 → 모든 태스크 완료 후 생성
- v7.13: main() function config reading Unicode fix
- v7.12: Config reading (UTF-16) robustness fix (UnicodeDecodeError fix)
- v7.11: 기본 백테스트 기간 수정 (2025.12.31 - 2026.02.25)

사용법:
    python integrated_solo_worker_v7.1.py --worker-id WORKER-008 --server http://100.80.221.25:9001
    python integrated_solo_worker_v7.1.py --worker-id WORKER-008 --server http://100.80.221.25:9001 --max-iterations 300
"""

import sys
import os
import io
import time
import json
import requests
import subprocess
import sqlite3
import configparser
from pathlib import Path
from datetime import datetime
import threading

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
SOLO_DIR = SCRIPT_DIR.parent
PROJECT_DIR = SOLO_DIR.parent
SET_DIR = SOLO_DIR / "configs" / "set_files"
INI_PATH = SOLO_DIR / "configs" / "current_config.ini"  # AHK이 읽는 configs 폴더 (SOLO_DIR 기준)
AHK_SCRIPT = SCRIPT_DIR / "SIMPLE_4STEPS_v4_0.ahk"
EA_TEST_DIR = Path(r"C:\NEWOPTMISER\EA_LOCAL")  # 로컬 EA 캐시 폴더 (서버에서 다운로드)

# report_analyzer_module 임포트
sys.path.insert(0, str(SOLO_DIR))
try:
    from report_analyzer_module import ReportAnalyzer
except ImportError:
    print("[WARN] report_analyzer_module not found. Analysis will be limited.")
    ReportAnalyzer = None


class IntegratedSOLOWorker:
    """통합 SOLO 워커 - AHK + 분석 + HTTP 통신"""

    def __init__(self, worker_id: int, server_url: str, max_iterations=100,
                 symbol='XAUUSD', tf='H1', from_date='2025.12.31', to_date='2026.02.25'):
        self.worker_id = worker_id
        self.server_url = server_url.rstrip('/')
        self.max_iterations = max_iterations
        self.symbol = symbol
        self.tf = tf
        self.from_date = from_date
        self.to_date = to_date
        self.running = True
        self.current_ea = ''
        self.current_iteration = 0

        # 서버에서 최신 파일 자동 업데이트
        self._auto_update()

        # AHK 찾기
        self.ahk_exe = self._find_autohotkey()

        # MT4 Experts 경로 읽기 (current_config.ini에서)
        self.experts_dir = self._get_experts_dir()

        # [★ NEW] 중복 실행 방지: 동일 ID의 다른 워커 종료
        self._kill_other_instances()

        # Analyzer 초기화
        self.analyzer = ReportAnalyzer() if ReportAnalyzer else None

        print(f"\n{'#'*60}")
        print(f"  Integrated SOLO Worker v7.1")
        print(f"  Worker ID: {self.worker_id}")
        print(f"  Server: {self.server_url}")
        print(f"  Max Iterations: {self.max_iterations}")
        print(f"  Symbol: {self.symbol} | TF: {self.tf}")
        print(f"  AHK: {self.ahk_exe}")
        print(f"  EA Storage: {EA_TEST_DIR}")
        print(f"  MT4 Experts: {self.experts_dir}")
        print(f"  Analyzer: {'Ready' if self.analyzer else 'Disabled'}")
        print(f"{'#'*60}\n")

    def _read_ini(self, path: Path) -> configparser.ConfigParser:
        """UTF-16/UTF-8 자동 감지하여 ConfigParser 반환"""
        config = configparser.ConfigParser()
        config.optionxform = str  # 대소문자 보존
        if not path.exists():
            return config
        try:
            raw = path.read_bytes()
            if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
                content = raw.decode('utf-16', errors='ignore')
            else:
                try:
                    content = raw.decode('utf-8')
                except UnicodeDecodeError:
                    content = raw.decode('cp949', errors='ignore') # 한글 윈도우 지원
            config.read_string(content)
        except Exception as e:
            self._log(f"[ERR] _read_ini 실패 ({path.name}): {e}")
        return config

    def _log(self, msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {msg}"
        print(line)
        try:
            with open(SCRIPT_DIR / "worker_debug.log", "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except:
            pass

    def _kill_other_instances(self):
        """본인(PID)을 제외한 다른 워커 프로세스 종료"""
        try:
            import psutil
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # python.exe 이면서 cmdline에 본 스크립트명이 포함된 경우
                    if 'python' in proc.info['name'].lower() and proc.info['cmdline']:
                        cmd = " ".join(proc.info['cmdline'])
                        if "integrated_solo_worker_v7.1.py" in cmd and f"--worker-id {self.worker_id}" in cmd:
                            if proc.info['pid'] != current_pid:
                                self._log(f"[INFO] Killing other instance (PID: {proc.info['pid']})")
                                proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except ImportError:
            # psutil 없으면 taskkill 시도
            try:
                # 윈도우 한정: taskkill 사용 (단, 본인도 죽을 수 있어 주의 필요하나 --worker-id 까지 필터링 어려움)
                pass 
            except: pass

    def _auto_update(self):
        """서버 /update/list 로 파일 목록 확인 → 변경된 파일만 다운로드 후 교체"""
        import base64, hashlib
        try:
            resp = requests.get(f"{self.server_url}/update/list", timeout=5)
            if resp.status_code != 200:
                return
            files = resp.json().get('files', [])
            if not files:
                return
            updated = []
            for item in files:
                rel   = item['path']           # 예: scripts/integrated_solo_worker_v7.1.py
                md5   = item['md5']
                dest  = SOLO_DIR / rel         # 워커 루트 기준 경로
                # 로컬 파일 해시 비교
                if dest.exists():
                    local_md5 = hashlib.md5(dest.read_bytes()).hexdigest()
                    if local_md5 == md5:
                        continue               # 동일하면 스킵
                # 다운로드
                dl = requests.get(f"{self.server_url}/update/file/{rel}", timeout=30)
                if dl.status_code != 200:
                    self._log(f"[UPDATE] 다운로드 실패: {rel}")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(base64.b64decode(dl.json()['content_b64']))
                updated.append(rel)
                self._log(f"[UPDATE] 업데이트됨: {rel}")
            if updated:
                self._log(f"[UPDATE] {len(updated)}개 파일 업데이트. 재시작 필요.")
                import sys, os
                os.execv(sys.executable, [sys.executable] + sys.argv)  # 자동 재시작
        except Exception as e:
            self._log(f"[UPDATE] 체크 실패 (서버 미실행 등): {e}")

    def _get_experts_dir(self):
        """MT4 Experts 폴더 경로 결정 (current_config.ini 기준 우선)"""
        # 1순위: current_config.ini의 terminal_path 기준
        try:
            if INI_PATH.exists():
                config = self._read_ini(INI_PATH)
                
                terminal_path = config.get('folders', 'terminal_path', fallback='').strip()
                if terminal_path and terminal_path.upper() != 'NOTSET':
                    experts = Path(terminal_path) / "MQL4" / "Experts"
                    if experts.exists():
                        self._log(f"[INFO] Experts dir (INI terminal_path): {experts.absolute()}")
                        return experts

                # ea_path 직접 읽기 (terminal_path가 NOTSET이거나 없을 때)
                ea_path = config.get('folders', 'ea_path', fallback='').strip()
                if ea_path and ea_path.upper() != 'NOTSET':
                    experts = Path(ea_path)
                    if experts.exists():
                        self._log(f"[INFO] Experts dir (INI ea_path): {experts.absolute()}")
                        return experts
        except Exception as e:
            self._log(f"[WARN] Failed to read terminal_path: {e}")

        # 2순위: 현재 프로젝트 폴더 기준 포터블 MT4 Experts
        portable = PROJECT_DIR / "Worker_Setup_Package" / "MT4_Portable" / "MQL4" / "Experts"
        if portable.exists():
            self._log(f"[INFO] Experts dir (Portable fallback): {portable.absolute()}")
            return portable

        self._log(f"[WARN] MT4 Experts directory not found!")
        return None

    def _download_ea_from_server(self, ea_name: str) -> bool:
        """서버에서 EA 파일 다운로드 → EA_TEST_DIR 저장
        서버가 .ex4 우선 제공. .mq4만 있으면 Experts에 복사 후 MT4 자동 컴파일 대기.
        """
        import base64
        EA_TEST_DIR.mkdir(parents=True, exist_ok=True)

        # 이미 로컬에 .ex4 있으면 스킵
        for f in EA_TEST_DIR.glob("*.ex4"):
            if ea_name.lower().replace(' ','') in f.stem.lower().replace(' ',''):
                self._log(f"[CACHE] 로컬 .ex4 사용: {f.name}")
                return True

        try:
            import urllib.parse
            url = f"{self.server_url}/ea/source/{urllib.parse.quote(ea_name)}"
            self._log(f"[DL] EA 다운로드: {url}")
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                self._log(f"[ERR] EA 다운로드 실패: {resp.status_code}")
                return False
            data = resp.json()
            content = base64.b64decode(data['content_b64'])
            filename = data['filename']
            ext = data['ext']
            dest = EA_TEST_DIR / filename
            dest.write_bytes(content)
            self._log(f"[DL] 저장 완료: {dest} ({len(content)} bytes, {ext})")

            # .ex4이면 바로 사용 가능
            if ext == '.ex4':
                self._log(f"[DL] .ex4 수신 완료 - 바로 사용")
                return True

            # .mq4이면: Experts 폴더에 복사 후 MT4가 자동 컴파일한 .ex4 대기
            if ext == '.mq4' and self.experts_dir:
                experts_mq4 = self.experts_dir / filename
                experts_ex4 = self.experts_dir / (dest.stem + '.ex4')
                import shutil
                shutil.copy2(str(dest), str(experts_mq4))
                self._log(f"[COMPILE] .mq4 → Experts 복사, MT4 자동 컴파일 대기...")
                # MT4 백테스트 시작 전 최대 30초 대기
                for _ in range(6):
                    time.sleep(5)
                    if experts_ex4.exists():
                        # Experts의 .ex4를 EA_LOCAL로 역복사 (캐시)
                        shutil.copy2(str(experts_ex4), str(EA_TEST_DIR / (dest.stem + '.ex4')))
                        self._log(f"[COMPILE] MT4 컴파일 완료: {experts_ex4.name}")
                        return True
                self._log(f"[WARN] .ex4 컴파일 대기 타임아웃 → .mq4로 진행 (MT4가 실행 중이 아닐 수 있음)")
            return True
        except Exception as e:
            self._log(f"[ERR] EA 다운로드 오류: {e}")
            return False

    def _copy_ea_to_experts(self, ea_name: str):
        """ea test 폴더에서 MT4 Experts 폴더로 EA 복사"""
        if not self.experts_dir:
            self._log(f"[ERR] Cannot copy: Experts directory not set.")
            return False

        import shutil
        
        # [★ FIX] '01. EA_Name' 형태에서 번호 제거
        import re
        m = re.match(r'^\d+\.\s+(.*)$', ea_name)
        clean_ea = m.group(1) if m else ea_name
        
        # [DEEP OPT] 가상 EA 이름 (_V1 등) 제거 후 실제 EX4 검색
        actual_ea_name = clean_ea.split('_V')[0].strip()
        
        # Search variations
        search_names = [actual_ea_name, actual_ea_name.replace(' ', '_'), actual_ea_name.replace('_', ' '), clean_ea]
        ea_file = None
        for name in search_names:
            for ext in ['.ex4', '.mq4']:
                candidate = EA_TEST_DIR / (name.strip() + ext)
                if candidate.exists():
                    ea_file = candidate
                    break
            if ea_file: break

        if not ea_file:
            # [★ ENHANCED MATCHING] 
            # 1. 키워드 추출 (숫자와 문자만)
            kw = "".join(c for c in actual_ea_name if c.isalnum()).lower()
            # 2. 모든 파일 스캔
            for f in EA_TEST_DIR.glob("*"):
                if f.suffix in ['.ex4', '.mq4']:
                    f_clean = "".join(c for c in f.stem if c.isalnum()).lower()
                    # 부분 일치 확인 (db이름이 파일명에 포함되거나 그 반대)
                    if kw and (kw in f_clean or f_clean in kw):
                        ea_file = f
                        self._log(f"  [MATCH] Found via fuzzy: {f.name} for {actual_ea_name}")
                        break
                if ea_file: break

        if not ea_file:
            self._log(f"[ERR] EA Not Found in {EA_TEST_DIR.absolute()}: {clean_ea} (raw: {ea_name})")
            return False

        # Cleaning old files
        deleted = []
        for old in self.experts_dir.glob("*.ex4"):
            try: old.unlink(); deleted.append(old.name)
            except: pass
        if deleted: self._log(f"🗑️ Experts cleanup: {deleted}")

        dest = self.experts_dir / ea_file.name
        try:
            shutil.copy2(str(ea_file), str(dest))
            self._log(f"📁 EA copied: {ea_file.name} -> Experts/")
            return True
        except Exception as e:
            self._log(f"[ERR] Copy failed: {e}")
            return False

    def _copy_set_to_mt4(self, set_file: str):
        """SET 파일을 MT4 Presets/tester 폴더로 복사"""
        import shutil
        set_path = Path(set_file)
        if not set_path.exists():
            print(f"    [WARN] SET file not found: {set_file}")
            return False

        if self.experts_dir:
            # MT4 tester 폴더에도 복사 (MT4 백테스트에서 읽는 위치)
            mt4_root = self.experts_dir.parent.parent  # MQL4 -> MT4 root
            tester_dir = mt4_root / "tester"
            tester_dir.mkdir(parents=True, exist_ok=True)
            dest = tester_dir / set_path.name
            try:
                shutil.copy2(str(set_path), str(dest))
                print(f"    📋 SET copied: {set_path.name} → MT4/tester/")
                return True
            except Exception as e:
                print(f"    [WARN] SET copy failed: {e}")
        return False

    def _find_autohotkey(self):
        """AutoHotkey.exe 찾기"""
        paths = [
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
            r"C:\Program Files\AutoHotkey\AutoHotkeyU64.exe",
            r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe",
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        try:
            result = subprocess.run(["where", "AutoHotkey.exe"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        return "AutoHotkey.exe"

    def _run_comprehensive_analysis(self, ea_name, symbol, tf, from_date, to_date):
        """
        Run BacktestAnalyzer for comprehensive analysis after all backtests complete.
        This runs ONCE per EA, not per SET file.
        """
        self._log(f"📊 [COMPREHENSIVE] Starting full analysis for {ea_name}")

        try:
            # Determine report folder path
            today = datetime.now().strftime("%Y%m%d")
            report_base = Path("D:/2026OPTMIZER") / today / ea_name

            if not report_base.exists():
                self._log(f"  [WARN] Report folder not found: {report_base}")
                return

            # Path to BacktestAnalyzer_v1.7.py
            analyzer_script = SCRIPT_DIR / "BacktestAnalyzer_v1.7.py"

            if not analyzer_script.exists():
                self._log(f"  [ERR] BacktestAnalyzer not found: {analyzer_script}")
                return

            # Build command
            cmd = [
                "python",
                str(analyzer_script),
                "--auto", str(report_base),
                "--server", self.server_url,
                "--worker-id", str(self.worker_id),
                "--ea-name", ea_name,
                # Optional: add --email if email.json exists
            ]

            # Check if email.json exists
            email_config = SCRIPT_DIR / "email.json"
            if email_config.exists():
                cmd.append("--email")

            self._log(f"  [CMD] Running: {' '.join(cmd)}")

            # Run analyzer (with timeout to prevent hanging)
            result = subprocess.run(
                cmd,
                cwd=str(SCRIPT_DIR),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes max
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode == 0:
                self._log(f"  ✅ [COMPREHENSIVE] Analysis completed successfully")
                # Log key output lines
                for line in result.stdout.split('\n')[-10:]:
                    if line.strip():
                        self._log(f"     {line.strip()}")
            else:
                self._log(f"  ⚠️  [COMPREHENSIVE] Analyzer exited with code {result.returncode}")
                if result.stderr:
                    for line in result.stderr.split('\n')[:5]:
                        if line.strip():
                            self._log(f"     ERROR: {line.strip()}")

        except subprocess.TimeoutExpired:
            self._log(f"  [ERR] Analyzer timeout (5 min)")
        except Exception as e:
            self._log(f"  [ERR] Failed to run comprehensive analysis: {e}")

    def heartbeat_loop(self):
        """30초마다 서버에 상태 보고"""
        while self.running:
            try:
                data = {
                    'current_ea': self.current_ea,
                    'status': 'running' if self.current_ea else 'idle',
                    'iteration': self.current_iteration
                }
                resp = requests.post(f"{self.server_url}/worker/{self.worker_id}/heartbeat",
                             json=data, timeout=5)
                if resp.status_code != 200:
                    print(f"  [WARN] Heartbeat failed: {resp.status_code}")
            except Exception as e:
                print(f"  [WARN] Heartbeat error: {e}")
            time.sleep(30)

    def command_poll_loop(self):
        """10초마다 서버에서 원격 제어 명령 폴링 (shutdown/reboot/restart_mt4/restart_worker)"""
        import subprocess, os, sys
        while self.running:
            try:
                # URL 생성 시 슬래시 중복 방지 및 경로 명확화
                url = f"{self.server_url.rstrip('/')}/worker/{self.worker_id}/command"
                resp = requests.get(url, timeout=5)
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        cmd = data.get('command', '')
                    except:
                        # JSON 파싱 실패 시 서버가 HTML에러를 보낸 것임
                        time.sleep(10)
                        continue

                    if not cmd:
                        time.sleep(10)
                        continue

                    self._log(f"[CMD] 원격 명령 수신: {cmd}")

                    if cmd == 'shutdown':
                        self._log("[CMD] PC 종료 예약 (10초 후)...")
                        subprocess.Popen(['shutdown', '/s', '/t', '10', '/c', 'Worker Remote Shutdown'])
                        self.running = False

                    elif cmd == 'reboot':
                        self._log("[CMD] PC 재부팅 예약 (10초 후)...")
                        subprocess.Popen(['shutdown', '/r', '/t', '10', '/c', 'Worker Remote Reboot'])
                        self.running = False

                    elif cmd == 'restart_mt4':
                        self._log("[CMD] MT4 프로세스 강제 종료 중...")
                        subprocess.run(['taskkill', '/F', '/IM', 'terminal.exe'], capture_output=True)
                        subprocess.run(['taskkill', '/F', '/IM', 'terminal64.exe'], capture_output=True)
                        time.sleep(4)
                        
                        # MT4 재실행 시도
                        try:
                            cfg_path = SOLO_DIR / 'configs' / 'current_config.ini'
                            cfg = self._read_ini(cfg_path)
                            mt4_path = ""
                            if 'settings' in cfg:
                                mt4_path = cfg['settings'].get('mt4_path', '')
                            
                            if not mt4_path:
                                # 기본 경로 추정
                                mt4_path = str(PROJECT_DIR / "Worker_Setup_Package" / "MT4_Portable" / "terminal.exe")

                            if Path(mt4_path).exists():
                                self._log(f"[CMD] MT4 재실행: {mt4_path}")
                                subprocess.Popen([mt4_path, "/portable"])
                            else:
                                self._log(f"[ERR] MT4 실행파일을 찾을 수 없음: {mt4_path}")
                        except Exception as e:
                            self._log(f"[ERR] MT4 재시작 과정 중 오류: {e}")

                    elif cmd in ('restart_worker', 'RESTART'):
                        self._log("[CMD] 워커 자체 재시작 실행...")
                        subprocess.Popen([sys.executable] + sys.argv)
                        self.running = False
                        os._exit(0)

                    elif cmd in ('stop_worker', 'STOP'):
                        self._log("[CMD] 워커 중지 명령 수신.")
                        self.running = False
                        os._exit(0)

                    elif cmd == 'UPDATE':
                        self._log("[CMD] 자동 업데이트 시작...")
                        try:
                            au_script = SCRIPT_DIR / 'worker_auto_update.py'
                            if au_script.exists():
                                r = subprocess.run(
                                    [sys.executable, str(au_script), '--server', self.server_url],
                                    capture_output=True, text=True, timeout=60
                                )
                                self._log(f"[CMD] 업데이트 결과: {r.stdout.strip()[-200:] if r.stdout else '없음'}")
                                if r.returncode == 0:
                                    self._log("[CMD] 업데이트 완료 → 워커 재시작")
                                    subprocess.Popen([sys.executable] + sys.argv)
                                    self.running = False
                                    os._exit(0)
                            else:
                                self._log(f"[ERR] worker_auto_update.py 없음: {au_script}")
                        except Exception as e:
                            self._log(f"[ERR] UPDATE 처리 중 오류: {e}")

                    elif cmd == 'STATUS':
                        self._log(f"[CMD] STATUS | running={self.running} | server={self.server_url}")

                elif resp.status_code == 204:
                    pass # 명령 없음 (정상)
                else:
                    # 404 등 예외 상황
                    pass

            except requests.exceptions.RequestException:
                pass # 서버 연결 일시 끊김
            except Exception as e:
                self._log(f"[ERR] 명령 폴링 루프 오류: {e}")
            time.sleep(10)


    def get_next_task(self):
        """서버에서 다음 작업 조회 (EA + SET + 심볼/TF/날짜 + 진행정보)"""
        try:
            resp = requests.get(f"{self.server_url}/worker/{self.worker_id}/next", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get('ea_name'), 
                    data.get('set_file'), 
                    data.get('total_sets', 0), 
                    data.get('set_content'),
                    data.get('symbol'),
                    data.get('timeframe'),
                    data.get('from_date'),
                    data.get('to_date'),
                    data.get('tested_sets', 0)  # 추가: 현재까지 완료된 개수
                )
        except Exception as e:
            self._log(f"[ERR] Failed to get next task: {e}")
        return None, None, 0, None, None, None, None, None, 0

    def report_start(self, ea_name: str, iteration: int):
        """서버에 작업 시작 보고"""
        try:
            data = {'ea_name': ea_name, 'iteration': iteration}
            resp = requests.post(f"{self.server_url}/worker/{self.worker_id}/start",
                         json=data, timeout=10)
            if resp.status_code == 200:
                print(f"  [INFO] Reported start: {ea_name}")
            else:
                print(f"  [WARN] Report start failed: {resp.status_code}")
        except Exception as e:
            print(f"  [WARN] Report start error: {e}")

    def report_result(self, ea_name: str, iteration: int, result: dict):
        """서버에 결과 보고 - /results/submit으로 전송 (set_files.tested 업데이트 + Round 2 트리거)"""
        try:
            # /results/submit 형식으로 변환
            submit_result = {
                'ea_name': ea_name,
                'score':          result.get('score', 0),
                'grade':          result.get('grade', ''),
                'net_profit':     result.get('net_profit', 0),
                'profit_factor':  result.get('profit_factor', 0),
                'max_drawdown':   result.get('max_drawdown', 0),
                'total_trades':   result.get('total_trades', 0),
                'win_rate':       result.get('win_rate', 0),
                'symbol':         result.get('symbol', self.symbol),
                'timeframe':      result.get('timeframe', self.tf),
                'parameters':     result.get('parameters', ''),
                'set_name':       result.get('set_name', ''),   # set_files 매칭 핵심
            }
            data = {
                'results': [submit_result],
                'worker_id': self.worker_id
            }
            resp = requests.post(f"{self.server_url}/results/submit",
                                json=data, timeout=10)
            if resp.status_code == 200:
                rjson = resp.json()
                self._log(f"    → Server: set_matched={rjson.get('set_matched',0)}, "
                      f"round2={rjson.get('round2_triggered', [])}")
                return rjson
            else:
                 self._log(f"    [WARN] Server rejected result: {resp.status_code} {resp.text}")
        except Exception as e:
            self._log(f"  [WARN] Failed to report result: {e}")
        return None

    def run_single_backtest(self, ea_name: str, set_file: str, iteration: int):
        """단일 백테스트 실행 (command.json을 통한 SOLO 7.0 연동 방식)"""
        self._log(f"\n  [{iteration}/{self.max_iterations}] Testing: {ea_name}")
        self._log(f"    SET: {Path(set_file).name if set_file else 'default'}")

        # 서버에서 EA 다운로드 (로컬에 없으면)
        self._download_ea_from_server(ea_name)
        # EA를 EA_LOCAL → MT4 Experts 폴더로 복사
        self._copy_ea_to_experts(ea_name)

        # SET 파일도 MT4 Presets 폴더로 복사
        if set_file:
            self._copy_set_to_mt4(set_file)

        # INI 설정 업데이트
        self._update_config(ea_name, set_file)

        # command.json 생성 (SOLO 7.0 자동 트리거용)
        # AHK A_ScriptDir = SOLO_3.0.ahk 위치 = SOLO_DIR (scripts의 부모)
        # AHK configsFolder = SOLO_DIR\configs → Python도 같은 폴더 사용
        base_configs = SOLO_DIR / "configs"
        command_file = base_configs / "command.json"
        completion_marker = base_configs / "test_completed.flag"
        
        # Ensure directory exists just in case
        base_configs.mkdir(parents=True, exist_ok=True)
        
        # 이전 완료 플래그 삭제
        if completion_marker.exists():
            completion_marker.unlink()
            
        task_data = {
            "ea_name": ea_name,
            "set_file": str(set_file) if set_file else "",
            "symbol": self.symbol,
            "tf": self.tf,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "iteration": iteration,  # 서버 기준 진행 번호
            "total_sets": getattr(self, '_current_total_sets', self.max_iterations)
        }
        
        with open(command_file, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=4, ensure_ascii=False)
        
        total_disp = getattr(self, '_current_total_sets', '?')
        print(f"    🚀 Triggered via command.json [{iteration}/{total_disp}], waiting for test_completed.flag...")

        start_time = datetime.now()
        timeout = 600  # 10분
        success = False

        try:
            # 완료 플래그 폴링
            last_print = 0
            while (datetime.now() - start_time).total_seconds() < timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Debug logging every 10 seconds
                if elapsed - last_print > 10:
                    self._log(f"    ... waiting for completion flag ({elapsed:.0f}s)")
                    last_print = elapsed
    
                if completion_marker.exists():
                    try:
                        size = completion_marker.stat().st_size
                        if size > 0:
                            success = True
                            self._log(f"    ✓ Completion Flag Detected (Size: {size})")
                            # [★ BUG FIX] 즉시 삭제 - 다음 SET 시작 시 오감지 방지
                            try:
                                completion_marker.unlink()
                                self._log(f"    🗑 Flag deleted (prevent re-detection)")
                            except Exception as del_e:
                                self._log(f"    [WARN] Flag delete failed: {del_e}")
                            break
                        else:
                            if elapsed - last_print > 5:
                                self._log(f"    . Flag found but empty...")
                    except:
                        pass
                time.sleep(1)

            elapsed = (datetime.now() - start_time).total_seconds()
            
            if not success:
                print(f"    ⏱ TIMEOUT ({timeout}s)")
                report_result = self._find_and_analyze_report(ea_name, start_time, set_file)
                return {
                    'success': False,
                    'elapsed': elapsed,
                    'timeout': True,
                    'analysis': report_result
                }

            print(f"    ✓ OK ({elapsed:.0f}s)")

            # 리포트 찾기 및 분석
            report_result = self._find_and_analyze_report(ea_name, start_time, set_file)

            return {
                'success': True,
                'elapsed': elapsed,
                'analysis': report_result
            }

        except Exception as e:
            print(f"    ✗ ERROR: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _update_config(self, ea_name: str, set_file: str):
        """current_config.ini 업데이트 (html_save_path 포함)"""
        try:
            config = self._read_ini(INI_PATH)

            if not config.has_section('current_backtest'):
                config.add_section('current_backtest')

            if set_file:
                config.set('current_backtest', 'has_set', '1')
                config.set('current_backtest', 'set_file_path', set_file)
            else:
                config.set('current_backtest', 'has_set', '0')

            config.set('current_backtest', 'ea_name', ea_name)

            # html_save_path 업데이트: 오늘 날짜 + EA 이름 폴더
            today = datetime.now().strftime('%Y%m%d')
            html_base = "D:/2026OPTMIZER"
            html_save_path = f"{html_base}/{today}/{ea_name}"
            if not config.has_section('folders'):
                config.add_section('folders')
            config.set('folders', 'html_save_path', html_save_path)
            self._current_html_save_path = html_save_path  # 나중에 참조용

            if not config.has_section('test_date'):
                config.add_section('test_date')
            config.set('test_date', 'enable', '1')
            config.set('test_date', 'from_date', self.from_date)
            config.set('test_date', 'to_date', self.to_date)

            with open(INI_PATH, 'w', encoding='utf-16') as f:
                config.write(f)

            print(f"    📂 HTML save: {html_save_path}")

            # [FAIL-SAFE] Modify MT4 tester.ini directly
            if self.experts_dir:
                try:
                    mt4_root = self.experts_dir.parent.parent
                    tester_ini = mt4_root / "tester" / "tester.ini"
                    if tester_ini.exists():
                        t_config = self._read_ini(tester_ini)
                        
                        if not t_config.has_section('Tester'):
                            t_config.add_section('Tester')
                            
                        # Set Expert
                        clean_name = ea_name
                        if clean_name.lower().endswith('.ex4'):
                            clean_name = clean_name[:-4]
                        t_config.set('Tester', 'Expert', clean_name)
                        
                        # Write back
                        with open(tester_ini, 'w', encoding='utf-16') as tf:
                            t_config.write(tf)
                            
                        print(f"    [FAIL-SAFE] Updated tester.ini: Expert={clean_name}")
                        
                except Exception as e2:
                    print(f"    [WARN] Failed to update tester.ini: {e2}")

        except Exception as e:
            print(f"    [WARN] Config update failed: {e}")

    def _wait_for_file_ready(self, file_path: Path, timeout=15):
        """파일이 완전히 쓰여질 때까지 대기 (사이즈 변화 체크)"""
        import time
        start_time = time.time()
        last_size = -1
        stable_count = 0
        
        while time.time() - start_time < timeout:
            try:
                if not file_path.exists():
                    time.sleep(0.5)
                    continue
                    
                size = file_path.stat().st_size
                if size == last_size and size > 0:
                    stable_count += 1
                else:
                    last_size = size
                    stable_count = 0
                
                if stable_count >= 4: # 2초간 안정되면 완료로 간주
                    return True
                    
                time.sleep(0.5)
            except:
                time.sleep(0.5)
        
        self._log(f"    [WARN] File wait timeout. Proceeding anyway: {file_path.name}")
        return False

    def _find_and_analyze_report(self, ea_name: str, since: datetime, set_file: str = None):
        """최신 리포트 찾기 - EA 폴더명 불일치해도 날짜 폴더 전체 검색"""

        import shutil
        from datetime import timedelta
        import re as _re

        search_dirs = []

        # ① INI에서 html_save_path 직접 읽기 (가장 우선)
        try:
            if INI_PATH.exists():
                raw = INI_PATH.read_bytes()
                enc = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
                cfg = configparser.ConfigParser()
                cfg.read_string(raw.decode(enc, errors='ignore'))
                p = cfg.get('folders', 'html_save_path', fallback='').strip()
                if p:
                    search_dirs.insert(0, Path(p))
        except: pass

        # ② 날짜 폴더 전체 서브폴더 (EA 폴더명 불문)
        for base in [r"D:\2026OPTMIZER", r"C:\2026OPTMIZER"]:
            for offset in [0, -1, -2]:
                d = (datetime.now() + timedelta(days=offset)).strftime('%Y%m%d')
                date_dir = Path(base) / d
                if date_dir.exists():
                    # mtime 순으로 최근 폴더 우선
                    try:
                        subs = sorted(date_dir.iterdir(),
                                      key=lambda p: p.stat().st_mtime, reverse=True)
                        for sub in subs:
                            if sub.is_dir() and sub not in search_dirs:
                                search_dirs.append(sub)
                    except: pass
                # EA 이름 직접 매칭도 추가
                search_dirs.append(Path(base) / d / ea_name)

        # ③ HTM 파일 탐색 (since 이후 OR 최근 30분)
        latest_file = None
        best_mtime  = 0.0
        cutoff = since.timestamp() - 60  # 1분 여유

        print(f"    🔍 {len(search_dirs)}개 경로 검색 (since {since.strftime('%H:%M:%S')})")

        for d in search_dirs:
            if not d.exists(): continue
            try:
                for htm in d.glob("*.htm"):
                    try:
                        mt = htm.stat().st_mtime
                        if mt >= cutoff and mt > best_mtime:
                            best_mtime = mt; latest_file = htm
                    except: continue
            except: continue

        # ④ 넓히기: 최근 60분 파일
        if not latest_file:
            cutoff2 = datetime.now().timestamp() - 3600
            for d in search_dirs:
                if not d.exists(): continue
                try:
                    for htm in d.glob("*.htm"):
                        try:
                            mt = htm.stat().st_mtime
                            if mt >= cutoff2 and mt > best_mtime:
                                best_mtime = mt; latest_file = htm
                        except: continue
                except: continue

        if not latest_file:
            self._log(f"    ❌ HTM 리포트 없음. 검색경로 예시: {search_dirs[:2]}")
            return None

        self._log(f"    ✅ Used Report: {latest_file}")

        if set_file and Path(set_file).exists():
            try: shutil.copy2(set_file, latest_file.with_suffix('.set'))
            except: pass

        # [★ FIX] 파일이 완전히 기록될 때까지 대기
        self._wait_for_file_ready(latest_file)

        # ⑤ 분석
        result = None
        if self.analyzer:
            try:
                result = self.analyzer.analyze_report(str(latest_file), allow_incomplete=True)
            except Exception as e:
                print(f"    [WARN] analyzer error: {e}")

        if not result:
            result = self._partial_analysis(latest_file)

        if result:
            if set_file:
                result['set_file'] = str(set_file)
                result['set_name'] = Path(set_file).stem
            result['file'] = str(latest_file)
            print(f"    📊 [{result.get('grade','?')}] "
                  f"NP:{result.get('net_profit',0):,.0f} "
                  f"PF:{result.get('profit_factor',0):.2f} "
                  f"T:{result.get('total_trades',0)} S:{result.get('score',0)}")
        return result


    def _partial_analysis(self, htm_file: Path):
        """불완전한 리포트라도 기본 정보 추출"""
        try:
            with open(htm_file, 'rb') as f:
                raw = f.read()
                try:
                    html = raw.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        html = raw.decode('cp949')
                    except UnicodeDecodeError:
                        html = raw.decode('utf-16', errors='ignore')

            # 최소한의 정보 추출
            import re

            # Net Profit 찾기
            net_match = re.search(r'Total net profit.*?(-?\d+\.?\d*)', html, re.IGNORECASE)
            net_profit = float(net_match.group(1)) if net_match else 0.0

            # Profit Factor 찾기
            pf_match = re.search(r'Profit factor.*?(\d+\.?\d*)', html, re.IGNORECASE)
            profit_factor = float(pf_match.group(1)) if pf_match else 0.0

            # Total Trades 찾기
            trades_match = re.search(r'Total trades.*?(\d+)', html, re.IGNORECASE)
            total_trades = int(trades_match.group(1)) if trades_match else 0

            return {
                'file': htm_file.name,
                'net_profit': net_profit,
                'profit_factor': profit_factor,
                'total_trades': total_trades,
                'grade': 'B' if profit_factor >= 1.2 else ('C' if profit_factor >= 1.0 else 'D'),
                'score': int(profit_factor * 30) if profit_factor > 0 else 0,
                'incomplete': True  # 불완전 데이터 플래그
            }

        except:
            return {'incomplete': True, 'error': 'partial_analysis_failed'}

    def _save_result_to_local_db(self, ea_name: str, result: dict):
        """결과를 로컬 optimizer.db에 직접 저장 (서버 불필요 - GUI 결과탭 표시용)"""
        if not result:
            return
        try:
            db_path = Path(r"C:\NEWOPTMISER\Server\3_SOLO_Local\configs\optimizer.db")
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(db_path, timeout=5)
            conn.execute("""CREATE TABLE IF NOT EXISTS backtest_results
                (id INTEGER PRIMARY KEY, ea_name TEXT, symbol TEXT, timeframe TEXT,
                 net_profit REAL, profit_factor REAL, max_drawdown REAL,
                 total_trades INTEGER, win_rate REAL, score REAL, grade TEXT,
                 set_file TEXT, analyzed_at TEXT)""")
            conn.execute("""INSERT INTO backtest_results
                (ea_name, symbol, timeframe, net_profit, profit_factor,
                 max_drawdown, total_trades, win_rate, score, grade, set_file, analyzed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                ea_name,
                result.get('symbol', self.symbol),
                result.get('timeframe', self.tf),
                result.get('net_profit', 0),
                result.get('profit_factor', 0),
                result.get('max_drawdown', 0),
                result.get('total_trades', 0),
                result.get('win_rate', 0),
                result.get('score', 0),
                result.get('grade', '?'),
                result.get('set_file', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            conn.close()
            print(f"    💾 Saved to local DB: {ea_name} | score={result.get('score',0)} | grade={result.get('grade','?')}")
        except Exception as e:
            print(f"    [WARN] Local DB save failed: {e}")

    def optimize_ea(self, ea_name: str, initial_set_files: list, start_iter=1, original_set_name=None):
        """EA 최적화 루프 (단일 SET 수행도 이 함수를 거침)"""

        # print(f"\n{'='*60}")
        # print(f"  Optimizing: {ea_name}")
        # print(f"{'='*60}")

        self.current_ea = ea_name
        # self._current_total_sets는 이미 run()에서 설정됨
        
        # 0번 iteration은 '시작' 의미로 사용 가능 (여기서는 생략하거나 필요시 호출)
        # self.report_start(ea_name, 0)

        best_result = None
        best_score = 0
        iteration_results = []

        # 1차: 초기 SET 파일 테스트
        for i, set_file in enumerate(initial_set_files[:self.max_iterations]):
            # [★ FIX] iteration 번호 동기화 (서버 기준)
            current_iter = i + start_iter
            self.current_iteration = current_iter

            result = self.run_single_backtest(ea_name, set_file, current_iter)

            if result.get('analysis'):
                analysis = result['analysis']
                # [★ FIX] set_name이 temp path로 되어있으면 original name으로 교체
                if original_set_name and len(initial_set_files) == 1:
                    analysis['set_name'] = original_set_name
                
                score = analysis.get('score', 0)

                if score > best_score:
                    best_score = score
                    best_result = analysis
                    print(f"    🌟 New Best: {best_score}pt")

                iteration_results.append(analysis)

                # 서버에 결과 보고
                server_response = self.report_result(ea_name, current_iter, analysis)

                # [★ NEW] 로컬 DB에도 직접 저장 (서버 연결 실패해도 결과 보존)
                self._save_result_to_local_db(ea_name, analysis)

                # 서버가 새로운 SET 파일 추천 가능
                if server_response and server_response.get('new_set'):
                    new_set = server_response['new_set']
                    print(f"    📥 Server suggests new SET: {new_set}")
                    if i + 1 < self.max_iterations:
                        initial_set_files.insert(i + 2, new_set)

            # 진행률 보고 (10회마다)
            if (i + 1) % 10 == 0:
                print(f"\n  Progress: {i+1}/{min(len(initial_set_files), self.max_iterations)} | "
                      f"Best: {best_score}pt")

        # 최종 결과
        print(f"\n{'='*60}")
        print(f"  Optimization Complete: {ea_name}")
        print(f"  Iterations: {len(iteration_results)}")
        print(f"  Best Score: {best_score}pt")
        if best_result:
            print(f"  Best PF: {best_result.get('profit_factor', 0):.2f}")
            print(f"  Best Net Profit: ${best_result.get('net_profit', 0):.2f}")
        print(f"{'='*60}\n")

        self.current_ea = ''
        return best_result, iteration_results

    def run(self):
        """메인 루프"""
        # Heartbeat 스레드 시작
        hb_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        hb_thread.start()

        # 원격 명령 폴링 스레드 시작 (shutdown/reboot/restart_mt4 등)
        cmd_thread = threading.Thread(target=self.command_poll_loop, daemon=True)
        cmd_thread.start()

        self._log(f"Worker {self.worker_id} started. Waiting for tasks...")
        idle_count = 0
        tasks_done = 0  # [★ FIX] 완료된 태스크 수 누적 (all_done.flag 생성 조건)

        while self.running:
            # 서버에서 다음 작업 조회
            task_info = self.get_next_task()
            ea_name, set_file, total_sets, set_content, symbol, tf, start_d, end_d, tested_sets = task_info

            if ea_name:
                idle_count = 0
                self._current_total_sets = total_sets  # AHK 전역 표시용
                iter_num = tested_sets + 1  # 1번부터 표시
                
                # 가변 설정 적용 (서버 데이터 우선)
                if symbol: self.symbol = symbol
                if tf: self.tf = tf
                if start_d: self.from_date = start_d
                if end_d: self.to_date = end_d
                
                self._log(f"  [TASK] {ea_name} | Sym: {self.symbol} | TF: {self.tf} | Period: {self.from_date} ~ {self.to_date}")

                # SET 파일 목록 구성
                set_files = []
                if set_content:
                    try:
                        ea_set_dir = SET_DIR / ea_name
                        ea_set_dir.mkdir(parents=True, exist_ok=True)
                        temp_set_path = ea_set_dir / f"{ea_name}_task.set"
                        with open(temp_set_path, "w", encoding="utf-8") as f:
                            f.write(set_content)
                        set_files.append(str(temp_set_path))
                        # set_file = str(temp_set_path) # [★ FIX] 원본 이름 보존!
                    except Exception as e:
                        self._log(f"[ERR] Failed to save task SET: {e}")

                # [★ FIX] 서버가 준 SET만 실행 (로컬 자동 수집 제거하여 분배 무결성 유지)
                if not set_files:
                    if set_file: set_files = [str(set_file)]

                if not set_files:
                    # Round 1: SET 없으면 InpBTMode=1 기본 SET 자동 생성 (EA 기본값=false 방지)
                    self._log(f"  [R1] No SET files for {ea_name}. Generating default BT SET (InpBTMode=1).")
                    ea_set_dir = SET_DIR / ea_name
                    ea_set_dir.mkdir(parents=True, exist_ok=True)
                    default_set_path = ea_set_dir / f"{ea_name}_default_bt.set"
                    default_set_content = (
                        f"; Auto-generated default BT SET for {ea_name}\n"
                        f"; InpBTMode=1 (BT_Patch ATR mode forced ON)\n"
                        f"InpBTMode=1\n"
                    )
                    try:
                        default_set_path.write_text(default_set_content, encoding="utf-8")
                        set_files = [str(default_set_path)]
                        self._log(f"  [R1] Default SET created: {default_set_path}")
                    except Exception as e:
                        self._log(f"  [ERR] Failed to create default SET: {e}")
                        set_files = ['']  # 최후 폴백

                # 백테스트 실행 (서버에서 가져온 1개 SET에 대해)
                # iteration 번호는 서버 기준 현재 번호(tested_sets+1)를 사용
                # [★ FIX] original_set_name 전달
                best_result, all_results = self.optimize_ea(ea_name, set_files, start_iter=iter_num, original_set_name=set_file)
                tasks_done += 1  # [★ FIX] 완료된 태스크 수 누적

                # 서버에 태스크 완료 보고
                try:
                    best_score = best_result.get('score', 0) if best_result else 0
                    best_grade = best_result.get('grade', '') if best_result else ''
                    requests.post(f"{self.server_url}/worker/{self.worker_id}/complete",
                                  json={"ea_name": ea_name, "tested": total_sets,
                                        "best_score": best_score, "best_grade": best_grade},
                                  timeout=10)
                except: pass

                self._log(f"✅ [TASK DONE] {ea_name} 완료됨. (누적 {tasks_done}개)")

                # [★ NEW] Run comprehensive analysis with BacktestAnalyzer (EA별 리포트)
                self._run_comprehensive_analysis(ea_name, self.symbol, self.tf,
                                                self.from_date, self.to_date)
            else:
                idle_count += 1
                if idle_count == 1:
                    print(f"  [IDLE] No tasks. Waiting... (tasks_done={tasks_done})")

                # [★ FIX] all_done.flag는 60초(6폴링) 연속 빈 응답 후에만 생성
                # - idle_count==1 즉시 발동 금지: 태스크 간 일시적 빈 응답에 오발동됨
                # - 10개 태스크(2 EA × 5 set) 전체 완료 후에만 1번 발동해야 함
                if tasks_done > 0 and idle_count >= 6:
                    base_configs = SOLO_DIR / "configs"
                    all_done_flag = base_configs / "all_done.flag"
                    try:
                        done_data = {
                            "ea_name": "",
                            "total_tested": tasks_done,
                            "timestamp": datetime.now().isoformat(),
                            "status": "ALL_COMPLETE"
                        }
                        all_done_flag.write_text(json.dumps(done_data, ensure_ascii=False), encoding="utf-8")
                        self._log(f"🚩 [ALL DONE] 총 {tasks_done}개 태스크 완료. 전체 완료 알림 플래그 생성됨.")
                    except Exception as e:
                        self._log(f"[ERR] all_done.flag 생성 실패: {e}")
                    tasks_done = 0   # 다음 배치를 위해 초기화
                    idle_count = 0   # 리셋
                time.sleep(10)

                # 30분 동안 작업 없으면 종료 (선택 사항)
                if idle_count > 180:
                    self._log("  [TIMEOUT] Shutting down after 30m idle.")
                    break


        self.running = False
        print(f"\n  Worker {self.worker_id} stopped.")


def main():
    import argparse, configparser, subprocess
    parser = argparse.ArgumentParser(description='Integrated SOLO Worker v7.1')
    parser.add_argument('--worker-id',   default='',  help='Worker ID (예: SOLO25, PC01 등)')
    parser.add_argument('--worker-name', default='',  help='Worker PC name')
    parser.add_argument('--server',      default='',  help='Master Server URL (예: http://100.80.221.25:9001)')
    parser.add_argument('--max-iterations', type=int, default=100)
    parser.add_argument('--symbol',      default='',  help='Symbol (미입력시 config.ini 사용)')
    parser.add_argument('--tf',          default='',  help='Timeframe')
    parser.add_argument('--from-date',   default='',  help='From date')
    parser.add_argument('--to-date',     default='',  help='To date')
    parser.add_argument('--launch-mt4',  action='store_true', help='MT4 Portable 자동 실행')
    parser.add_argument('--config',      default='',  help='current_config.ini 경로')
    args = parser.parse_args()

    # ── config.ini 에서 설정 읽기 ──────────────────────────────
    cfg = configparser.ConfigParser()
    cfg_path = Path(args.config) if args.config else SCRIPT_DIR / 'current_config.ini'
    if not cfg_path.exists():
        cfg_path = SCRIPT_DIR.parent / 'configs' / 'current_config.ini'
    if cfg_path.exists():
        # 임시로 더미 객체 생성하여 메서드 사용 (혹은 전역 함수로 분리 가능)
        class Dummy: pass
        d = Dummy()
        d._log = lambda x: print(x)
        def _read_ini_simple(path):
            config = configparser.ConfigParser()
            config.optionxform = str
            raw = path.read_bytes()
            if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
                content = raw.decode('utf-16', errors='ignore')
            else:
                try: content = raw.decode('utf-8')
                except: content = raw.decode('cp949', errors='ignore')
            config.read_string(content)
            return config
        
        cfg = _read_ini_simple(cfg_path)
        sec = cfg['settings'] if 'settings' in cfg else (cfg['worker'] if 'worker' in cfg else {})
        if not args.worker_id:    args.worker_id   = sec.get('worker_id',   'WORKER01')
        if not args.server:       args.server      = sec.get('server_url',  'http://100.80.221.25:9001')
        if not args.symbol:       args.symbol      = sec.get('symbol',      'XAUUSD')
        if not args.tf:           args.tf          = sec.get('timeframe',   'H1')
        if not args.from_date:    args.from_date   = sec.get('from_date',   '2024.07.01')
        if not args.to_date:      args.to_date     = sec.get('to_date',     '2024.09.30')
        mt4_path = sec.get('mt4_path', '')
        print(f"  [CONFIG] {cfg_path}")
    else:
        mt4_path = ''
        print(f"  [WARN] config.ini not found, use defaults")

    # ── 최종 설정 출력 ────────────────────────────────────────
    if not args.worker_id: args.worker_id = 'WORKER01'
    if not args.server:    args.server    = 'http://100.80.221.25:9001'
    print(f"  Worker ID : {args.worker_id}")
    print(f"  Server    : {args.server}")
    print(f"  Symbol    : {args.symbol} / {args.tf}")
    print(f"  Period    : {args.from_date} ~ {args.to_date}")

    # ── MT4 Portable 자동 실행 ────────────────────────────────
    if args.launch_mt4 and mt4_path:
        mt4 = Path(mt4_path)
        if mt4.exists():
            subprocess.Popen([str(mt4)], cwd=str(mt4.parent))
            print(f"  [MT4] 실행: {mt4}")
            import time; time.sleep(5)  # MT4 초기화 대기
        else:
            print(f"  [WARN] MT4 경로 없음: {mt4_path}")

    # ── 서버 연결 확인 ─────────────────────────────────────────
    import time
    for retry in range(5):
        try:
            resp = requests.get(f"{args.server}/status", timeout=5)
            if resp.status_code == 200:
                print(f"  [OK] 서버 연결 성공: {args.server}")
                break
        except Exception as e:
            print(f"  [RETRY {retry+1}/5] 서버 연결 실패: {e}")
            time.sleep(3)
    else:
        print(f"[ERROR] 서버({args.server})에 연결할 수 없습니다.")
        sys.exit(1)

    worker = IntegratedSOLOWorker(
        args.worker_id,
        args.server,
        args.max_iterations,
        args.symbol,
        args.tf,
        args.from_date,
        args.to_date
    )

    try:
        worker.run()
    except KeyboardInterrupt:
        print(f"\n  [STOP] Worker {args.worker_id} stopped.")
        worker.running = False


if __name__ == "__main__":
    main()
