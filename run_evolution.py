"""
run_evolution.py — EA Auto Master v8.1
기존 R1 결과 기반 자동 진화 런처.

사용법:
    python run_evolution.py              # R2부터 자동 (결과 자동 감지)
    python run_evolution.py --rounds 3   # 최대 3라운드
    python run_evolution.py --start 3    # R3부터 시작
"""
import os, sys, subprocess

HERE      = os.path.dirname(os.path.abspath(__file__))
OPTIMIZER = os.path.join(HERE, 'ea_optimizer_v7.py')

if __name__ == '__main__':
    # 인자 그대로 ea_optimizer_v7.py --evolve 에 전달
    extra = [a for a in sys.argv[1:] if a not in ('--evolve',)]
    cmd = [sys.executable, '-u', OPTIMIZER, '--evolve'] + extra
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run(cmd, env=env, cwd=HERE)
    sys.exit(result.returncode)
