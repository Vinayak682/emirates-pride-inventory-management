#!/usr/bin/env python3
"""
EP Guard — Bug & Security Check Engine (Python edition)
Emirates Pride Integrated Operations Platform

Trained on 15+ documented bugs and 16 security findings from CLAUDE.md + memory files.
Run before every git push. Exit 0 = pass. Exit 1 = fail.

Usage:
    python scripts/ep-guard.py           # check all HTML files
    python scripts/ep-guard.py --json    # output JSON report

Incident history baked in:
  F1  async async (killed login TWICE — commits 15f2e52, e98cae8)
  F2  Script parse error detection (grep-based; full JS parse in ep-guard.js)
  F3  Key globals must be defined (doLogin, initApp, renderGrid)
  F4  doLogin NOT CDN-gated on window.supabase (recurred, commit d92ff1c)
  F5  No service role key in HTML/JS
  F6  No hardcoded PINs (migrated to Supabase, commit 785306d)
  W1  CDN SRI hashes missing
  W2  Password constants documented in CLAUDE.md
  W3  Unicode corruption outside Arabic regions
  W4  innerHTML with unescaped variable data
  W5  localStorage cleared on logout
  W6  Supabase CDN defer attribute
  W7  openpyxl 6-char hex colors (transparent text bug)
  W8  Security TODO/FIXME notes
"""

import os
import re
import sys
import json
import io

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_FILES = ['sop-portal.html', 'stock-register.html', 'index.html']
PY_FILES = [f for f in os.listdir(ROOT) if f.endswith('.py')]
JSON_MODE = '--json' in sys.argv

# Documented password values — update when CLAUDE.md documents a change
KNOWN_PASSWORDS = {
    'SOP_PASS': 'EPP@12345',   # changed from Vinayak@1998 on 5 Jun 2026 (commit aec9dcd)
}

# Key globals per file
REQUIRED_GLOBALS = {
    'sop-portal.html':     ['doLogin', 'initApp'],
    'stock-register.html': ['doLogin', 'renderStores'],  # renderGrid was the old name; now renderStores
    'index.html':          ['loginV'],                   # index.html uses loginV() not doLogin()
}

results = []
failures = 0
warnings = 0


def _pass(id_, label, detail=''):
    results.append({'id': id_, 'status': 'PASS', 'label': label, 'detail': detail})


def _fail(id_, label, detail):
    global failures
    results.append({'id': id_, 'status': 'FAIL', 'label': label, 'detail': detail})
    failures += 1


def _warn(id_, label, detail):
    global warnings
    results.append({'id': id_, 'status': 'WARN', 'label': label, 'detail': detail})
    warnings += 1


def read_file(filename):
    path = os.path.join(ROOT, filename)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def extract_inline_script(html):
    """Extract the LARGEST inline <script> block — always the main app script."""
    best = None
    search_from = 0
    while True:
        start = html.find('<script>', search_from)
        if start == -1:
            break
        end = html.find('</script>', start)
        if end == -1:
            break
        block = html[start + 8:end]
        if best is None or len(block) > len(best):
            best = block
        search_from = end + 9
    return best


def extract_function_body(script, func_name):
    """Rough extraction of a function body by brace counting."""
    idx = script.find(f'function {func_name}')
    if idx == -1:
        return None
    depth = 0
    in_func = False
    start = -1
    for i in range(idx, len(script)):
        if script[i] == '{':
            if not in_func:
                in_func = True
                start = i
            depth += 1
        elif script[i] == '}':
            depth -= 1
            if in_func and depth == 0:
                return script[start:i + 1]
    return None


script_cache = {}


# ── F1: async async double keyword ──────────────────────────────────────────
def check_f1():
    label = 'async async double keyword'
    found = []
    for filename in HTML_FILES:
        content = read_file(filename)
        if not content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(r'async\s+async', line):
                found.append(f'{filename}:{i}  →  {line.strip()[:100]}')
    if found:
        _fail('F1', label,
              'DOUBLE async KEYWORD FOUND — kills the entire inline script.\n'
              'Every function becomes undefined. Login throws ReferenceError.\n'
              'This happened TWICE (commits 15f2e52, e98cae8). Fix: remove duplicate async.\n'
              'Locations:\n  ' + '\n  '.join(found))
    else:
        _pass('F1', label)


# ── F2: Script block patterns (Python best-effort) ───────────────────────────
def check_f2():
    """
    Python can't run JS via new Function(). We check for the most common
    syntax-breaking patterns we've seen in this codebase.
    Note: ep-guard.js on GitHub Actions does a full JS parse.
    """
    for filename in HTML_FILES:
        content = read_file(filename)
        if not content:
            continue
        script = extract_inline_script(content)
        if not script:
            _warn('F2', f'Script extract ({filename})', 'No inline <script> found — skipped')
            continue
        script_cache[filename] = script

        issues = []

        # Unmatched template literal backticks (rough check)
        # Count backticks outside strings/comments is complex; just flag triple-backtick patterns
        if '```' in script:
            issues.append('Triple backtick found — likely a Markdown fragment in JS code')

        # Common paste error: console.log( without closing paren on same line followed by function def
        # (too noisy to check reliably — skip)

        if issues:
            _warn('F2', f'Script patterns ({filename})',
                  'Possible syntax issues found (Python check — run node scripts/ep-guard.js for full parse):\n  ' +
                  '\n  '.join(issues))
        else:
            _pass('F2', f'Script patterns ({filename}) — run ep-guard.js for full JS parse')


# ── F3: Key globals defined ───────────────────────────────────────────────────
def check_f3():
    for filename, globals_list in REQUIRED_GLOBALS.items():
        script = script_cache.get(filename)
        if not script:
            continue
        missing = []
        for g in globals_list:
            fn_decl  = bool(re.search(rf'function\s+{re.escape(g)}\s*\(', script))
            var_decl = bool(re.search(rf'(?:const|let|var)\s+{re.escape(g)}\s*=', script))
            if not fn_decl and not var_decl:
                missing.append(g)
        if missing:
            _fail('F3', f'Key globals ({filename})',
                  f'Missing: {", ".join(missing)}\n'
                  'These must be defined as functions or const assignments at module scope.')
        else:
            _pass('F3', f'Key globals ({filename})')


# ── F4: doLogin not CDN-gated ─────────────────────────────────────────────────
def check_f4():
    label = 'doLogin not CDN-gated'
    script = script_cache.get('sop-portal.html')
    if not script:
        _warn('F4', label, 'sop-portal.html not parsed — skipped')
        return

    body = extract_function_body(script, 'doLogin')
    if not body:
        _warn('F4', label, 'doLogin function not found in sop-portal.html')
        return

    has_cdn_gate = bool(re.search(r'if\s*\(\s*!window\.supabase\s*\)', body))
    supabase_pos = body.find('window.supabase')
    pass_pos = body.find('SOP_PASS') if 'SOP_PASS' in body else body.find('pwd')

    if has_cdn_gate and supabase_pos != -1 and pass_pos != -1 and supabase_pos < pass_pos:
        _fail('F4', label,
              'doLogin() has !window.supabase guard BEFORE password check.\n'
              'Slow/offline CDN = permanently locked login screen.\n'
              'Fix: password check needs NO network. Move CDN wait to initApp() only.\n'
              'Reference: commit d92ff1c (bug recurred twice).')
    else:
        _pass('F4', label)


# ── F5: No service role key ───────────────────────────────────────────────────
def check_f5():
    label = 'No service role key in HTML/JS'
    found = []
    service_role_text = re.compile(r'service_role|SERVICE_ROLE', re.IGNORECASE)
    jwt_pattern = re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+')

    for filename in HTML_FILES + PY_FILES:
        content = read_file(filename)
        if not content:
            continue

        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # Match service_role keyword but exclude documentation comments
            if service_role_text.search(line):
                if not any(stripped.startswith(c) for c in ('//', '*', '#', '<!--')):
                    if not any(kw in line for kw in ('NEVER', 'must not', 'do not', 'not in', 'belongs',
                                                      'YOUR_SERVICE_ROLE_KEY', 'placeholder', 'Replace with')):
                        found.append(f'{filename}:{i}  →  {stripped[:80]}')

        # Check for service role JWT
        for match in jwt_pattern.finditer(content):
            jwt = match.group()
            try:
                import base64
                payload_b64 = jwt.split('.')[1]
                # Pad base64
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64).decode('utf-8', errors='ignore'))
                if payload.get('role') == 'service_role':
                    line_num = content[:match.start()].count('\n') + 1
                    found.append(f'{filename}:{line_num}  →  SERVICE ROLE JWT TOKEN ({jwt[:20]}...)')
            except Exception:
                pass

    if found:
        _fail('F5', label,
              'SERVICE ROLE KEY DETECTED — grants unrestricted DB access. REMOVE IMMEDIATELY.\n'
              'The service role key must only appear in local Python scripts (gitignored) or Edge Functions.\n'
              'Locations:\n  ' + '\n  '.join(found))
    else:
        _pass('F5', label)


# ── F6: No hardcoded PINs ─────────────────────────────────────────────────────
def check_f6():
    label = 'No hardcoded PINs in STORES array'
    found = []
    pin_pattern = re.compile(r'\bpin\s*:\s*[\'"](\d{4})[\'"]')
    const_pattern = re.compile(r'(?:MGR_PIN|WH_PIN|STORE_PIN)\s*=\s*[\'"](\d{3,6})[\'"]')

    for filename in HTML_FILES:
        script = script_cache.get(filename)
        if not script:
            continue
        for i, line in enumerate(script.splitlines(), 1):
            if pin_pattern.search(line):
                found.append(f'{filename} script:{i}  →  {line.strip()[:80]}')
            if const_pattern.search(line):
                found.append(f'{filename} script:{i}  →  {line.strip()[:80]}')

    if found:
        _fail('F6', label,
              'HARDCODED PINs — PINs belong only in Supabase store_pins table.\n'
              'Use verify_store_pin() RPC (commit 785306d).\n'
              'Locations:\n  ' + '\n  '.join(found))
    else:
        _pass('F6', label)


# ── W1: CDN SRI hashes ────────────────────────────────────────────────────────
def check_w1():
    label = 'CDN scripts missing SRI integrity attribute'
    found = []
    script_tag = re.compile(r'<script[^>]+src=[\'"]https?://[^\'"]+[\'"][^>]*>', re.IGNORECASE)

    for filename in HTML_FILES:
        content = read_file(filename)
        if not content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if script_tag.search(line) and 'integrity=' not in line:
                found.append(f'{filename}:{i}  →  {line.strip()[:100]}')

    if found:
        _warn('W1', label,
              'CDN scripts without SRI hashes — compromised CDN = full JS injection.\n'
              'Add: integrity="sha384-..." crossorigin="anonymous"\n'
              'Generate: https://www.srihash.org/\n'
              'Locations:\n  ' + '\n  '.join(found))
    else:
        _pass('W1', label)


# ── W2: Password constants documented ────────────────────────────────────────
def check_w2():
    label = 'Password constants match documented values'
    for filename in HTML_FILES:
        script = script_cache.get(filename)
        if not script:
            continue
        for const_name, known_value in KNOWN_PASSWORDS.items():
            pattern = re.compile(rf'(?:const|let|var)\s+{re.escape(const_name)}\s*=\s*[\'"]([^\'"]+)[\'"]')
            m = pattern.search(script)
            if not m:
                continue
            actual = m.group(1)
            if actual != known_value:
                _warn('W2', label,
                      f'{const_name} in {filename} = \'{actual}\' but CLAUDE.md documents \'{known_value}\'.\n'
                      'If intentionally changed, update CLAUDE.md immediately (same commit).\n'
                      'Undocumented changes lock out management.')
            else:
                _pass('W2', f'{const_name} matches documented value ({filename})')


# ── W3: Unicode corruption ────────────────────────────────────────────────────
def check_w3():
    label = 'Non-ASCII outside Arabic text regions'
    suspect_files = []

    for filename in HTML_FILES:
        fpath = os.path.join(ROOT, filename)
        if not os.path.exists(fpath):
            continue
        # Read raw bytes. C1 control chars (U+0080-U+009F) in UTF-8 are encoded as
        # 0xC2 followed by 0x80-0x9F. These are NEVER valid in HTML5 and were the
        # root cause of the commit 38597ba corruption bug.
        # Box-drawing chars and emoji are intentional in these files — only flag C1.
        with open(fpath, 'rb') as f:
            raw_bytes = f.read()
        c1_count = 0
        for i in range(len(raw_bytes) - 1):
            if raw_bytes[i] == 0xC2 and 0x80 <= raw_bytes[i + 1] <= 0x9F:
                c1_count += 1
        if c1_count > 0:
            suspect_files.append(f'{filename}: {c1_count} C1 control chars (U+0080-U+009F)')

    if suspect_files:
        _warn('W3', label,
              'C1 control characters found — indicates UTF-8 corruption (commit 38597ba).\n'
              'These are never valid in HTML5. Fix: strip with editor or re-save as UTF-8.\n' +
              '\n'.join(suspect_files))
    else:
        _pass('W3', label)

def check_w4():
    label = 'innerHTML with unescaped variable data (XSS risk)'
    found = []
    pattern = re.compile(
        r'\.innerHTML\s*=\s*`[^`]*\$\{[^}]*(?:name|input|val|note|desc|remark|title|msg)[^}]*\}',
        re.IGNORECASE
    )
    for filename in HTML_FILES:
        script = script_cache.get(filename)
        if not script:
            continue
        for i, line in enumerate(script.splitlines(), 1):
            if pattern.search(line):
                found.append(f'{filename} script:{i}  →  {line.strip()[:100]}')

    if found:
        _warn('W4', label,
              'innerHTML with interpolated user data = XSS risk.\n'
              'Fix: escape values with escHtml(val) or use textContent.\n'
              'Locations:\n  ' + '\n  '.join(found))
    else:
        _pass('W4', label)


# ── W5: localStorage cleared on logout ───────────────────────────────────────
def check_w5():
    label = 'localStorage cleared on logout (shared device)'
    for filename in HTML_FILES:
        script = script_cache.get(filename)
        if not script:
            continue
        body = extract_function_body(script, 'doLogout')
        if not body:
            continue
        if not re.search(r'localStorage\s*\.\s*(?:clear|removeItem)', body):
            _warn('W5', label,
                  f'{filename}: doLogout() does not clear localStorage.\n'
                  'Risk: shared iPads — next person sees previous session data.\n'
                  'Fix: add localStorage.clear() in doLogout().')
        else:
            _pass('W5', f'{label} ({filename})')


# ── W6: Supabase CDN defer ────────────────────────────────────────────────────
def check_w6():
    label = 'Supabase CDN defer attribute risk'
    for filename in HTML_FILES:
        content = read_file(filename)
        if not content:
            continue
        if re.search(r'<script[^>]+supabase[^>]+defer', content, re.IGNORECASE):
            _warn('W6', label,
                  f'{filename}: Supabase CDN has defer — script loads after DOM.\n'
                  'Verify initApp() polls for window.supabase before using it.\n'
                  'Pattern from commit d92ff1c.')
        else:
            _pass('W6', f'{label} ({filename})')


# ── W7: openpyxl ARGB colors ─────────────────────────────────────────────────
def check_w7():
    label = 'openpyxl colors must be 8-char ARGB (transparent text bug)'
    found = []
    six_char = re.compile(r'(?:fgColor|bgColor|color)\s*=\s*[\'"]([0-9A-Fa-f]{6})[\'"]')

    for filename in PY_FILES:
        content = read_file(filename)
        if not content:
            continue
        if 'openpyxl' not in content and 'PatternFill' not in content and 'Font(' not in content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            for m in six_char.finditer(line):
                found.append(f"{filename}:{i}  →  color='{m.group(1)}' → use 'FF{m.group(1)}'")

    if found:
        _warn('W7', label,
              '6-char hex in openpyxl = alpha=00 = invisible text.\n'
              'Prepend "FF": "C9A84C" → "FFC9A84C"\n'
              'Locations:\n  ' + '\n  '.join(found))
    else:
        _pass('W7', label)


# ── W8: Security TODO/FIXME ───────────────────────────────────────────────────
def check_w8():
    label = 'Unresolved security TODO/FIXME'
    found = []
    # Only match actual comment lines — not variable/property names containing these words
    comment_line = re.compile(r'^\s*(?://|/\*|\*|#|<!--)')
    pattern = re.compile(
        r'\b(?:TODO|FIXME)\b.*(?:security|auth|pin|password|key|rls|xss|inject)',
        re.IGNORECASE
    )
    for filename in HTML_FILES:
        content = read_file(filename)
        if not content:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if pattern.search(line) and comment_line.match(line):
                found.append(f'{filename}:{i}  →  {line.strip()[:80]}')

    if found:
        _warn('W8', label,
              'Security-related TODO/FIXME comments:\n  ' + '\n  '.join(found))
    else:
        _pass('W8', label)


# ── Report ────────────────────────────────────────────────────────────────────
def print_report():
    if JSON_MODE:
        report = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'summary': {
                'total': len(results),
                'failures': failures,
                'warnings': warnings,
                'passed': sum(1 for r in results if r['status'] == 'PASS'),
            },
            'result': 'PASS' if failures == 0 else 'FAIL',
            'checks': results,
        }
        print(json.dumps(report, indent=2))
        with open(os.path.join(ROOT, 'ep-guard-report.json'), 'w') as f:
            json.dump(report, f, indent=2)
        return

    LINE = '═' * 60
    THIN = '─' * 60

    print(f'\n{LINE}')
    print('  EP GUARD — Bug & Security Check')
    print('  Emirates Pride Integrated Operations Platform')
    print('  Files: sop-portal.html · stock-register.html')
    print(f'{LINE}\n')

    for r in results:
        icon = '✅' if r['status'] == 'PASS' else ('❌' if r['status'] == 'FAIL' else '⚠️ ')
        label_str = f"{r['id']:<3} {r['label']}"
        dots = '.' * max(1, 46 - len(label_str))

        if r['status'] == 'PASS':
            print(f"{icon}  {label_str} {dots} PASS")
        else:
            print(f"\n{icon}  {label_str} {dots} {r['status']}")
            for line in r['detail'].split('\n'):
                print(f"       {line}")
            print()

    print(THIN)
    result_icon = '✅' if failures == 0 else '❌'
    warn_s = '' if warnings == 1 else 's'
    fail_s = '' if failures == 1 else 's'
    if failures == 0:
        result_text = f'PASS  ({warnings} warning{warn_s})'
    else:
        result_text = f'FAIL  ({failures} failure{fail_s}, {warnings} warning{warn_s})'

    print(f'  {result_icon}  RESULT: {result_text}')
    print(f'{LINE}\n')

    if failures > 0:
        print('  Push BLOCKED. Fix all ❌ failures before pushing.\n')

    # Write JSON artifact
    try:
        report = {
            'summary': {'failures': failures, 'warnings': warnings},
            'result': 'PASS' if failures == 0 else 'FAIL',
            'checks': results,
        }
        with open(os.path.join(ROOT, 'ep-guard-report.json'), 'w') as f:
            json.dump(report, f, indent=2)
    except Exception:
        pass


def main():
    # FAIL checks
    check_f1()
    check_f2()
    check_f3()
    check_f4()
    check_f5()
    check_f6()
    # WARN checks
    check_w1()
    check_w2()
    check_w3()
    check_w4()
    check_w5()
    check_w6()
    check_w7()
    check_w8()

    print_report()
    sys.exit(1 if failures > 0 else 0)


if __name__ == '__main__':
    main()
