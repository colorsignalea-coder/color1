"""
core/mql4_autofix.py — EA Auto Master v6.0
===========================================
MQL4 컴파일 오류 12개 룰 기반 자동 검사/수정.
+ COMPILE_V1 통합: MetaEditor 컴파일 로그 파싱 + 타깃 수정.
UI 무관 — 순수 로직만.
"""
import os
import re
import subprocess


def _autofix_check_local_redecl(src):
    """OnTick/OnInit 함수 내부에서 double/int/string 재선언 검사."""
    inside = False
    depth = 0
    for line in src.splitlines():
        stripped = line.strip()
        if re.match(r'(int|void)\s+On(Tick|Init|Deinit)\s*\(', stripped):
            inside = True
            depth = 0
        if inside:
            depth += stripped.count("{") - stripped.count("}")
            if depth <= 0 and inside and "{" not in stripped and "}" in stripped:
                inside = False
            if inside and re.match(r'(double|int|string|bool)\s+\w+\s*=', stripped):
                return True
    return False


# 12개 자동수정 룰 정의
# (rule_id, name, description, checker_fn, fixer_fn_or_None)
RULES = [
    ("R01", "R01 #property strict 없음",
     "strict 없으면 변수 미선언/타입 오류가 무시되다가 런타임에 터짐",
     lambda src: "#property strict" not in src,
     lambda src: "#property strict\n" + src),

    ("R02", "R02 extern -> input 미변환",
     "MT4 빌드 600+ 에서 extern 대신 input 권장 (하위호환은 됨)",
     lambda src: bool(re.search(r"\bextern\b", src)),
     lambda src: re.sub(r"\bextern\b", "input", src)),

    ("R03", "R03 { } 괄호 불일치",
     "여는 괄호 { 와 닫는 괄호 } 개수가 다름",
     lambda src: src.count("{") != src.count("}"),
     None),

    ("R04", "R04 ( ) 괄호 불일치",
     "여는 ( 와 닫는 ) 개수가 다름",
     lambda src: src.count("(") != src.count(")"),
     None),

    ("R05", "R05 OnInit 반환형 누락",
     "int OnInit() 이어야 하는데 void OnInit() 사용",
     lambda src: bool(re.search(r"\bvoid\s+OnInit\s*\(", src)),
     lambda src: re.sub(r"\bvoid\s+OnInit\s*\(", "int OnInit(", src)),

    ("R06", "R06 Print 문자열 연산 오류",
     'Print(숫자변수+"text") 타입 불일치',
     lambda src: bool(re.search(r'\bPrint\s*\([^;]*\+\s*"', src)),
     lambda src: re.sub(
         r'\bPrint\s*\(([^;]*)\)',
         lambda m: "Print(" + re.sub(
             r'\b([A-Za-z_]\w*)\s*\+', r'string(\1)+', m.group(1)) + ")",
         src)),

    ("R07", "R07 부동소수점 직접 == 비교",
     "Ask/Bid/Close == 숫자 직접 비교",
     lambda src: bool(re.search(
         r'(Ask|Bid|Close\[\d+\]|Open\[\d+\])\s*==\s*([\d.]+)', src)),
     lambda src: re.sub(
         r'(Ask|Bid|Close\[\d+\]|Open\[\d+\])\s*==\s*([\d.]+)',
         r'MathAbs(\1-\2)<_Point', src)),

    ("R08", "R08 Sleep() 호출 (백테스트 오류)",
     "Sleep()은 백테스트에서 무한대기 유발",
     lambda src: bool(re.search(r'\bSleep\s*\(', src)),
     lambda src: re.sub(
         r'(\s*)(Sleep\s*\([^)]*\)\s*;)',
         r'\1// [AutoFix R08] \2', src)),

    ("R09", "R09 세미콜론 없는 return/break/continue",
     "return/break/continue 뒤 ; 없으면 구문 오류",
     lambda src: bool(re.search(r'\b(return|break|continue)\b[ \t]*\n', src)),
     lambda src: re.sub(
         r'\b(return|break|continue)\b([ \t]*)\n',
         lambda m: m.group(1) + ";" + m.group(2) + "\n", src)),

    ("R10", "R10 함수 내부 전역변수 재선언",
     "OnTick 내 double/int 선언은 매 틱 초기화됨",
     lambda src: _autofix_check_local_redecl(src),
     None),

    ("R11", "R11 OrderSend 반환값 미확인",
     "OrderSend() 결과를 변수에 받지 않으면 주문 실패를 모름",
     lambda src: bool(re.search(
         r'(?<!ticket\s=\s)(?<!int\s\w+\s=\s)OrderSend\s*\(', src)),
     lambda src: re.sub(
         r'(?<![=\w])(OrderSend\s*\([^;]+;)',
         r'int _ticket=\1', src)),

    ("R12", "R12 GetLastError() 미호출 (OrderSend 후)",
     "OrderSend 실패 시 GetLastError()로 원인 확인 필요",
     lambda src: (bool(re.search(r'\bOrderSend\s*\(', src))
                  and not bool(re.search(r'\bGetLastError\s*\(', src))),
     None),
]


def scan_rules(src):
    """소스 코드에 대해 모든 룰 스캔.
    Returns list of (rule_id, name, found: bool, can_fix: bool)
    """
    results = []
    for rule_id, name, desc, checker, fixer in RULES:
        try:
            found = checker(src)
        except Exception:
            found = False
        results.append((rule_id, name, found, fixer is not None))
    return results


def apply_rules(src, selected_rule_ids):
    """선택된 룰의 fixer 적용.
    Returns (modified_src, applied_count, skipped_list)
    """
    applied = 0
    skipped = []
    for rule_id, name, desc, checker, fixer in RULES:
        if rule_id not in selected_rule_ids:
            continue
        if fixer is None:
            skipped.append(rule_id)
            continue
        try:
            if checker(src):
                src = fixer(src)
                applied += 1
        except Exception:
            skipped.append(rule_id)
    return src, applied, skipped


# ================================================================
# COMPILE_V1 통합: MetaEditor 컴파일 로그 기반 자동 수정
# ================================================================

def cv1_preprocess(path):
    """BOM 정리 + 유효기간 2099 패치."""
    with open(path, 'rb') as f:
        raw = f.read()
    changed = False
    if raw[:3] == b'\xef\xbb\xbf':
        inner = raw[3:]
        if b'\xef\xbb\xbf' in inner:
            raw = b'\xef\xbb\xbf' + inner.replace(b'\xef\xbb\xbf', b'')
            changed = True
    else:
        raw = b'\xef\xbb\xbf' + raw
        changed = True
    try:
        text = raw.decode('utf-8', errors='ignore')
        new_text = re.sub(
            r'"20(?:2[5-9]|[3-9]\d)\.\d{2}\.\d{2}"', '"2099.12.31"', text)
        if new_text != text:
            raw = new_text.encode('utf-8')
            if not raw.startswith(b'\xef\xbb\xbf'):
                raw = b'\xef\xbb\xbf' + raw
            changed = True
    except Exception:
        pass
    if changed:
        with open(path, 'wb') as f:
            f.write(raw)
    return changed


def cv1_compile_ea(me_exe, file_path, log_file):
    """MetaEditor 컴파일 실행."""
    cmd = f'"{me_exe}" /compile:"{file_path}" /log:"{log_file}"'
    try:
        subprocess.run(cmd, shell=True, capture_output=True, timeout=45,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        return False


def cv1_read_log(log_file):
    """컴파일 로그 읽기 (UTF-16/UTF-8/cp1252 자동 감지)."""
    if not os.path.exists(log_file):
        return ""
    for enc in ['utf-16', 'utf-8', 'cp1252', 'latin1']:
        try:
            with open(log_file, 'r', encoding=enc, errors='ignore') as f:
                content = f.read()
            if content.strip():
                return content
        except Exception:
            pass
    return ""


def cv1_parse_errors(log_content):
    """컴파일 오류/경고 파싱.
    Returns: [{"file", "line", "col", "type", "num", "message"}, ...]
    """
    errors = []
    pat = re.compile(
        r'(.+?)\((\d+),(\d+)\)\s*:\s*(error|warning)\s*(\d+)?:\s*(.+?)(?=\n|$)',
        re.IGNORECASE | re.MULTILINE)
    for m in pat.finditer(log_content):
        fname, line, col, etype, enum, msg = m.groups()
        errors.append({
            "file": os.path.basename(fname.strip()),
            "line": int(line),
            "col": int(col),
            "type": etype.upper(),
            "num": int(enum) if enum else 0,
            "message": msg.strip(),
        })
    return errors[:60]


def cv1_apply_patches(src):
    """글로벌 패치: AccountNumber 조건 제거 + ExpiryDate 2099 + NormalizeLots 주입."""
    src = src.replace('\ufeff', '')
    src = re.sub(r'AccountNumber\(\)\s*!=\s*[^\s)|&;]+', 'false',
                 src, flags=re.IGNORECASE)
    src = re.sub(r'Expiry_Date_Str\s*=\s*"[^"]+"',
                 'Expiry_Date_Str = "2099.12.31"', src, flags=re.IGNORECASE)
    src = re.sub(r"ExpiryDate\s*=\s*D'[^']+'",
                 "ExpiryDate = D'2099.12.31 23:59:59'",
                 src, flags=re.IGNORECASE)
    if 'double NormalizeLots(double lots)' not in src:
        src += (
            "\n// === Auto-injected by COMPILE_V1 ===\n"
            "double NormalizeLots(double lots)\n{\n"
            "   double lotStep=MarketInfo(Symbol(),MODE_LOTSTEP);\n"
            "   double minLot =MarketInfo(Symbol(),MODE_MINLOT);\n"
            "   double maxLot =MarketInfo(Symbol(),MODE_MAXLOT);\n"
            "   if(lotStep<=0)lotStep=0.01; if(minLot<=0)minLot=0.01;"
            " if(maxLot<=0)maxLot=100.0;\n"
            "   double n=MathFloor(lots/lotStep)*lotStep;\n"
            "   return NormalizeDouble(MathMax(minLot,MathMin(maxLot,n)),2);\n"
            "}\n")
    return src


def cv1_apply_targeted(src, errors):
    """컴파일 오류별 타깃 수정.
    - W62: 전역변수 숨김 -> 언더스코어 prefix
    - W43: 타입 변환 손실 -> NormalizeDouble
    - W83: 반환값 미확인 -> if 래핑
    Returns: (fixed_src, applied_list)
    """
    lines = src.splitlines()
    applied = []
    for err in sorted(errors, key=lambda x: x['line'], reverse=True):
        idx = err['line'] - 1
        if idx < 0 or idx >= len(lines):
            continue
        orig = lines[idx]
        code = str(err['num'])
        msg = err['message']

        if code == '62' and 'hides global' in msg:
            m = re.search(r"'(\w+)'", msg)
            if m:
                v = m.group(1)
                lines[idx] = orig.replace(v, f"_{v}", 1)
                applied.append(f"L{err['line']} W62: '{v}'->'_{v}'")

        elif code == '43' and 'loss of data' in msg:
            if '=' in orig and 'NormalizeDouble' not in orig:
                new = re.sub(
                    r'=\s*([A-Za-z_][A-Za-z0-9_().\[\]]*)\s*([,;])',
                    r'= (int)NormalizeDouble(\1,0)\2', orig)
                if new != orig:
                    lines[idx] = new
                    applied.append(f"L{err['line']} W43: NormalizeDouble")

        elif code == '83' and 'should be checked' in msg:
            m = re.search(r"'(\w+)'", msg)
            if m:
                fn = m.group(1)
                if f'{fn}(' in orig and 'if' not in orig:
                    new = re.sub(
                        rf'(\s*)({fn}\s*\([^)]*\))',
                        rf'\1if(!\2) Print("Failed:{fn}");', orig)
                    if new != orig:
                        lines[idx] = new
                        applied.append(f"L{err['line']} W83: {fn}()")

    return '\n'.join(lines), applied
