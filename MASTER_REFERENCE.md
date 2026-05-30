# Emirates Pride Perfumes — Master Reference Document
**Last updated: May 2026 | Maintained by Emirates Pride Operations**

> Copy this file with the project folder to any new machine or login. It contains everything needed to resume work.

---

## 1. LIVE WEBSITE

**GitHub Pages URL**: https://vinayak682.github.io/emirates-pride-inventory-management/

All HTML files in this folder are automatically served from that URL. Pushing changes to GitHub deploys them live instantly.

---

## 2. ALL PASSWORDS & ACCESS CREDENTIALS

### Application Logins

| File / Module | Access Method | Credential |
|--------------|--------------|------------|
| `sop-portal.html` | Password (every login, no session) | `Vinayak@1998` |
| `index.html` (Operations 2.0) | Staff PIN | Store-specific PINs |
| `index.html` | Manager PIN | `9999` |
| `stock-register.html` | Manager PIN | `9999` |
| `stock-register.html` | Warehouse PIN | `8888` |
| `fg-approve.html` | Manager only | `9999` |
| `demand-planning-dashboard.html` | Manager only | `9999` |

### Supabase (Backend Database)

| Item | Value |
|------|-------|
| **Dashboard URL** | https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln |
| **Project REST URL** | `https://ncszurcrkngjcjqsowln.supabase.co` |
| **Anon Key (read)** | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5jc3p1cmNya25namNqcXNvd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NjA4NTgsImV4cCI6MjA5MzAzNjg1OH0.i5cPlP7JTTCKMXuFqI81WXbjQa71qBkRBZEBvNf6ZmM` |
| **Service Role Key** | NOT stored in any file — retrieve from Supabase Dashboard → Settings → API |
| **Login email** | (project owner email) |

> **Note**: The anon key is safe in client-side code — it is read-only. The service role key must NEVER go into HTML/JS files.

### GitHub Repository

| Item | Value |
|------|-------|
| **Repo** | `vinayak682/emirates-pride-inventory-management` |
| **Branch** | `main` |
| **GitHub Pages** | Enabled on `main` branch root |

---

## 3. ALL FILES IN THIS FOLDER & WHAT THEY DO

### Core Application Files

| File | What It Does | Who Can Access |
|------|-------------|---------------|
| `index.html` | **Operations 2.0** — Daily operations for store staff: record sales, GRN receipts, inter-store transfers, tester issuances. All data writes to Supabase. | Store staff (PIN) + Manager (9999) |
| `stock-register.html` | **Weekly Stock Register** — Spreadsheet-style live stock tracker per store per week. Shows opening stock, GRN, transfers, sales, closing balance. Pulls from Supabase. | Store PINs + Manager 9999 + Warehouse 8888 |
| `sop-portal.html` | **S&OP Portal** — Management dashboard with 3 tabs: Sales (multi-region), Inventory (Excel upload + deviation), Testers (5 KPIs). For company owners and senior management. | Password: `Vinayak@1998` |
| `demand-planning-dashboard.html` | **Demand Planning Dashboard** — Shows reorder priorities, benchmarks, min/max targets per SKU per store. Used for monthly planning. | Manager 9999 |
| `fg-request-form.html` | Form for store staff to request conversion of FG bottles into testers | Open (no login) |
| `fg-approve.html` | Manager approves/rejects FG-to-tester conversion requests | Manager 9999 |
| `fg-report.html` | Audit report of all FG conversion activity | Manager 9999 |
| `fg-to-tester-form.html` | Alternate variant of FG-to-tester form | Open |
| `stock-register-REGION-SPECIFIC.html` | Region-specific variant of the stock register | Store PINs |

### New Files — AM Hub (May 2026)

| File | What It Does | Who Can Access |
|------|-------------|---------------|
| `am-stock-request.html` | **AM Weekly Stock Request Form** — Mobile-first form for Area Managers to submit weekly stock requests. 4-screen flow: Identity → Browse → Review → Confirm. 163 perfume SKUs + 40 testers + supplies (bags/tissue). Bilingual EN+AR. Saves to Supabase `am_weekly_requests`. | AMs (no login required) |
| `fg-tester-manager.html` | **FG Tester Manager Portal** — Standalone password-gated portal for reviewing and actioning FG-to-Tester conversion requests. Password: `Vinayak@1998`. Shows pending/approved/rejected with PDF download. | Password: `Vinayak@1998` |

### Setup SQL Files

| File | Purpose | Status |
|------|---------|--------|
| `am_requests_setup.sql` | Creates `am_weekly_requests`, `am_feedback_sessions`, `am_issues_log` tables with RLS policies | ✅ Run in Supabase 20 May 2026 |
| `pin_table_setup.sql` | Creates `store_pins` table + `verify_store_pin()` RPC — secure PIN storage | ✅ Run in Supabase |
| `security_setup.sql` | Creates `store_sessions`, `audit_log`, `security_config` tables + triggers | ✅ Run in Supabase |
| `pin_inserts.sql` | Populates all 35 store PINs — LOCAL ONLY, gitignored, never commit | ✅ Run locally in Supabase |

### Data Files (in this folder — for Supabase upload)

| File | What It Contains | Status |
|------|-----------------|--------|
| `sales_history_upload.json` | EPP UAE monthly sales, Jan 2025 – Apr 2026, 17,267 rows | ✅ Uploaded to Supabase |
| `benchmarks_upload.json` | Demand planning benchmarks, 1,458 rows, all EPP UAE SKU-store combos | ✅ Uploaded to Supabase |
| `oman_sales_upload.json` | Oman (3 stores) monthly sales, Oct 2025 – Mar 2026 | ⏳ Ready — NOT YET uploaded |

### Reference Files

| File | What It Contains |
|------|----------------|
| `MASTER_REFERENCE.md` | This file — full project reference |
| `CLAUDE.md` | Instructions for Claude AI assistant working on this project |
| `Master file-New.xlsx` | SKU master — 606 SKUs across all brands (on Desktop) |

---

## 4. SUPABASE DATABASE — FULL SCHEMA

### Tables Currently Live

#### `sales_history`
```
sku_code     TEXT       -- e.g. "C00007", "SP0037"
store_code   TEXT       -- e.g. "DX001", "OM001"
month_year   TEXT       -- format: "YYYY-MM" e.g. "2025-01"
qty_sold     INTEGER
```
**Primary key**: `(sku_code, store_code, month_year)`
**Rows**: 17,267+ (EPP UAE only as of May 2026)
**Coverage**: Jan 2025 – Apr 2026

#### `benchmarks_cache`
```
sku_code       TEXT
store_code     TEXT
l30d_qty       NUMERIC    -- last 30-day quantity
min_monthly    NUMERIC    -- minimum monthly stock target
max_monthly    NUMERIC    -- maximum monthly stock target
(+ additional benchmark columns)
```
**Rows**: 1,458+

#### `transfer_history`
```
-- Records stock movements: GRN, inter-store transfers, tester issuances
-- Also used for tester KPI tracking in S&OP portal
-- Schema: TBD (check Supabase dashboard)
```

#### `data_uploads_log`
```
-- Audit trail of all data upload events
-- Schema: TBD (check Supabase dashboard)
```

#### `store_pins` (security — PIN storage)
```
store_code   TEXT PRIMARY KEY
pin_hash     TEXT   -- bcrypt hash of the PIN (never stored plain)
```
RLS: **anon has zero policies** — completely invisible to client. Only accessible via `verify_store_pin()` RPC (SECURITY DEFINER). This means even if someone has the anon key, they cannot read PINs.

#### `store_sessions` (security — login tracking)
```
id           BIGSERIAL PRIMARY KEY
store_code   TEXT
login_type   TEXT    -- 'store','manager','warehouse','am'
user_agent   TEXT
login_at     TIMESTAMPTZ
last_active  TIMESTAMPTZ
is_active    BOOLEAN
```

#### `audit_log` (security — every event)
```
id           BIGSERIAL PRIMARY KEY
session_id   BIGINT
store_code   TEXT
operation    TEXT    -- 'LOGIN','LOGOUT','WRITE','FAILED_LOGIN'
record_key   TEXT    -- e.g. "DX001/2026-05-19/AP001/sold"
old_value    TEXT
new_value    TEXT
is_flagged   BOOLEAN
flag_reason  TEXT
```
Server-side Postgres trigger `trg_audit_stock_cells` on `stock_cells` — tamper-proof backup.

#### `security_config` (tunable thresholds)
```
max_writes_per_min    INT   DEFAULT 25
large_qty             INT   DEFAULT 100
off_hours_start       TIME  DEFAULT '22:00'
off_hours_end         TIME  DEFAULT '06:00'
failed_login_threshold INT  DEFAULT 3
```

#### `am_weekly_requests` (AM Hub — stock request submissions)
```
id              BIGSERIAL PRIMARY KEY
request_ref     TEXT NOT NULL UNIQUE   -- AMR-YYYYMMDD-XXXX
am_code         TEXT                   -- AM_HESSIN / AM_IMAD / AM_ELMAT
am_name         TEXT
store_code      TEXT
store_name      TEXT
week_starting   DATE
items           JSONB    -- [{code, en, ar, qty, cat}]
notes           TEXT
status          TEXT     -- pending/approved/dispatched/cancelled
submitted_at    TIMESTAMPTZ
approved_by     TEXT
approved_at     TIMESTAMPTZ
dispatched_by   TEXT
dispatched_at   TIMESTAMPTZ
dispatch_notes  TEXT
```

#### `am_feedback_sessions` (AM Hub — call/meeting log)
```
id              BIGSERIAL PRIMARY KEY
am_code         TEXT
am_name         TEXT
session_date    DATE
session_type    TEXT    -- Call/WhatsApp/Meeting/Visit
duration_mins   INTEGER
stock_notes     TEXT
tester_notes    TEXT
sales_notes     TEXT
general_notes   TEXT
action_items    TEXT
logged_by       TEXT
created_at      TIMESTAMPTZ
```

#### `am_issues_log` (AM Hub — issue tracker)
```
id              BIGSERIAL PRIMARY KEY
am_code         TEXT
am_name         TEXT
store_code      TEXT
store_name      TEXT
category        TEXT    -- Stock/Sales/Testers/Packaging/Staff/Other
title           TEXT
details         TEXT
severity        TEXT    -- Low/Medium/High/Critical
status          TEXT    -- Open/In Progress/Resolved/Closed
raised_date     DATE
resolved_date   DATE
resolution      TEXT
logged_by       TEXT
```

### Tables Planned (not yet created)

| Table | Purpose |
|-------|---------|
| `sop_inventory_uploads` | Store inventory snapshots uploaded via S&OP portal |
| `sop_inventory_history` | Full history of inventory uploads for deviation tracking |

> **Important**: Supabase free tier pauses after 7 days of inactivity. If the database is unreachable, go to the Supabase Dashboard and click "Resume Project".

---

## 5. REGIONAL DIVISIONS & STORE CODES

### Division 1 — EPP UAE (Emirates Pride Direct)
**Status**: ✅ Sales data in Supabase (Jan 2025 – Apr 2026)

| Store Code | Location |
|-----------|---------|
| DX001 | Dubai Mall |
| DX004 | Mall of Emirates |
| DX005 | Mirdif City Centre |
| DX006 | Dubai Hills |
| A0001–A0009 | Abu Dhabi stores |
| SH001 | Zahia City Centre (Sharjah) |
| AJ001 | Ajman City Centre |
| RK001, RK002 | Manar Mall (RAK) |
| FJ001 | Fujairah City Centre |
| AL001–AL006 | Al Ain stores |

### Division 2 — ASL UAE (Franchise Stores)
**Status**: ⏳ NOT YET UPLOADED — waiting for Excel files
- Same pivot format as EPP data
- Will use ASL-prefixed store codes

### Division 3 — Oman (3 Stores)
**Status**: ⏳ Data extracted, JSON ready, NOT YET uploaded to Supabase

| Store Code | Store Name | Type |
|-----------|-----------|------|
| `OM001` | Mall Of Oman | EPP Direct |
| `OM002` | Muscat City Centre | EPP Direct |
| `OM_ASL001` | ASL-Mall Of Oman | ASL Franchise |

### Division 4 — KSA (Saudi Arabia)
**Status**: ⏳ DEFERRED — no data yet

---

## 6. SKU COLLECTIONS — FULL REFERENCE

### Master File
**Path**: `C:\Users\AMALKANDATHIL\OneDrive - Emirates Pride Perfumes Trading\Desktop\Master file-New.xlsx`
**Sheet**: `FG STOCK`
**Total SKUs**: 606 across all brands

### SKU Prefix Reference

| Prefix | Collection | Brand | Notes |
|--------|-----------|-------|-------|
| `C00xxx` | Caballo Collection | EPP | C00002–C00014 |
| `B00xxx` | Bel Collection | EPP | B00001–B00021, includes -PB variants |
| `O0000x` | Oud | EPP | O00001–O00008 |
| `D0000x` | Dakhoon | EPP | D00001–D00008 |
| `SP0xxx` | Sets & Specials | EPP | Includes Future Collection |
| `BX0xxx` | Gift Boxes | EPP | Unboxed gift sets |
| `HR0xxx` | Heritage Collection | EPP | HR0001–HR0007 |
| `DIF-xxx` | Reed Diffusers | EPP | DIF-001 = Future Oud Diffuser |
| `SPGxxx` | Samplers | EPP | SPG001, SPG002 |
| `AC0xxx` | Accessories | EPP | Charcoal, lighters, etc. |
| `AP0xx` | ASL Perfumes | ASL | AP001–AP011 |
| `AO0xx` | ASL Oils | ASL | AO001–AO011 |
| `AH0xx` | ASL Hair & Body Mist | ASL | |
| `AG0xx` | ASL Gift Sets | ASL | AG001–AG016 |
| `ADS0x` | ASL Discovery Sets | ASL | ADS01, ADS03, ADS04 |
| `AOGxxx` | ASL Gift Oils | ASL | AOG001–AOG011 |
| `ASLAOS-xxx` | ASL All Over Sprays | ASL | |
| `RM2-xxx` | RIMAL | Other | |
| `SR3-xxx` | Serenity | Other | |
| `FS1-xxx` | Flower Scent | Other | |

### Future Collection SKUs (⚠️ MISSING from Supabase sales_history)

| SKU | Product Name | Has Tester? | In Supabase Sales? | In Benchmarks? |
|-----|-------------|------------|-------------------|----------------|
| `SP0037` | Future Bakhoor 100ml | Yes | ❌ No | ❌ No |
| `SP0038` | Future Oud 100ml | Yes | ❌ No | ❌ No |
| `SP0039` | Future Traditional Set 2×100ml | No | ❌ No | ❌ No |
| `DIF-001` | Future Oud Reed Diffuser | No | ❌ No | ❌ No |
| `SPG001` | Future Bakhoor 1.5ml Sampler | No | ❌ No | ❌ No |
| `SPG002` | Future Oud 1.5ml Sampler | No | ❌ No | ❌ No |

> **Action required**: Check original EPP UAE Excel files for Future Collection sales. If data exists, re-extract and upload. Also check tester records in `transfer_history` for SP0037 and SP0038.

---

## 7. WHAT HAS BEEN BUILT — FULL DEVELOPMENT LOG

### Phase 1 — Stock Register (stock-register.html)
- Weekly spreadsheet-style stock tracker per store
- Shows opening stock, GRN, inter-store transfers in/out, testers issued, sales, closing balance
- Store PIN login system (each store has unique PIN + manager override 9999)
- Warehouse PIN 8888 for WH staff
- Color-coded UI: dark `#0f1824`, gold `#C9A84C`, navy `#1a2744`
- All data reads/writes directly to Supabase

### Phase 2 — Operations 2.0 (index.html)
- Daily operations interface for store staff
- Record sales per SKU
- GRN receipts (goods received from warehouse)
- Inter-store transfer requests
- Tester issuance tracking
- All transactions write to Supabase `transfer_history`

### Phase 3 — FG-to-Tester Workflow
- `fg-request-form.html` — store staff submits conversion request
- `fg-approve.html` — manager approves/rejects requests
- `fg-report.html` — audit report of all conversions
- Tracks which full bottles (FG) were converted to testers

### Phase 4 — Demand Planning Dashboard (demand-planning-dashboard.html)
- Reads benchmarks from `benchmarks_cache` in Supabase
- Shows reorder priorities, min/max stock targets per SKU per store
- Used for monthly demand planning cycle
- Manager access only

### Phase 5 — Data Pipeline (Python scripts + JSON files)
- Parsed EPP UAE Excel pivot files (Jan 2025 – Apr 2026)
- Uploaded 17,267 rows to `sales_history`
- Built benchmark calculations → uploaded 1,458 rows to `benchmarks_cache`
- Parsed Oman Excel files (Oct 2025 – Mar 2026) → `oman_sales_upload.json` ready
- SKU master extracted → `sku_master.json` (606 SKUs)
- Handled edge cases: no SKU codes in Oct–Dec 2025 Oman sheets (mapped by product name)

### Phase 6 — S&OP Portal (sop-portal.html) — Built May 2026
- Password: `Vinayak@1998` — required every login, no session persistence

#### Tab 1 — SALES
- Units sold only (no revenue)
- View A: All stores side-by-side for selected period
- View B: SKU performance matrix across stores and months
- Filters: Region (EPP/ASL/Oman/KSA), Store, Month, Quarter, Year
- Fiscal quarters: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
- MoM trend table
- CSV export

#### Tab 2 — INVENTORY
- Excel upload (drag & drop or file browse)
- Auto-detects column structure
- First upload = full replace; subsequent uploads = deviation report
- History stored in localStorage (interim — migration to Supabase planned)
- Shows last snapshot + full upload history
- CSV export per store

#### Tab 3 — TESTERS
- 5 mandatory KPIs: issued, FG→tester conversions, wastage/write-offs, live count, conversion rate
- Per-store breakdown table
- Top 20 SKUs by tester activity
- Data source: Supabase `transfer_history`

### Phase 7 — Intelligence & Warehouse Tabs (stock-register.html)
- Intelligence tab: per-SKU analysis — identifies slow movers, fast movers, out-of-stock risk
- Warehouse tab: consolidated view across all stores for warehouse staff
- Production delivery schedule integration (parses weekly production Excel)
- Fixed product name lookup using `item_spec_name` + transfers as fallback

### Phase 8 — Security Layer (May 2026)
- **PIN migration**: All PINs removed from source code → stored in Supabase `store_pins` with RLS; only `verify_store_pin()` RPC returns boolean
- **Audit log**: Every LOGIN, LOGOUT, WRITE, FAILED_LOGIN event written to `audit_log`; server-side trigger on `stock_cells` for tamper-proof backup
- **Session tracking**: `store_sessions` table tracks who is logged in, when, from what device
- **Anomaly detection**: Off-hours writes (22:00–06:00 UAE), large qty (>100), rapid writes (>25/min), 3 failed logins all trigger alerts
- **Email alerts**: Supabase Edge Function `security-alert` sends branded HTML email via Resend (3,000/month free)
- **Security dashboard**: "🔐 Security Log" button in MGR view — active sessions panel + flagged event table with filters
- **GitHub hardened**: Repo made private; `.gitignore` blocks `pin_inserts.sql`, `*.env`, `secrets.json`

### Phase 9 — Brand Redesign (May 2026)
- **Light theme**: Full audit and replacement of all dark backgrounds (`#1A1A1A`, `#141414`, `rgba(0,0,0,0.88)`) → brand light palette
- **Color system**: `--gold-bar: #6B5B35` (olive-gold) replaces navy `#1a2744` for all dark headers via CSS alias
- **Font stack upgraded**: Cormorant Garamond (luxury serif for KPIs/headings) + Montserrat (body/buttons) + IBM Plex Mono (codes/numbers)
- **Login screen**: Executive dark glass-morphism login retained as deliberate cinematic entry point (only dark screen in app)
- **Training Guide**: Upgraded to v9 — new sections for Sales Associate, Area Manager, Security; updated hero stats; animated

### Phase 10 — FG Tester Manager Portal (May 2026)
- **`fg-tester-manager.html`**: Standalone password-gated portal (`Vinayak@1998`) to review and action FG-to-Tester requests
- Stats strip: live pending/approved/rejected counts
- Filter chips: All / Pending / Approved / Rejected
- Approve → prompts approver name → updates Supabase → downloads PDF
- Reject → prompts approver name + reason → updates Supabase → downloads PDF
- Re-download PDF on already-processed cards
- Area Manager login access control: AM logins see filtered dashboard (their stores only); Demand Planning button hidden from AM

### Phase 11 — AM Hub (May 2026)
- **`am-stock-request.html`**: Mobile-first 4-screen stock request form for Area Managers
  - 163 perfume SKUs + 40 testers + 4 supplies (bags S/M/L, tissue paper)
  - Bilingual EN+AR product names and category pills
  - Inline qty controls in browse screen (no scroll jump via in-place DOM update)
  - Generates `AMR-YYYYMMDD-XXXX` ref, saves to Supabase, downloads bilingual PDF
- **AM Hub panel** in `stock-register.html` (MGR access): 4 tabs
  - **Weekly Requests**: table of all submissions from `am_weekly_requests`; Approve / Dispatch / PDF per row; CSV + PDF export
  - **AM Sessions**: log calls/WhatsApp/meetings per AM; timeline view per AM from Supabase
  - **Issue Log**: raise and track issues per store (Stock/Sales/Testers/Packaging/Staff/Other); severity + status workflow
  - **Daily TODO**: AM checklist (morning stock updates, AM check-ins, tester reviews, weekly tasks); localStorage per day
- AM assignments: Hessin = 17 stores (Abu Dhabi + Al Ain), Imad = 4 stores (Dubai), Elmatloub = 6 stores (Northern + Eastern)

---

## 8. PENDING BUILD QUEUE

| Priority | Task | Status |
|----------|------|--------|
| 🔴 HIGH | Upload `oman_sales_upload.json` to Supabase `sales_history` | Ready — needs upload |
| 🔴 HIGH | Check Future Collection sales in original EPP Excel files and upload missing data | Investigation needed |
| 🟡 MED | Provide ASL UAE Excel sales files for upload | Pending |
| 🟡 MED | Create `sop_inventory_uploads` table in Supabase (migrate from localStorage) | Not started |
| 🟡 MED | Add kiosk store list — apply 50% capacity multiplier to benchmarks | Pending |
| 🟡 MED | Rotate all store PINs before go-live (old PINs were briefly in GitHub README) | Critical security action |
| 🟢 LOW | S&OP Inventory tab — Excel upload + deviation report | Spec ready in CLAUDE.md |
| 🟢 LOW | S&OP Testers tab — 5 KPIs from Supabase | Spec ready in CLAUDE.md |
| 🟢 LOW | Store replenishment schedule — confirm delivery days with warehouse | Template in INTELLIGENCE_SKILL.md |
| 🟢 LOW | Monthly Excel auto-upload script with new month detection | Not started |
| 🟢 LOW | KSA stores and sales data | Deferred — no data |
| 🟢 LOW | Sales targets input form | Future feature |
| 🟢 LOW | Top/Bottom 10 SKU ranking per region | Future feature |
| 🟢 LOW | Cross-region comparison dashboard | Future feature |

---

## 9. DESIGN SYSTEM

All files use these consistent styles (updated to light brand theme May 2026):

```css
--gold:       #C9A84C   /* Primary brand gold */
--gold-dark:  #7A6525   /* Headings, store codes, active text */
--gold-bar:   #6B5B35   /* Olive-gold — ALL dark headers, topbars, category separators */
--gold-pale:  #F5F2EC   /* Card tint — website product card background */
--border:     #E5E0D8   /* Standard separator */
--ink:        #1A1A1A   /* Primary text */
--ink-mid:    #4A4540   /* Secondary text */
--ink-light:  #8A8278   /* Muted — column headers, sub-labels */
--page:       #FFFFFF   /* Page background — pure white */
--navy:       #6B5B35   /* ALIAS for gold-bar — all legacy navy refs auto-remap */
```

**Typography system**:
```
Headings / KPI numbers / Store names → Cormorant Garamond 500–600 (luxury serif)
Body / Labels / Buttons / Tabs       → Montserrat 400–700 (geometric sans)
SKU codes / Numbers / Timestamps     → IBM Plex Mono 400–600 (technical)
Arabic text                          → IBM Plex Sans Arabic 400–600
```

**Login screen**: Intentional exception — executive dark glass-morphism theme. All other screens are light brand palette.

**Login pattern**: Full-screen overlay `position:fixed; inset:0` — password checked via Supabase `verify_store_pin()` RPC (async), no server auth beyond that, no session storage.

**Libraries loaded via CDN** (no npm, no build step — all plain HTML/JS):
- **SheetJS (xlsx)** — Excel file parsing for inventory uploads
- **Supabase JS client** — database reads/writes

---

## 10. HOW TO SET UP ON A NEW MACHINE / LOGIN

1. **Copy the entire project folder** to `Desktop\Emirates Pride Stock Register\` (or any path)
2. **Open any `.html` file directly in Chrome** — all static, no server needed for local use
3. **For live site**: push to GitHub repo `vinayak682/emirates-pride-inventory-management` → GitHub Pages serves it
4. **Supabase connection** is hardcoded in every HTML file — the anon key above is already embedded, no setup needed
5. **To upload data** (Oman JSON etc.): use the Supabase Dashboard → Table Editor → Import, or run the upload via the S&OP portal Excel upload feature
6. **Claude AI context**: open the project folder in Claude Code — `CLAUDE.md` in the root automatically loads all project context

---

## 11. KNOWN DATA GAPS

| Gap | Detail | Action |
|-----|--------|--------|
| Future Collection — EPP UAE sales | SP0037, SP0038, SP0039, DIF-001, SPG001, SPG002 have ZERO rows in `sales_history` | Check original Excel → re-upload |
| Future Collection — benchmarks | No benchmarks exist for any Future Collection SKU | Seed manually or calculate after sales data is added |
| Future Collection — tester data | Unknown — check `transfer_history` in Supabase for SP0037/SP0038 | Query Supabase dashboard |
| Oman sales | JSON ready but not uploaded to Supabase | Upload `oman_sales_upload.json` |
| ASL UAE sales | No data received yet | Waiting for Excel files |
| KSA | No data | Deferred |
| Kiosk capacity list | 5 kiosks confirmed, full list pending | Pending |

---

*This document is the single source of truth for the Emirates Pride Operations Platform.*
*Update it whenever credentials, tables, or major features change.*
