
import os
import sys
import shutil
import json
import time

# 원본 경로 설정
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(HERE)

from core.folder_queue import FolderQueue

def setup_mock_folders(num=5):
    ready_dir = os.path.join(HERE, "reports", "READY_FOR_TEST")
    # 기존 폴더 삭제 후 재생성 (완전 초기화)
    if os.path.exists(ready_dir):
        shutil.rmtree(ready_dir)
    os.makedirs(ready_dir, exist_ok=True)
    
    for i in range(1, num+1):
        folder_path = os.path.join(ready_dir, f"{i:02d}_TestFolder")
        os.makedirs(folder_path, exist_ok=True)
        # 가상 EA 파일 생성
        with open(os.path.join(folder_path, f"EA_SC001_R1.ex4"), "w") as f:
            f.write("mock ea content")
    print(f"[REPRO] {num}개의 가상 테스트 폴더를 생성했습니다.")

def run_repro_test():
    print("\n[REPRO] 큐 로직 스트레스 테스트를 시작합니다...")
    fq = FolderQueue()
    fq.reset() # 상태 초기화
    
    # 가상의 선택 목록 (1~5번 모두 선택)
    selected_set = {f"{i:02d}_TestFolder" for i in range(1, 6)}
    
    loop_count = 0
    while True:
        loop_count += 1
        print(f"\n--- 루프 #{loop_count} ---")
        
        # 1. 다음 폴더 가져오기
        folder_info = fq.get_next_pending()
        if not folder_info:
            print("[REPRO] 모든 폴더 완료 감지 (PASS)")
            break
            
        folder_name = folder_info['name']
        print(f"[REPRO] 대상 감지: {folder_name}")
        
        # 2. 선택 필터 비교
        if folder_name not in selected_set:
            print(f"[REPRO] 스킵 (필터): {folder_name}")
            continue
            
        # 3. 테스트 실행 모사 (3초 대기)
        print(f"[REPRO] {folder_name} 테스트 실행 중 (3초)...")
        time.sleep(1) # 시뮬레이션을 위해 짧게
        
        # 4. 완료 처리 (파일 이동 포함)
        print(f"[REPRO] {folder_name} 완료 처리 중...")
        fq.mark_done(folder_name)
        
        # 5. 파일 존재 여부 확인 (Ready에서 사라졌는지)
        ready_path = os.path.join(HERE, "reports", "READY_FOR_TEST", folder_name)
        after_path = os.path.join(HERE, "reports", "AFTER_FOR_TEST", folder_name)
        
        if os.path.exists(ready_path):
            print(f"[REPRO] [FAIL] 폴더가 READY에서 사라지지 않았습니다!")
            return False
            
        if not os.path.exists(after_path):
            print(f"[REPRO] [FAIL] 폴더가 AFTER로 이동되지 않았습니다!")
            return False
            
        print(f"[REPRO] {folder_name} 이동 및 완료 검증 성공")
        
        if loop_count > 50: # 무한 루프 방지
            print("[REPRO] [FAIL] 비정상적인 무한 루프가 발생했습니다.")
            return False

    print("\n[REPRO] 모든 과정이 정상적으로 종료되었습니다. (TOTAL 5/5 SUCCESS)")
    return True

if __name__ == "__main__":
    setup_mock_folders(5)
    success = run_repro_test()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
