
import os
import sys
import tkinter as tk

# PATH 설정
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.append(HERE)

def test_imports():
    print("[TEST] Testing imports...")
    try:
        from core.folder_queue import FolderQueue
        from ui.tab_run_control import RunControlTab
        print("  - Core & UI imports: OK")
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        return False
    return True

def test_physical_files():
    print("[TEST] Testing physical file access (Deep Test)...")
    ready_dir = os.path.join(HERE, "reports", "READY_FOR_TEST")
    if not os.path.exists(ready_dir):
        print(f"  [FAIL] READY_FOR_TEST folder not found at: {ready_dir}")
        return False
    
    folders = [d for d in os.listdir(ready_dir) if os.path.isdir(os.path.join(ready_dir, d))]
    print(f"  - Found {len(folders)} root folders in READY_FOR_TEST")
    
    ex4_found = False
    for root, dirs, files in os.walk(ready_dir):
        for f in files:
            if f.lower().endswith(".ex4"):
                ex4_found = True
                # 실제 파일 오픈 시도 (읽기 권한 체크)
                try:
                    with open(os.path.join(root, f), "rb") as fh:
                        fh.read(10)
                    # print(f"    - Access OK: {f}")
                    break
                except Exception as e:
                    print(f"  [FAIL] Cannot read file {f}: {e}")
                    return False
        if ex4_found: break
    
    if not ex4_found:
        print("  [WARN] No .ex4 files found in any subdirectory. UI might look empty but it's correct.")
    else:
        print("  - Physical file access: OK")
    return True

def test_ui_variables():
    print("[TEST] Testing UI Instance variables (Attribute Check)...")
    root = tk.Tk()
    root.withdraw()
    try:
        from ui.tab_run_control import RunControlTab
        # Mock config
        cfg = {"solo_dir": HERE}
        # 인스턴스 생성 시도
        tab = RunControlTab(root, cfg)
        
        # 필수 변수 존재 체크
        required = ["_queue_vars", "_queue_labels", "_file_vars", "_file_labels", "log"]
        for attr in required:
            if not hasattr(tab, attr):
                print(f"  [FAIL] Missing attribute: {attr}")
                return False
            else:
                pass
        print("  - Required UI attributes: OK")
        
        # _refresh_queue_list 실행 시뮬레이션 (AttributeError 방지 확인)
        try:
            tab._refresh_queue_list()
            print("  - _refresh_queue_list execution: OK")
        except Exception as e:
            print(f"  [FAIL] _refresh_queue_list crashed: {e}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] UI Instance creation failed: {e}")
        return False
    finally:
        root.destroy()
    return True

if __name__ == "__main__":
    print(f"\n=== EA AUTO MASTER v8.2 DEEP SELF-TEST ===")
    success = True
    if not test_imports(): success = False
    if success and not test_physical_files(): success = False
    if success and not test_ui_variables(): success = False
    
    if success:
        print("\n[RESULT] DEEP SELF-TEST PASSED")
        sys.exit(0)
    else:
        print("\n[RESULT] DEEP SELF-TEST FAILED")
        sys.exit(1)
