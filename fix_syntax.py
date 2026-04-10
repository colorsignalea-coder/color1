import os
fpath = r'C:\AG TO DO\EA_AUTO_MASTER_v8.0\ea_optimizer_v7.py'
with open(fpath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

lines[616] = '    print(f\"  EA Auto Master V7.0 지능형 파라미터 최적화\")\n'
lines[618] = '    print(f\"  라운드당 {SAMPLES_PER_ROUND}개 시나리오  최대 {MAX_ROUNDS}라운드\")\n'
lines[792] = '            print(f\"  [ALARM] all_done.flag 생성 -> SOLO 알람 트리거\")\n'
lines[818] = '    print(\"  EA Auto Master V7.0 -- 폴더 큐 모드\")\n'
lines[819] = '    print(\"  READY_FOR_TEST/ 하위 폴더 순서대로 테스트\")\n'

with open(fpath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
