# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

### Local Development
No build step. All frontend files are plain HTML/CSS/JS — open directly in a browser or serve locally:
```bash
python3 -m http.server 8080
# then open http://localhost:8080/stock-register.html
```

### Monthly Sales Upload (Python)
```bash
python3 monthly_sales_upload.py path/to/April_2026_Sales.xlsx
```
Requires: `openpyxl`, `requests` (`pip install openpyxl requests`).  
**Set `SUPABASE_SERVICE_KEY`** in the script before running — the placeholder `YOUR_SERVICE_ROLE_KEY_HERE` must be replaced with the actual service role key (never commit this).

### OCR Stock Upload (Python)
```bash
python3 stock_ocr_api.py
```
Separate API server for the barcode/OCR scanner workflow (`stock-ocr-upload.html`).

### Supabase SQL — Execution Order (one-time setup)
Run these in Supabase SQL Editor in this order:
1. `create_tables.sql` — core tables (`sales_history`, `benchmarks_cache`, `transfer_history`, `data_uploads_log`)
2. `pin_table_setup.sql` — `store_pins` table + `verify_store_pin()` RPC (SECURITY DEFINER)
3. `security_setup.sql` — `store_sessions`, `audit_log`, `security_config`, Postgres trigger
4. `am_requests_setup.sql` — `am_weekly_requests`, `am_feedback_sessions`, `am_issues_log`
5. `am_requests_migration.sql` — adds `fulfilled_items`, `approval_remarks`, `edit_history` columns
6. `scanner_db_setup.sql` — barcode scanner tables

### Supabase Edge Function
```bash
supabase functions deploy security-alert
# Set secrets:
supabase secrets set RESEND_API_KEY=xxx ALERT_EMAIL=xxx
```
Source: `supabase/functions/security-alert/index.ts`

### Deploy
Push to `main` → GitHub Pages auto-deploys within ~60 seconds. No CI/CD config needed.

---

## Architecture

### Request / Data Flow
```
Browser (GitHub Pages static HTML)
  └── Supabase REST API (anon key, client-side)
        ├── verify_store_pin() RPC  →  boolean only (PIN never exposed)
        ├── stock_cells table        →  read/write per store+day
        ├── sales_history            →  17K+ rows, read-only for client
        ├── am_weekly_requests       →  JSONB items column
        └── audit_log                →  written by Postgres trigger + JS
              └── anomaly detected → supabase/functions/security-alert → Resend email
```

### File Roles
| File | Role | Size |
|------|------|------|
| `stock-register.html` | Core daily operations app — all store/MGR/WH logic in one file | 799 KB |
| `index.html` | Operations 2.0 — older GRN/transfer/tester entry app | 126 KB |
| `sop-portal.html` | S&OP reporting portal — 8 tabs, queries `sales_history` | 400 KB |
| `am-stock-request.html` | Mobile AM request form — 4-screen flow, 163 SKUs bilingual | 51 KB |
| `stock-register-REGION-SPECIFIC.html` | Variant with per-region filtering | 515 KB |

All HTML files are self-contained — styles, scripts, and data (SKU catalogue) are inline. There is no shared JS module or CSS file.

### stock-register.html — Internal Structure
The file is ~18,000 lines. Key sections in order:
1. **CSS** (`:root` tokens → layout → grid → panels → modals)
2. **HTML shell** — login overlay → app topbar → day tabs → product grid → all slide-up panels
3. **JS constants** — `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `STORES[]` array (35+ entries with store codes, names, AM assignment)
4. **Auth layer** — `doLogin()` (async RPC), `submitMgrPin()`, session flags (`isAmSession`, `amManagedStores`)
5. **Grid rendering** — `renderGrid()`, `renderDay()`, cell update functions
6. **Supabase sync** — `loadDayData()`, `saveCell()`, `loadAllStores()`
7. **Security module** — `_secCreateSession()`, `_secQAudit()`, anomaly detection, email alert cooldown
8. **Manager panels** — dashboard, all-stores panel, AM Hub (requests/feedback/issues/TODO tabs)
9. **Export functions** — CSV, Excel (SheetJS), PDF (print window)
10. **Demand Planning panel** — reads `benchmarks_cache`, reorder priority logic

### Login / Access Control
- Store staff → PIN verified via `verify_store_pin()` RPC → session flag `currentStore`
- AM login → sets `isAmSession = true`, `amManagedStores[]` filtered to their stores only
- MGR (PIN 9999) → full access; WH (PIN 8888) → warehouse-only panel
- Demand Planning panel: double-guarded — button hidden + entry function blocked for AM sessions
- S&OP portal (`sop-portal.html`) and FG manager portal use separate password constant (`Vinayak@1998`), no Supabase auth

### Supabase Patterns
```js
// Standard query
const { data, error } = await supabase
  .from('table_name')
  .select('*')
  .eq('column', value)
  .limit(5000);

// Upsert (used for all stock cell writes)
await supabase.from('stock_cells').upsert(payload, { onConflict: 'store_code,day,sku' });

// RPC (PIN verification)
const { data } = await _SBC.rpc('verify_store_pin', { p_code, p_pin });
```

### Design System (enforced — do not deviate)
```css
--gold-bar: #6B5B35   /* ALL dark headers, topbars, panel headers */
--gold:     #C9A84C   /* Borders, active states */
--page:     #FFFFFF   /* Page background */
--gold-pale:#F5F2EC   /* Card tints, alternating rows */
```
Fonts: **Cormorant Garamond** (display/numbers) · **Montserrat** (body/UI) · **IBM Plex Mono** (codes/timestamps) · **IBM Plex Sans Arabic** (Arabic text).

**No dark backgrounds anywhere** — including login screens. The only exception is the executive login in `stock-register.html` which uses a dark theme by deliberate design decision (documented in CLAUDE.md session log Session 8).

### SKU Data
SKU catalogue (253 SKUs) is embedded as JS arrays inside each HTML file — `CATS[]`, `TESTERS[]`, `SUPPLIES[]`. There is no external SKU JSON file served to the browser. When adding new SKUs, update the array in every HTML file that references it.

---

# Emirates Pride Perfumes — Integrated Operations Platform
## CLAUDE Working Memory (updated May 2026)

---

## ⚠️ MANDATORY RULE — APPLIES TO EVERY CHAT SESSION WITHOUT EXCEPTION

> **AT THE END OF EVERY CONVERSATION — regardless of which chat window, which worktree, or which file was changed — Claude MUST update the PROJECT DETAILS section at the bottom of this file.**
>
> This rule is not optional. It is not limited to "this chat". It applies to ALL sessions that touch ANY file in this project.
>
> **What to record**: date, files changed, what was built/fixed/changed, commit hash, whether it was pushed to GitHub, and any decisions made.
>
> **Why**: This is the single source of truth for all development history. If a session ends without updating this file, the next session starts blind.

---

## SYSTEM ARCHITECTURE

### Frontend Files (served from GitHub Pages: vinayak682.github.io/emirates-pride-inventory-management/)
| File | Purpose | Access |
|------|---------|--------|
| `index.html` | Operations 2.0 — staff daily sales, GRN, transfers, testers | Store PINs + MGR PIN 9999 |
| `stock-register.html` | Weekly Stock Register (spreadsheet-style) | Store PINs + MGR 9999 + WH 8888 |
| `demand-planning-dashboard.html` | Demand Planning Dashboard | MGR access only |
| `sop-portal.html` | **S&OP Portal — Sales, Inventory, Testers** | Password: `Vinayak@1998` (every login) |
| `fg-request-form.html` | FG-to-Tester conversion request | Open |
| `fg-approve.html` | Approve FG conversion requests | MGR |
| `fg-report.html` | FG conversion audit report | MGR |
| `fg-to-tester-form.html` | FG-to-tester form variant | Open |

### Backend: Supabase (PostgreSQL)
- **Project URL**: `https://ncszurcrkngjcjqsowln.supabase.co`
- **Anon key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5jc3p1cmNya25namNqcXNvd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NjA4NTgsImV4cCI6MjA5MzAzNjg1OH0.i5cPlP7JTTCKMXuFqI81WXbjQa71qBkRBZEBvNf6ZmM`
- **Dashboard**: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln
- **Service role key**: NOT in client code (must be added securely for write ops)

### Supabase Tables
| Table | Rows | Purpose |
|-------|------|---------|
| `sales_history` | 17,267+ | SKU-level monthly sales: `sku_code`, `store_code`, `month_year` (YYYY-MM), `qty_sold` |
| `benchmarks_cache` | 1,458+ | Demand planning benchmarks per SKU-store |
| `transfer_history` | TBD | Consumption/transfer reports |
| `data_uploads_log` | TBD | Audit trail of uploads |
| `sop_inventory_uploads` | NEW | Inventory snapshots per store per upload date |
| `sop_inventory_history` | NEW | Full upload history for deviation tracking |

---

## REGIONAL DIVISIONS & STORE REGISTRY

### Division 1 — EPP UAE (Emirates Pride Perfumes Direct Stores)
- **Status**: Sales data in Supabase `sales_history`, Jan 2025 – Apr 2026 (17,267 rows)
- **Stores**: ~30+ UAE outlets (Dubai, Abu Dhabi, Sharjah, Ajman, RAK, Fujairah, Al Ain)
- Store codes: DX001 (Dubai Mall), DX004 (Mall of Emirates), DX005 (Mirdif CC), DX006 (Dubai Hills), A0001–A0009 (Abu Dhabi), SH001 (Zahia CC), AJ001 (Ajman CC), RK001/RK002 (Manar Mall), FJ001 (Fujairah CC), AL001–AL006 (Al Ain), etc.

### Division 2 — ASL UAE (ASL Franchise Stores)
- **Status**: NOT YET UPLOADED. Same Excel pivot format as EPP. Will be provided store-by-store.
- Action: When received, upload to `sales_history` with ASL-prefixed store codes.

### Division 3 — Oman (3 Stores)
- **Status**: Oct 2025 – Mar 2026 data parsed from Excel, ready to upload
- **Stores**:
  | Store Code | Store Name | Type |
  |-----------|-----------|------|
  | `OM001` | Mall Of Oman | EPP Direct |
  | `OM002` | Muscat City Centre | EPP Direct |
  | `OM_ASL001` | ASL-Mall Of Oman | ASL Franchise |
- **Data file**: `oman_sales_upload.json` (generated, ready for Supabase)
- **Note**: Oct–Dec 2025 sheets had no SKU codes — mapped via product name matching to Jan–Mar 2026 data

### Division 4 — KSA (Saudi Arabia)
- **Status**: DEFERRED. No data yet. Design S&OP to be extensible (region filter in UI).

---

## S&OP PORTAL — FULL SPECIFICATION

### File: `sop-portal.html`
### Password: `Vinayak@1998` (required EVERY time — no session persistence)
### Audience: Company owners, higher management — must be error-free

### Tab 1 — SALES
- **Metric**: Units sold only (no revenue for now)
- **Default view**: Configurable — both views available:
  - View A: All stores side-by-side for one selected month
  - View C: SKU performance across all stores + all months (matrix)
- **Filters**: Region (EPP/ASL/Oman/KSA), Store, Month, Quarter, Year
- **Fiscal quarters**: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
- **Targets**: NOT built yet — future
- **Top/Bottom SKU ranking**: NOT yet — will differ per region

### Tab 2 — INVENTORY
- **Input**: Excel upload per store (user uploads, system parses)
- **First-time behavior**: Replace existing data (full sync)
- **Subsequent uploads**: Match + generate deviation report (formatted, downloadable)
- **History**: Show last upload snapshot + full upload history log
- **Real-time sync to stock register**: DEFERRED — not in current build

### Tab 3 — TESTERS
All 5 KPIs mandatory:
1. Total testers issued per store per month
2. Testers converted from FG (full bottle → tester)
3. Tester wastage / write-offs
4. Current live tester count per store
5. Top SKUs by tester activity
- **Data source**: Supabase (same project, same tables used by stock register)

### Future Tabs (not built yet — note for next sessions):
- Targets vs Actuals (after targets are set)
- KSA tab (when data arrives)
- Cross-region comparison dashboard

---

## SKU REFERENCE

The system has ~253 unique SKUs across ASL and EPP lines. Key categories:
- **AP series**: ASL Perfumes (AP001–AP011)
- **AO series**: ASL Oils (AO001–AO011)
- **B series**: EPP Bakhoor/premium (B00001–B00021)
- **C series**: EPP Caballo line (C00002–C00014)
- **D series**: Dakhoon (D00001–D00008)
- **O series**: Oud (O00001–O00008)
- **SP series**: Sets/special packs
- **AG series**: ASL Gift Sets
- **AH series**: ASL Hair & Body Mist
- **AC series**: Accessories (charcoal, lighters, etc.)

---

## DEVELOPMENT PATTERNS & CONVENTIONS

### Login Pattern
- All protected sections use a full-screen overlay div (`position:fixed;inset:0`)
- Password stored as JS constant, compared on submit, no persistence
- Design: **LIGHT brand theme** — `#FFFFFF` / `#F5F2EC` backgrounds, navy `#1a2744` or olive-gold `#6B5B35` accents, gold `#C9A84C` borders. **No dark backgrounds anywhere — including login.**

### Color System
```
--gold: #C9A84C
--navy: #1a2744
--dark: #0f1824
--darker: #0D0D0D
```

### Supabase Query Pattern (existing code style)
```js
const { data, error } = await supabase
  .from('table_name')
  .select('*')
  .eq('column', value)
  .limit(5000);
```

### Data Upload Flow
1. User uploads Excel file via file input
2. JS parses using SheetJS (xlsx library, already loaded via CDN)
3. Data validated client-side
4. Upserted to Supabase via REST API with `Prefer: resolution=merge-duplicates`

---

## WORKFLOW — S&OP AS DEMAND PLANNER

The S&OP portal is used by Emirates Pride management. Primary responsibilities:
1. Monthly sales reporting across all regions (EPP, ASL, Oman, KSA)
2. Inventory accuracy verification per store
3. Tester tracking and write-off auditing
4. Forecasting and demand planning (benchmarks already built)

**Monthly process**:
1. Receive monthly sales Excel per region → upload via S&OP portal or Python script
2. Inventory count from stores → upload Excel → auto-deviation report generated
3. Review tester KPIs → share with management
4. Demand planning dashboard shows reorder priorities and benchmarks

---

## ONGOING BUILD QUEUE (next sessions)

1. [ ] Upload Oman sales JSON to Supabase `sales_history` (oman_sales_upload.json ready)
2. [ ] ASL UAE sales data — waiting for files
3. [ ] Create Supabase `sop_inventory_uploads` table for inventory snapshots
4. [ ] Monthly Excel upload script that auto-maps new months
5. [ ] KSA stores — deferred until data available
6. [ ] Sales targets input form (future)
7. [ ] Top/bottom 10 SKU ranking per region (future)

---

## ⚠️ STANDING INSTRUCTION — MANDATORY AFTER EVERY CONVERSATION
> **Claude must update the PROJECT DETAILS section below at the end of EVERY chat session.**
> Record every change made, file edited, commit hash, feature added, bug fixed, or decision taken.
> No exception. This is the single source of truth for all development history.

---

## PROJECT DETAILS — Full Development Log

> **Format**: Each session listed newest first. Include: date, files changed, what was done, commit hash if pushed.

---

### Session — 24 May 2026 (Session 16 — /init, /architecture, /code-review, /compliance-tracking, /webapp-testing, /data:analyze + Obsidian Vault)

**Files changed**: `CLAUDE.md` (major update — Claude Code guidance section prepended)
**Commit**: Not yet pushed

#### What was done:

**1. Obsidian Vault — Project Note Created**
- Created `Emirates Pride — Integrated Operations Platform.md` in `Noah's Ark Bank - LIFE OS Vault / 01 - PROJECTS / In Progress /`
- Full project summary: all frontend files, Supabase tables, key features, tech stack, brand palette, skills used, regional coverage, next steps
- Tagged: `#projects #web-development #emirates-pride #supabase #built-by-me`

**2. /init — CLAUDE.md Claude Code Guidance Section**
- Prepended a proper Claude Code guidance header to `CLAUDE.md` (was only project working memory, lacked commands/architecture for Claude Code)
- Added: local dev command (`python3 -m http.server 8080`), Python script usage + dependencies, SQL execution order (all 6 files in correct sequence), Edge Function deploy command, deploy workflow
- Added: request/data flow diagram, file roles table with sizes, `stock-register.html` internal structure map (critical — 18K line file), login/access control matrix, Supabase query patterns, design system tokens

**3. /architecture — ADR-001**
- Created Architecture Decision Record: Static HTML Monoliths vs React SPA vs Low-Code
- Decision: self-contained static HTML on GitHub Pages + Supabase — justified by zero ops overhead, one-person maintainability, free hosting
- Documented consequences + 4 action items (shared SKU catalogue, dynamic regions table, sales query pagination before KSA data, splitting stock-register.html if >1MB)

**4. /code-review — Security & Correctness Audit**
Three critical issues found:
- `monthly_sales_upload.py`: `parse_excel_sales()` always returns `[]` — script never uploads anything (incomplete TODO)
- `stock-register.html` line 11722: `_failedLoginCount` is in-memory only — brute-force bypass via page refresh resets 3-strike counter
- `stock-register.html` line 11882: `l.flag_reason` interpolated into `innerHTML` unescaped — stored XSS risk in security dashboard
Two medium issues: AM sessions get `isMgrSession=true` (lines 10740, 10766, 11749 not guarded), Edge Function auth via anon key (any reader of source can call it)
Fixes provided with code examples for all 5 issues

**5. /compliance-tracking — Regulatory Gap Analysis**
- Frameworks assessed: UAE PDPL (2021), internal financial controls, retail audit readiness
- Status: Audit trail ✅ Compliant | Access control ⚠️ Partial | UAE PDPL ❌ Gap
- Key findings: `am_weekly_requests.am_name` and `approved_by` fields constitute personal data under UAE PDPL (fines up to AED 5M) — no privacy notice shown to AM/staff
- No data retention policy — `audit_log` accumulates indefinitely
- MGR PIN rotation not scheduled; `SECURITY_INSTRUCTIONS.md` PIN rotation docs are incorrect (says edit source code, actual path is Supabase SQL)
- Produced: 7-item control inventory, audit calendar through May 2027, evidence collection plan, prioritised remediation table (P1/P2/P3)

**6. /webapp-testing — Playwright Test Suite**
- 21/21 tests passed, 0 warnings, 0 failures
- Tested: all 7 HTML pages, PIN keypad (12 keys), wrong-PIN rejection (DX001 + PIN 1234 → "Wrong PIN — try again."), S&OP password gate (wrong rejected, correct accepted), 32 stores in dropdown, AM form mobile layout at 390px (zero overflow), 0 fatal JS errors across all pages
- Screenshots saved to /tmp/ep_01 through ep_10

#### Key decisions / findings:
- `SUPABASE_SERVICE_KEY` in `monthly_sales_upload.py` is correctly a placeholder — never committed with real value
- All pages load with 0 JS console errors (clean build)
- AM login sets `isAmSession=true` AND `isMgrSession=true` — access boundary gap at lines 10740, 10766, 11749

**7. /data:analyze — Sales Analysis (257,568 units, 16 months)**
- Analysed `sales_history_upload.json` (16,201 rows), `oman_sales_upload.json` (844 rows), `benchmarks_upload.json` (1,458 benchmarks)
- **Dec 2025 confirmed outlier**: 56,993 units = +362% vs normal months (4x–6.5x per store) — confirmed National Day / gifting season; must be excluded from benchmark calculations
- **YoY Jan–Apr 2025→2026**: −6.8% overall; Jan −13.5%, Feb −13.5%, Mar −39.0%, Apr +63.4% recovery
- **Seasonality**: clear two-phase year — High season Jan–Apr (1.3x–1.7x avg), Low season May–Nov (0.64x–0.78x avg); September is lowest month
- **SKU concentration**: C00002 alone = 18.8% of all volume; top 3 SKUs = 34%; 5 near-zero SKUs (ABL004, AH005, AG015, ABL001, AAF002) = 1–2 units total in 16 months → delist candidates
- **Category mix**: EPP B series 44%, Caballo 25%, Sets/Oud/Dakhoon 8% each; ASL lines only 0.7% (likely because ASL UAE data not yet uploaded)
- **Store concentration**: DX001 = 18.7% of network; top 4 stores = 35%; OM001 (Oman) is #3 in recent 3-month velocity despite only 6 months of data
- **Reorder priorities**: 22% of benchmarked SKU-store pairs below 50% of median in Apr 2026; DX001 has severe shortfalls in D00003, D00004, B00003 (3–5% of historical median)
- **P1 action**: Upload `oman_sales_upload.json` (ready, 844 rows); investigate DX001 April shortfalls; confirm December excluded from `benchmarks_cache` medians

**8. /data:analyze — Security Concerns Severity Register (all findings ranked)**
- See full register below. 14 issues identified across /code-review, /compliance-tracking, /architecture, /webapp-testing
- 3 CRITICAL · 3 HIGH · 3 MEDIUM · 5 LOW
- Top 3 require action within this week (PDPL, brute-force, privacy notice)

---

## SECURITY CONCERNS — MASTER SEVERITY REGISTER
### Last updated: 24 May 2026 | Scoring: Impact(1–5) × Exploitability(1–5) × Detectability(1–5)/5 | Max = 25

| # | Score | Severity | Source | Issue | Status |
|---|-------|----------|--------|-------|--------|
| 1 | 25.0 | 🔴 CRITICAL | compliance | UAE PDPL — personal data (am_name, approved_by) stored without notice | ❌ Open |
| 2 | 16.0 | 🔴 CRITICAL | code-review | Brute-force PIN bypass — _failedLoginCount resets on page refresh | ❌ Open |
| 3 | 15.0 | 🔴 CRITICAL | compliance | No privacy notice at point of collection (AM request form) | ❌ Open |
| 4 | 12.0 | 🟠 HIGH | compliance | MGR PIN never rotated — default 9999 in SETUP_INSTRUCTIONS.md | ❌ Open |
| 5 | 9.6 | 🟠 HIGH | code-review | AM privilege escalation — isMgrSession=true at lines 10740/10766/11749 | ❌ Open |
| 6 | 9.0 | 🟠 HIGH | compliance | Off-hours anomaly fires on all ops → alert fatigue | ❌ Open |
| 7 | 8.0 | 🟡 MEDIUM | code-review | Stored XSS — flag_reason in innerHTML unescaped (line 11882) | ❌ Open |
| 8 | 6.4 | 🟡 MEDIUM | code-review | monthly_sales_upload.py — service key hardcoded string pattern | ❌ Open |
| 9 | 6.0 | 🟡 MEDIUM | compliance | SECURITY_INSTRUCTIONS.md PIN rotation docs are wrong | ❌ Open |
| 10 | 4.0 | 🟢 LOW | code-review | Edge Function auth via anon key — alert endpoint publicly triggerable | ❌ Open |
| 11 | 4.0 | 🟢 LOW | compliance | No tested backup and restore procedure | ❌ Open |
| 12 | 3.6 | 🟢 LOW | architecture | No branch protection on GitHub main | ❌ Open |
| 13 | 3.0 | 🟢 LOW | compliance | No data retention policy — audit_log grows indefinitely | ❌ Open |
| 14 | 2.0 | 🟢 LOW | compliance | No vendor DPA review (Supabase, Resend) | ❌ Open |

### Fixes — This Week (CRITICAL)

**#1 + #3 — PDPL & Privacy Notice (15 min each)**
- Add to `am-stock-request.html` above submit: `"Your name and request details are stored securely for Emirates Pride operational purposes · جميع البيانات المُدخلة تُحفظ لأغراض تشغيلية داخلية"`
- Create data processing register: `am_name`, `approved_by`, `dispatched_by` → retention 12 months → add deletion query to offboarding checklist

**#2 — Brute-force PIN bypass (30 min)**
```js
// In _secTrackFailedLogin():
const key = `ep_fail_${storeCode}`;
const count = parseInt(sessionStorage.getItem(key) || '0') + 1;
sessionStorage.setItem(key, count);
_failedLoginCount[storeCode] = count;
// On doLogin() success: sessionStorage.removeItem(`ep_fail_${code}`);
```

### Fixes — This Month (HIGH)

**#4 — MGR PIN rotation**
```sql
ALTER TABLE store_pins ADD COLUMN IF NOT EXISTS last_changed_at TIMESTAMPTZ DEFAULT NOW();
UPDATE store_pins SET pin = 'NEW_PIN', last_changed_at = NOW() WHERE store_code = 'MGR';
```
Remove "PIN: 9999" from SETUP_INSTRUCTIONS.md. Set quarterly rotation calendar reminder.

**#5 — AM privilege escalation**
```js
function _canFullMgr(){ return isMgrSession && !isAmSession; }
// Replace isMgrSession checks at lines 10740, 10766, 11749 with _canFullMgr()
```

**#6 — Alert fatigue fix**
```js
// Scope off-hours to WRITE ops on store (not MGR/AM) sessions:
if (op === 'WRITE' && !storeCode.startsWith('AM_') && storeCode !== 'MGR') {
  if (uaeHr >= _SEC.OFF_HOUR_START || uaeHr < _SEC.OFF_HOUR_END) { flagged=true; ... }
}
```

### Fixes — Medium Term (MEDIUM)

**#7 — XSS escape (5 min)**
```js
const _esc = s => String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
// Apply to: l.flag_reason (line 11882), l.store_code (11887), l.record_key (11890), l.operation (11889)
```

**#8 — Service key via env var**
```python
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
if not SUPABASE_SERVICE_KEY: print("Set env var"); sys.exit(1)
```

**#9 — Fix SECURITY_INSTRUCTIONS.md**
Replace line 206: "change store's PIN in STORES array" → `UPDATE store_pins SET pin='NEW' WHERE store_code='DX001';`

### Deferred (LOW — Q3 2026)

- **#10**: Add `x-ep-secret` header check to Edge Function
- **#11**: Document + test Supabase restore procedure
- **#12**: Enable GitHub branch protection (2 min in Settings)
- **#13**: Add annual `audit_log` purge query to runbook
- **#14**: Review Supabase + Resend DPAs for UAE coverage

---

### Session — 22 May 2026 (Session 14 — Excel 30-Sheet Consolidation → 6 Sheets)
**Files changed**: `build_excel_consolidated.py` (new), `EP_Demand_Planner_SAP_Reporting_Master_v3.xlsx` (output)
**Commit**: Not pushed (local Python output — no web app changes)

#### What was built:

**Problem solved**: The 30-sheet Excel workbook (`v2`) had significant overlap and was too unwieldy for a single demand planner to operate. User requested consolidation to a maximum of 6 sheets with no data loss.

**New file: `build_excel_consolidated.py`** → outputs `EP_Demand_Planner_SAP_Reporting_Master_v3.xlsx`

| Sheet | Name | Replaces (from v2) | Key Design Decisions |
|-------|------|--------------------|----------------------|
| 1 | MASTER DASHBOARD | INDEX (S1) + Regional KPI Dashboard (S15) + Demand Forecast vs Actuals (S10) | 3 sections: Navigation table, Regional KPI Scorecard (EPP/ASL/Oman/KSA), Forecast Accuracy table with colour-coded acc% |
| 2 | INVENTORY INTELLIGENCE | Daily Stock Overview (S2) + Physical Inventory Count (S12) + Inventory Turnover (S24) + ABC-XYZ (S25) + Dead Stock (S9) + Stock Age & FIFO (S27) + Safety Stock Calculator (S26) | One 33-column master table. Header groups colour-coded by domain (teal=stock, purple=count, blue=analytics, orange=age, red=deadstock). Filter-ready. |
| 3 | SALES & DEMAND PLANNING | Monthly Sales SKU (S4) + Store Sales Summary (S5) + Seasonal Demand Planner (S16) + Event Forecast 2026 (S28) + Seasonal ABC Reclassification (S29) + Replenishment Plan (S6) | 5 sections in one sheet with bold section divider rows. Sections A-E separated by olive section headers. |
| 4 | OPERATIONS LOG | Goods Movement Log (S3) + Transfer Tracker (S7) + PO & GRN Log (S13) + Write-off Log (S14) + AM Stock Request Tracker (S11) | Single master log with TYPE column. Colour-coded by type: GRN=green, Transfer=blue, Write-off=red, AM Request=purple, Count Adj=orange. Drop-down validation. |
| 5 | TESTER HUB | Tester Register (S8) + Allocation Master (S17) + Distribution Plan (S18) + Age & Condition (S19) + Wastage Analysis (S20) + Effectiveness ROI (S21) + Lifecycle Pipeline (S22) + Store Coverage Matrix (S23) | 7 sections A-G in one sheet. Tester gold (#8B6914) tab and section headers. AGE: CRITICAL rows auto-red. Coverage Matrix: A/L/X/N/C cell codes colour-coded. |
| 6 | SAP REFERENCE & CONFIG | SAP IBP Seasonal Config (S30) + movement type content scattered across sheets | 4 sections: Movement Type Register (14 types), Key T-Codes (23 codes), IBP Seasonal Profiles (6 profiles), Formula Reference (15 metrics) |

**Colour architecture maintained throughout**:
- OLIVE `#6B5B35` header bars, GOLD `#C9A84C` subtitle bars — matches brand
- GREEN = OK/Complete, AMBER = Review/Monitor, RED = Action Required/Critical, BLUE = In Transit/Planned
- Section divider rows: `#EDEBE6` background with gold medium border top/bottom
- Tab colours: Olive (S1), Teal (S2), Blue (S3), Purple (S4), Tester Gold (S5), Gold Dark (S6)

**Sample data quality**:
- All 15 sample store-SKU combinations in Sheet 2 include real store codes (DX001, DX004, A0001, SH001, AJ001, RK001, OM001, OM002)
- Realistic forecast accuracy % with proper colour-coding (green≥95%, amber 90-94%, red<90%)
- AM Request entries in Operations Log reference real AMR refs from existing system

**Bug fixed**: `UnicodeEncodeError` on Windows cp1252 console — removed ← arrow from print() statements (file itself unaffected)

**Temp file pattern used**: Saves to `%TEMP%\EP_v3_consolidated.xlsx` first, then `shutil.copy2()` to OneDrive path (avoids OneDrive lock)

---

### Session — 22 May 2026 (Session 15 — AM Form Full Bilingual + Manager Hub View/Edit/Approve/Dispatch)
**Files changed**: `am-stock-request.html`, `stock-register.html`, `am_requests_migration.sql` (new)
**Commit**: `a0154da` → pushed to `main` → GitHub Pages live

#### What was built:

**1. `am-stock-request.html` — Full bilingual + phone UX overhaul**
- Arabic added alongside every English-only string across all 4 screens
- iOS Safari zoom fix: all `input`/`select`/`textarea` bumped to `font-size:16px`
- Tap targets enlarged: product rows `min-height:60px`, + button `44px`, qty steppers `40px`, remove `44×44px`
- Screen 1: footer note + `جميع الطلبات محفوظة في لوحة تحكم المدير`
- Screen 2: "← Change · تغيير", Arabic week label `barWeekAr` element populated
- Screen 3: added "Review Request / مراجعة الطلب" title, all meta labels bilingual, notes placeholder Arabic, "Add More Items · إضافة منتجات أخرى"
- Screen 4: confirm sub-text Arabic, "Submit Another · طلب جديد"
- JS: `onAMChange` fallback Arabic, `resetForm` pill bug fixed (`dataset.cat` not `textContent`), empty cart state Arabic

**2. `stock-register.html` — Manager Hub: Full View → Edit → Save → Approve/Dispatch flow**

**Request cards**: replaced inline Approve/Dispatch buttons with single "👁 View" button → forces manager to view before acting

**Detail panel (`viewAMRequest` / `_renderReqDetail`)**:
- Sticky header: ← All Requests | Ref | Status badge | ⬇ PDF
- Store info card: store name, AM, week, SKU count, units requested
- Request Timeline section: 📥 Received / ✓ Approved / 🚚 Dispatched — each with full datetime + who + remarks; greyed out if not yet reached
- Stock Items table: SKU code | Product EN+AR | Req'd qty (read-only) | ✎ Fulfill qty (editable input) | Diff column (green +, amber −, red if 0)
  - Live per-row diff + totals footer update as manager types
  - Row turns amber if adjusted, red if set to 0 with [NOT DISPATCHING] label
  - Blue info banner explaining how to use the edit (canEdit only)
- Approval Remarks textarea (editable when pending/approved, locked when dispatched)
- AM Notes section (original notes from the request form, read-only)
- Edit History panel (collapsible ▾): every save/approval/dispatch logged with who, when, and what changed per SKU code (from_qty → to_qty, colour-coded)

**Sticky action bar (changes per status)**:
- Pending: [Approved By name input] + [💾 Save Draft] [✓ Approve Request]
- Approved: [Dispatched By input] + [Dispatch Notes input] + [💾 Save Changes] [🚚 Mark as Dispatched]
- Dispatched: read-only message + [⬇ Download PDF]

**Traceability (all stored in Supabase)**:
- `fulfilled_items` JSONB — manager-adjusted quantities (original `items` never overwritten)
- `approval_remarks` TEXT — reason for shortfalls
- `edit_history` JSONB array — every event: `{at, by, type, changes:[{code,en,from_qty,to_qty}], remarks}`
- Three-timestamp timeline on request cards: Received / Approved (with who + adj badge) / Dispatched
- PDF updated: two qty columns if adjusted, full Request Timeline block, amber remarks callout

**3. `am_requests_migration.sql` (new file)**
- `ADD COLUMN IF NOT EXISTS fulfilled_items JSONB DEFAULT NULL`
- `ADD COLUMN IF NOT EXISTS approval_remarks TEXT DEFAULT NULL`
- `ADD COLUMN IF NOT EXISTS edit_history JSONB DEFAULT '[]'::jsonb`
- Verification SELECT included
- **✅ User confirmed: migration was run successfully in Supabase and all features checked OK**

---

### Session — 21 May 2026 (Session 13 — AM Form Arabic + Manager Hub Approval/Dispatch Overhaul)
**Files changed**: `am-stock-request.html` (bilingual upgrade), `stock-register.html` (manager hub requests tab), `am_requests_migration.sql` (new)
**Commit**: pending push

#### What was built:

**1. `am-stock-request.html` — Full bilingual upgrade + phone UX**
- Every English-only string now has Arabic alongside it throughout all 4 screens
- iOS Safari zoom fix: all `input`/`select`/`textarea` bumped to `font-size:16px` (prevents auto-zoom on focus)
- Tap target enlargement: product rows `min-height:60px`, + button `44px`, qty steppers `40px`, remove button `44×44px`
- Screen 1 footer note: + `جميع الطلبات محفوظة في لوحة تحكم المدير`
- Screen 2 browse bar: "← Change" → "← Change · تغيير"; week line now shows dual Arabic date below
- Screen 3: added "Review Request / مراجعة الطلب" title; meta labels now bilingual (AM · المدير, Store · المحل, Week · أسبوع); notes placeholder + Arabic; "Add More Items" + Arabic
- Screen 4: confirm sub-text + Arabic; "Submit Another" → "Submit Another · طلب جديد"
- JS fixes: `onAMChange` fallback option + Arabic; `barWeekAr` element populated; cart empty state + Arabic; `resetForm` pill bug fixed (was `textContent === 'All'` — now correctly `dataset.cat === 'All'`)

**2. `stock-register.html` — Manager Hub: Requests tab overhaul**

**Approve modal (replaces `prompt()`):**
- Full slide-up modal with scrollable SKU table
- Each item shows: SKU code, EN name, AR name, Requested qty (read-only), Fulfil qty (editable input)
- Running total updates live as manager edits fulfil quantities
- Set to 0 = SKU will not be dispatched this week
- "Approval Remarks" textarea — manager explains any shortfalls (e.g. "White 100ml out of stock")
- "Approved By" required name field
- Saves to Supabase: `status:'approved'`, `approved_by`, `approved_at`, `fulfilled_items` (JSONB), `approval_remarks`

**Dispatch modal (replaces two `prompt()` calls):**
- Slide-up modal showing store/AM/week summary + scrollable list of approved items (only qty>0)
- "Dispatched By" required name field
- "Dispatch Notes / Remarks" textarea
- Saves: `status:'dispatched'`, `dispatched_by`, `dispatched_at`, `dispatch_notes`

**Request cards — three-timestamp timeline:**
- 📥 Received: [submitted_at datetime]
- ✓ Approved: [approved_at] · [approved_by] + "X req → Y approved" badge if quantities differ
- 🚚 Dispatched: [dispatched_at] · [dispatched_by] + dispatch notes inline
- Approval remarks shown as gold-bordered callout block below timeline
- AM notes shown in italics

**PDF (`printAMRequest`) — updated:**
- Meta section: status with colour coding, all three timestamps in a "Request Timeline" block
- If stock was adjusted: table shows two qty columns (Requested + Approved Qty) with amber highlight on changed rows, warning banner showing total difference
- Approval Remarks + Dispatch Notes section in amber callout
- Signature boxes pre-filled with approved_by / dispatched_by names

**3. `am_requests_migration.sql` (new)**
- `ALTER TABLE am_weekly_requests ADD COLUMN IF NOT EXISTS fulfilled_items JSONB`
- `ALTER TABLE am_weekly_requests ADD COLUMN IF NOT EXISTS approval_remarks TEXT`
- **⚠️ USER ACTION REQUIRED: Run this in Supabase SQL Editor before using the Approve & Adjust feature**
- URL: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql

---

### Session — 21 May 2026 (Session 12 — SAP S/4HANA PDF + Excel Demand Planner Master Workbook)
**Files changed**: `generate_sap_pdf.py` (new), `build_excel_p1.py` (new), `build_excel_p2.py` (new), `build_excel_p3.py` (new), `build_excel_p4.py` (new), `build_excel_p5.py` (new)
**Output files**: `EP_SAP_S4HANA_Transaction_Report_Register_v1.pdf` (59.2 KB), `EP_Demand_Planner_SAP_Reporting_Master_v2.xlsx` (128 KB, 30 sheets)
**Commit**: Not pushed (local Python output files — no web app changes)

#### What was built:

**1. SAP S/4HANA Executive PDF (`generate_sap_pdf.py` → `EP_SAP_S4HANA_Transaction_Report_Register_v1.pdf`)**
- 11-page executive-grade PDF for submission to Narendra Rai (SCM) + IT/SAP team
- Brand palette: Olive #6B5B35, Gold #C9A84C, executive dark-cream theme
- Sections: Cover Page, Executive Summary, Org Structure (Company Codes/Plants/Storage Locs/Sales Orgs), Movement Type Register (14 movement types), SD/MM Transactions, FG-to-Tester Flow (9-step process), IBP Demand Planning Configuration, Full Reports Register (40+ reports), Custom Z-Codes (9 Z-transactions), Data Migration Plan, Sign-off Page
- Framework: ReportLab Platypus with custom Flowables (SectionHeader, ProcessStep)
- Fixed: UnicodeEncodeError on Windows cp1252 by removing emoji from print statement

**2. Excel Demand Planner Master Workbook — 27 Sheets Total**
Built across 5 Python scripts in sequence:

| Script | Sheets | Content |
|--------|--------|---------|
| `build_excel_p1.py` | 1–6 | INDEX, Daily Stock Overview, Goods Movement Log, Monthly Sales SKU, Store Sales Summary, Replenishment Plan |
| `build_excel_p2.py` | 7–11 | Transfer Tracker, Tester Register, Dead Stock Report, Demand Forecast vs Actuals, AM Stock Request Tracker |
| `build_excel_p3.py` | 12–16 | Physical Inventory Count, PO & GRN Log, Write-off Log, Regional KPI Dashboard, Seasonal Demand Planner |
| `build_excel_p4.py` | 17–23 | **7 TESTER DEEP-DIVE SHEETS** (see below) |
| `build_excel_p5.py` | 24–27 | Inventory Turnover Analysis, ABC-XYZ Classification, Safety Stock Calculator, Stock Age & FIFO |
| `build_excel_p6.py` | 28–30 | Event-Based Demand Forecast 2026, Seasonal ABC Reclassification, SAP IBP Seasonal Config Guide |

**Tester Deep-Dive Sheets (17–23) — Added in response to user: "THIS IS HIGH POINT OF CONFLICT":**
- **Sheet 17 — Tester Allocation Master**: GRN qty → 10% entitlement → deployed → WH pool tracking per SKU. Status: Fully/Under/Over-Allocated / Critical Gap
- **Sheet 18 — Tester Distribution Plan**: Per-SKU per-store allocation by sales rank tiers (Tier 1 Must Have → Tier 4 No Tester)
- **Sheet 19 — Tester Age & Condition Monitor**: Every live tester with ZTC ref, age days, fill level %, replacement urgency rules (>120 days OR <20% fill = REPLACE NOW)
- **Sheet 20 — Tester Wastage Deep Analysis**: Root cause per write-off — Normal End-of-Life, Premature, Damaged, Expired-Idle, Missing/Theft
- **Sheet 21 — Tester Effectiveness ROI**: Before/after sales comparison per SKU-store, Lift%, Revenue from Lift, ROI, verdict
- **Sheet 22 — Tester Full Lifecycle Pipeline**: 10-stage pipeline with SLA (7 days request to in-store), BLOCKED/OVERDUE alerts
- **Sheet 23 — Store Tester Coverage Matrix**: 18 stores × 20 SKUs grid with A/L/X/N/C codes + coverage %

**Advanced Analytics Sheets (24–27):**
- **Sheet 24 — Inventory Turnover**: Turnover Rate (x/year), Days on Hand, Velocity Class (A/B/C/D), action column
- **Sheet 25 — ABC-XYZ Classification**: ABC by revenue contribution + XYZ by CoV; 9-cell strategy matrix with inventory policies
- **Sheet 26 — Safety Stock Calculator**: Formula-driven — Z-score × StdDev × √LT = SS; ROP auto-calc; IBP upload steps; status alerts (BELOW SAFETY / ADEQUATE)
- **Sheet 27 — Stock Age & FIFO Compliance**: Batch-level age tracking, FIFO compliance flag, age brackets with color coding, write-off escalation logic

**Bugs fixed in this session:**
- `build_excel_p4.py` line 748: `UnboundLocalError: INK_MID` — fixed by moving assignment before usage
- `build_excel_p4.py` line 800: `PermissionError` on OneDrive file — fixed by using temp file (`C:\AppData\Local\Temp\`) + copy back
- `build_excel_p5.py` line 161: `ValueError: too many values to unpack` — fixed by adding `_unused` to unpack 8-tuple

**Business rules embedded throughout:**
- Tester 10% rule (production sends 10% of GRN qty as testers)
- FIFO: Oldest batch issued first; >365 days = write-off escalation
- Safety stock: A-class 99% service level (Z=2.33), B=95% (Z=1.65), C=90% (Z=1.28)
- ABC: A = top 70% revenue, B = 70-90%, C = 90-100%
- XYZ: X = CoV <30%, Y = 30-60%, Z = >60%
- Tester age rule: >120 days OR <20% fill = REPLACE NOW

---

### Session — 20 May 2026 (Session 10 — AM Feedback Hub + Weekly Stock Request Form)
**Files changed**: `am-stock-request.html` (new), `am_requests_setup.sql` (new), `stock-register.html` (AM Hub button + panel + JS added)
**Commit**: pending — not yet pushed

#### What was built:

**1. `am-stock-request.html` — Standalone Mobile Weekly Stock Request Form**
- 4-screen mobile-first flow: Identity → Browse → Review → Confirm
- Screen 1: AM selects name (Hessin / Imad / Elmatloub) → store filtered to their assigned stores → week picker (defaults to next Monday)
- Screen 2: Full product catalogue (CATS + Testers + Supplies) with category pill filter + search bar. Tap "+" to add to cart, turns green on add
- Screen 3: Cart review with qty steppers (−/qty/+), remove button, notes field, submit
- Screen 4: Confirmation with request ref (AMR-YYYYMMDD-XXXX), PDF download via browser print, "Submit Another" button
- Includes all 163 products with Arabic + English names, 40 testers, 4 supply items (Shopping Bag S/M/L, Tissue Paper Roll)
- Submits to Supabase `am_weekly_requests` table
- PDF prints bilingual table (EN + AR) with signature lines (AM / Approved / Dispatched)
- Emirates Pride brand design (Cormorant Garamond + Montserrat + IBM Plex Mono, olive-gold bar, cream palette)
- Live URL after push: `https://vinayak682.github.io/emirates-pride-inventory-management/am-stock-request.html`

**2. `am_requests_setup.sql` — Supabase Table Setup**
- `am_weekly_requests`: request_ref, am_code, am_name, store_code, week_starting, items (JSONB), notes, status (pending/approved/dispatched/cancelled), approved_by, dispatched_by, timestamps
- `am_feedback_sessions`: am_code, session_date, session_type (Call/WhatsApp/Meeting/Visit), stock_notes, tester_notes, general_notes, action_items
- `am_issues_log`: am_code, store_code, category (Stock/Sales/Testers/Packaging/Staff/Other), title, details, severity (Low/Medium/High/Critical), status (Open/In Progress/Resolved/Closed), raised_date, resolved_date, resolution
- RLS policies: anon insert + read/update for all 3 tables
- Indexes on am_code, status, date fields
- **ACTION REQUIRED**: Run this SQL in Supabase SQL Editor before using the hub

**3. `stock-register.html` — AM Feedback Hub (MGR only)**
- New "👥 AM Feedback" button added to Manager Dashboard header (green gradient, beside Security Log)
- New full-screen panel `#amHubPanel` (z-index 825) with 4 tabs:

  **Tab 1: ☑ Daily TODO**
  - Progress bar showing tasks completed today (%)
  - 3 sections: Morning (stock updates from WhatsApp, confirm all 3 AMs sent updates), AM Check-ins (call/WhatsApp each AM), Testers (review counts, record write-offs), Weekly Tasks (send form links, approve requests)
  - Interactive checkboxes — state saved in localStorage per day (resets each morning)
  - Daily reminder: enter previous day closing stock from WhatsApp messages

  **Tab 2: 📞 AM Sessions**
  - Segmented control: Hessin / Imad / Elmatloub
  - Timeline of all logged sessions per AM from Supabase
  - Shows: date, type badge (Call/WhatsApp/Meeting/Visit), duration, Stock/Testers/General/Action notes
  - "+ Log Session" button → bottom-sheet modal with full fields

  **Tab 3: 📦 Weekly Requests**
  - Table of all submitted requests from `am_weekly_requests`
  - Shows: ref, AM name, store, week, SKU count, total qty, status pill
  - Pending → "✓ Approve" button (asks approver name → updates Supabase)
  - Approved → "🚚 Dispatch" button (asks who dispatched + notes → updates Supabase)
  - All → "⬇ PDF" button → opens print window with branded bilingual document
  - "📲 Open Form" link → am-stock-request.html in new tab

  **Tab 4: ⚑ Issue Log**
  - Issue cards with colour-coded left border (Open=amber, In Progress=blue, Resolved=green)
  - Category pill, severity badge (Critical pulses red), status pill per issue
  - "✓ Mark Resolved" button on open issues → asks resolution notes → updates Supabase
  - "⚑ Log Issue" button → bottom-sheet modal (AM, store, category, severity, title, details, date)

#### Supabase tables needed (run am_requests_setup.sql):
- `am_weekly_requests` ← form submissions
- `am_feedback_sessions` ← AM call/WhatsApp logs
- `am_issues_log` ← issue tracker

#### AM assignments (confirmed from STORES array):
- `AM_HESSIN` = Mohamed Hessin → 17 stores (Abu Dhabi + Al Ain)
- `AM_IMAD` = Mohammed Imad → 4 stores (Dubai)
- `AM_ELMAT` = Mohammed Elmatloub → 6 stores (RAK, Sharjah, Ajman, Fujairah)

---

### Session — 20 May 2026 (Session 11 — AM Hub: Stock Request Form + Manager Export + Inline Qty)
**Files changed**: `am-stock-request.html` (new), `stock-register.html` (modified), `am_requests_setup.sql` (new)
**Commit**: `d45a409` → pushed to `main` → GitHub Pages live
**Live URL**: https://vinayak682.github.io/emirates-pride-inventory-management/am-stock-request.html

#### What was built:

**New file: `am-stock-request.html`** — standalone mobile-first stock request form for Area Managers
- 4-screen flow: Identity (AM + store select) → Browse products → Review cart → Confirmation
- Full CATS catalogue (163 perfume SKUs) + TESTERS array (40 items) + SUPPLIES (bags S/M/L, tissue paper)
- Bilingual product names: EN + AR displayed for every SKU
- Bilingual category pills with stacked EN+AR text; `data-cat` attribute used for active state toggling (not textContent — fixes setCat bug when bilingual text was added)
- Inline qty controls in Browse screen: `+` button → adds item with qty=1; then `− [input] +` replaces button in-place (no scroll jump via `_refreshRow()` DOM update)
- Review screen: typed `<input class="qinp">` for qty, `adjQty()` uses `el.value`
- Cart float badge shows count, navigates to review
- Submit generates unique `AMR-YYYYMMDD-XXXX` ref, saves to Supabase `am_weekly_requests`, downloads PDF, shows WhatsApp share prompt
- PDF generation via `window.print()` — styled print-only template showing full request details

**`_esc` helper** — escapes backslashes and single quotes in onclick attribute strings (required for codes like `C00002-T`)

**New file: `am_requests_setup.sql`** — creates 3 Supabase tables:
- `am_weekly_requests` — stock request submissions with JSONB `items` column
- `am_feedback_sessions` — call/WhatsApp/meeting log entries
- `am_issues_log` — issue tracker per store with severity + status
- RLS policies: anon can insert + read + update requests; all operations for sessions/issues
- **⚠️ USER ACTION REQUIRED: Run this SQL in Supabase SQL Editor before form will work**

**`stock-register.html` modifications:**
- Added "👥 AM Feedback" button (green gradient) to MGR dashboard header
- Added full `#amHubPanel` overlay with 4 tabs: Requests / Feedback / Issues / TODO
- Requests tab: loads `am_weekly_requests` from Supabase, filter by AM/store/status/period
- Export functions: CSV (UTF-8 BOM for Arabic in Excel) + PDF (print window with summary + detail tables)
- Feedback tab: log sessions (Call/WhatsApp/Meeting/Visit), view history
- Issues tab: raise/track issues per store with severity, status progression
- TODO tab: daily AM checklist (Stock/Sales/Testers check-ins)

#### Bugs fixed:
- `setCat()` broke after bilingual pills — fixed by using `p.dataset.cat === cat` instead of `p.textContent === cat`
- Review screen qty: changed `<span class="qval">` to `<input class="qinp">`, updated `adjQty()` to use `el.value`
- Git push permission error (loose object) — fixed with `git gc --prune=now`, then push succeeded

#### Still pending (user action):
- Run `am_requests_setup.sql` in Supabase SQL Editor: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql

---

### Session — 19 May 2026 (Session 9 — Standalone FG Tester Manager Portal)
**Files changed**: `fg-tester-manager.html` (new)
**Commit**: `ac4aeff` → branch `claude/tender-spence-8b07d2` (pushed to GitHub, PR pending merge to main)

#### What was built:

**New file: `fg-tester-manager.html`**
- Standalone password-gated portal for reviewing and actioning FG Tester Requests
- Password: `Vinayak@1998` (same as S&OP portal)
- No login to `stock-register.html` required

#### Features:
1. **Login gate** — full-screen overlay, Emirates Pride branded card (light theme matching brand standards)
2. **Stats strip** — 3 cards showing live counts: Pending (amber), Approved (green), Rejected (red)
3. **Filter chips** — All / Pending / Approved / Rejected — filters the list client-side (no extra DB calls)
4. **Request cards** — colour-coded left border by status; shows ref, timestamp, store, employee, items count + total qty, remarks
5. **Approve button** — prompts for approver name → updates Supabase `fg_tester_requests` → downloads PDF
6. **Reject button** — prompts for approver name + reason → updates Supabase → downloads PDF
7. **Re-download PDF** — on already-processed cards, a "⬇ Download PDF" button re-generates the approval/rejection document
8. **Refresh button** — re-fetches all records from Supabase
9. **Full Report link** — opens `fg-report.html` in new tab
10. **Logout** — clears session, returns to login overlay
11. **Toast notifications** — bottom-centre, gold-bar branded, 3s auto-dismiss

#### Design:
- Full Emirates Pride brand palette: `--gold-bar:#6B5B35` topbar, `--gold-pale` backgrounds, Cormorant Garamond + Montserrat + IBM Plex Mono font stack
- Mobile-responsive: stat cards and typography scale down, button text hidden on small screens with icon-only buttons

#### Flow (unchanged):
1. Store fills `fg-request-form.html` → submits to Supabase → downloads pending PDF → sends WhatsApp to management
2. Manager opens `fg-tester-manager.html` (new standalone link) → logs in → sees all requests → approves/rejects → downloads decision PDF
3. Individual link approvals via `fg-approve.html?ref=XXX` (WhatsApp link) still work as before
4. FG panel inside `stock-register.html` (MGR tab) still works as before — both access points remain live

#### Live URL (after merging to main):
`https://vinayak682.github.io/emirates-pride-inventory-management/fg-tester-manager.html`

---

### Session — 19 May 2026 (Session 6 — Full Security Layer: Audit Log, Sessions, Anomaly Detection, Email Alerts)
**Files changed**: `stock-register.html`, `security_setup.sql` (new), `supabase/functions/security-alert/index.ts` (new), `SECURITY_INSTRUCTIONS.md` (new)
**Branch**: `claude/happy-agnesi-4a30dc` → merged to `main`
**Commits**: `3124a61` (security layer), `1355552` (SQL fix), `0dd7fa2` (merge to main)
**Pushed to**: `main` → GitHub Pages live

#### What was built:

**1. Supabase Tables (`security_setup.sql` — already run ✅)**
- `store_sessions` — row per login: store_code, login_type, user_agent, login_at, last_active, is_active
- `audit_log` — every event logged: LOGIN, LOGOUT, WRITE, FAILED_LOGIN; fields: session_id, store_code, operation, record_key (e.g. DX001/2026-05-19/AP001/sold), old_value, new_value, is_flagged, flag_reason
- `security_config` — tunable thresholds: max_writes_per_min=25, large_qty=100, off_hours 22:00–06:00 UAE, failed_login_threshold=3
- Server-side Postgres trigger `trg_audit_stock_cells` on `stock_cells` — tamper-proof backup (can't be bypassed from browser)

**2. Edge Function — Email Alert via Resend (already deployed ✅)**
- Function name: `security-alert` (deployed in Supabase Edge Functions)
- Provider: **Resend** (free — 3,000 emails/month)
- Secrets set in Supabase: `RESEND_API_KEY`, `ALERT_EMAIL`
- Sends branded HTML email: Emirates Pride header, alert reason, store, record key, UAE timestamp
- **NOTE**: Resend API key was shared in chat — regenerate it at resend.com → API Keys

**3. Security Module JS (in `stock-register.html`)**
- `_secCreateSession()` — creates session on login, heartbeat every 5 min
- `_secCloseSession()` — closes session on logout
- `_secQAudit()` — anomaly checks on every event:
  - Off-hours: 22:00–06:00 UAE time
  - Large quantity: single cell value > 100
  - Rapid writes: > 25 edits in 60 seconds
  - Failed logins: 3+ consecutive wrong PINs
- Alert cooldown: 5 minutes between emails (no spam)

**4. Security Log Dashboard (MGR-only)**
- `🔐 Security Log` button in All Stores Dashboard header
- Stats: Active Sessions | Events Shown | Flag Count
- Active sessions panel: who is logged in right now, device (iPad/desktop), login time
- Log table: Time (UAE) | Store | Device | Action | Record | Old→New | Flag reason
- Filters: by store, date range (Today/7d/30d/All), Flagged Only toggle
- Red row highlight for all flagged entries

**5. GitHub Security (completed ✅)**
- Repo made **private** (Supabase key no longer publicly visible)
- 2FA enabled on GitHub account (email + SMS)
- All-activity email notifications enabled on repo

**6. Security instructions documented in `SECURITY_INSTRUCTIONS.md`**

---

### Session — 19 May 2026 (Session 8 — Executive Login Redesign + Training Guide v9)
**Files changed**: `stock-register.html`, `training-guide.html`
**Commit**: `f2a37c2` → branch `claude/silly-varahamihira-2c8353` (pending merge to main)

#### What was done:

**1. Login Screen — Full Executive Dark Redesign**
- Requested because the existing login didn't meet the standard for MDs, CEOs, CFOs, Board of Directors
- Background: multi-layer radial gradients (deep `#060402` + atmospheric gold glow from top, accent glows at bottom corners) + diagonal texture overlay
- Gold hairline across top of full screen (CSS `::after`)
- 28 floating gold particles (JS-injected `.lp` divs, CSS `lp-rise` keyframe animation)
- Login card: glass morphism (`rgba(10,7,3,0.84)` + `backdrop-filter:blur(24px)`) with multi-layer `box-shadow` glow + inner gold shimmer hairline (`::before`)
- `EMIRATES PRIDE` wordmark: 26px, 7px letter-spacing, animated gold gradient shimmer (`go-shimmer` keyframe)
- `فخـر الإمارات` Arabic line: `rgba(201,168,76,0.50)` muted gold
- New tagline: `INTEGRATED OPERATIONS PLATFORM` in 7.5px ultra-light gold uppercase
- PIN dots: 50×50px, gold glow border + inner box-shadow when filled
- PIN keys: glass background, hover gold tint, press scale + glow animation
- ENTER button: animated 200% gold gradient shimmer + lift-on-hover shadow
- S&OP and Training Guide links: redesigned as glass dark cards with icon, subtitle line, hover state
- All link styles updated from light/mixed to consistent dark executive aesthetic

**2. Training Guide — Upgraded from v7 to v9 Animated**
- Source file: `C:\Users\AMALKANDATHIL\Downloads\EP_Stock_Register_Training_Guide_v8_Animated.html`
- Copied to `training-guide.html` in repo (replacing the simpler light v2 guide)
- Hero stats updated: 28→35+ stores, 111→253 SKUs, v7→v9, "UAE & Oman" label
- Nav: added 3 new sections (Sales Associate, Area Manager, Security)
- **New: Sales Associate Quick Reference** — 5 non-negotiables, common mistakes grid (4 cards), what correct data achieves (3 outcomes)
- **New: Area Manager Dashboard** — AM login flow (4 steps), what the AM dashboard shows (5 items), AM access boundary callout
- **New: Security & Audit System** — 6 feature cards (PIN security, audit log, anomaly detection, email alerts, session tracking, tamper-proof records) + implications grid for staff
- Footer badges: `35+ STORES · UAE & OMAN`, `253 ACTIVE SKUs`, `MAY 2026 · v9`, `SECURITY ENABLED`

#### Design decision:
- Login is now the only screen in the app that retains the full dark theme
- Rest of app (app shell, panels, grid) remains on the light brand palette per existing CLAUDE.md standing instruction
- Dark login is intentional: executive first-impression, brand cinematic entry point

---

### Session — 19 May 2026 (Session 7 — PIN Security Migration: Hardcoded PINs → Supabase)
**Files changed**: `stock-register.html`, `pin_table_setup.sql` (new), `.gitignore` (new)
**Commit**: `785306d` → pushed to `main` → GitHub Pages live
**pin_inserts.sql**: LOCAL ONLY — gitignored, never committed, must be run manually in Supabase SQL Editor

#### What was done:
- **Removed all hardcoded PINs** from `STORES` array (all 35 store entries, 3 AM entries, MGR, WH001)
- **Removed `MGR_PIN='9999'` constant** — replaced with comment
- **`doLogin()` made async** — now calls `_SBC.rpc('verify_store_pin', {p_code, p_pin})` instead of local comparison
- **`submitMgrPin()` made async** — same RPC for manager override PIN
- **Fallback handling**: if Supabase not loaded, login is blocked with clear error message
- **Login button UX**: disabled + "Verifying…" text during async RPC call, re-enabled on success/fail
- **Created `pin_table_setup.sql`** — creates `store_pins` table with RLS blocking anon direct reads, and `verify_store_pin()` SECURITY DEFINER RPC that returns only boolean
- **Created `.gitignore`** — permanently blocks `pin_inserts.sql`, `*.env`, `secrets.json` from being committed
- **pin_inserts.sql** — local-only file with all 35 store PINs, user must run in Supabase SQL Editor

#### Security outcome:
- Source code (public on GitHub) contains ZERO PIN values
- PINs stored in Supabase `store_pins` table, protected by RLS (zero anon policies — table is invisible to anon role)
- Only `verify_store_pin()` RPC (SECURITY DEFINER, runs as postgres) can read the table — returns true/false only
- Even if someone has the Supabase anon key, they cannot read the PINs directly

#### User action required (CRITICAL — app won't work until these are run):
1. Open Supabase SQL Editor: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql
2. Run `pin_table_setup.sql` first (creates table + RPC)
3. Run `pin_inserts.sql` second (populates all PINs)
4. Verify with: `SELECT store_code FROM store_pins ORDER BY store_code;`

#### Also completed in this session block (Sessions 6):
- Created `SECURITY_INSTRUCTIONS.md` (full security reference doc)
- Built complete security layer: session tracking, audit log, anomaly detection, email alerts (Resend)
- Supabase Edge Function `security-alert` deployed for email alerts
- Security dashboard panel added (MGR only, "🔐 Security Log" button)
- All changes committed and pushed to main

---

### Session — 19 May 2026 (Session 5 — Area Manager Login & Demand Planning Access Control)
**Files changed**: `stock-register.html`
**Commits**: `440d752` (worktree), `73e3bd0` (merge to main)
**Pushed to**: `main` branch → GitHub Pages live

#### What was done:
- **Fixed Demand Planning access control** — ensured MGR-exclusive feature is hidden from AM logins
- **Added ID to mgrDashPanel Demand Planning button** (`id="mgrDashDPBtn"`) for conditional visibility
- **Modified `openMgrDashboard()` function** — hides Demand Planning button for AM sessions (line 6721): `if(dpBtn) dpBtn.style.display=isAmSession?'none':'block';`
- **Modified `openDPPanel()` function** — blocks AM sessions from opening Demand Planning panel (lines 6767-6770) with guard: `if(isAmSession){ alert('...Manager only'); return; }`
- **Verified dashboard filtering** — `renderMgrDashboard()` correctly filters stores for AM sessions based on `amManagedStores` array

#### Feature Status:
- ✅ AM logins show "My Stores Dashboard" button (filtered to their assigned stores)
- ✅ Demand Planning button hidden from AM dashboard
- ✅ Demand Planning panel inaccessible to AM sessions (blocked at entry point)
- ✅ All other manager features work for AM logins (lock status, finance status, compliance tracking, store filtering)
- ✅ MGR logins retain full access including Demand Planning

#### Technical Details:
- AM login detection: `isAmSession=true` flag set during AM login
- Store filtering: `if(isAmSession) return amManagedStores.includes(s.code);` in dashboard filter
- Button visibility: Conditional display check in `openMgrDashboard()` runs on every dashboard open
- Double guard: Button hidden via CSS + entry guard on function prevents direct access attempts

---

---

## ⚠️ ACTUAL CURRENT STATE OF stock-register.html (verified 19 May 2026)

> Sessions 2 and 3 below claim the brand transformation was completed and pushed. **This is NOT accurate.**
> As of 19 May 2026, the file is verified to still be on the original dark theme:
> - Font: IBM Plex Sans (not Montserrat / Cormorant Garamond)
> - Background: `#1A1A1A` dark (not `#FFFFFF` white)
> - Topbar: `#111` dark (not `#6B5B35` olive-gold)
> - No brand palette tokens in `:root`
> - `tst` (Tester Received) column still present
>
> **The full brand transformation is still pending. When a session completes it, update this note.**

---

### Session — 19 May 2026 (Session 3 — Brand UI & Typography Overhaul)
**Files changed**: `stock-register.html`
**Commits**: `c178aed` (brand palette), `534f3e4` (typography precision)
**Pushed to**: `main` branch → GitHub Pages live

#### A. Brand Color System — Full Transformation (matched to emiratespride.com)
- **`:root` CSS variables completely rebuilt**:
  - `--page: #FFFFFF` (was `#FFFDF9` cream — now pure white matching website)
  - `--gold-pale: #F5F2EC` (was `#F5EDD8` warm gold — now subtle near-white card tint)
  - `--gold-bar: #6B5B35` ← **NEW token** — website announcement bar olive-gold color
  - `--border: #E5E0D8` (lightened from `#E2D9C8`)
  - Removed separate `--navy`, `--navy-mid`, `--navy-light` tokens
  - Added `--navy: #6B5B35`, `--navy-mid: #5C4A1A` as **aliases** → all legacy navy references auto-remap to olive-gold
  - Column group tint tokens updated to lighter, cleaner versions
- **Meta `theme-color` updated**: `#0D0D0D` → `#6B5B35`

#### B. App Topbar (`.app-topbar`)
- Background: `var(--navy)` `#1a2744` → `var(--gold-bar)` `#6B5B35` (olive-gold)
- Box shadow: navy rgba → olive-gold rgba
- `.top-store`: color `var(--gold)` → `#FFFFFF` white; font-size 16px → 19px; weight 600 → 500
- `.top-day`: colors updated from gold-on-navy to white-on-olive
- `.top-btn`: white text 10.5px uppercase, letter-spacing 0.5px; hover/active states updated
- `.top-btn.logout`: reddish tint preserved
- Manager dashboard button inline style updated to match topbar aesthetic

#### C. Category Separators
- `.cat-sep-inner`: gradient `#1a2744→#243258→#1a2744` → `#6B5B35→#7A6830→#5C4A1A` (olive-gold)
- `.cat-sep-en`: color `#E8C87A` (gold) → `#FFFFFF` (white)
- `.cat-sep-inner::before` shimmer: gold rgba → white rgba
- `.cat-sep-icon` border: gold rgba → white rgba
- `.tstr-cat-inner` (tester grid separator): same treatment — navy gradient → olive-gold

#### D. All Panel Headers transformed (via `--navy` alias)
| Panel | Element | Result |
|-------|---------|--------|
| All-Stores Panel | `.sp-header` | Olive-gold bar, white title/close button |
| AM Panel | `.sp-am-hdr` | Olive-gold, white text |
| Dashboard | `.dash-topbar` | Olive-gold, white title |
| Tester Panel | `.tstr-topbar` | Olive-gold, white store name |
| Finance Tab | `.fin-topbar`, `.fin-sheet-header` | Olive-gold, all text → white |
| Export buttons | `.exp-close`, `.exp-period-btn.sel`, `.exp-type-btn.active` | Olive-gold |
| Summary frozen bar | `.summary-frozen` | Olive-gold (via `--navy` alias) |
| MGR pin confirm | `.mgr-pin-confirm` | Olive-gold gradient |

#### E. Text Color Updates (elements on olive-gold backgrounds)
- All `color:var(--gold)` on navy bars → `color:#FFFFFF`
- All `color:rgba(232,212,154,…)` (gold-tinted) → `color:rgba(255,255,255,…)` (white-tinted)
- `.sf-label` (summary bar KPI labels): gold rgba → white rgba
- `.sf-div` separator: gold rgba → white rgba

#### F. Tester Section Header (inline HTML)
- Background `#111` → `#6B5B35`
- Border `#2A2A1A` → `var(--gold)` gold
- Text color updated to white / white-60%

#### G. Transfer Impact Preview (inline HTML)
- Background `#111`, border `#2A2A2A` → `#F5F2EC` light cream, border `#E5E0D8`
- Text colors: grey on dark → proper ink/muted on light background
- Danger value: `#E87070` → `#C0392B`; safe value: `#6FCF97` → `#1A6A40`

#### H. Miscellaneous
- `html,body` background: `var(--navy)` → `var(--page)` (white)
- Toast: background olive-gold, white text
- `.dd-chip.active` (dashboard day chip): navy bg gold text → olive-gold bg white text
- `.dash-sku-table thead th:first-child`: gold text → white text
- `.sc-mine` (my store badge): navy bg gold text → olive-gold bg white text

---

#### I. Typography Precision Overhaul (matched to SOP Command Centre screenshot)

**Reference**: SOP portal (`sop-portal.html`) screenshot showing the exact Emirates Pride font system

| Element | Before | After |
|---------|--------|-------|
| Grid column headers | IBM Plex Mono 9.5px 0.5px spacing | **Montserrat 700 10px UPPERCASE 1px spacing `#8A8278`** |
| Product name `.pname` | Montserrat **700** bold | **Montserrat 500** — refined, editorial |
| Product code `.pcode` | Color `#B0A898` muted grey | **Color `#7A6525` warm gold** — matches DX001 store codes in SOP |
| Data cell values `.dcell-val` | weight 500 | **weight 600, letter-spacing -0.3px** |
| Day tabs background | `var(--gold-pale)` yellow tint | **Pure white `#FFFFFF`** |
| Day tab letter-spacing | 0.5px | **1px** |
| Day tab date sub-label | weight same | **weight 400 (lighter hierarchy)** |
| Summary bar labels `.sf-label` | IBM Plex Mono 8px 0.8px | **Montserrat 700 7.5px UPPERCASE 1.2px** |
| Summary bar values `.sf-val` | IBM Plex Mono 18px 800 | **Cormorant Garamond 22px 600** (luxury serif) |
| Totals row `.tot-num` | IBM Plex Mono 16px 800 | **Cormorant Garamond 19px 600** |
| KPI card values `.kpi-val` | IBM Plex Mono 22px 700 | **Cormorant Garamond 26px 600** |
| KPI card labels | 9px 0.8px spacing | **8.5px 1.2px spacing Montserrat 700** |
| Activity log name `.dl-name` | weight 600 `#1A2A4A` | **weight 500 `var(--ink)`** |
| Activity log qty `.dl-qty` | IBM Plex Mono 16px 700 | **Cormorant Garamond 19px 600** |
| Category sep text `.cat-sep-en` | IBM Plex Mono | **Montserrat 700 2px letter-spacing** |
| Tester cat text `.tstr-cat-name` | IBM Plex Mono 11px 800 | **Montserrat 700 10px** |
| Topbar store name | 17px weight 600 | **19px weight 500** |
| Bilingual `.hdr-ar` | weight 600 opacity 0.8 | **weight 500 opacity 0.70** |
| Bilingual `.hdr-sub-lbl` | 9px mono | **8px Montserrat UPPERCASE 0.5px spacing** |
| Top buttons | no text-transform | **UPPERCASE letter-spacing 0.5px** |
| Region header | gold-dark color | **`var(--ink-mid)` 1.2px spacing** |

**Typography System now in use (from SOP screenshot)**:
```
Headings / Store names   → Cormorant Garamond 500–600 (luxury serif, editorial)
Body / UI / Buttons      → Montserrat 400–700 (geometric sans, clean)
Codes / Numbers / Mono   → IBM Plex Mono 400–600 (technical precision)
Arabic text              → IBM Plex Sans Arabic 400–600
```

---

### Session — 19 May 2026 (Session 2 — Dark Background Purge)
**Files changed**: `stock-register.html` (worktree branch `claude/priceless-kepler-777398` → merged to `main`)
**Commits**: `1ff3ce6` (worktree), `9cee6dd` (merge to main)

#### What was done:
- **Complete audit and replacement of all dark backgrounds** across the entire app
- Elements fixed: login-adjacent drawers, modals, panels, FG print template, GRN sections
- Every `#141414`, `#1A1A1A`, `rgba(0,0,0,0.88)` etc. replaced with brand light palette
- Merged branch to main and pushed to GitHub Pages

---

### Session — Prior Sessions (May 2026 — Stock Register Core Build)
**Files changed**: `stock-register.html`

#### Core Features Built:
1. **Spreadsheet-style grid** — sticky product column, scrollable day columns (15 days)
2. **Bilingual headers** — English + Arabic for every column group (Opening, Warehouse, Store-In, Sold, Transfer, Write-off, Out, Balance)
3. **Category separators** — Premium row dividers between product categories with icon + name
4. **Day tabs** — 15-day navigation bar, today highlighted, data dot indicator
5. **Summary frozen bar** — Sticky KPI strip showing Opening / WH / In / Sold / Transfer / Balance totals
6. **Login system** — Store PIN login, MGR PIN (9999), WH PIN (8888), full-screen overlay
7. **Supabase sync** — All data reads/writes go to Supabase (ncszurcrkngjcjqsowln)
8. **Lock system** — MGR can lock/unlock any day's data
9. **All-stores panel** — MGR can view all stores' stock in one panel
10. **Transfer tracking** — Inter-store transfers tracked with source/destination store name
11. **Tester tracking** — Opening tester count, condition pills (Active/Low/Empty/Sealed)
12. **Warehouse (WH) panel** — Separate view for WH001 login showing regional dispatch
13. **Dashboard** — Activity log, KPI cards, day selector for MGR view
14. **Export system** — CSV, Excel, PDF export for day/week/month periods
15. **Finance tab** — Cash + card + BNPL (Tabby/Tamara) daily finance entry
16. **Demand Planning panel** — SKU benchmarks, reorder priorities (MGR only)
17. **Consumables section** — Track non-perfume consumables (bags, boxes, etc.)

#### Column Structure (current — after Tester Received removal):
`Opening | Warehouse Stock | Store-In | Sold | Transfer | Write-off | Out | Balance`
*(Tester Received column was removed — see below)*

#### Tester Received Column — REMOVED
- Column was present in original build
- **Removed permanently** across: `hdr-group` header row, `hdr-sub` sub-header, `hdr-totals` totals sub-header, all data cells (`dcell.tst`), totals row, day summary calculations, export functions
- Reason: Tester tracking moved to dedicated Tester tab/section

---

### S&OP Portal (sop-portal.html) — Development History

#### Built Features (as of May 2026):
1. **Login gate** — Password `Vinayak@1998` required every login, no persistence
2. **Header bar** — Emirates Pride logo (EN + AR), S&OP title, Management badge, timestamp
3. **Tab navigation** — Sales, Inventory, Testers, Production, Warehouse, Intelligence, Campaigns & Orders, Forecast (8 tabs)
4. **SALES Tab**:
   - Supabase query: `sales_history` table, 17,267+ rows (Jan 2025 – Apr 2026)
   - Filters: Region (EPP/ASL/Oman/KSA), Store, Monthly/Quarterly/Annual, Year, Month
   - View A: Store performance table — rank, store code (gold mono), store name, city, region pill, units sold, % share bar
   - View C: SKU matrix — all SKUs vs all months
   - KPI cards: Total Units Sold (Cormorant Garamond serif large), Active Stores, Active SKUs, Top Store
   - CSV export button
   - Search SKU or store filter
5. **Color & Typography System** (from emiratespride.com):
   - Exact brand match: `--gold:#C9A84C`, `--gold-bar:#6B5B35`, `--page:#FFFFFF`
   - Fonts: Cormorant Garamond (serif/display) + Montserrat (body) + IBM Plex Mono (numbers/codes)
   - Store codes: IBM Plex Mono `#7A6525` warm gold
   - KPI big numbers: Cormorant Garamond 48px+
   - Column headers: Montserrat 700 UPPERCASE 1px letter-spacing `#8A8278`
   - Table rows: very generous line-height, minimal borders
6. **Inventory Tab**: Placeholder (Excel upload UI spec ready, backend pending)
7. **Testers Tab**: Placeholder (5 KPIs defined, data source = Supabase)

---

## CURRENT BRAND DESIGN SYSTEM (as of 19 May 2026)

> **Overrides the older brand_design_system.md memory** — this is the authoritative version

### CSS Tokens (`:root` in stock-register.html)
```css
--gold: #C9A84C          /* Primary brand gold */
--gold-dark: #7A6525     /* Headings, store codes, active text */
--gold-bar: #6B5B35      /* Website announcement bar — ALL dark headers use this */
--gold-deeper: #5C4A1A   /* Deepest gold — hover states */
--gold-light: #D4B86A    /* Subtle highlight */
--gold-pale: #F5F2EC     /* Card tint — website product card background */
--border: #E5E0D8        /* Standard separator */
--border-dark: #D0C8B8   /* Stronger separator */
--ink: #1A1A1A           /* Primary text */
--ink-mid: #4A4540       /* Secondary text */
--ink-light: #8A8278     /* Muted — column headers, sub-labels */
--white: #FFFFFF
--page: #FFFFFF          /* Page background — pure white */
--sheet: #FAFAF8         /* Grid background */
--row-alt: #F5F2EC       /* Alternating row tint */
--navy: #6B5B35          /* ALIAS for gold-bar — used by all legacy dark headers */
--navy-mid: #5C4A1A      /* ALIAS — hover/active on dark bars */
```

### Font Stack
```
Headings / KPI numbers / Store names → 'Cormorant Garamond', serif (500–600)
Body / Labels / Buttons / Tabs       → 'Montserrat', sans-serif (400–700)
SKU codes / Numbers / Timestamps     → 'IBM Plex Mono', monospace (400–600)
Arabic text                          → 'IBM Plex Sans Arabic', sans-serif (400–600)
```

### Dark Header Rule
**ALL dark headers, topbars, panel headers, category separators use `#6B5B35` (olive-gold).**
Never use `#1a2744` navy or `#0D0D0D` black anywhere in the app — including the login screen.
**There are NO exceptions. The login screen is ALSO light brand theme.**

---

## ONGOING BUILD QUEUE (next sessions)

1. [ ] Upload Oman sales JSON to Supabase `sales_history` (oman_sales_upload.json ready)
2. [ ] ASL UAE sales data — waiting for files
3. [ ] Create Supabase `sop_inventory_uploads` table for inventory snapshots
4. [ ] Monthly Excel upload script that auto-maps new months
5. [ ] KSA stores — deferred until data available
6. [ ] Sales targets input form (future)
7. [ ] Top/bottom 10 SKU ranking per region (future)
8. [ ] S&OP Inventory tab — Excel upload + deviation report (spec ready)
9. [ ] S&OP Testers tab — 5 KPIs from Supabase (spec ready)

---
*Last updated: 19 May 2026 | Maintained by Claude (Demand Planning AI)*
*⚠️ REMINDER: Update PROJECT DETAILS section after EVERY conversation without exception*
