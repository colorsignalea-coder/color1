"""
core/reset_engine.py -- 초기화 엔진
=====================================
configs/round_*_progress.json 전부 삭제,
status.json 초기화, flag/command 파일 정리.
g4_results는 백업 후 보존 (원본 삭제 금지 규칙).

주의: tkinter 금지 (core/ 규칙). 순수 Python만.
"""
import os
import glob
import json
import shutil
from datetime import datetime

_BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGS_DIR = os.path.join(_BASE, 'configs')
RESULTS_DIR = os.path.join(_BASE, 'g4_results')


def reset_all(backup_results=True):
    """전체 초기화.
    반환: (삭제 파일 수, 메시지 목록)
    """
    msgs    = []
    deleted = 0

    # 1. round_*_progress.json 전부 삭제
    prog_files = glob.glob(os.path.join(CONFIGS_DIR, 'round_*_progress*.json'))
    for f in sorted(prog_files):
        try:
            os.remove(f)
            msgs.append('  삭제: ' + os.path.basename(f))
            deleted += 1
        except Exception as e:
            msgs.append('  [WARN] 삭제 실패: %s -- %s' % (os.path.basename(f), e))

    # 2. flag / command 파일 삭제
    flag_patterns = [
        'test_completed*.flag',
        'all_done.flag',
        'runner_stop.signal',
        'command.json',
        'command_processing.json',
        '_btc_batch_patch.json',
    ]
    for pat in flag_patterns:
        for f in glob.glob(os.path.join(CONFIGS_DIR, pat)):
            try:
                os.remove(f)
                msgs.append('  삭제: ' + os.path.basename(f))
                deleted += 1
            except Exception as e:
                msgs.append('  [WARN] 삭제 실패: %s -- %s' % (os.path.basename(f), e))

    # 3. status.json -> idle
    status_f = os.path.join(CONFIGS_DIR, 'status.json')
    try:
        with open(status_f, 'w', encoding='utf-8') as f:
            json.dump({
                'status':    'idle',
                'message':   '초기화 완료',
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            }, f, ensure_ascii=False)
        msgs.append('  status.json -> idle')
    except Exception as e:
        msgs.append('  [WARN] status.json 초기화 실패: %s' % e)

    # 4. queue_status.json 초기화
    q_file = os.path.join(CONFIGS_DIR, 'queue_status.json')
    try:
        with open(q_file, 'w', encoding='utf-8') as f:
            json.dump({
                'mode':              'folder_queue',
                'current_folder':    '',
                'current_sc':        0,
                'current_sym':       '',
                'current_tf':        '',
                'completed_folders': [],
                'queue':             [],
            }, f, ensure_ascii=False)
        msgs.append('  queue_status.json -> 초기화')
    except Exception as e:
        msgs.append('  [WARN] queue_status.json 초기화 실패: %s' % e)

    # 5. g4_results 백업 (삭제 금지 -- 원본 보관 규칙)
    if backup_results and os.path.exists(RESULTS_DIR):
        ts  = datetime.now().strftime('%m%d_%H%M')
        bak = RESULTS_DIR + '_bak_' + ts
        try:
            shutil.copytree(RESULTS_DIR, bak)
            msgs.append('  g4_results 백업: ' + os.path.basename(bak))
        except Exception as e:
            msgs.append('  [WARN] g4_results 백업 실패: %s' % e)

    return deleted, msgs


def delete_json_only():
    """JSON 파일만 실제 삭제. g4_results 레포트(HTML/CSV)는 건드리지 않음.
    반환: (삭제 파일 수, 메시지 목록)
    """
    msgs    = []
    deleted = 0

    # 1. round_*_progress.json 전부 삭제
    prog_files = glob.glob(os.path.join(CONFIGS_DIR, 'round_*_progress*.json'))
    for f in sorted(prog_files):
        try:
            os.remove(f)
            msgs.append('  [삭제] ' + os.path.basename(f))
            deleted += 1
        except Exception as e:
            msgs.append('  [WARN] 삭제 실패: %s -- %s' % (os.path.basename(f), e))

    # 2. flag / command JSON 파일 삭제
    flag_patterns = [
        'test_completed*.flag',
        'all_done.flag',
        'runner_stop.signal',
        'command.json',
        'command_processing.json',
        '_btc_batch_patch.json',
    ]
    for pat in flag_patterns:
        for f in glob.glob(os.path.join(CONFIGS_DIR, pat)):
            try:
                os.remove(f)
                msgs.append('  [삭제] ' + os.path.basename(f))
                deleted += 1
            except Exception as e:
                msgs.append('  [WARN] 삭제 실패: %s -- %s' % (os.path.basename(f), e))

    # 3. g4_results 폴더 안 JSON만 삭제 (HTML/CSV 레포트는 보존)
    if os.path.exists(RESULTS_DIR):
        json_files = glob.glob(os.path.join(RESULTS_DIR, '*.json'))
        json_files += glob.glob(os.path.join(RESULTS_DIR, '**', '*.json'))
        for f in sorted(set(json_files)):
            try:
                os.remove(f)
                msgs.append('  [삭제] g4_results/' + os.path.relpath(f, RESULTS_DIR))
                deleted += 1
            except Exception as e:
                msgs.append('  [WARN] 삭제 실패: %s -- %s' % (os.path.basename(f), e))

    # 4. status.json -> idle
    status_f = os.path.join(CONFIGS_DIR, 'status.json')
    try:
        with open(status_f, 'w', encoding='utf-8') as f:
            json.dump({
                'status':    'idle',
                'message':   'JSON 완전삭제 완료',
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            }, f, ensure_ascii=False)
        msgs.append('  status.json -> idle')
    except Exception as e:
        msgs.append('  [WARN] status.json 초기화 실패: %s' % e)

    # 5. queue_status.json 초기화
    q_file = os.path.join(CONFIGS_DIR, 'queue_status.json')
    try:
        with open(q_file, 'w', encoding='utf-8') as f:
            json.dump({
                'mode':              'folder_queue',
                'current_folder':    '',
                'current_sc':        0,
                'current_sym':       '',
                'current_tf':        '',
                'completed_folders': [],
                'queue':             [],
            }, f, ensure_ascii=False)
        msgs.append('  queue_status.json -> 초기화')
    except Exception as e:
        msgs.append('  [WARN] queue_status.json 초기화 실패: %s' % e)

    return deleted, msgs


if __name__ == '__main__':
    print('=== 초기화 시작 ===')
    cnt, msgs = reset_all()
    for m in msgs:
        print(m)
    print('\n완료: %d개 파일 정리' % cnt)
