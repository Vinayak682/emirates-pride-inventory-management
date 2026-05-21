# Emirates Pride — Intelligence Tab Skill
## S&OP Intelligence, Replenishment Planning & Proactive Notification System
**Version**: 2.0 | **Owner**: Amal Kandathil, Demand Planner | **Last Updated**: May 2026

---

## 1. PURPOSE & VISION

The Intelligence Tab is the **operational brain** of the Emirates Pride S&OP Portal. It transforms raw Supabase data from 5 sources (Sales, WH Stock, WH Transfers, Production, Consumables) into actionable, proactive guidance for the warehouse team at **Nad Al Hammar**.

**The system answers 4 questions every day:**
1. Which stores need a delivery TODAY or THIS WEEK?
2. Which SKUs are at risk of stocking out before the next delivery?
3. Is the warehouse stocked to cover all scheduled deliveries?
4. Are non-product items (bags, packing, promo) at any store about to run out?

---

## 2. DATA SOURCES & SUPABASE TABLES

### Currently Active Tables

| Table | Key Columns | Used For |
|-------|-------------|---------|
| `sales_history` | sku_code, store_code, month_year, qty_sold | Weekly velocity calculation per SKU per store |
| `wh_stock_on_hand` | sku_code, item_name, item_spec_name, qty, division, snapshot_date | Current WH inventory levels |
| `wh_transfers` | sku_code, item_name, to_location_code, qty_transferred, transfer_date, division | Last delivery date per store per SKU; replenishment history |
| `production_history` | sku_code, product_name, planned_fg_qty, actual_fg_qty, plan_date, record_status | Production pipeline tracking |
| `benchmarks_cache` | sku_code, store_code, weekly_avg, min_monthly, max_monthly | Pre-calculated velocity benchmarks |
| `sales_targets` | sku_code, store_code, month_year, target_qty | Achievement gap analysis |

### AM Hub Tables (created May 2026)

| Table | Key Columns | Used For |
|-------|-------------|---------|
| `am_weekly_requests` | request_ref, am_code, store_code, week_starting, items (JSONB), status | Weekly stock requests from Area Managers — demand signal per store per week |
| `am_feedback_sessions` | am_code, session_date, session_type, stock_notes, tester_notes, action_items | Call/WhatsApp/meeting logs for each AM |
| `am_issues_log` | am_code, store_code, category, severity, status, title, details | Issue tracker per store — Stock/Sales/Testers/Packaging/Staff/Other |

> **Intelligence value of `am_weekly_requests`**: The `items` JSONB column (array of `{code, qty}` per SKU) gives store-level demand signals that can supplement velocity calculations — especially for new SKUs or spike periods. Future enhancement: cross-reference AM requests vs benchmark replenishment quantities to flag discrepancies.

### Required New Tables (not yet created)

#### `store_replenishment_schedule`
```sql
CREATE TABLE store_replenishment_schedule (
  id            BIGSERIAL PRIMARY KEY,
  store_code    TEXT NOT NULL UNIQUE,
  store_name    TEXT,
  delivery_days TEXT NOT NULL,    -- "MON,THU" or "WED" etc.
  lead_time_days INT DEFAULT 1,   -- days from WH pick to store delivery
  safety_days   INT DEFAULT 3,    -- buffer days before reordering
  driver_name   TEXT,
  route_name    TEXT,             -- e.g. "Dubai North Route"
  min_order_qty INT DEFAULT 10,
  active        BOOLEAN DEFAULT TRUE,
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE store_replenishment_schedule ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON store_replenishment_schedule FOR ALL USING (true) WITH CHECK (true);
```

#### `consumable_items`
```sql
CREATE TABLE consumable_items (
  item_code   TEXT PRIMARY KEY,
  item_name   TEXT NOT NULL,
  category    TEXT NOT NULL,  -- 'BAGS', 'PACKING', 'PROMO', 'STATIONERY', 'MISC'
  subcategory TEXT,           -- e.g. 'BAGS_LARGE', 'BAGS_SMALL'
  unit        TEXT DEFAULT 'pcs',
  reorder_threshold INT DEFAULT 50,  -- universal floor; per-store override in consumable_stock
  active      BOOLEAN DEFAULT TRUE
);
-- Standard seed data
INSERT INTO consumable_items (item_code, item_name, category, subcategory, unit, reorder_threshold) VALUES
  ('BAG-S',    'Shopping Bag — Small',    'BAGS',       'BAGS_SMALL',  'pcs', 200),
  ('BAG-M',    'Shopping Bag — Medium',   'BAGS',       'BAGS_MED',    'pcs', 200),
  ('BAG-L',    'Shopping Bag — Large',    'BAGS',       'BAGS_LARGE',  'pcs', 100),
  ('BAG-XL',   'Shopping Bag — X-Large',  'BAGS',       'BAGS_XL',     'pcs', 50),
  ('TISSUE',   'Tissue Wrapping Paper',   'PACKING',    NULL,          'sheets', 500),
  ('RIBBON',   'Gift Ribbon Roll',        'PACKING',    NULL,          'rolls', 10),
  ('BUBBLEWRAP','Bubble Wrap Roll',       'PACKING',    NULL,          'rolls', 5),
  ('TAPE',     'Packing Tape',            'PACKING',    NULL,          'rolls', 10),
  ('RECEIPT',  'Receipt Roll Paper',      'STATIONERY', NULL,          'rolls', 5),
  ('LEAFLET',  'Product Leaflet A5',      'PROMO',      NULL,          'pcs', 100),
  ('TESTER-BTL','Empty Tester Bottle',    'PROMO',      NULL,          'pcs', 20),
  ('GIFT-BOX-S','Gift Box — Small',       'PACKING',    NULL,          'pcs', 50),
  ('GIFT-BOX-L','Gift Box — Large',       'PACKING',    NULL,          'pcs', 20);
```

#### `consumable_stock`
```sql
CREATE TABLE consumable_stock (
  id            BIGSERIAL PRIMARY KEY,
  item_code     TEXT NOT NULL REFERENCES consumable_items(item_code),
  store_code    TEXT NOT NULL,
  qty_on_hand   INT NOT NULL DEFAULT 0,
  weekly_usage  NUMERIC(8,1) DEFAULT 0,  -- manually set or auto-calc from transactions
  reorder_qty   INT DEFAULT 0,           -- per-store override of consumable_items.reorder_threshold
  snapshot_date DATE NOT NULL,
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(item_code, store_code, snapshot_date)
);
ALTER TABLE consumable_stock ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON consumable_stock FOR ALL USING (true) WITH CHECK (true);
```

#### `store_alerts` (persistent alert log — optional for v1)
```sql
CREATE TABLE store_alerts (
  id              BIGSERIAL PRIMARY KEY,
  store_code      TEXT NOT NULL,
  alert_type      TEXT NOT NULL,  -- 'STOCKOUT','LOW_COVER','DEAD_STOCK','REPLEN_DUE','CONSUMABLE_LOW','TARGET_GAP'
  severity        TEXT NOT NULL,  -- 'CRITICAL','WARNING','INFO'
  sku_code        TEXT,
  item_code       TEXT,
  message         TEXT NOT NULL,
  data_json       JSONB,          -- additional context
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by TEXT
);
CREATE INDEX idx_alerts_store ON store_alerts(store_code, created_at DESC);
ALTER TABLE store_alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON store_alerts FOR ALL USING (true) WITH CHECK (true);
```

---

## 3. REPLENISHMENT CYCLE SPECIFICATION

### Nad Al Hammar Warehouse → Store Delivery Schedule

**To be confirmed by Amal and warehouse team.** Template below:

| Store Code | Store Name | Delivery Days | Frequency | Lead Time | Route |
|-----------|-----------|--------------|-----------|-----------|-------|
| DX001 | Dubai Mall | MON, THU | 2x/week | 1 day | Dubai Route 1 |
| DX004 | Mall of Emirates | MON, THU | 2x/week | 1 day | Dubai Route 1 |
| DX005 | Mirdif City Centre | TUE, FRI | 2x/week | 1 day | Dubai Route 2 |
| DX006 | Dubai Hills Mall | TUE, FRI | 2x/week | 1 day | Dubai Route 2 |
| A0001 | Bawabat al Sharq | TUE, SAT | 2x/week | 1 day | Abu Dhabi Route |
| A0003 | Dalma Mall | TUE, SAT | 2x/week | 1 day | Abu Dhabi Route |
| A0009 | Yas Mall | WED, SAT | 2x/week | 1 day | Abu Dhabi Route |
| SH001 | Zahia City Centre | WED | 1x/week | 1 day | Northern Route |
| AJ001 | Ajman City Centre | WED | 1x/week | 1 day | Northern Route |
| RK001 | Manar Mall | THU | 1x/week | 1 day | Northern Route |
| FJ001 | Fujairah CC | THU | 1x/week | 2 days | Eastern Route |
| AL001–006 | Al Ain stores | SAT | 1x/week | 2 days | Al Ain Route |
| OM001 | Mall Of Oman | MON | 1x/week | 3 days | Oman (courier) |
| OM002 | Muscat City Centre | MON | 1x/week | 3 days | Oman (courier) |

> ⚠ **ACTION NEEDED**: Confirm actual delivery days with warehouse manager. Update `store_replenishment_schedule` table in Supabase once confirmed.

---

## 4. INTELLIGENCE VIEWS — FULL SPECIFICATION

### View 1 — Proactive Alerts Dashboard (DEFAULT)
**Who uses it**: Warehouse manager every morning before picking starts  
**What it shows**:
- Per-severity counts (CRITICAL / WARNING / INFO)
- Per-store alert cards — collapsed by default, expand on click
- For each store: which SKUs to include in next delivery + why
- WH availability check per alert
- "Generate Order Sheet" button → exports a pick list for the warehouse

**Alert Types and Triggers**:

| Alert Type | Severity | Trigger Condition |
|-----------|---------|------------------|
| `STOCKOUT_RISK` | CRITICAL | WH stock for SKU < 2 weeks cover AND that SKU's weekly velocity > 10 |
| `OVERDUE_DELIVERY` | CRITICAL | Store's last received transfer > 1.5× delivery interval |
| `LOW_WH_COVER` | WARNING | WH stock / weekly velocity between 2–4 weeks |
| `DEAD_STOCK` | WARNING | WH qty > 0 AND no transfers to ANY store in 56+ days |
| `TARGET_GAP` | WARNING | Store achievement < 80% of monthly target with <10 days left in month |
| `CONSUMABLE_LOW` | WARNING | Store consumable qty < reorder_threshold |
| `PRODUCTION_DELAY` | INFO | Production plan status = 'not_produced' AND plan_date < today |
| `NEW_REPLEN_NEEDED` | INFO | WH stock > 0 AND SKU not transferred in 30+ days to a store that sells it |

### View 2 — Store Replenishment Plan
**Who uses it**: Warehouse picking team  
**What it shows**:
- Per-store order sheet based on next delivery date
- Calculates recommended qty = weekly_velocity × (delivery_interval + safety_days)
- Checks WH availability before recommending
- Export button → downloadable order sheet per store or all stores
- Colour-coded urgency (URGENT / PLAN AHEAD / OK)

### View 3 — SKU Coverage (WH-level)
- All SKUs sorted by cover weeks ascending
- Risk levels: CRITICAL (<2wk), WATCH (2–4wk), SAFE (>4wk)
- Shows production pipeline arrival date

### View 4 — Fast Movers
- Top 30 by weekly velocity
- WH cover weeks
- Trigger: REPLENISH NOW if <2wk cover

### View 5 — Slow Movers / Dead Stock
- Dead stock: in WH, no transfers in 56 days
- Slow sellers: <5 units/week
- Recommendation: promote/mark down vs. transfer

### View 6 — Replenishment History
- Per-store aggregate of all WH→store transfers
- Timeline: last 30 / 90 / 180 days toggle
- Top SKU received per store

### View 7 — Production Delivery Tracker
- Planned vs actual FG by week
- Variance + status colours
- Links to WH coverage (when expected production will arrive)

### View 8 — Consumables & Non-Product Items
- Per-store consumable stock levels (when `consumable_stock` table is populated)
- Alert when any item < reorder threshold
- Weekly usage rate + estimated runout date
- Category filters: BAGS / PACKING / PROMO / STATIONERY / MISC

---

## 5. NOTIFICATION SYSTEM ARCHITECTURE

### Current (v1 — in-browser only)
```
Supabase → JavaScript → Dynamic DOM → Alert badges + nav-dot indicator
```
No persistence, no push, no history. Resets on page refresh.

### Target (v2 — persistent + proactive)
```
Supabase scheduled function (pg_cron) → store_alerts table → 
  ↓ webhook trigger
  ↓ WhatsApp Business API (Cloud) / email
  ↓ In-app notification center reads store_alerts + marks acknowledged
```

**v2 Implementation Steps**:
1. Enable `pg_cron` in Supabase (available on Pro plan)
2. Write a PostgreSQL function `fn_generate_store_alerts()` that evaluates all trigger conditions nightly at 06:00 UAE time and writes to `store_alerts`
3. Configure a Supabase webhook to hit a Vercel Edge Function on INSERT to `store_alerts`
4. Vercel Edge Function calls WhatsApp Business Cloud API for CRITICAL alerts
5. In-app alert center reads unacknowledged rows from `store_alerts` on load

---

## 6. VELOCITY CALCULATION METHODOLOGY

```
weekly_velocity(sku, store) =
  SUM(qty_sold WHERE store_code = store AND sku_code = sku) 
  ÷ COUNT(DISTINCT month_year WHERE above)   ← actual months with data
  × 12 ÷ 52                                  ← annualise → weekly
```

**Rules**:
- Minimum 2 months of data required for a reliable velocity
- Seasonal spike detection: if any single month > 3× the average → flag as seasonal SKU
- New SKUs (<2 months data): use category average as proxy until data accumulates

### Coverage Calculation
```
wh_cover_weeks(sku) = wh_stock_on_hand(sku) ÷ total_weekly_velocity(sku)
store_cover_days(sku, store) = est_store_stock ÷ (store_weekly_velocity / 7)
```

### Replenishment Quantity Formula
```
rec_qty(sku, store) = 
  store_weekly_velocity × (delivery_interval_days + safety_days) / 7
  − current_store_stock_estimate (if available from stock_cells)
  (floored at 0, rounded up to nearest 10)
```

---

## 7. TAB DATA LINKING MAP

```
┌─────────────────────────────────────────────────────────┐
│                    DATA FLOW                             │
│                                                         │
│  Sales Tab           → salesData[]                      │
│  Targets (View C)    → targetsCache{}                   │
│  Warehouse Tab       → whStock{}, whTransfers[]         │
│  Production Tab      → prodPlan[], prodHistory[]        │
│  Intelligence Tab    → reads ALL of the above           │
│                                                         │
│  Intelligence checks:                                   │
│  1. If salesData[] populated (Sales tab loaded) → reuse │
│  2. Otherwise → load from Supabase directly             │
│  3. Same for all other data sources                     │
│                                                         │
│  Notification triggers from Intelligence → write to     │
│  store_alerts table → visible in ALL tab nav-dots       │
└─────────────────────────────────────────────────────────┘
```

---

## 8. PROCESS FLOW — DAILY S&OP INTELLIGENCE CYCLE

```
06:30 UAE — Warehouse Opens
  ↓
  Open S&OP Portal → Intelligence Tab auto-loads
  ↓
  ALERT DASHBOARD shows:
  - Which stores have overdue deliveries
  - Which SKUs hit CRITICAL cover (< 2 weeks)
  - Any consumables below threshold
  ↓
  Switch to STORE REPLENISHMENT PLAN view
  ↓
  Check each store card — expand for SKU detail
  ↓
  Click "Generate Order Sheet" → PDF/CSV pick list for WH team
  ↓
  WH team picks and loads van
  ↓
  Delivery recorded in stock-register.html (GRN at store)
  ↓
  wh_transfers table updated → Intelligence re-calculates
```

---

## 9. BUILD STATUS & PENDING ITEMS

| # | Feature | Status | Blocker |
|---|---------|--------|---------|
| 1 | Proactive Alerts Dashboard (View 1) | ✅ Built v1 | — |
| 2 | Store Replenishment Plan (View 2) | ✅ Built v1 | Replenishment schedule data needed |
| 3 | SKU Coverage (View 3) | ✅ Complete | — |
| 4 | Fast Movers (View 4) | ✅ Complete | — |
| 5 | Slow Movers / Dead Stock (View 5) | ✅ Complete | — |
| 6 | Replenishment History (View 6) | ✅ Complete | — |
| 7 | Production Delivery Tracker (View 7) | ✅ Complete | — |
| 8 | Consumables View (View 8) | 🔲 Framework only | consumable_stock table needs data |
| 9 | store_replenishment_schedule table + SQL | 🔲 SQL written, not created | Run SQL in Supabase |
| 10 | consumable_items + consumable_stock tables | 🔲 SQL written, not created | Run SQL in Supabase |
| 11 | Per-store delivery calendar UI | 🔲 Not started | Schedule data from Amal |
| 12 | WhatsApp notification integration | 🔲 Not started | WhatsApp Business API key |
| 13 | pg_cron nightly alert generation | 🔲 Not started | Supabase Pro plan required |
| 14 | Tab data sharing (reuse cached data) | ✅ Built | — |
| 15 | Export order sheet (PDF/CSV) | 🔲 Partially (CSV) | — |

---

## 10. SUPABASE SQL — RUN THESE IN ORDER

```sql
-- 1. Store Replenishment Schedule
CREATE TABLE IF NOT EXISTS store_replenishment_schedule (
  id            BIGSERIAL PRIMARY KEY,
  store_code    TEXT NOT NULL UNIQUE,
  store_name    TEXT,
  delivery_days TEXT NOT NULL,
  lead_time_days INT DEFAULT 1,
  safety_days   INT DEFAULT 3,
  driver_name   TEXT,
  route_name    TEXT,
  min_order_qty INT DEFAULT 10,
  active        BOOLEAN DEFAULT TRUE,
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE store_replenishment_schedule ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_replen" ON store_replenishment_schedule FOR ALL USING (true) WITH CHECK (true);

-- 2. Consumable Items Master
CREATE TABLE IF NOT EXISTS consumable_items (
  item_code   TEXT PRIMARY KEY,
  item_name   TEXT NOT NULL,
  category    TEXT NOT NULL,
  subcategory TEXT,
  unit        TEXT DEFAULT 'pcs',
  reorder_threshold INT DEFAULT 50,
  active      BOOLEAN DEFAULT TRUE
);
ALTER TABLE consumable_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_cons_items" ON consumable_items FOR ALL USING (true) WITH CHECK (true);

-- 3. Consumable Stock (per store snapshot)
CREATE TABLE IF NOT EXISTS consumable_stock (
  id            BIGSERIAL PRIMARY KEY,
  item_code     TEXT NOT NULL,
  store_code    TEXT NOT NULL,
  qty_on_hand   INT NOT NULL DEFAULT 0,
  weekly_usage  NUMERIC(8,1) DEFAULT 0,
  reorder_qty   INT DEFAULT 0,
  snapshot_date DATE NOT NULL,
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(item_code, store_code, snapshot_date)
);
ALTER TABLE consumable_stock ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_cons_stock" ON consumable_stock FOR ALL USING (true) WITH CHECK (true);

-- 4. Store Alerts Log (for persistent notification history)
CREATE TABLE IF NOT EXISTS store_alerts (
  id              BIGSERIAL PRIMARY KEY,
  store_code      TEXT NOT NULL,
  alert_type      TEXT NOT NULL,
  severity        TEXT NOT NULL,
  sku_code        TEXT,
  item_code       TEXT,
  message         TEXT NOT NULL,
  data_json       JSONB,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_store ON store_alerts(store_code, created_at DESC);
ALTER TABLE store_alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all_alerts" ON store_alerts FOR ALL USING (true) WITH CHECK (true);
```

---

---

## 11. STANDING UPDATE INSTRUCTION

**At the end of EVERY conversation, Claude must update:**
1. `CLAUDE.md` → PROJECT DETAILS section (session log, files changed, commit hash)
2. `INTELLIGENCE_SKILL.md` → new tables, new views, build status changes
3. `MASTER_REFERENCE.md` → new files, schema changes, phase completions, pending queue updates

This applies to all sessions without exception.

---

*This skill file documents the complete S&OP Intelligence system for Emirates Pride Perfumes.*
*Last updated: 20 May 2026 | Cross-reference: MASTER_REFERENCE.md, CLAUDE.md*
