-- ═══════════════════════════════════════════════════
-- EMIRATES PRIDE — Replenishment History Table Setup
-- Run this ONCE in Supabase SQL Editor before using
-- the Replenishment tab in sop-portal.html
-- ═══════════════════════════════════════════════════

-- STEP 1: Create table
CREATE TABLE IF NOT EXISTS replenishment_history (
  id             bigint generated always as identity primary key,
  dispatch_ref   text,
  dispatch_date  date NOT NULL,
  month_year     text NOT NULL,          -- 'YYYY-MM' format
  store_code     text NOT NULL,
  sku_code       text NOT NULL,
  product_name   text,
  qty_dispatched int  NOT NULL DEFAULT 0,
  dispatch_type  text DEFAULT 'Regular', -- Regular / Urgent / Event / Opening
  notes          text,
  created_at     timestamptz default now()
);

-- STEP 2: Unique constraint to allow safe upserts
-- Allows duplicate dispatch_ref=NULL rows but deduplicates on ref+store+sku+date
CREATE UNIQUE INDEX IF NOT EXISTS uq_repl_with_ref
  ON replenishment_history(dispatch_ref, dispatch_date, store_code, sku_code)
  WHERE dispatch_ref IS NOT NULL;

-- STEP 3: Performance indexes
CREATE INDEX IF NOT EXISTS idx_repl_store    ON replenishment_history(store_code);
CREATE INDEX IF NOT EXISTS idx_repl_sku      ON replenishment_history(sku_code);
CREATE INDEX IF NOT EXISTS idx_repl_month    ON replenishment_history(month_year);
CREATE INDEX IF NOT EXISTS idx_repl_date     ON replenishment_history(dispatch_date);

-- STEP 4: Enable Row Level Security
ALTER TABLE replenishment_history ENABLE ROW LEVEL SECURITY;

-- STEP 5: RLS Policies (anon key can read + write)
CREATE POLICY "anon_select_repl"
  ON replenishment_history FOR SELECT USING (true);

CREATE POLICY "anon_insert_repl"
  ON replenishment_history FOR INSERT WITH CHECK (true);

CREATE POLICY "anon_update_repl"
  ON replenishment_history FOR UPDATE USING (true);

-- STEP 6: Verify
SELECT
  COUNT(*)              as total_rows,
  COUNT(DISTINCT store_code) as stores,
  COUNT(DISTINCT sku_code)   as skus,
  MIN(dispatch_date)    as earliest,
  MAX(dispatch_date)    as latest
FROM replenishment_history;

-- Expected after setup (table empty): 0 rows — that's correct.
-- After uploading your first Excel file, re-run the SELECT to confirm.
