
-- sales_history table
CREATE TABLE IF NOT EXISTS sales_history (
  id BIGSERIAL PRIMARY KEY,
  sku_code TEXT NOT NULL,
  store_code TEXT NOT NULL,
  month_year TEXT NOT NULL,
  qty_sold INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(sku_code, store_code, month_year)
);

CREATE INDEX idx_sales_sku_store ON sales_history(sku_code, store_code);
CREATE INDEX idx_sales_month ON sales_history(month_year);

-- transfer_history table
CREATE TABLE IF NOT EXISTS transfer_history (
  id BIGSERIAL PRIMARY KEY,
  sku_code TEXT NOT NULL,
  store_code TEXT NOT NULL,
  month_year TEXT NOT NULL,
  qty_transferred INTEGER NOT NULL DEFAULT 0,
  frequency INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(sku_code, store_code, month_year)
);

CREATE INDEX idx_transfer_sku_store ON transfer_history(sku_code, store_code);

-- benchmarks_cache table
CREATE TABLE IF NOT EXISTS benchmarks_cache (
  id BIGSERIAL PRIMARY KEY,
  sku_code TEXT NOT NULL,
  store_code TEXT NOT NULL,
  weekly_avg DECIMAL(10,2),
  l30d_qty INTEGER,
  l90d_avg DECIMAL(10,2),
  min_monthly INTEGER,
  max_monthly INTEGER,
  median_monthly DECIMAL(10,2),
  total_sold_16m INTEGER,
  months_tracked INTEGER,
  last_sale_month TEXT,
  calculated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(sku_code, store_code)
);

CREATE INDEX idx_bench_sku ON benchmarks_cache(sku_code);
CREATE INDEX idx_bench_store ON benchmarks_cache(store_code);
CREATE INDEX idx_bench_velocity ON benchmarks_cache(weekly_avg);

-- data_uploads_log table
CREATE TABLE IF NOT EXISTS data_uploads_log (
  id BIGSERIAL PRIMARY KEY,
  upload_type TEXT,
  month_year TEXT,
  rows_inserted INTEGER,
  rows_updated INTEGER,
  uploaded_by TEXT,
  uploaded_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT,
  error_message TEXT
);

-- ══════════════════════════════════════════════════════════════
-- MIN/MAX OVERRIDES TABLE
-- Stores manual MIN/MAX overrides set by managers
-- ══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS min_max_overrides (
  id BIGSERIAL PRIMARY KEY,
  store_code TEXT NOT NULL,
  sku_code TEXT NOT NULL,
  min_qty INT NOT NULL,
  max_qty INT NOT NULL,
  reason TEXT, -- 'auto_calc', 'new_sku', 'dead_stock', 'manual', 'override'
  set_by TEXT,
  set_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_code, sku_code)
);

CREATE INDEX IF NOT EXISTS idx_minmax_overrides ON min_max_overrides(store_code, sku_code);

COMMENT ON TABLE min_max_overrides IS 'Manual MIN/MAX stock level overrides per store';
COMMENT ON COLUMN min_max_overrides.reason IS 'Why this override was set: auto_calc, new_sku, dead_stock, manual, override';


-- ══════════════════════════════════════════════════════════════
-- UPDATE BENCHMARKS TABLE - Add MIN/MAX columns
-- ══════════════════════════════════════════════════════════════
ALTER TABLE benchmarks ADD COLUMN IF NOT EXISTS min_stock INT DEFAULT 0;
ALTER TABLE benchmarks ADD COLUMN IF NOT EXISTS max_stock INT DEFAULT 0;
ALTER TABLE benchmarks ADD COLUMN IF NOT EXISTS calculation_reason TEXT;
ALTER TABLE benchmarks ADD COLUMN IF NOT EXISTS l90d_transfers_out INT DEFAULT 0;
ALTER TABLE benchmarks ADD COLUMN IF NOT EXISTS weekly_transfer_demand NUMERIC(10,2) DEFAULT 0;

COMMENT ON COLUMN benchmarks.min_stock IS 'Minimum stock level (typically 2-week cover)';
COMMENT ON COLUMN benchmarks.max_stock IS 'Maximum stock level (typically 4-week cover)';
COMMENT ON COLUMN benchmarks.calculation_reason IS 'How MIN/MAX was calculated: calculated_from_actuals, new_sku_category_avg, dead_stock_90d';
COMMENT ON COLUMN benchmarks.l90d_transfers_out IS 'Total units transferred OUT in last 90 days (for hub stores)';
COMMENT ON COLUMN benchmarks.weekly_transfer_demand IS 'Average weekly transfer demand (for redistribution hubs)';

