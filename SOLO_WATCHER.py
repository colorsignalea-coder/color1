import os
import time

# [WATCHER] Real-time Report Layout Fixer v1.01
CSS_CODE = """<style type='text/css'>
/* Layout Fix v5.4 AUTO-WATCH */
body { overflow-x: auto !important; margin: 0 !important; padding: 10px !important; }
table { width: 100% !important; table-layout: fixed !important; border-collapse: collapse !important; border: 1px solid #ccc !important; }
td, th { padding: 6px !important; border: 1px solid #ddd !important; word-wrap: break-word !important; }
tr > td:first-child, tr > th:first-child { 
    width: 220px !important; min-width: 220px !important; max-width: 220px !important; 
    white-space: nowrap !important; background-color: #f8f9fa !important; 
    font-weight: bold !important; vertical-align: top !important; border-right: 2px solid #aaa !important;
}
tr > td:not(:first-child), tr > th:not(:first-child) { width: auto !important; }
</style>
"""

# 배포형: 스크립트 위치 기준 reports 폴더 + 공통 MT4 경로 자동 탐지
_HERE = os.path.dirname(os.path.abspath(__file__))
_reports_local = os.path.join(_HERE, "reports")
os.makedirs(_reports_local, exist_ok=True)

search_roots = [
    _reports_local,                           # RUNTIME/reports/ (최우선)
    os.path.abspath(os.path.join(HERE, "..", "MT4")),
    r"C:\MT4\tester\history",
    r"D:\MT4\tester\history",
    r"C:\2026NEWOPTMIZER", r"D:\2026NEWOPTMIZER",
    r"C:\NEWOPTMISER",     r"C:\NEWOPTIMISER",
]

print("==================================================")
print("  SOLO REPORT WATCHER ACTIVE [v1.01 DEPLOY]")
print(f"  Primary: {_reports_local}")
print("  Monitoring reports + MT4 tester folders...")
print("==================================================")

while True:
    try:
        for root_dir in search_roots:
            if not os.path.exists(root_dir):
                continue
                
            for root, dirs, files in os.walk(root_dir):
                for file in files:
                    if file.lower().endswith(('.htm', '.html')):
                        fpath = os.path.join(root, file)
                        
                        # Read binary to detect and fix without encoding issues
                        with open(fpath, 'rb') as f:
                            raw_data = f.read()
                        
                        if b"Layout Fix v5.4" in raw_data:
                            continue
                            
                        # Try to find </head> tag (any case) in binary
                        head_tag = b"</head>"
                        if head_tag.lower() not in raw_data.lower():
                            continue
                            
                        # Perform the replacement
                        # We use UTF-8 as the primary write format
                        content = ""
                        for enc in ['utf-8', 'cp949', 'latin-1']:
                            try:
                                content = raw_data.decode(enc)
                                break
                            except:
                                continue
                        
                        if content and "Layout Fix v5.4" not in content:
                            new_content = None
                            if "</head>" in content.lower():
                                low = content.lower()
                                idx = low.find("</head>")
                                tag = content[idx:idx+7]
                                new_content = content.replace(tag, CSS_CODE + tag)

                            if new_content:
                                # Write to temp file first, then rename to avoid file lock contention
                                tmp = fpath + '.tmp'
                                try:
                                    with open(tmp, 'w', encoding='utf-8') as f:
                                        f.write(new_content)
                                    import os as _os
                                    _os.replace(tmp, fpath)
                                    print(f"[FIXED] {_os.path.basename(fpath)}")
                                except Exception:
                                    try: _os.remove(tmp)
                                    except: pass
                                
        # Check every 10 seconds (reduced to avoid file lock contention with optimizer)
        time.sleep(10)
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        # Silently continue on errors (permissions, etc)
        time.sleep(2)
