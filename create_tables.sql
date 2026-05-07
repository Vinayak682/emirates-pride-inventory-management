
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
