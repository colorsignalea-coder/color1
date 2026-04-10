"""
core/mql4_merger.py — EA Auto Master v6.0
==========================================
MQL4 모듈 합치기: 구조적 블록 파싱 + 함수 주입.
"""
import re


def parse_mq4_blocks(content):
    """MQL4 파일에서 구조적 블록 추출.
    Returns dict: params, buffers, funcs, globals, icustom, signals
    """
    blocks = {}

    # extern/input 파라미터
    params = re.findall(
        r'^\s*(?:extern|input)\s+(\w+)\s+(\w+)\s*=\s*([^;/\r\n]+)',
        content, re.MULTILINE)
    blocks["params"] = params

    # 인디케이터 버퍼
    buffers = re.findall(r'SetIndexBuffer\s*\(\s*\d+\s*,\s*(\w+)', content)
    blocks["buffers"] = buffers

    # 함수 정의 추출
    funcs = {}
    pat = re.compile(
        r'^((?:void|double|int|bool|string|datetime)\s+(\w+)\s*\([^)]*\)\s*\{)',
        re.MULTILINE)
    for m in pat.finditer(content):
        name = m.group(2)
        start = m.start()
        depth = 0
        i = m.start(1)
        while i < len(content):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    funcs[name] = content[start:i + 1]
                    break
            i += 1
    blocks["funcs"] = funcs

    # 전역 변수 (함수 외부)
    global_vars = re.findall(
        r'^(?!//|extern|input|#)\s*(?:double|int|bool|string|datetime)\s+(\w+)[^(][^;]*;',
        content, re.MULTILINE)
    blocks["globals"] = global_vars

    # iCustom 호출
    icustom = re.findall(r'iCustom\s*\(\s*[^,]+,\s*[^,]+,\s*"([^"]+)"', content)
    blocks["icustom"] = icustom

    # 시그널 패턴 감지
    sig_patterns = {
        "LRC": r"LinearReg|lrc|LRC|linear_reg",
        "Braid": r"braid|Braid|BRAID",
        "Channel": r"channel|Channel|CHANNEL",
        "ATR": r"\bATR\b|atr_|_atr",
        "RSI": r"\bRSI\b|rsi_|_rsi",
        "MACD": r"\bMACD\b|macd_",
        "BB": r"Bollinger|bollinger|BB_",
        "EMA": r"\bEMA\b|ema_|iMA\s*\(",
        "CCI": r"\bCCI\b|cci_",
        "Stoch": r"iStochastic|stoch",
    }
    detected = []
    for k, pat_str in sig_patterns.items():
        if re.search(pat_str, content):
            detected.append(k)
    blocks["signals"] = detected

    return blocks


def extract_module_for_inject(module_content, selected_funcs):
    """선택된 함수 + 관련 전역변수를 모듈에서 추출."""
    blocks = parse_mq4_blocks(module_content)
    inject_lines = [
        "\n// ===================================================",
        "// [MODULE INJECT] EA AUTO MASTER v6.0 자동 주입",
        "// ===================================================\n"
    ]
    for fn in selected_funcs:
        if fn in blocks["funcs"]:
            inject_lines.append(f"// -- 함수: {fn} --")
            inject_lines.append(blocks["funcs"][fn])
            inject_lines.append("")
    return "\n".join(inject_lines)


def inject_into_base(base_content, inject_code, inject_params):
    """베이스 EA에 모듈 코드 주입."""
    if inject_params:
        param_block = "\n// [모듈 파라미터]\n" + "\n".join(inject_params)
        m = re.search(r'^int\s+OnInit\s*\(', base_content, re.MULTILINE)
        if m:
            base_content = base_content[:m.start()] + param_block + "\n\n" + base_content[m.start():]
    base_content = base_content.rstrip() + "\n\n" + inject_code + "\n"
    return base_content
