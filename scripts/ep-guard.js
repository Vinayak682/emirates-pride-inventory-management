#!/usr/bin/env node
/**
 * EP Guard — Bug & Security Check Engine
 * Emirates Pride Integrated Operations Platform
 *
 * Trained on 15+ documented bugs and 16 security findings from CLAUDE.md + memory files.
 * Run before every git push. Exit 0 = pass. Exit 1 = fail (blocks push).
 *
 * Usage:
 *   node scripts/ep-guard.js              # check all HTML files
 *   node scripts/ep-guard.js --json       # output JSON report
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * KNOWLEDGE BASE (from CLAUDE.md incident log + memory files)
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * FAIL CHECKS (any failure blocks push):
 *  F1  async async double keyword — killed login TWICE (commits 15f2e52, e98cae8)
 *  F2  Inline <script> block must parse without SyntaxError (new Function test)
 *  F3  Key globals (doLogin, initApp, renderGrid) must be defined after parse
 *  F4  doLogin() must NOT gate on window.supabase (CDN block bug, commit d92ff1c)
 *  F5  No service role key in any HTML/JS file (security — client code is public)
 *  F6  No hardcoded 4-digit PIN values in STORES array (migrated to Supabase, commit 785306d)
 *
 * WARN CHECKS (allow push but print warning):
 *  W1  CDN scripts missing SRI integrity attribute
 *  W2  SOP_PASS / password constants — verify CLAUDE.md documents current value
 *  W3  Non-ASCII outside Arabic text regions (commit 38597ba Unicode corruption bug)
 *  W4  innerHTML with template literal containing variable (XSS risk)
 *  W5  localStorage not cleared on logout (shared device risk)
 *  W6  Supabase CDN has defer attribute (race condition risk)
 *  W7  openpyxl color hex without 8-char ARGB prefix in .py files (transparent text bug)
 *  W8  Any TODO/FIXME security notes left unresolved
 * ─────────────────────────────────────────────────────────────────────────────
 */

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

// ── Configuration ──────────────────────────────────────────────────────────
const ROOT = path.resolve(__dirname, '..');
const HTML_FILES = ['sop-portal.html', 'stock-register.html', 'index.html'];
const PY_FILES   = fs.readdirSync(ROOT).filter(f => f.endsWith('.py'));
const JSON_MODE  = process.argv.includes('--json');

// Known documented password values (update when CLAUDE.md documents a change)
const KNOWN_PASSWORDS = {
  'SOP_PASS':  'EPP@12345',   // changed from Vinayak@1998 on 5 Jun 2026 (commit aec9dcd)
};

// Key globals that must be defined after script parse
const REQUIRED_GLOBALS = {
  'sop-portal.html':    ['doLogin', 'initApp'],
  'stock-register.html': ['doLogin', 'renderGrid'],
  'index.html':          ['doLogin'],
};

// ── Result tracking ─────────────────────────────────────────────────────────
const results = [];
let failures = 0;
let warnings = 0;

function pass(id, label, detail = '') {
  results.push({ id, status: 'PASS', label, detail });
}
function fail(id, label, detail) {
  results.push({ id, status: 'FAIL', label, detail });
  failures++;
}
function warn(id, label, detail) {
  results.push({ id, status: 'WARN', label, detail });
  warnings++;
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function readFile(filename) {
  const fullPath = path.join(ROOT, filename);
  if (!fs.existsSync(fullPath)) return null;
  return fs.readFileSync(fullPath, 'utf8');
}

function extractInlineScript(html) {
  // Extract the LAST inline <script> block (the main app script)
  // These files have one large inline script at the bottom
  const start = html.lastIndexOf('<script>');
  const end   = html.lastIndexOf('</script>');
  if (start === -1 || end === -1 || end <= start) return null;
  return html.slice(start + 8, end);
}

function extractFunctionBody(script, funcName) {
  // Rough extraction of a function body for pattern checking
  const idx = script.indexOf(`function ${funcName}`);
  if (idx === -1) return null;
  let depth = 0;
  let inFunc = false;
  let start = -1;
  for (let i = idx; i < script.length; i++) {
    if (script[i] === '{') {
      if (!inFunc) { inFunc = true; start = i; }
      depth++;
    } else if (script[i] === '}') {
      depth--;
      if (inFunc && depth === 0) return script.slice(start, i + 1);
    }
  }
  return null;
}

// ── F1: async async double keyword ──────────────────────────────────────────
// This killed sop-portal.html login TWICE. A single grep catches it instantly.
function checkF1() {
  const label = 'async async double keyword';
  const found = [];

  for (const file of HTML_FILES) {
    const content = readFile(file);
    if (!content) continue;
    const lines = content.split('\n');
    lines.forEach((line, i) => {
      if (/async\s+async/.test(line)) {
        found.push(`${file}:${i + 1}  →  ${line.trim()}`);
      }
    });
  }

  if (found.length > 0) {
    fail('F1', label,
      'DOUBLE async KEYWORD FOUND — this kills the entire inline script, making doLogin undefined.\n' +
      'Fix: remove the duplicate "async" keyword.\n' +
      'Locations:\n  ' + found.join('\n  ')
    );
  } else {
    pass('F1', label);
  }
}

// ── F2: Script block parse test ─────────────────────────────────────────────
// Catches ALL syntax errors — mismatched quotes, stray backticks, etc.
const scriptCache = {};
function checkF2() {
  for (const file of HTML_FILES) {
    const content = readFile(file);
    if (!content) continue;

    const script = extractInlineScript(content);
    if (!script) {
      warn('F2', `Script extract (${file})`, 'No inline <script> block found — skipped');
      continue;
    }
    scriptCache[file] = script;

    try {
      new vm.Script(script, { filename: file });
      pass('F2', `Script parse (${file})`);
    } catch (e) {
      // Find the approximate line in the original HTML
      const scriptStartLine = content.slice(0, content.lastIndexOf('<script>')).split('\n').length;
      const errorLine = e.lineNumber ? scriptStartLine + e.lineNumber : '?';
      fail('F2', `Script parse (${file})`,
        `SyntaxError at line ~${errorLine}: ${e.message}\n` +
        'Fix: check the line above for mismatched quotes, stray backtick, or duplicate keyword.'
      );
    }
  }
}

// ── F3: Key globals defined after parse ─────────────────────────────────────
function checkF3() {
  for (const [file, globals] of Object.entries(REQUIRED_GLOBALS)) {
    const script = scriptCache[file];
    if (!script) continue; // F2 would have caught missing script

    const missing = globals.filter(g => {
      // Check function declaration OR const/let/var assignment
      const fnDecl  = new RegExp(`function\\s+${g}\\s*\\(`).test(script);
      const varDecl = new RegExp(`(?:const|let|var)\\s+${g}\\s*=`).test(script);
      return !fnDecl && !varDecl;
    });

    if (missing.length > 0) {
      fail('F3', `Key globals (${file})`,
        `Missing definitions: ${missing.join(', ')}\n` +
        'If the script failed to parse (F2), fix that first — these will reappear.'
      );
    } else {
      pass('F3', `Key globals (${file})`);
    }
  }
}

// ── F4: doLogin NOT CDN-gated ────────────────────────────────────────────────
// doLogin() must check password IMMEDIATELY. Supabase CDN must not gate auth.
// Bug history: CDN slow/failure = permanently locked login. Fixed d92ff1c, keep fixed.
function checkF4() {
  const label = 'doLogin not CDN-gated';
  const sopScript = scriptCache['sop-portal.html'];
  if (!sopScript) { warn('F4', label, 'sop-portal.html not parsed — skipped'); return; }

  const doLoginBody = extractFunctionBody(sopScript, 'doLogin');
  if (!doLoginBody) { warn('F4', label, 'doLogin function not found in sop-portal.html'); return; }

  // Check for the specific CDN-guard pattern that caused the bug
  const hasCdnGate = /if\s*\(\s*!window\.supabase\s*\)/.test(doLoginBody);
  // Also check if the check is BEFORE the password comparison
  const supabasePos = doLoginBody.indexOf('window.supabase');
  const passCheckPos = doLoginBody.search(/SOP_PASS|pwd\s*===/);

  if (hasCdnGate && supabasePos < passCheckPos) {
    fail('F4', label,
      'doLogin() has !window.supabase guard BEFORE password check.\n' +
      'This means a slow CDN = permanently locked login screen.\n' +
      'Fix: move CDN wait to initApp(). Password check is pure client-side — no network needed.\n' +
      'Reference: commit d92ff1c (this bug has recurred twice).'
    );
  } else {
    pass('F4', label);
  }
}

// ── F5: No service role key ──────────────────────────────────────────────────
// The Supabase service role key grants unrestricted DB access. Must NEVER be in HTML.
// The anon key is designed to be public — not flagged.
function checkF5() {
  const label = 'No service role key in HTML/JS';
  const found = [];

  // Service role JWT has "role":"service_role" in its payload
  const serviceRoleJwtPattern = /eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+/g;
  const serviceRoleTextPattern = /service_role|SERVICE_ROLE|service-role/;

  const filesToCheck = [...HTML_FILES, ...PY_FILES];
  for (const file of filesToCheck) {
    const ext = path.extname(file);
    if (ext !== '.html' && ext !== '.py' && ext !== '.js') continue;
    const content = readFile(file);
    if (!content) continue;

    // Check for service_role text keyword in JS/HTML (not in comments about security)
    if (serviceRoleTextPattern.test(content)) {
      // Exclude lines that are documentation/comments about why NOT to use it
      const lines = content.split('\n');
      lines.forEach((line, i) => {
        if (serviceRoleTextPattern.test(line) &&
            !line.trim().startsWith('//') &&
            !line.trim().startsWith('*') &&
            !line.trim().startsWith('#') &&
            !line.includes('NEVER') &&
            !line.includes('must not') &&
            !line.includes('do not')) {
          found.push(`${file}:${i + 1}  →  ${line.trim().slice(0, 80)}`);
        }
      });
    }

    // Check for JWT tokens that could be service role (base64 decode check)
    const jwtMatches = content.match(serviceRoleJwtPattern) || [];
    for (const jwt of jwtMatches) {
      try {
        const payload = JSON.parse(Buffer.from(jwt.split('.')[1], 'base64').toString());
        if (payload.role === 'service_role') {
          const lineNum = content.slice(0, content.indexOf(jwt)).split('\n').length;
          found.push(`${file}:${lineNum}  →  SERVICE ROLE JWT TOKEN DETECTED (${jwt.slice(0, 20)}...)`);
        }
      } catch (e) { /* not a valid JWT — skip */ }
    }
  }

  if (found.length > 0) {
    fail('F5', label,
      'SERVICE ROLE KEY DETECTED — this grants unrestricted DB access. REMOVE IMMEDIATELY.\n' +
      'The service role key belongs ONLY in local Python scripts or Supabase Edge Functions.\n' +
      'The anon key (eyJhbGci...anon...) is safe in HTML.\n' +
      'Locations:\n  ' + found.join('\n  ')
    );
  } else {
    pass('F5', label);
  }
}

// ── F6: No hardcoded PINs ────────────────────────────────────────────────────
// PINs were migrated to Supabase store_pins in commit 785306d.
// Hardcoded PINs in STORES array = security regression.
function checkF6() {
  const label = 'No hardcoded PINs in STORES array';
  const found = [];

  for (const file of HTML_FILES) {
    const script = scriptCache[file];
    if (!script) continue;

    // Look for pin: 'NNNN' or pin: "NNNN" patterns inside STORES-like arrays
    const pinPattern = /\bpin\s*:\s*['"](\d{4})['"]/g;
    let match;
    while ((match = pinPattern.exec(script)) !== null) {
      const lineNum = script.slice(0, match.index).split('\n').length;
      found.push(`${file}:${lineNum}  →  pin: '${match[1]}' (hardcoded PIN)`);
    }

    // Also check for MGR_PIN or WH_PIN constants
    const mgrPinPattern = /(?:MGR_PIN|WH_PIN|STORE_PIN)\s*=\s*['"](\d{3,6})['"]/g;
    while ((match = mgrPinPattern.exec(script)) !== null) {
      const lineNum = script.slice(0, match.index).split('\n').length;
      found.push(`${file}:${lineNum}  →  ${match[0].trim()} (hardcoded PIN constant)`);
    }
  }

  if (found.length > 0) {
    fail('F6', label,
      'HARDCODED PINs FOUND — PINs belong ONLY in Supabase store_pins table.\n' +
      'Use verify_store_pin() RPC (SECURITY DEFINER) — returns boolean only.\n' +
      'Reference: commit 785306d (PIN migration). See pin_table_setup.sql.\n' +
      'Locations:\n  ' + found.join('\n  ')
    );
  } else {
    pass('F6', label);
  }
}

// ── W1: CDN SRI hashes ───────────────────────────────────────────────────────
function checkW1() {
  const label = 'CDN scripts missing SRI integrity attribute';
  const found = [];

  for (const file of HTML_FILES) {
    const content = readFile(file);
    if (!content) continue;

    // Find all external script tags
    const scriptTagPattern = /<script[^>]+src=['"]https?:\/\/[^'"]+['"][^>]*>/g;
    const lines = content.split('\n');
    lines.forEach((line, i) => {
      if (scriptTagPattern.test(line) && !line.includes('integrity=')) {
        scriptTagPattern.lastIndex = 0; // reset regex
        found.push(`${file}:${i + 1}  →  ${line.trim().slice(0, 100)}`);
      }
      scriptTagPattern.lastIndex = 0;
    });
  }

  if (found.length > 0) {
    warn('W1', label,
      'CDN scripts without SRI hashes can be compromised if CDN is hacked.\n' +
      'Add: integrity="sha384-..." crossorigin="anonymous" to each CDN script tag.\n' +
      'Generate hashes at: https://www.srihash.org/\n' +
      'Locations:\n  ' + found.join('\n  ')
    );
  } else {
    pass('W1', label);
  }
}

// ── W2: Password constants documented ────────────────────────────────────────
function checkW2() {
  const label = 'Password constants match documented values';

  for (const file of HTML_FILES) {
    const script = scriptCache[file];
    if (!script) continue;

    for (const [constName, knownValue] of Object.entries(KNOWN_PASSWORDS)) {
      const pattern = new RegExp(`(?:const|let|var)\\s+${constName}\\s*=\\s*['"]([^'"]+)['"]`);
      const match = script.match(pattern);
      if (!match) continue;

      const actualValue = match[1];
      if (actualValue !== knownValue) {
        warn('W2', label,
          `${constName} in ${file} = '${actualValue}' but CLAUDE.md documents '${knownValue}'.\n` +
          'If password was intentionally changed, update CLAUDE.md + memory files to match.\n' +
          'Undocumented password changes lock out management.'
        );
      } else {
        pass('W2', `${constName} matches documented value (${file})`);
      }
    }
  }
}

// ── W3: Unicode corruption ────────────────────────────────────────────────────
// commit 38597ba fixed corrupted box-drawing / non-ASCII chars that broke display
function checkW3() {
  const label = 'Non-ASCII chars outside Arabic text regions';
  const suspiciousFiles = [];

  for (const file of HTML_FILES) {
    const content = readFile(file);
    if (!content) continue;

    // Count non-ASCII chars outside of font declarations and known safe zones
    let suspiciousCount = 0;
    const lines = content.split('\n');
    lines.forEach((line, i) => {
      // Skip font-face declarations, charset declarations, and known Arabic strings
      if (line.includes('@font-face') ||
          line.includes('charset') ||
          line.includes('font-family') ||
          line.includes('IBM Plex Sans Arabic') ||
          line.match(/[؀-ۿ]/)) return; // Arabic Unicode range — OK

      // Check for suspicious non-ASCII in JS/CSS (not Arabic)
      const nonAscii = line.match(/[^\x00-\x7F؀-ۿ]/g);
      if (nonAscii && nonAscii.length > 0) {
        // Ignore common Unicode that's intentional (bullet •, em dash —, etc.)
        const suspicious = nonAscii.filter(c => {
          const cp = c.codePointAt(0);
          // Box-drawing chars (U+2500-U+257F) and other control chars are suspicious
          return (cp >= 0x2500 && cp <= 0x27FF) || (cp >= 0x0080 && cp <= 0x009F);
        });
        suspiciousCount += suspicious.length;
      }
    });

    if (suspiciousCount > 0) {
      suspiciousFiles.push(`${file}: ${suspiciousCount} suspicious non-ASCII chars`);
    }
  }

  if (suspiciousFiles.length > 0) {
    warn('W3', label,
      'Potentially corrupted non-ASCII characters found (not Arabic).\n' +
      'Reference: commit 38597ba removed corrupted Unicode that broke display.\n' +
      'Run: grep -Pn "[\\x80-\\x9F\\x{2500}-\\x{257F}]" *.html to locate.\n' +
      suspiciousFiles.join('\n')
    );
  } else {
    pass('W3', label);
  }
}

// ── W4: innerHTML XSS risk ───────────────────────────────────────────────────
function checkW4() {
  const label = 'innerHTML with unescaped variable data (XSS risk)';
  const found = [];

  for (const file of HTML_FILES) {
    const script = scriptCache[file];
    if (!script) continue;

    // Look for innerHTML = `...${variable}...` where variable could be user data
    // Specifically look for patterns where store names, SKU names, or user input is interpolated
    const dangerPattern = /\.innerHTML\s*=\s*`[^`]*\$\{[^}]*(?:name|input|val|note|desc|remark|title|msg)[^}]*\}/gi;
    const lines = script.split('\n');
    lines.forEach((line, i) => {
      if (dangerPattern.test(line)) {
        dangerPattern.lastIndex = 0;
        found.push(`${file} script line ${i + 1}  →  ${line.trim().slice(0, 100)}`);
      }
      dangerPattern.lastIndex = 0;
    });
  }

  if (found.length > 0) {
    warn('W4', label,
      'innerHTML assignments with interpolated user data risk XSS.\n' +
      'Mitigation: use textContent for plain text, or sanitize with a whitelist.\n' +
      'Or use: .innerHTML = `...${escHtml(variable)}...`\n' +
      'Locations:\n  ' + found.join('\n  ')
    );
  } else {
    pass('W4', label);
  }
}

// ── W5: localStorage cleared on logout ──────────────────────────────────────
function checkW5() {
  const label = 'localStorage cleared on logout (shared device)';

  for (const file of HTML_FILES) {
    const script = scriptCache[file];
    if (!script) continue;

    const doLogoutBody = extractFunctionBody(script, 'doLogout');
    if (!doLogoutBody) continue;

    const hasLocalStorageClear = /localStorage\s*\.\s*(?:clear|removeItem)/.test(doLogoutBody);
    if (!hasLocalStorageClear) {
      warn('W5', label,
        `${file}: doLogout() does not call localStorage.clear() or removeItem().\n` +
        'Business data (PIN sessions, finance data) stays in browser after logout.\n' +
        'Risk: shared iPads in stores — next person sees previous session data.\n' +
        'Fix: add localStorage.clear() or selective removeItem() in doLogout().'
      );
    } else {
      pass('W5', label + ` (${file})`);
    }
  }
}

// ── W6: Supabase CDN defer attribute ─────────────────────────────────────────
function checkW6() {
  const label = 'Supabase CDN defer attribute risk';

  for (const file of HTML_FILES) {
    const content = readFile(file);
    if (!content) continue;

    const cdnLinePattern = /<script[^>]+supabase[^>]+defer[^>]*>/;
    if (cdnLinePattern.test(content)) {
      // This is only a warning — not a fail — because initApp() now handles lazy init
      warn('W6', label,
        `${file}: Supabase CDN has defer attribute — script loads after DOM.\n` +
        'If initApp() does not wait for window.supabase, features may fail silently.\n' +
        'Current fix (commit d92ff1c): initApp() polls for window.supabase — verify this is in place.'
      );
    } else {
      pass('W6', label + ` (${file})`);
    }
  }
}

// ── W7: openpyxl ARGB colors ─────────────────────────────────────────────────
// openpyxl requires 8-char ARGB (e.g. FF0000FF). 6-char hex = alpha=00 = transparent.
function checkW7() {
  const label = 'openpyxl colors must be 8-char ARGB (transparent text bug)';
  const found = [];

  for (const file of PY_FILES) {
    const content = readFile(file);
    if (!content) continue;
    if (!content.includes('openpyxl') && !content.includes('PatternFill') && !content.includes('Font(')) continue;

    const lines = content.split('\n');
    lines.forEach((line, i) => {
      // Look for hex colors that are 6 chars (no alpha prefix)
      const sixCharPattern = /(?:fgColor|bgColor|color)\s*=\s*['"]([0-9A-Fa-f]{6})['"]/g;
      let match;
      while ((match = sixCharPattern.exec(line)) !== null) {
        found.push(`${file}:${i + 1}  →  color='${match[1]}' should be 'FF${match[1]}' (add FF alpha prefix)`);
      }
    });
  }

  if (found.length > 0) {
    warn('W7', label,
      '6-char hex in openpyxl = alpha=00 = transparent (invisible text/cells).\n' +
      'Fix: prepend "FF" to every 6-char color: "C9A84C" → "FFC9A84C"\n' +
      'Locations:\n  ' + found.join('\n  ')
    );
  } else {
    pass('W7', label);
  }
}

// ── W8: Security TODO/FIXME notes ────────────────────────────────────────────
function checkW8() {
  const label = 'Unresolved security TODO/FIXME';
  const found = [];

  const securityKeywords = /TODO.*(?:security|auth|pin|password|key|rls|xss|inject)/i;
  const fixmeKeywords = /FIXME.*(?:security|auth|pin|password|key|rls)/i;

  for (const file of HTML_FILES) {
    const content = readFile(file);
    if (!content) continue;

    content.split('\n').forEach((line, i) => {
      if (securityKeywords.test(line) || fixmeKeywords.test(line)) {
        found.push(`${file}:${i + 1}  →  ${line.trim().slice(0, 80)}`);
      }
    });
  }

  if (found.length > 0) {
    warn('W8', label,
      'Security-related TODO/FIXME comments found — review before shipping:\n  ' +
      found.join('\n  ')
    );
  } else {
    pass('W8', label);
  }
}

// ── Report renderer ──────────────────────────────────────────────────────────
function printReport() {
  if (JSON_MODE) {
    const report = {
      timestamp: new Date().toISOString(),
      summary: { total: results.length, failures, warnings, passed: results.length - failures - warnings },
      result: failures === 0 ? 'PASS' : 'FAIL',
      checks: results,
    };
    console.log(JSON.stringify(report, null, 2));
    // Write artifact for GitHub Actions
    fs.writeFileSync(path.join(ROOT, 'ep-guard-report.json'), JSON.stringify(report, null, 2));
    return;
  }

  const LINE = '═'.repeat(60);
  const THIN = '─'.repeat(60);

  console.log('\n' + LINE);
  console.log('  EP GUARD — Bug & Security Check');
  console.log('  Emirates Pride Integrated Operations Platform');
  console.log('  Files: sop-portal.html · stock-register.html');
  console.log(LINE + '\n');

  // Write GitHub Actions step summary if running in Actions
  const summaryLines = [];
  if (process.env.GITHUB_STEP_SUMMARY) {
    summaryLines.push('# EP Guard — Bug & Security Check\n');
    summaryLines.push('| Status | Check | Detail |\n|--------|-------|--------|\n');
  }

  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : r.status === 'FAIL' ? '❌' : '⚠️ ';
    const label = `${r.id.padEnd(3)} ${r.label}`;
    const dots  = '.'.repeat(Math.max(1, 46 - label.length));

    if (r.status === 'PASS') {
      console.log(`${icon}  ${label} ${dots} PASS`);
    } else if (r.status === 'FAIL') {
      console.log(`\n${icon}  ${label} ${dots} FAIL`);
      r.detail.split('\n').forEach(l => console.log(`       ${l}`));
      console.log();
    } else {
      console.log(`\n${icon}  ${label} ${dots} WARN`);
      r.detail.split('\n').forEach(l => console.log(`       ${l}`));
      console.log();
    }

    if (process.env.GITHUB_STEP_SUMMARY) {
      const statusEmoji = r.status === 'PASS' ? '✅' : r.status === 'FAIL' ? '❌' : '⚠️';
      summaryLines.push(`| ${statusEmoji} ${r.status} | **${r.id}** ${r.label} | ${(r.detail || '').replace(/\n/g, '<br>').slice(0, 200)} |\n`);
    }
  }

  console.log(THIN);
  const resultIcon = failures === 0 ? '✅' : '❌';
  const resultText = failures === 0
    ? `PASS  (${warnings} warning${warnings !== 1 ? 's' : ''})`
    : `FAIL  (${failures} failure${failures !== 1 ? 's' : ''}, ${warnings} warning${warnings !== 1 ? 's' : ''})`;
  console.log(`  ${resultIcon}  RESULT: ${resultText}`);
  console.log(LINE + '\n');

  if (failures > 0) {
    console.log('  Push BLOCKED. Fix all ❌ failures before pushing.\n');
  }

  if (process.env.GITHUB_STEP_SUMMARY) {
    summaryLines.push(`\n## Result: ${failures === 0 ? '✅ PASS' : '❌ FAIL'}\n`);
    summaryLines.push(`${failures} failure(s), ${warnings} warning(s)\n`);
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, summaryLines.join(''));
  }

  // Write JSON artifact regardless of mode
  try {
    const report = {
      timestamp: new Date().toISOString(),
      summary: { total: results.length, failures, warnings, passed: results.filter(r => r.status === 'PASS').length },
      result: failures === 0 ? 'PASS' : 'FAIL',
      checks: results,
    };
    fs.writeFileSync(path.join(ROOT, 'ep-guard-report.json'), JSON.stringify(report, null, 2));
  } catch (e) { /* non-fatal */ }
}

// ── Main ─────────────────────────────────────────────────────────────────────
function main() {
  // FAIL checks — run in order, build script cache
  checkF1();
  checkF2();
  checkF3();
  checkF4();
  checkF5();
  checkF6();

  // WARN checks
  checkW1();
  checkW2();
  checkW3();
  checkW4();
  checkW5();
  checkW6();
  checkW7();
  checkW8();

  printReport();
  process.exit(failures > 0 ? 1 : 0);
}

main();
