-- ═══════════════════════════════════════════════════════════════
-- EMIRATES PRIDE — WhatsApp Scanner Supabase Setup
-- Run this ONCE in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql
-- ═══════════════════════════════════════════════════════════════

-- ── scanner_log: tracks every store's daily scan result ──────────
CREATE TABLE IF NOT EXISTS scanner_log (
  id               BIGSERIAL PRIMARY KEY,
  store_code       TEXT NOT NULL,
  scan_date        DATE NOT NULL,
  store_name       TEXT,
  group_name       TEXT,

  -- Status: pending | scanning | complete | review | no_images | error | upload_error
  status           TEXT DEFAULT 'pending',

  -- Counts
  images_found     INTEGER DEFAULT 0,
  images_processed INTEGER DEFAULT 0,
  skus_extracted   INTEGER DEFAULT 0,
  cells_uploaded   INTEGER DEFAULT 0,
  confidence_avg   FLOAT,

  -- Review data (JSONB arrays — editable from dashboard)
  review_items     JSONB DEFAULT '[]'::jsonb,
  extracted_data   JSONB DEFAULT '[]'::jsonb,

  -- Error detail
  error_message    TEXT,

  -- Timestamps
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (store_code, scan_date)
);

-- Index for dashboard queries
CREATE INDEX IF NOT EXISTS idx_scanner_log_date     ON scanner_log (scan_date DESC);
CREATE INDEX IF NOT EXISTS idx_scanner_log_status   ON scanner_log (status);
CREATE INDEX IF NOT EXISTS idx_scanner_log_store    ON scanner_log (store_code);

-- ── RLS: allow anon read/write (scanner uses anon key) ───────────
ALTER TABLE scanner_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "scanner_log_anon_all"
  ON scanner_log FOR ALL
  TO anon
  USING (true)
  WITH CHECK (true);

-- ── scanner_config: group-name mapping (editable via dashboard) ──
CREATE TABLE IF NOT EXISTS scanner_config (
  id          BIGSERIAL PRIMARY KEY,
  store_code  TEXT UNIQUE NOT NULL,
  store_name  TEXT,
  group_name  TEXT,
  active      BOOLEAN DEFAULT TRUE,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE scanner_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "scanner_config_anon_all"
  ON scanner_config FOR ALL
  TO anon
  USING (true)
  WITH CHECK (true);

-- ── Verification query ────────────────────────────────────────────
SELECT table_name, pg_size_pretty(pg_total_relation_size(table_name::regclass)) AS size
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('scanner_log', 'scanner_config', 'stock_cells')
ORDER BY table_name;
