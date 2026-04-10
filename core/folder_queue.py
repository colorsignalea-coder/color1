"""
core/folder_queue.py -- 폴더 큐 기반 백테스트 관리
================================================
READY_FOR_TEST/ 하위 폴더를 큐로 사용.
a_project/ -> b_project/ -> c_project/ 알파벳 순 테스트.
완료 폴더 -> AFTER_FOR_TEST/{폴더명}/으로 이동.

주의: tkinter 금지 (core/ 규칙). 순수 Python만.
"""
import os
import json
import re as _re
import shutil


def _numeric_key(name):
    """폴더명 앞의 숫자를 기준으로 정렬. 숫자 없으면 이름 알파벳 순."""
    m = _re.match(r'^(\d+)', name)
    return (int(m.group(1)) if m else float('inf'), name.lower())

_BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READY_DIR  = os.path.join(_BASE, 'reports', 'READY_FOR_TEST')
AFTER_DIR  = os.path.join(_BASE, 'reports', 'AFTER_FOR_TEST')
QUEUE_FILE = os.path.join(_BASE, 'configs', 'queue_status.json')


class FolderQueue:
    """READY_FOR_TEST 하위 폴더 큐 관리."""

    def __init__(self):
        self._ready_dir = READY_DIR
        self._after_dir = AFTER_DIR
        self._file      = QUEUE_FILE
        os.makedirs(self._ready_dir, exist_ok=True)
        os.makedirs(self._after_dir, exist_ok=True)
        self._state = self._load()

    # -- 상태 로드/저장 --------------------------------------------------
    def _load(self):
        if os.path.exists(self._file):
            try:
                with open(self._file, encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            'mode':               'folder_queue',
            'current_folder':     '',
            'current_sc':         0,
            'current_sym':        '',
            'current_tf':         '',
            'completed_folders':  [],
            'queue':              [],
        }

    def save(self):
        os.makedirs(os.path.dirname(self._file), exist_ok=True)
        with open(self._file, 'w', encoding='utf-8') as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    # -- 폴더 스캔 --------------------------------------------------------
    def scan_folders(self):
        """READY_FOR_TEST 하위 폴더 스캔 -> 번호 순 (앞 숫자 기준, 없으면 알파벳).
        .ex4 파일이 있는 폴더만 반환."""
        folders = []
        if not os.path.exists(self._ready_dir):
            return folders
        for name in sorted(os.listdir(self._ready_dir), key=_numeric_key):
            path = os.path.join(self._ready_dir, name)
            if not os.path.isdir(path):
                continue
            ex4s = [f for f in os.listdir(path) if f.lower().endswith('.ex4')]
            if ex4s:
                folders.append({'name': name, 'path': path, 'count': len(ex4s)})
        return folders

    def get_ex4_files(self, folder_name):
        """특정 폴더의 .ex4 파일 전체 경로 목록 반환."""
        path = os.path.join(self._ready_dir, folder_name)
        if not os.path.exists(path):
            return []
        return sorted([
            os.path.join(path, f)
            for f in os.listdir(path) if f.lower().endswith('.ex4')
        ])

    # -- 큐 제어 ----------------------------------------------------------
    def get_next_pending(self):
        """다음 테스트 대상 폴더 정보 반환. 없으면 None."""
        done = set(self._state.get('completed_folders', []))
        for folder in self.scan_folders():
            if folder['name'] not in done:
                return folder
        return None

    def mark_running(self, folder_name, current_sc=0, sym='', tf=''):
        self._state['current_folder'] = folder_name
        self._state['current_sc']     = current_sc
        self._state['current_sym']    = sym
        self._state['current_tf']     = tf
        self.save()

    def mark_done(self, folder_name):
        """완료 처리 + AFTER_FOR_TEST로 이동."""
        done = self._state.setdefault('completed_folders', [])
        if folder_name not in done:
            done.append(folder_name)
        if self._state.get('current_folder') == folder_name:
            self._state['current_folder'] = ''
            self._state['current_sc']     = 0
        self.save()
        self._move_to_after(folder_name)

    def mark_error(self, folder_name, reason=''):
        """에러 폴더 -> 스킵하고 다음으로 (무한루프 방지)."""
        print('  [QUEUE ERROR] %s: %s' % (folder_name, reason))
        self.mark_done(folder_name)

    def reset(self):
        """큐 완전 초기화."""
        self._state = {
            'mode':               'folder_queue',
            'current_folder':     '',
            'current_sc':         0,
            'current_sym':        '',
            'current_tf':         '',
            'completed_folders':  [],
            'queue':              [],
        }
        self.save()

    # -- 진행률 -----------------------------------------------------------
    def get_progress(self):
        """(완료수, 전체수) 반환."""
        total = len(self.scan_folders())
        done  = len(self._state.get('completed_folders', []))
        return done, total

    def get_current_folder(self):
        return self._state.get('current_folder', '')

    def get_status_text(self):
        done, total = self.get_progress()
        cur = self._state.get('current_folder', '')
        sc  = self._state.get('current_sc', 0)
        if cur:
            return '%s (SC%d)  [%d/%d]' % (cur, sc, done, total)
        return '대기 중  [%d/%d]' % (done, total)

    # -- 내부 -------------------------------------------------------------
    def _move_to_after(self, folder_name):
        src = os.path.join(self._ready_dir, folder_name)
        dst = os.path.join(self._after_dir, folder_name)
        if not os.path.exists(src):
            return
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(src, dst)
            print('  [QUEUE] 완료 이동: %s -> AFTER_FOR_TEST/' % folder_name)
        except Exception as e:
            print('  [WARN] 폴더 이동 실패: %s' % e)


# -- CLI -----------------------------------------------------------------
if __name__ == '__main__':
    import sys
    q = FolderQueue()
    if '--scan' in sys.argv:
        folders = q.scan_folders()
        print('READY_FOR_TEST 하위 폴더 (%d개):' % len(folders))
        for fd in folders:
            done_mark = ' [완료]' if fd['name'] in q._state.get('completed_folders', []) else ''
            print('  %s/  (%d개 .ex4)%s' % (fd['name'], fd['count'], done_mark))
        print()
        nxt = q.get_next_pending()
        print('다음 테스트 대상: %s' % (nxt['name'] if nxt else '없음'))
    elif '--reset' in sys.argv:
        q.reset()
        print('큐 초기화 완료.')
    else:
        print(q.get_status_text())
