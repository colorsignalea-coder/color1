import os, shutil, glob

def setup_test_environment(count=2):
    base_dir = r"C:\AG TO DO\EA_AUTO_MASTER_v8.0"
    ready_dir = os.path.join(base_dir, "reports", "READY_FOR_TEST")
    experts_dir = os.path.join(r"C:\AG TO DO\MT4", "MQL4", "Experts")
    
    print(f"--- 큐 자동 완주 테스트({count}개) 시작 ---")
    
    # 청소
    for existing in glob.glob(os.path.join(ready_dir, "AUTO_TEST_V8_*")):
        shutil.rmtree(existing)

    ex4_files = glob.glob(os.path.join(experts_dir, "*.ex4"))
    sample_ea = ex4_files[0] if ex4_files else os.path.join(ready_dir, "Dummy.ex4")

    for i in range(1, count + 1):
        test_folder = os.path.join(ready_dir, f"AUTO_TEST_V8_{i}")
        os.makedirs(test_folder, exist_ok=True)
        shutil.copy2(sample_ea, os.path.join(test_folder, f"Test_EA_{i}.ex4"))
        print(f"생성 완료: {test_folder}")

    print(f"\n[성공] 테스트 폴더 {count}개가 준비되었습니다.")

if __name__ == "__main__":
    setup_test_environment(2) # 2개로 완주 테스트
