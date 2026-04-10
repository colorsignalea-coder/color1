import os, time, json
from datetime import datetime

def simulate_mt4_response():
    base_dir = r"C:\AG TO DO\EA_AUTO_MASTER_v8.0"
    config_dir = os.path.join(base_dir, "configs")
    cmd_file = os.path.join(config_dir, "command.json")
    flag_file = os.path.join(config_dir, "test_completed.flag")
    
    print("MT4 시뮬레이터 가동 중... (명령 감지 시 완료 플래그 생성)")
    count = 0
    while count < 20: # 최대 20번만 수행하고 종료
        if os.path.exists(cmd_file):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 명령 감지! 5초 후 완료 처리...")
            time.sleep(5)
            
            # 완료 플래그 생성
            with open(flag_file, "w") as f:
                f.write("done")
            
            # 명령 파일 삭제 (처리 완료)
            try: os.remove(cmd_file)
            except: pass
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 완료 플래그 생성 완료. (작업 {count+1})")
            count += 1
        time.sleep(2)

if __name__ == "__main__":
    simulate_mt4_response()
