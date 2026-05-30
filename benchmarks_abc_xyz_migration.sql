-- Emirates Pride — Add ABC×XYZ columns to benchmarks_cache
-- Run this ONCE in Supabase SQL Editor before running classify_minmax.py

ALTER TABLE benchmarks_cache
  ADD COLUMN IF NOT EXISTS abc_class      TEXT    DEFAULT 'C',
  ADD COLUMN IF NOT EXISTS xyz_class      TEXT    DEFAULT 'X',
  ADD COLUMN IF NOT EXISTS sku_category   TEXT    DEFAULT 'Regular',
  ADD COLUMN IF NOT EXISTS peak_month_avg NUMERIC DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cov_pct        NUMERIC DEFAULT NULL;

-- Index for fast lookups in the Stock Guide
CREATE INDEX IF NOT EXISTS idx_bench_category ON benchmarks_cache(sku_category);
CREATE INDEX IF NOT EXISTS idx_bench_abc      ON benchmarks_cache(abc_class);

-- Verify
SELECT
  sku_category,
  abc_class,
  xyz_class,
  COUNT(*) AS rows
FROM benchmarks_cache
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
