"""
ea_optimizer_v7.py ??EA Auto Master v8.0 硫붿씤 ?듯떚留덉씠?
=========================================================
?대뼡 EA?? 紐?媛?蹂?섎뱺 吏?ν삎 ?먯깋?쇰줈 理쒖쟻 ?뚮씪誘명꽣 諛쒓뎬.

?먯깋 ?꾨왂 (?먮룞 ?꾪솚):
  R1~2:  LHS    ???꾩껜 怨듦컙 洹좊벑 ?ㅼ틪
  R3~5:  FOCUSED ???곸쐞 寃곌낵 二쇰? 吏묒쨷
  R6+:   GENETIC ??援먯감 吏꾪솕

?먯닔: 6媛?紐⑹쟻?⑥닔 (?섏씡쨌?덉쟾쨌?덉젙쨌?⑥쑉쨌?쒖옣?곹빀쨌寃ш퀬??
"""
import os, sys, json, glob, shutil, re, time, subprocess
from datetime import datetime

# Windows 肄섏넄 UTF-8 (line_buffering=True so output flows through pipes)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8',
                                  errors='replace', line_buffering=True)

# ?? 寃쎈줈 ?ㅼ젙 ?????????????????????????????????????????????????????????????
SOLO_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(SOLO_DIR, 'configs')
CMD_JSON    = os.path.join(CONFIGS_DIR, 'command.json')
DONE_FLAG   = os.path.join(CONFIGS_DIR, 'test_completed.flag')
REPORTS_BASE= os.path.join(SOLO_DIR, 'reports')
RESULTS_DIR = os.path.join(SOLO_DIR, 'g4_results')
READY_DIR   = os.path.join(REPORTS_BASE, 'READY_FOR_TEST')   # ?뚯뒪???湲?EA 蹂닿?
AFTER_DIR   = os.path.join(REPORTS_BASE, 'AFTER_FOR_TEST')   # ?뚯뒪???꾨즺 EA 蹂닿?

def _find_mt4():
    # 1순위: current_config.ini의 terminal_path (어떤 PC에서도 동작)
    try:
        cfg_path = os.path.join(SOLO_DIR, 'configs', 'current_config.ini')
        if os.path.exists(cfg_path):
            with open(cfg_path, 'rb') as _f:
                _raw = _f.read()
            _text = _raw[2:].decode('utf-16-le') if _raw[:2] in (b'\xff\xfe', b'\xfe\xff') else _raw.decode('utf-8', errors='replace')
            for _line in _text.splitlines():
                _line = _line.strip()
                if _line.lower().startswith('terminal_path='):
                    _p = _line.split('=', 1)[1].strip()
                    if _p and os.path.exists(os.path.join(_p, 'terminal.exe')):
                        return _p
    except Exception:
        pass
    # 2순위: 일반 경로 탐색
    for p in [r'C:\AG TO DO\MT4', r'C:\MT4', r'D:\MT4',
              r'C:\Program Files\MetaTrader 4',
              r'C:\Program Files (x86)\MetaTrader 4']:
        if os.path.exists(os.path.join(p, 'terminal.exe')):
            return p
    return r'C:\AG TO DO\MT4'

MT4_DIR     = _find_mt4()
EXPERTS_DIR = os.path.join(MT4_DIR, r'MQL4\Experts')
BACKUP_ROOT = os.path.join(MT4_DIR, r'MQL4\_EXPERTS_BACKUP_V7')
ME_EXE      = os.path.join(MT4_DIR, 'metaeditor.exe')

def _restart_mt4_for_new_round():
    """새 EA 파일 인식을 위해 MT4 재시작 (라운드 전환 시 호출)."""
    print('  [MT4] 새 EA 파일 인식 위해 MT4 재시작...')
    # MT4 종료
    subprocess.run(['taskkill', '/F', '/IM', 'terminal.exe'],
                   capture_output=True)
    time.sleep(4)
    # MT4 재시작 (포터블 모드 우선)
    mt4 = _find_mt4()
    portable_bat = os.path.join(mt4, 'Start_Portable.bat')
    if os.path.exists(portable_bat):
        subprocess.Popen(['cmd', '/c', portable_bat], cwd=mt4,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen([os.path.join(mt4, 'terminal.exe'), '/portable'],
                         cwd=mt4,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    print('  [MT4] 재시작 후 30초 대기...')
    time.sleep(30)
    print('  [MT4] 준비 완료')

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(BACKUP_ROOT, exist_ok=True)
os.makedirs(READY_DIR,   exist_ok=True)
os.makedirs(AFTER_DIR,   exist_ok=True)


def _ea_to_ready(ex4_path: str):
    """而댄뙆?쇰맂 EA瑜?READY_FOR_TEST??蹂듭궗 (??뼱?곌린 ?덉슜)."""
    try:
        dst = os.path.join(READY_DIR, os.path.basename(ex4_path))
        shutil.copy2(ex4_path, dst)
    except Exception as e:
        print(f"  [WARN] READY 蹂듭궗 ?ㅽ뙣: {e}")


def _ea_to_after(ex4_path: str):
    """?뚯뒪???꾨즺??EA瑜?AFTER_FOR_TEST濡??대룞 (READY?먯꽌 ??젣)."""
    try:
        fname = os.path.basename(ex4_path)
        dst   = os.path.join(AFTER_DIR, fname)
        shutil.copy2(ex4_path, dst)
        # READY?먯꽌 ?쒓굅
        ready_src = os.path.join(READY_DIR, fname)
        if os.path.exists(ready_src):
            os.remove(ready_src)
    except Exception as e:
        print(f"  [WARN] AFTER ?대룞 ?ㅽ뙣: {e}")

# ?€?€ 諛깊뀒?ㅽ듃 ?ㅼ젙 ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# 硫€???щ낵/TF: 媛??쒕굹由ъ삤瑜?紐⑤뱺 肄ㅻ낫濡??뚯뒪?????됯퇏 ?ㅼ퐫?대줈 ??궧
SYMBOLS    = ['XAUUSD', 'BTCUSD']   # GOLD + BTC
TIMEFRAMES = ['M5', 'M15', 'M30']   # 5遺?15遺?30遺?(6肄ㅻ낫/?쒕굹由ъ삤)
SYMBOL    = SYMBOLS[0]   # ?섏쐞 ?명솚??(?⑤룆 異쒕젰 ?깆뿉 ?ъ슜)
TIMEFRAME = TIMEFRAMES[0]
FROM_DATE = '2025.04.01'
TO_DATE   = '2026.04.01'
MAX_ROUNDS = 10

def _read_ini_robust(path):
    import configparser
    cp = configparser.ConfigParser()
    if not os.path.exists(path): return cp
    try:
        with open(path, 'rb') as f:
            raw = f.read()
            # UTF-16 check
            if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
                content = raw.decode('utf-16', errors='replace')
            # UTF-8 BOM check (\xef\xbb\xbf)
            elif raw.startswith(b'\xef\xbb\xbf'):
                content = raw.decode('utf-8-sig', errors='replace')
            else:
                try: content = raw.decode('utf-8')
                except: content = raw.decode('cp949', errors='replace')
        cp.read_string(content)
    except Exception as e:
        print(f"  [WARN] INI ?뚯씪 ?쎌궓 ?ㅽ뙣: {e}")
    return cp

def _load_dates_from_ini():
    """configs/current_config.ini [test_date] ?섏뀡?먕꽌 ?쒖꽦 ??씪 ?쎌궓."""
    ini_path = os.path.join(CONFIGS_DIR, 'current_config.ini')
    cp = _read_ini_robust(ini_path)
    try:
        sec = 'test_date'
        if cp.has_section(sec):
            for i in range(1, 25):
                if cp.get(sec, f'enable{i}', fallback='0') == '1':
                    fd = cp.get(sec, f'from_date{i}', fallback=FROM_DATE)
                    td = cp.get(sec, f'to_date{i}',   fallback=TO_DATE)
                    if fd and td: return fd, td
            fd = cp.get(sec, 'from_date', fallback=FROM_DATE)
            td = cp.get(sec, 'to_date',   fallback=TO_DATE)
            if fd and td: return fd, td
    except Exception: pass
    return FROM_DATE, TO_DATE

def _load_symbols_from_ini():
    """configs/current_config.ini [symbols]/[selection] ?먕꽌 ?쒖꽦 ??蹂?TF ?쎌궓."""
    ini_path = os.path.join(CONFIGS_DIR, 'current_config.ini')
    cp = _read_ini_robust(ini_path)
    syms_out, tfs_out = [], []
    valid_syms = {'XAUUSD', 'BTCUSD', 'USDJPY', 'NAS100', 'EURUSD', 'GBPUSD'}
    try:
        sel, sym_sec = 'selection', 'symbols'
        if cp.has_section(sel) and cp.has_section(sym_sec):
            for i in range(1, 11):
                if cp.get(sel, f'sym{i}chk', fallback='0') == '1':
                    sv = cp.get(sym_sec, f'sym{i}', fallback='').upper()
                    if sv and sv != 'ERROR' and sv in valid_syms: syms_out.append(sv)
            tf_map = {'tfm1':'M1','tfm5':'M5','tfm15':'M15','tfm30':'M30','tfh1':'H1','tfh4':'H4'}
            for key, tf in tf_map.items():
                if cp.get(sel, key, fallback='0') == '1':
                    tfs_out.append(tf)
    except Exception as e:
        print(f"  [WARN] INI ?щ낵 ?쎄린 ?ㅽ뙣: {e}")
    return (syms_out or SYMBOLS), (tfs_out or TIMEFRAMES)


SAMPLES_PER_ROUND = 50    # ?쇱슫?쒕떦 ?쒕굹由ъ삤 ??(13蹂??怨듦컙???곹빀??而ㅻ쾭由ъ?)

# ?? 紐⑤뱢 ?꾪룷????????????????????????????????????????????????????????????
sys.path.insert(0, SOLO_DIR)
from core.param_space   import make_g4_param_space
from core.sampler       import get_samples_for_round
from core.scorer        import score_full, interpret_score
from core.ea_template_v7 import generate_mq4_v7, make_ea_filename

print(f"[PATH] SOLO_DIR  = {SOLO_DIR}")
print(f"[PATH] MT4_DIR   = {MT4_DIR}")
print(f"[PATH] EXPERTS   = {EXPERTS_DIR}")


# ?????????????????????????????????????????????????????????????????????????????
# 1. MQ4 而댄뙆????ex4
# ?????????????????????????????????????????????????????????????????????????????

def compile_mq4(mq4_path: str) -> bool:
    """MetaEditor compile .mq4 -> .ex4. Returns True on success."""
    if not os.path.exists(ME_EXE):
        print(f"  [WARN] MetaEditor not found: {ME_EXE}")
        return False
    me_dir   = os.path.dirname(ME_EXE)
    log_path = mq4_path.replace('.mq4', '.log')
    ex4_path = mq4_path.replace('.mq4', '.ex4')
    # Remove stale ex4
    if os.path.exists(ex4_path):
        try: os.remove(ex4_path)
        except: pass
    try:
        cmd = f'"{ME_EXE}" /compile:"{mq4_path}" /log:"{log_path}" /portable'
        subprocess.run(cmd, shell=True, timeout=30, cwd=me_dir,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        return os.path.exists(ex4_path)
    except subprocess.TimeoutExpired:
        subprocess.run(f'taskkill /f /im "{os.path.basename(ME_EXE)}"',
                       shell=True, capture_output=True)
        return False
    except Exception as e:
        print(f"  [ERR] Compile error: {e}")
        return False


# ?????????????????????????????????????????????????????????????????????????????
# 2. ?쇱슫???뚯씪 ?앹꽦 (MQ4 ??而댄뙆????Experts 諛곗튂)
# ?????????????????????????????????????????????????????????????????????????????

def generate_round_files(samples: list, round_num: int) -> dict:
    """
    samples: [{param_name: value, ...}, ...]
    Returns: {sc_id: {'params': ..., 'fname': 'G4v7_SC001_R1_...'}}
    MQ4 written directly to EXPERTS_DIR (MetaEditor requires MT4 tree).
    Source .mq4 files kept in _staging_v7_R{n} subfolder for reference.
    """
    staging = os.path.join(EXPERTS_DIR, f'_staging_v7_R{round_num}')
    os.makedirs(staging, exist_ok=True)

    scenarios_map = {}

    for sc_id, params in enumerate(samples, 1):
        base     = make_ea_filename(sc_id, round_num, params)
        # Write MQ4 into Experts root so MetaEditor can compile it
        mq4_path = os.path.join(EXPERTS_DIR, base + '.mq4')
        ex4_path = os.path.join(EXPERTS_DIR, base + '.ex4')

        src = generate_mq4_v7(sc_id, round_num, params)
        with open(mq4_path, 'w', encoding='ascii', errors='replace') as f:
            f.write(src)
        # Keep a copy in staging for reference
        shutil.copy2(mq4_path, os.path.join(staging, base + '.mq4'))

        ok = compile_mq4(mq4_path)
        if ok:
            scenarios_map[sc_id] = {'params': params, 'fname': base + '.ex4'}
            _ea_to_ready(ex4_path)   # 而댄뙆??吏곹썑 READY_FOR_TEST??蹂듭궗
        else:
            print(f"  [FAIL] SC{sc_id:03d} compile failed: {base}")

    ok_count = len(scenarios_map)
    fail_count = len(samples) - ok_count
    print(f"  Compiled: {ok_count} OK / {fail_count} FAIL (total {len(samples)})")
    return scenarios_map


# ?????????????????????????????????????????????????????????????????????????????
# 3. SOLO IPC ??諛깊뀒?ㅽ듃 紐낅졊 ?꾩넚 + ?꾨즺 ?湲?# ?????????????????????????????????????????????????????????????????????????????

def _write_status(round_num, sc_num, total, ea_name, message=""):
    """Monitor tab??status.json + current_ea_name.txt ?ㅼ떆媛?媛깆떊."""
    status = {
        'status':   'busy',
        'round':    round_num,
        'current':  sc_num,
        'total':    total,
        'ea':       ea_name,
        'message':  message or f'R{round_num} [{sc_num}/{total}] {ea_name}',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    }
    try:
        with open(os.path.join(CONFIGS_DIR, 'status.json'), 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False)
        with open(os.path.join(CONFIGS_DIR, 'current_ea_name.txt'), 'w', encoding='utf-8') as f:
            f.write(f'R{round_num} [{sc_num}/{total}] {ea_name}')
    except Exception:
        pass


def send_command_and_wait(ea_name, symbol, tf, from_date, to_date,
                          sc_num, total, timeout=600):
    """command.json ?묒꽦 ??test_completed.flag ?湲?(理쒕? timeout珥?."""
    for p in glob.glob(DONE_FLAG.replace('.flag', '*.flag')):
        try: os.remove(p)
        except: pass

    cmd = {
        'action':     'run_backtest',
        'ea_name':    ea_name, 'symbol': symbol, 'tf': tf,
        'from_date':  from_date, 'to_date': to_date,
        'iteration':  sc_num,       # SOLO GUI EA count display
        'total_sets': total,        # SOLO GUI total display
        'timestamp':  datetime.now().strftime('%Y%m%d_%H%M%S'),
    }
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    with open(CMD_JSON, 'w', encoding='utf-8') as f:
        json.dump(cmd, f, ensure_ascii=False)
    print(f"  [{sc_num}/{total}] CMD ??{ea_name}")

    t0 = time.time()
    while time.time() - t0 < timeout:
        flags = glob.glob(DONE_FLAG.replace('.flag', '*.flag'))
        if flags:
            print(f"  [{sc_num}/{total}] ?꾨즺 ({int(time.time()-t0)}s)")
            return True
        stop = os.path.join(CONFIGS_DIR, 'runner_stop.signal')
        if os.path.exists(stop):
            print("  [STOP] 以묒? ?좏샇")
            return False
        elapsed = int(time.time() - t0)
        if elapsed % 60 == 0 and elapsed > 0:
            print(f"  [{sc_num}/{total}] ?湲?以?.. {elapsed}s/{timeout}s")
        time.sleep(2)

    print(f"  [{sc_num}/{total}] ??꾩븘??({timeout}s)")
    return False


# ?????????????????????????????????????????????????????????????????????????????
# 4. HTM ?뚯떛
# ?????????????????????????????????????????????????????????????????????????????

def parse_htm(path):
    """HTM ?붿빟 ?듦퀎 異붿텧."""
    import re as _re
    try:
        with open(path, 'rb') as f: raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        nums = []
        for v in _re.findall(r'<td[^>]*align=right[^>]*>([-\d.,]+)</td>', text):
            try: nums.append(float(v.replace(',', '')))
            except: pass
        profit = pf = dd = trades = 0.0
        for i, n in enumerate(nums):
            if abs(n - 10000.0) < 0.1 and i + 4 < len(nums):
                profit = nums[i + 1]
                pf     = nums[i + 4]
                break
        m = _re.search(r'<td[^>]*align=right[^>]*>([\d.]+)%\s*\([\d.,]+\)</td>', text)
        dd = float(m.group(1)) if m else 0.0
        m2 = _re.search(r'<td[^>]*align=right[^>]*>(\d+)</td><td[^>]*>[^<]+(won|%)', text)
        trades = int(m2.group(1)) if m2 else 0
        return {'profit': profit, 'drawdown_pct': dd,
                'profit_factor': pf, 'trades': trades}
    except Exception as e:
        return {'profit': 0, 'drawdown_pct': 100, 'profit_factor': 0,
                'trades': 0, 'error': str(e)}


def _htm_creation_time(fpath):
    """Extract creation time from HTM filename timestamp (MMDDHHMMSS).
    Falls back to os.path.getctime() if pattern not found.
    SOLO_WATCHER modifies HTMs (changes mtime), so we must NOT use mtime.
    """
    import re as _re
    fname = os.path.basename(fpath)
    # Pattern: _MMDDHHmmss_ e.g. _0408081539_
    m = _re.search(r'_(\d{10})_', fname)
    if m:
        ts_str = m.group(1)  # e.g. '0408081539'
        try:
            now = datetime.now()
            mo  = int(ts_str[0:2])
            dy  = int(ts_str[2:4])
            hr  = int(ts_str[4:6])
            mn  = int(ts_str[6:8])
            sc2 = int(ts_str[8:10])
            yr  = now.year
            # Use .timestamp() to convert local datetime -> UTC Unix timestamp
            return datetime(yr, mo, dy, hr, mn, sc2).timestamp()
        except Exception:
            pass
    # Fallback: use creation time (ctime) ??not mtime (SOLO_WATCHER changes mtime)
    try:
        return os.path.getctime(fpath)
    except Exception:
        return 0.0


def find_latest_htm(ea_name, newer_than=None):
    """ea_name 湲곕컲 理쒖떊 HTM ?먯깋.
    newer_than: Unix timestamp ?????쒓컙 ?댄썑 ?앹꽦???뚯씪留?諛섑솚.
    NOTE: Uses filename-embedded timestamp (not mtime) to avoid SOLO_WATCHER
          CSS injection corrupting the modification time.
    """
    today = datetime.now().strftime('%Y%m%d')
    base  = os.path.splitext(ea_name)[0]
    for pattern in [
        os.path.join(REPORTS_BASE, today, ea_name, '*.htm'),
        os.path.join(REPORTS_BASE, today, ea_name, '*.ht'),   # MAX_PATH 珥덇낵 ??.ht濡???λ맖
        os.path.join(REPORTS_BASE, '**', base + '*.htm'),
        os.path.join(REPORTS_BASE, '**', base + '*.ht'),
    ]:
        files = glob.glob(pattern, recursive=True)
        if newer_than is not None:
            files = [f for f in files if _htm_creation_time(f) > newer_than]
        if files:
            return max(files, key=_htm_creation_time)
    return None


# ?????????????????????????????????????????????????????????????????????????????
# 5. ?쇱슫???ㅽ뻾
# ?????????????????????????????????????????????????????????????????????????????

def run_round(round_num: int, scenarios_map: dict) -> list:
    """
    scenarios_map: {sc_id: {'params': ..., 'fname': '...'}}
    諛섑솚: results list (媛???ぉ??params + HTM ?듦퀎 + score ?ы븿)
    """
    items = sorted(scenarios_map.items())
    total = len(items)
    sym_str = "+".join(SYMBOLS)
    tf_str  = "+".join(TIMEFRAMES)
    n_combos = len(SYMBOLS) * len(TIMEFRAMES)
    print(f"\n{'='*60}")
    print(f"  V7 ROUND {round_num}  |  {total}媛??쒕굹由ъ삤  |  {sym_str} 횞 {tf_str}")
    print(f"  肄ㅻ낫: {n_combos}媛??쒕굹由ъ삤  珥?{total * n_combos}??諛깊뀒?ㅽ듃")
    print(f"  {FROM_DATE} ~ {TO_DATE}")
    print(f"{'='*60}")

    results = []
    error_count = 0
    total_combos = total * n_combos        # ?? 50 횞 4 = 200
    global_bt_num = 0                      # ?꾩껜 諛깊뀒?ㅽ듃 ?쒕쾲 (1~200)

    # ?ъ떆??蹂듦뎄: ?대? ?꾨즺??SC 嫄대꼫?곌린
    prog_file = os.path.join(CONFIGS_DIR, f'round_{round_num}_progress.json')
    completed_ids = set()
    if os.path.exists(prog_file):
        try:
            with open(prog_file, encoding='utf-8') as _pf:
                _prog = json.load(_pf)
                completed_ids = set(_prog.get('completed', []))
            if completed_ids:
                print(f"  [RESUME] ?대? ?꾨즺: {sorted(completed_ids)} ??嫄대꼫?")
        except Exception:
            pass

    for sc_id, sc in items:
        if sc_id in completed_ids:
            print(f"  [SKIP] SC{sc_id:03d} ?대? ?꾨즺 ??嫄대꼫?")
            continue
        ea_name = sc['fname']
        params  = sc['params']
        idx     = sc_id

        # ?? 硫??肄ㅻ낫: SYMBOLS 횞 TIMEFRAMES 紐⑤몢 ?뚯뒪????????????????
        combo_results = []
        combo_skipped = False

        # EA ?묐몢?ъ? SYMBOLS ?ㅼ젙???곕씪 ?뚯뒪???щ낵 寃곗젙
        # SYMBOLS媛 紐낆떆?곸쑝濡??ㅼ젙??寃쎌슦 洹멸쾬???곗꽑 ?ъ슜 (?щ낵 怨좎젙 ?놁쓬)
        if ea_name.startswith('B_BTC') or ea_name.startswith('B_SC'):
            _sym_list = [s for s in SYMBOLS if 'BTC' in s]
            if not _sym_list:
                _sym_list = ['BTCUSD']
        else:
            # G4v7_, G_SC ??紐⑤몢 SYMBOLS ?ㅼ젙 洹몃?濡??ъ슜
            _sym_list = SYMBOLS

        for sym in _sym_list:
            for tf in TIMEFRAMES:
                global_bt_num += 1          # 1 ??total_combos (?? 1~200)
                t_before = time.time()
                htm = None
                _write_status(round_num, global_bt_num, total_combos, ea_name)
                ok = send_command_and_wait(
                    ea_name, sym, tf, FROM_DATE, TO_DATE,
                    sc_num=global_bt_num, total=total_combos)
                if not ok:
                    error_count += 1
                    if error_count >= 15:
                        print("  [ABORT] ?먮윭 15???댁긽")
                        combo_skipped = True
                        break
                    continue
                htm = find_latest_htm(ea_name, newer_than=t_before)
                if not htm:
                    t0 = time.time()
                    while time.time() - t0 < 120:
                        time.sleep(10)
                        htm = find_latest_htm(ea_name, newer_than=t_before)
                        if htm: break
                        print(f"  HTM ?€湲?{int(time.time()-t0)}s... ({sym} {tf})")

                # HTM ?뚯떛
                if htm:
                    c_htm = parse_htm(htm)
                else:
                    c_htm = {'profit': 0, 'drawdown_pct': 100,
                             'profit_factor': 0, 'trades': 0}

                # 시장분석기 (선택적: 큰 HTM(>5MB)는 스킵, 타임아웃 20초)
                c_ma = None
                try:
                    from core.market_analyzer import analyze_round as _ma
                    if htm:
                        htm_size = os.path.getsize(htm) if os.path.exists(htm) else 0
                        if htm_size < 5 * 1024 * 1024:
                            import threading as _th
                            _res = [None]
                            def _run_ma(_res=_res):
                                try: _res[0] = _ma([htm], round_num, ea_name)
                                except Exception: pass
                            _t = _th.Thread(target=_run_ma, daemon=True)
                            _t.start(); _t.join(timeout=20)
                            c_ma = _res[0]
                        else:
                            print(f"  [SKIP] ?쒖옣遺꾩꽍 ?ㅽ궢 (HTM {htm_size//1024//1024}MB > 5MB)")
                except Exception:
                    pass

                c_score = score_full(c_htm, market_analysis=c_ma)
                combo_results.append({
                    'sym': sym, 'tf': tf,
                    'htm_data': c_htm,
                    'score_res': c_score,
                })
                print(f"  ?? {sym} {tf}: profit=${c_htm['profit']:,.0f}  "
                      f"DD={c_htm['drawdown_pct']:.1f}%  score={c_score['total']:.1f}")

            if combo_skipped:
                break

        if combo_skipped:
            break

        # ?€?€ 肄ㅻ낫 吏묎퀎: ?됯퇏 ?ㅼ퐫?? 理쒖븙 DD ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
        if combo_results:
            sc_total  = sum(c['score_res']['total'] for c in combo_results) / len(combo_results)
            bd        = combo_results[0]['score_res']['breakdown']
            htm_data  = {
                'profit':       sum(c['htm_data']['profit'] for c in combo_results) / len(combo_results),
                'drawdown_pct': max(c['htm_data']['drawdown_pct'] for c in combo_results),
                'profit_factor':sum(c['htm_data']['profit_factor'] for c in combo_results) / len(combo_results),
                'trades':       sum(c['htm_data']['trades'] for c in combo_results),
            }
        else:
            htm_data = {'profit': 0, 'drawdown_pct': 100, 'profit_factor': 0, 'trades': 0}
            sc_total = 0
            bd = score_full(htm_data)['breakdown']

        entry = {
            'sc_id':    sc_id,
            'ea_name':  ea_name,
            'params':   params,
            'round':    round_num,
            **htm_data,
            'score':        sc_total,
            'score_detail': bd,
            'combos': [{'sym': c['sym'], 'tf': c['tf'],
                        'score': c['score_res']['total'],
                        'profit': c['htm_data']['profit'],
                        'dd': c['htm_data']['drawdown_pct']} for c in combo_results],
        }
        results.append(entry)

        # 吏꾪뻾?곹솴 ?ㅼ떆媛??€??(?ъ떆????嫄대꼫?곌린??
        try:
            prog_file = os.path.join(CONFIGS_DIR, f'round_{round_num}_progress.json')
            with open(prog_file, 'w', encoding='utf-8') as _pf:
                json.dump({'round': round_num, 'completed': [r['sc_id'] for r in results]},
                          _pf, ensure_ascii=False)
        except Exception:
            pass

        # ?뚯뒪???꾨즺 ??AFTER_FOR_TEST濡??대룞 (READY?먯꽌 ?쒓굅)
        _ea_to_after(os.path.join(EXPERTS_DIR, ea_name))

        # 異쒕젰
        grade = 'S' if sc_total>=85 else 'A' if sc_total>=70 else 'B' if sc_total>=55 else 'C' if sc_total>=40 else 'D'
        sl  = params.get('InpSLMultiplier', 0)
        tp  = params.get('InpTPMultiplier', 0)
        adx = params.get('InpADXMin', 0)
        mp  = params.get('InpMaxPositions', 1)
        print(f"\n  ?뚢? [{idx}/{total}] {ea_name}")
        print(f"  ?? SL={sl:.3f} TP={tp:.1f} ADX>={adx} MaxPos={mp}  ({len(combo_results)}肄ㅻ낫 ?됯퇏)")
        print(f"  ?? ?됯퇏?댁씡: ${htm_data['profit']:>10,.0f}  PF: {htm_data['profit_factor']:.2f}  理쒖븙DD: {htm_data['drawdown_pct']:.1f}%")
        print(f"  ?붴? SCORE: {sc_total:5.1f} [{grade}]  "
              f"?섏씡:{bd.get('profitability',0):.0f} "
              f"?덉쟾:{bd.get('safety',0):.0f} "
              f"?덉젙:{bd.get('stability',0):.0f} "
              f"?⑥쑉:{bd.get('efficiency',0):.0f} "
              f"?쒖옣:{bd.get('market_fit',0):.0f}")

    # ?€?€ ?쇱슫??寃곌낵 ?€???€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    ts   = datetime.now().strftime('%H%M')
    rfile = os.path.join(RESULTS_DIR, f'V7_R{round_num:02d}_{ts}.json')
    try:
        with open(rfile, 'w', encoding='utf-8') as f:
            json.dump({'round': round_num, 'symbols': SYMBOLS, 'timeframes': TIMEFRAMES,
                       'symbol': "+".join(SYMBOLS), 'tf': "+".join(TIMEFRAMES),
                       'from_date': FROM_DATE, 'to_date': TO_DATE,
                       'results': results}, f, indent=2, ensure_ascii=False)
        print(f"\n  寃곌낵 ?€?? {os.path.basename(rfile)}")
    except Exception as e:
        print(f"\n  [ERROR] 寃곌낵 ?€???ㅽ뙣: {e}")
        # ?꾩떆 寃쎈줈濡??ъ떆??        rfile_tmp = rfile + '.tmp'
        try:
            with open(rfile_tmp, 'w', encoding='utf-8') as f:
                json.dump({'round': round_num, 'results': results}, f, ensure_ascii=False)
            print(f"  [RECOVER] ?꾩떆 ?€?? {os.path.basename(rfile_tmp)}")
        except Exception:
            pass

    # TOP5 異쒕젰
    top5 = sorted(results, key=lambda x: x['score'], reverse=True)[:5]
    print(f"\n  {'='*55}")
    print(f"  ROUND {round_num} TOP 5")
    print(f"  {'='*55}")
    for i, e in enumerate(top5, 1):
        nm = e['ea_name'].replace('.ex4','')[-40:]
        print(f"  {i}. {nm}  score={e['score']:.1f}  "
              f"profit=${e['profit']:,.0f}  DD={e['drawdown_pct']:.1f}%")
    print(f"  {'='*55}\n")

    return results


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# 6. ?뚯씪 諛깆뾽
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def backup_round_files(round_num):
    pattern = os.path.join(EXPERTS_DIR, f'G4v7_*_R{round_num}*.ex4')
    files   = glob.glob(pattern)
    if not files: return
    bak_dir = os.path.join(BACKUP_ROOT,
                           f'R{round_num}_bak_{datetime.now().strftime("%H%M")}')
    os.makedirs(bak_dir, exist_ok=True)
    for f in files:
        shutil.move(f, os.path.join(bak_dir, os.path.basename(f)))
    print(f"  R{round_num} {len(files)}媛?諛깆뾽: {os.path.basename(bak_dir)}")


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# 7. 硫붿씤
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

def main():
    global FROM_DATE, TO_DATE, SYMBOLS, TIMEFRAMES, SYMBOL, TIMEFRAME
    print(f"\n{'#'*60}")
    print(f"  EA Auto Master V7.0 지능형 파라미터 최적화")
    print(f"  {SYMBOL} {TIMEFRAME}  |  {FROM_DATE} ~ {TO_DATE}")
    print(f"  라운드당 {SAMPLES_PER_ROUND}개 시나리오  최대 {MAX_ROUNDS}라운드")
    print(f"{'#'*60}\n")

    # ?뚮씪誘명꽣 怨듦컙 ?ㅼ젙 (extra_params=True = ADX쨌RSI쨌DD쨌硫€?고룷吏€???ы븿)
    use_full_params = True   # False = 湲곕낯 5媛쒕쭔
    param_space = make_g4_param_space(extra_params=use_full_params)
    print(param_space.summary())
    print()

    # ?댁쟾 寃곌낵 濡쒕뱶 (?ъ떆??蹂듦뎄)
    prev_results = []
    prev_files = sorted(glob.glob(os.path.join(RESULTS_DIR, 'V7_R*.json')))
    if prev_files:
        with open(prev_files[-1], encoding='utf-8') as f:
            d = json.load(f)
        prev_results = d.get('results', [])
        print(f"  [RESUME] ?댁쟾 寃곌낵 {len(prev_results)}媛?濡쒕뱶")

    # ?꾩옱 ?쇱슫??媛먯?: 寃곌낵 JSON ?뚯씪 湲곕컲 (Experts ?대뜑 湲곕컲?먯꽌 媛쒖꽑)
    auto_round = 1
    # 諛⑸쾿1: g4_results ?대뜑???꾩꽦??寃곌낵 JSON 寃€??(50媛??댁긽 = ?꾩꽦)
    for rn in range(MAX_ROUNDS, 0, -1):
        rn_files = sorted(glob.glob(os.path.join(RESULTS_DIR, f'V7_R{rn:02d}*.json')))
        for rf in rn_files:
            try:
                with open(rf, encoding='utf-8') as _f:
                    _d = json.load(_f)
                if len(_d.get('results', [])) >= SAMPLES_PER_ROUND:
                    auto_round = rn + 1   # ?꾩꽦???쇱슫???ㅼ쓬?쇰줈
                    break
            except Exception:
                pass
        else:
            continue
        break
    # 諛⑸쾿2: Experts ?대뜑??R{n} ?뚯씪???덇퀬 諛⑸쾿1蹂대떎 ?믪쑝硫??곗꽑
    for rn in range(MAX_ROUNDS, 1, -1):
        ex4_list = glob.glob(os.path.join(EXPERTS_DIR, f'G4v7_*_R{rn}*.ex4'))
        if len(ex4_list) >= SAMPLES_PER_ROUND:   # 異⑸텇???섏쓽 ?뚯씪???덉쓣 ?뚮쭔
            if rn >= auto_round:
                auto_round = rn
            break
    print(f"  [AUTO] ?쒖옉 ?쇱슫?? R{auto_round}\n")

    for round_num in range(auto_round, MAX_ROUNDS + 1):

        # ?€?€ 留??쇱슫???쒖옉 ??INI?먯꽌 ?좎쭨쨌?щ낵쨌TF ?щ줈???€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
        _fd, _td = _load_dates_from_ini()
        if (_fd, _td) != (FROM_DATE, TO_DATE):
            print(f"  [DATE] INI ?좎쭨 蹂€寃? {FROM_DATE}~{TO_DATE} ??{_fd}~{_td}")
            FROM_DATE, TO_DATE = _fd, _td
        _syms, _tfs = _load_symbols_from_ini()
        if _syms != SYMBOLS or _tfs != TIMEFRAMES:
            print(f"  [SYM]  INI ?щ낵 蹂€寃? {SYMBOLS}횞{TIMEFRAMES} ??{_syms}횞{_tfs}")
            SYMBOLS, TIMEFRAMES = _syms, _tfs
            SYMBOL, TIMEFRAME   = SYMBOLS[0], TIMEFRAMES[0]
        # ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€

        # Check if R{n} EX4 files already exist (pre-compiled)
        existing_ex4 = sorted(glob.glob(
            os.path.join(EXPERTS_DIR, f'G4v7_*_R{round_num}*.ex4')))

        if existing_ex4:
            # Use existing files ??build scenarios_map from filenames
            print(f"\n  === R{round_num}: {len(existing_ex4)} pre-compiled EA files found ===")
            scenarios_map = {}
            for sc_id, ex4_path in enumerate(existing_ex4, 1):
                fname = os.path.basename(ex4_path)
                # Try to recover SL/TP from filename: G4v7_SC001_R4_SL024_TP0110_ADX20_MP1.ex4
                params = {'InpSLMultiplier': 0.3, 'InpTPMultiplier': 10.0,
                          'InpATRPeriod': 14, 'InpFastMA': 8, 'InpSlowMA': 21,
                          'InpADXPeriod': 14, 'InpADXMin': 20.0,
                          'InpRSIPeriod': 14, 'InpRSILower': 40.0, 'InpRSIUpper': 60.0,
                          'InpMaxDD': 15.0, 'InpMaxPositions': 1, 'InpCooldownBars': 3}
                import re as _re
                # New format: G4v7_SC001_R4_SL062_TP0185_AT20_FM16_SM24_AX28_RL45_RH75_DD20_MP1_CD01
                m = _re.search(
                    r'SL(\d+)_TP(\d+)_AT(\d+)_FM(\d+)_SM(\d+)_AX(\d+)_RL(\d+)_RH(\d+)_DD(\d+)_MP(\d+)_CD(\d+)',
                    fname)
                if m:
                    params['InpSLMultiplier']  = int(m.group(1))  / 100.0
                    params['InpTPMultiplier']  = int(m.group(2))  / 10.0
                    params['InpATRPeriod']     = int(m.group(3))
                    params['InpFastMA']        = int(m.group(4))
                    params['InpSlowMA']        = int(m.group(5))
                    params['InpADXMin']        = float(m.group(6))
                    params['InpRSILower']      = float(m.group(7))
                    params['InpRSIUpper']      = float(m.group(8))
                    params['InpMaxDD']         = float(m.group(9))
                    params['InpMaxPositions']  = int(m.group(10))
                    params['InpCooldownBars']  = int(m.group(11))
                else:
                    # Legacy format fallback: SL_TP_ADX_MP
                    m2 = _re.search(r'SL(\d+)_TP(\d+)_ADX(\d+)_MP(\d+)', fname)
                    if m2:
                        params['InpSLMultiplier'] = int(m2.group(1)) / 100.0
                        params['InpTPMultiplier'] = int(m2.group(2)) / 10.0
                        params['InpADXMin']       = float(m2.group(3))
                        params['InpMaxPositions'] = int(m2.group(4))
                scenarios_map[sc_id] = {'params': params, 'fname': fname}
            print(f"  Loaded {len(scenarios_map)} pre-compiled EAs for R{round_num}")
        else:
            print(f"\n  === R{round_num} sample generation ===")

            # Auto sampling strategy (LHS -> FOCUSED -> GENETIC)
            all_prev = []
            for pf in sorted(glob.glob(os.path.join(RESULTS_DIR, 'V7_R*.json'))):
                with open(pf, encoding='utf-8') as f:
                    d = json.load(f)
                for r in d.get('results', []):
                    all_prev.append({'params': r.get('params', {}),
                                     'score':  r.get('score', 0)})

            samples = get_samples_for_round(
                param_space, round_num, all_prev,
                n=SAMPLES_PER_ROUND, seed=42 + round_num)

            # Generate EA files + compile
            print(f"  === R{round_num} EA file generation ===")
            scenarios_map = generate_round_files(samples, round_num)

        if not scenarios_map:
            print(f"  [ERROR] R{round_num} ?뚯씪 ?앹꽦 ?ㅽ뙣")
            break

        # 諛깊뀒?ㅽ듃 ?ㅽ뻾
        results = run_round(round_num, scenarios_map)

        if not results:
            print("  寃곌낵 ?놁쓬 ??以묐떒")
            break

        valid = [r for r in results if r['score'] > 0]
        print(f"  ?좏슚: {len(valid)}/{len(results)}")

        if round_num >= MAX_ROUNDS:
            print(f"\n  {MAX_ROUNDS}?쇱슫???꾨즺!")
            break

        if len(valid) < 3:
            print("  ?좏슚 寃곌낵 3媛?誘묃쭔 ??以묐떒")
            break

        # ?꾩옱 ?쇱슫???뚯씪 諛깆뾽 ???ㅼ쓬 ?쇱슫??以€鍮?        backup_round_files(round_num)

        # ?쇱슫???꾨즺 ??status.json + all_done.flag (SOLO ?뚮엺 ?몃━嫄?
        top5 = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:5]
        top1 = top5[0] if top5 else {}
        done_msg = (f"R{round_num} DONE  {len(results)}媛??꾨즺  "
                    f"TOP: {top1.get('ea_name','')[:30]}  score={top1.get('score',0):.1f}")
        ts_now = datetime.now().strftime('%Y%m%d_%H%M%S')
        try:
            with open(os.path.join(CONFIGS_DIR, 'status.json'), 'w', encoding='utf-8') as f:
                json.dump({'status': 'done', 'round': round_num,
                           'message': done_msg,
                           'timestamp': ts_now},
                          f, ensure_ascii=False)
        except Exception:
            pass

        # ??all_done.flag ??SOLO CheckAllDone ?€?대㉧媛€ 3珥덈쭏??媛먯떆
        # ???뚯씪???놁쑝硫?SOLO ?뚮엺 誘몃컻??(湲곗〈 踰꾧렇 ?섏젙)
        try:
            all_done_path = os.path.join(CONFIGS_DIR, 'all_done.flag')
            valid_scores = [r for r in results if r.get('score', 0) > 0]
            with open(all_done_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_tested': len(results),
                    'best_score':   top1.get('score', 0),
                    'ea_name':      top1.get('ea_name', ''),
                    'round':        round_num,
                    'valid_count':  len(valid_scores),
                    'timestamp':    ts_now,
                }, f, ensure_ascii=False)
            print(f"  [ALARM] all_done.flag 생성 -> SOLO 알람 트리거")
        except Exception as e:
            print(f"  [WARN] all_done.flag ?앹꽦 ?ㅽ뙣: {e}")

        print(f"\n  R{round_num} ?꾨즺. ?ㅼ쓬 START_ALL_v7.bat ?ㅽ뻾 ??R{round_num+1} ?먮룞 吏꾪뻾.")
        print(f"  (R{round_num+1} EA ?뚯씪?€ ?ㅼ쓬 ?ㅽ뻾 ???먮룞 ?앹꽦 ??FOCUSED ?섑뵆留?")
        break  # 1 round per execution ??next START_ALL_v7.bat continues R{n+1}

    print(f"\n{'#'*60}")
    print(f"  V7 理쒖쟻???꾨즺. 寃곌낵: {RESULTS_DIR}")
    print(f"{'#'*60}\n")


def run_folder_queue():
    """--folder-queue 紐⑤뱶: READY_FOR_TEST/ ?섏쐞 ?대뜑瑜??먮줈 ?쒖꽌?€濡??뚯뒪??
    媛??대뜑??.ex4 ?뚯씪??4肄ㅻ낫 (GOLD횞M5, GOLD횞M30, BTC횞M5, BTC횞M30)濡??뚯뒪??
    ?꾨즺 ?대뜑 -> AFTER_FOR_TEST/ ?대룞, ?ㅼ쓬 ?대뜑 ?먮룞 吏꾪뻾.
    """
    global FROM_DATE, TO_DATE, SYMBOLS, TIMEFRAMES, SYMBOL, TIMEFRAME

    sys.path.insert(0, SOLO_DIR)
    from core.folder_queue import FolderQueue

    fq = FolderQueue()

    def _log_debug(msg):
        with open(os.path.join(SOLO_DIR, 'debug_queue.log'), 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        print(f"  [DEBUG] {msg}")

    print('\n' + '#' * 60)
    print("  EA Auto Master V7.0 -- 폴더 큐 모드")
    print("  READY_FOR_TEST/ 하위 폴더 순서대로 테스트")
    print('#' * 60 + '\n')

    # INI?먯꽌 ?щ낵/TF/?좎쭨 濡쒕뱶
    FROM_DATE, TO_DATE = _load_dates_from_ini()
    SYMBOLS, TIMEFRAMES = _load_symbols_from_ini()
    SYMBOL, TIMEFRAME = SYMBOLS[0], TIMEFRAMES[0]

    print('  ?щ낵: %s  TF: %s' % ('+'.join(SYMBOLS), '+'.join(TIMEFRAMES)))
    print('  湲곌컙: %s ~ %s\n' % (FROM_DATE, TO_DATE))

    # queue_selected.json 읽기 (선택 폴더 필터 + 스텝 샘플링)
    _sel_file = os.path.join(CONFIGS_DIR, 'queue_selected.json')
    _selected_set = None
    _step = 1  # 기본: 전체 파일
    _file_filter = None
    _filter_folder = None

    if os.path.exists(_sel_file):
        try:
            _sel_data = json.load(open(_sel_file, encoding='utf-8'))
            _sel_list     = _sel_data.get('selected', [])
            _step         = max(1, int(_sel_data.get('step', 1)))
            _file_filter  = _sel_data.get('file_filter', None) or None
            _filter_folder= _sel_data.get('filter_folder', None)
            if _sel_list:
                _selected_set = set(_sel_list)
                print('  [QUEUE] 선택 폴더 필터: %d개 — %s' % (len(_sel_list), ', '.join(_sel_list)))
            if _file_filter:
                print('  [QUEUE] 파일 필터 적용: %d개 파일 (폴더: %s)' % (len(_file_filter), _filter_folder))
            if _step > 1:
                print('  [QUEUE] 스텝 샘플링: %d번째마다 1개 (1, %d, %d, ...)' % (_step, _step+1, 2*_step+1))
            else:
                print('  [QUEUE] 전체 파일 순차 실행')
        except Exception as e:
            print('  [WARN] queue_selected.json 읽기 실패: %s' % e)
    else:
        print('  [QUEUE] 필터링 없이 모든 폴더를 순차 실행합니다.')

    _pause_file = os.path.join(CONFIGS_DIR, 'runner_pause.signal')
    _stop_file  = os.path.join(CONFIGS_DIR, 'runner_stop.signal')

    while True:
        # 정지 신호 확인
        if os.path.exists(_stop_file):
            print('  [QUEUE] 정지 신호 감지 — 종료')
            break

        # 일시정지 신호 확인 (파일이 있는 동안 대기)
        if os.path.exists(_pause_file):
            print('  [QUEUE] ⏸ 일시정지 중... (resume.signal 삭제 시 재개)')
            while os.path.exists(_pause_file):
                if os.path.exists(_stop_file):
                    break
                import time; time.sleep(2)
            print('  [QUEUE] ▶ 재개')

        # [v8.4] 무한루프 방지를 위한 짧은 휴식 및 큐 상태 강제 갱신
        import time
        time.sleep(1)

        fq = FolderQueue()
        _log_debug("--- fq.get_next_pending() 호출 시작 ---")
        folder_info = fq.get_next_pending()
        if not folder_info:
            _log_debug("모든 폴더 완료 감지 (folder_info is None)")
            break
        
        folder_name = folder_info['name']
        _log_debug(f"대상 폴더 감지: {folder_name}")

        # 선택 필터 적용 — 스킵 시 mark_done으로 큐에서 제거해야 무한루프 방지
        if _selected_set is not None and folder_name not in _selected_set:
            _log_debug(f"필터(SelectedSet)에 의해 스킵됨: {folder_name}")
            fq.mark_done(folder_name)
            continue
        ex4_files   = fq.get_ex4_files(folder_name)
        total_ex4 = len(ex4_files)

        # 특정 파일만 필터링 (선택된 파일만 실행)
        if _file_filter and folder_name == _filter_folder:
            ex4_files = [f for f in ex4_files if os.path.basename(f) in _file_filter]
            print('  [QUEUE] 폴더 내 파일 필터링 적용: %d개 선택됨' % len(ex4_files))

        # 스텝 샘플링 적용: 0, step, 2*step ... 인덱스만 선택 (1번, step+1번, ...)
        if _step > 1 and ex4_files:
            ex4_files = ex4_files[0::_step]
            print('  [QUEUE] 스텝 샘플링 적용: 전체 %d개 → %d개 (간격 %d)' % (total_ex4, len(ex4_files), _step))

        if not ex4_files:
            _log_debug(f"EX4 파일이 없어 스킵됨: {folder_name}")
            print('  [QUEUE] %s: .ex4 파일 없음 -- 건너뜀' % folder_name)
            fq.mark_error(folder_name, 'ex4 파일 없음')
            continue

        print('\n' + '=' * 60)
        print('  [QUEUE] ?대뜑: %s  (%d媛?EA)' % (folder_name, len(ex4_files)))
        print('=' * 60)

        fq.mark_running(folder_name, current_sc=0)

        # ?쒕굹由ъ삤 留?援ъ꽦 (?뚯씪紐낆뿉???뚮씪誘명꽣 ?뚯떛 -- L696~L721 濡쒖쭅 ?ъ궗??
        scenarios_map = {}
        for sc_id, ex4_path in enumerate(ex4_files, 1):
            fname  = os.path.basename(ex4_path)
            params = {
                'InpSLMultiplier': 0.3, 'InpTPMultiplier': 10.0,
                'InpATRPeriod': 14,     'InpFastMA': 8,
                'InpSlowMA': 21,        'InpADXPeriod': 14,
                'InpADXMin': 20.0,      'InpRSIPeriod': 14,
                'InpRSILower': 40.0,    'InpRSIUpper': 60.0,
                'InpMaxDD': 15.0,       'InpMaxPositions': 1,
                'InpCooldownBars': 3,
            }
            # ???뺤떇: G4v7_SC001_R4_SL062_TP0185_AT20_FM16_SM24_AX28_RL45_RH75_DD20_MP1_CD01
            m = re.search(
                r'SL(\d+)_TP(\d+)_AT(\d+)_FM(\d+)_SM(\d+)_AX(\d+)'
                r'_RL(\d+)_RH(\d+)_DD(\d+)_MP(\d+)_CD(\d+)', fname)
            if m:
                params['InpSLMultiplier']  = int(m.group(1))  / 100.0
                params['InpTPMultiplier']  = int(m.group(2))  / 10.0
                params['InpATRPeriod']     = int(m.group(3))
                params['InpFastMA']        = int(m.group(4))
                params['InpSlowMA']        = int(m.group(5))
                params['InpADXMin']        = float(m.group(6))
                params['InpRSILower']      = float(m.group(7))
                params['InpRSIUpper']      = float(m.group(8))
                params['InpMaxDD']         = float(m.group(9))
                params['InpMaxPositions']  = int(m.group(10))
                params['InpCooldownBars']  = int(m.group(11))
            else:
                # 援ы삎 ?뺤떇 fallback
                m2 = re.search(r'SL(\d+)_TP(\d+)_ADX(\d+)_MP(\d+)', fname)
                if m2:
                    params['InpSLMultiplier']  = int(m2.group(1)) / 100.0
                    params['InpTPMultiplier']  = int(m2.group(2)) / 10.0
                    params['InpADXMin']        = float(m2.group(3))
                    params['InpMaxPositions']  = int(m2.group(4))

            # Experts ?대뜑??蹂듭궗 (諛깊뀒?ㅽ듃瑜??꾪빐)
            dst = os.path.join(EXPERTS_DIR, fname)
            try:
                shutil.copy2(ex4_path, dst)
            except Exception as e:
                print('  [WARN] EA 蹂듭궗 ?ㅽ뙣: %s -- %s' % (fname, e))
                continue

            scenarios_map[sc_id] = {'params': params, 'fname': fname}
            fq.mark_running(folder_name, current_sc=sc_id)

        if not scenarios_map:
            print('  [QUEUE] %s: ?좏슚??EA ?놁쓬 -- 嫄대꼫?' % folder_name)
            fq.mark_error(folder_name, '?좏슚??EA ?놁쓬')
            continue

        # ── R1: 기존 결과 있으면 로드, 없으면 백테스트 실행 ────────
        round_num = 1
        all_round_results = []
        safe = folder_name.replace(' ', '_')

        def _clean_flags(rn):
            for _f in [f'round_{rn}_progress.json', 'command.json', 'test_completed.flag']:
                _p = os.path.join(CONFIGS_DIR, _f)
                if os.path.exists(_p):
                    try: os.remove(_p)
                    except: pass

        # 기존 R1 결과 파일 탐색 (폴더명 기반)
        _existing_r1 = sorted(glob.glob(
            os.path.join(RESULTS_DIR, 'V7_FOLDER_%s*.json' % safe[:20])))
        _loaded_prev = []
        for _rf in _existing_r1:
            try:
                with open(_rf, encoding='utf-8') as _fp:
                    _rd = json.load(_fp)
                _rr = _rd.get('results', [])
                if _rr:
                    _loaded_prev.extend(_rr)
            except Exception:
                pass

        _max_rounds = int(_sel_data.get('max_rounds', 1)) if _sel_data else 1

        if _loaded_prev and _max_rounds > 1:
            # 기존 결과 사용 → R1 스킵
            all_round_results = _loaded_prev
            print('  [QUEUE] %s: 기존 R1 결과 %d개 로드 → R2부터 진화 시작' % (folder_name, len(_loaded_prev)))
            round_num = 2  # R2부터 시작
        else:
            # R1 신규 실행
            try:
                _clean_flags(round_num)
                results = run_round(round_num, scenarios_map)
            except Exception as e:
                print('  [ERR] %s R1 실행 오류: %s' % (folder_name, e))
                _log_debug(f"폴더 실행 중 에러 발생: {e}")
                fq.mark_error(folder_name, f'실행 오류: {e}')
                continue
            finally:
                _clean_flags(round_num)

            all_round_results.extend(results or [])

            # R1 결과 저장
            ts   = datetime.now().strftime('%m%d_%H%M')
            rfile = os.path.join(RESULTS_DIR, 'V7_FOLDER_%s_R01_%s.json' % (safe, ts))
            try:
                with open(rfile, 'w', encoding='utf-8') as f:
                    json.dump({'mode': 'folder_queue', 'folder': folder_name,
                               'round': 1, 'symbols': SYMBOLS, 'timeframes': TIMEFRAMES,
                               'from_date': FROM_DATE, 'to_date': TO_DATE,
                               'results': results}, f, indent=2, ensure_ascii=False)
                print('  [QUEUE] R1 결과 저장: %s' % os.path.basename(rfile))
            except Exception as e:
                print('  [WARN] R1 결과 저장 실패: %s' % e)

        # ── R2~N: LHS→FOCUSED→GENETIC 자동 진화 ─────────────
        from core.sampler import get_samples_for_round
        from core.param_space import make_g4_param_space
        _param_space = make_g4_param_space(extra_params=True)
        # round_num은 위에서 설정됨: 기존결과 있으면 2, 없으면 2(R1 완료 후)

        for round_num in range(round_num, _max_rounds + 1):
            if os.path.exists(_stop_file):
                print('  [QUEUE] 정지 신호 — 라운드 진화 중단')
                break
            if os.path.exists(_pause_file):
                print('  [QUEUE] ⏸ 일시정지...')
                while os.path.exists(_pause_file):
                    if os.path.exists(_stop_file): break
                    import time as _t; _t.sleep(2)
                print('  [QUEUE] ▶ 재개')

            prev = sorted(all_round_results, key=lambda x: x.get('score', 0), reverse=True)
            if not prev:
                print('  [QUEUE] 이전 결과 없음 — 라운드 진화 중단')
                break

            strategy = 'LHS' if round_num <= 2 else ('FOCUSED' if round_num <= 5 else 'GENETIC')
            print('\n  [QUEUE] === R%d (%s) -- %s ===' % (round_num, strategy, folder_name))

            try:
                samples = get_samples_for_round(_param_space, round_num, prev,
                                                n=SAMPLES_PER_ROUND, seed=42 + round_num)
                new_scenarios = generate_round_files(samples, round_num)
                # 새 EA 파일 인식을 위해 MT4 재시작
                _restart_mt4_for_new_round()
            except Exception as e:
                print('  [ERR] R%d 샘플/EA 생성 실패: %s' % (round_num, e))
                break

            try:
                _clean_flags(round_num)
                r_results = run_round(round_num, new_scenarios)
            except Exception as e:
                print('  [ERR] R%d 실행 오류: %s' % (round_num, e))
                _log_debug(f"R{round_num} 실행 오류: {e}")
                break
            finally:
                _clean_flags(round_num)

            all_round_results.extend(r_results or [])

            ts2 = datetime.now().strftime('%m%d_%H%M')
            rfile2 = os.path.join(RESULTS_DIR, 'V7_FOLDER_%s_R%02d_%s.json' % (safe, round_num, ts2))
            try:
                with open(rfile2, 'w', encoding='utf-8') as f:
                    json.dump({'mode': 'folder_queue', 'folder': folder_name,
                               'round': round_num, 'strategy': strategy,
                               'symbols': SYMBOLS, 'timeframes': TIMEFRAMES,
                               'from_date': FROM_DATE, 'to_date': TO_DATE,
                               'results': r_results}, f, indent=2, ensure_ascii=False)
                print('  [QUEUE] R%d 결과 저장: %s' % (round_num, os.path.basename(rfile2)))
            except Exception as e:
                print('  [WARN] R%d 결과 저장 실패: %s' % (round_num, e))

            top3 = sorted(r_results or [], key=lambda x: x.get('score', 0), reverse=True)[:3]
            for i, r in enumerate(top3, 1):
                print('  TOP%d: score=%.1f profit=$%,.0f dd=%.1f%% %s' % (
                    i, r.get('score', 0), r.get('profit', 0),
                    r.get('drawdown_pct', 0), r.get('ea_name', '')[:40]))

        fq.mark_done(folder_name)
        print('  [QUEUE] %s 완료 (%d라운드) -> 다음 폴더로..' % (folder_name, _max_rounds))

    print('\n' + '#' * 60)
    print('  ?대뜑 ???꾩껜 ?꾨즺. 寃곌낵: %s' % RESULTS_DIR)
    print('#' * 60 + '\n')


if __name__ == '__main__':
    if '--folder-queue' in sys.argv:
        run_folder_queue()
    elif '--round' in sys.argv:
        # --round N [--to M]  : ?⑥씪/踰붿쐞 ?쇱슫???ㅽ뻾
        idx = sys.argv.index('--round')
        _r_start = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 1
        _r_end   = _r_start
        if '--to' in sys.argv:
            idx2   = sys.argv.index('--to')
            _r_end = int(sys.argv[idx2 + 1]) if idx2 + 1 < len(sys.argv) else _r_start
        # main() ???꾩뿭 蹂??珥덇린????吏???쇱슫?쒕쭔 ?ㅽ뻾
        FROM_DATE, TO_DATE = _load_dates_from_ini()
        SYMBOLS, TIMEFRAMES = _load_symbols_from_ini()
        SYMBOL, TIMEFRAME   = SYMBOLS[0], TIMEFRAMES[0]
        param_space = make_g4_param_space(extra_params=True)
        for _rn in range(_r_start, _r_end + 1):
            print(f'\n{"#"*60}')
            print(f'  EA Auto Master V7.0 ??R{_rn} ?⑤룆 ?ㅽ뻾')
            print(f'{"#"*60}\n')
            existing = sorted(glob.glob(os.path.join(EXPERTS_DIR, f'G4v7_*_R{_rn}*.ex4')))
            if existing:
                sc_map = {}
                for _i, _ep in enumerate(existing, 1):
                    sc_map[_i] = {'params': {}, 'ex4_path': _ep}
                results = run_round(_rn, sc_map)
            else:
                from core.sampler import get_samples_for_round
                samples  = get_samples_for_round(param_space, _rn, [], SAMPLES_PER_ROUND)
                sc_map   = {s['sc_id']: s for s in samples}
                generate_round_files(samples, _rn)
                results  = run_round(_rn, sc_map)
            if results:
                backup_round_files(_rn)
    elif '--evolve' in sys.argv:
        # --evolve [--rounds N] [--start R]  : 기존 결과 기반 자동 진화
        _max_r = 6
        _start_r = None
        if '--rounds' in sys.argv:
            _i = sys.argv.index('--rounds')
            _max_r = int(sys.argv[_i + 1]) if _i + 1 < len(sys.argv) else 6
        if '--start' in sys.argv:
            _i = sys.argv.index('--start')
            _start_r = int(sys.argv[_i + 1]) if _i + 1 < len(sys.argv) else None

        from core.sampler import get_samples_for_round

        # 기존 결과 전체 로드
        _all_prev = []
        for _rf in sorted(glob.glob(os.path.join(RESULTS_DIR, '*.json'))):
            try:
                with open(_rf, encoding='utf-8') as _fp:
                    _rd = json.load(_fp)
                _all_prev.extend(_rd.get('results', []))
            except Exception:
                pass

        if not _all_prev:
            print('  [EVO] 결과 없음. 먼저 R1을 실행하세요.')
            sys.exit(1)

        # 완료된 마지막 라운드 감지
        _last_done = 0
        for _rf in glob.glob(os.path.join(RESULTS_DIR, '*.json')):
            try:
                with open(_rf, encoding='utf-8') as _fp:
                    _rd = json.load(_fp)
                _r = _rd.get('round') or 0
                if not _r and _rd.get('results'):
                    _r = max((x.get('round') or 0) for x in _rd['results'])
                if _r > _last_done:
                    _last_done = _r
            except Exception:
                pass

        _begin = _start_r if _start_r else max(2, _last_done + 1)
        _param_space = make_g4_param_space(extra_params=True)
        _stop_f  = os.path.join(CONFIGS_DIR, 'runner_stop.signal')
        _pause_f = os.path.join(CONFIGS_DIR, 'runner_pause.signal')

        print('\n' + '#' * 60)
        print('  AUTO EVOLUTION  R%d ~ R%d' % (_begin, _max_r))
        print('  기존 결과: %d개  최근완료: R%d' % (len(_all_prev), _last_done))
        print('#' * 60 + '\n')

        for _rn in range(_begin, _max_r + 1):
            if os.path.exists(_stop_f):
                print('  [EVO] 정지 신호 — 종료')
                break
            while os.path.exists(_pause_f):
                if os.path.exists(_stop_f): break
                import time as _tm; _tm.sleep(2)

            _strat = 'LHS' if _rn <= 2 else ('FOCUSED' if _rn <= 5 else 'GENETIC')
            print('\n  === R%d (%s) ===' % (_rn, _strat))

            _samples = get_samples_for_round(_param_space, _rn, _all_prev,
                                             n=SAMPLES_PER_ROUND, seed=42 + _rn * 7)
            _sc_map  = generate_round_files(_samples, _rn)
            if not _sc_map:
                print('  [ERR] R%d 시나리오 없음' % _rn)
                break

            # 새 EA 파일 인식을 위해 MT4 재시작
            _restart_mt4_for_new_round()

            def _evo_clean(_n):
                for _fn in ['round_%d_progress.json' % _n, 'command.json', 'test_completed.flag']:
                    _p = os.path.join(CONFIGS_DIR, _fn)
                    if os.path.exists(_p):
                        try: os.remove(_p)
                        except: pass

            _evo_clean(_rn)
            _r_res = run_round(_rn, _sc_map)
            _evo_clean(_rn)

            if not _r_res:
                print('  [WARN] R%d 결과 없음' % _rn)
                break

            _all_prev.extend(_r_res)

            _ts2 = datetime.now().strftime('%m%d_%H%M')
            _rfile2 = os.path.join(RESULTS_DIR, 'V7_EVO_R%02d_%s.json' % (_rn, _ts2))
            try:
                with open(_rfile2, 'w', encoding='utf-8') as _f2:
                    json.dump({'mode': 'evolution', 'round': _rn, 'strategy': _strat,
                               'symbols': SYMBOLS, 'timeframes': TIMEFRAMES,
                               'from_date': FROM_DATE, 'to_date': TO_DATE,
                               'results': _r_res}, _f2, indent=2, ensure_ascii=False)
                print('  [EVO] R%d 결과 저장: %s' % (_rn, os.path.basename(_rfile2)))
            except Exception as _e2:
                print('  [WARN] 저장 실패: %s' % _e2)

            _top5 = sorted(_r_res, key=lambda x: x.get('score', 0), reverse=True)[:5]
            print('  --- R%d TOP5 ---' % _rn)
            for _i2, _r2 in enumerate(_top5, 1):
                print('  %d. score=%.1f profit=$%,.0f dd=%.1f%% %s' % (
                    _i2, _r2.get('score', 0), _r2.get('profit', 0),
                    _r2.get('drawdown_pct', 0), _r2.get('ea_name', '')[:45]))

            backup_round_files(_rn)

        print('\n' + '#' * 60)
        print('  진화 완료. 결과: %s' % RESULTS_DIR)
        print('#' * 60 + '\n')
    else:
        main()

