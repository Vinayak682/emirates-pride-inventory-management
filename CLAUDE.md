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

Amal Kandathil is the Demand Planner at Emirates Pride. Primary responsibilities:
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
2. [ ] ASL UAE sales data — waiting for files from Amal
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

### Session — 19 May 2026 (Session 4 — Area Manager Logins)
**Files changed**: `stock-register.html`
**Commit**: `947baec` (worktree) → `db4f971` (merged to main)
**Pushed to**: `main` branch → GitHub Pages live

#### What was done:
- Read `Area Manager details.xlsx` — found **3 area managers** (user said "3 or 4"):
  1. **Mohamed Hessin** — Abu Dhabi + Al Ain (EPP + ASL): 17 stores — PIN `1000`
  2. **Mohammed Imad Muwfaq Saleh** — Dubai (EPP): 4 stores — PIN `3000`
  3. **Mohammed Elmatloub** — RAK, Sharjah, Ajman, Fujairah EPP+ASL — PIN `4000`
- Added 3 AM entries to `STORES` array (codes `AM_HESSIN`, `AM_IMAD`, `AM_ELMAT`) each with `amStores` array
- AM login flow: identical to MGR — opens filtered dashboard showing only their stores, logout on close
- Fixed wrong `mgr` assignments vs Excel: DX001–DX006 corrected to Imad; FJ001A corrected to Elmatloub; removed duplicate FJ001A
- Added `isAmSession` + `amManagedStores` globals
- `buildStoreSelect()` — AM options in a separate "Area Managers" optgroup
- `renderMgrDashboard()` — filters `allStores` to `amManagedStores` when `isAmSession`
- All `STORES.filter()` calls patched to exclude `AM_*` and `WH001` codes

#### Next steps for AM feature:
- Add Oman stores to STORES and assign to Mohammed Elmatloub
- User to confirm if a 4th area manager exists (only 3 found in Excel)

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
2. [ ] ASL UAE sales data — waiting for files from Amal
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
