-- ═══════════════════════════════════════════════════════════════════════════
-- Emirates Pride — ABC×XYZ Classifier  (rewritten — no complex CTEs)
-- Run in Supabase SQL Editor. Safe to re-run.
-- ═══════════════════════════════════════════════════════════════════════════

-- STEP 1: Add columns (already done — safe to re-run)
ALTER TABLE benchmarks_cache
  ADD COLUMN IF NOT EXISTS abc_class      TEXT    DEFAULT 'C',
  ADD COLUMN IF NOT EXISTS xyz_class      TEXT    DEFAULT 'X',
  ADD COLUMN IF NOT EXISTS sku_category   TEXT    DEFAULT 'Regular',
  ADD COLUMN IF NOT EXISTS peak_month_avg NUMERIC DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cov_pct        NUMERIC DEFAULT NULL;

-- ───────────────────────────────────────────────────────────────────────────
-- STEP 2: CoV % and peak_month_avg from sales_history
-- ───────────────────────────────────────────────────────────────────────────
UPDATE benchmarks_cache bc
SET
  cov_pct        = s.cov_val,
  peak_month_avg = s.peak_avg
FROM (
  SELECT
    sku_code,
    store_code,
    ROUND(
      CASE WHEN AVG(mq) > 0
           THEN STDDEV(mq) / AVG(mq) * 100
           ELSE NULL END
    ::NUMERIC, 1) AS cov_val,
    -- Average of top-2 months
    ROUND((
      (array_agg(mq ORDER BY mq DESC))[1]
      + COALESCE((array_agg(mq ORDER BY mq DESC))[2], (array_agg(mq ORDER BY mq DESC))[1])
    ) / 2.0, 1) AS peak_avg
  FROM (
    SELECT sku_code, store_code, SUM(COALESCE(qty_sold,0)) AS mq
    FROM sales_history
    GROUP BY sku_code, store_code, month_year
  ) monthly
  GROUP BY sku_code, store_code
) s
WHERE bc.sku_code = s.sku_code AND bc.store_code = s.store_code;

-- ───────────────────────────────────────────────────────────────────────────
-- STEP 3: XYZ — based on CoV
-- ───────────────────────────────────────────────────────────────────────────
UPDATE benchmarks_cache SET xyz_class = 'X' WHERE cov_pct < 30;
UPDATE benchmarks_cache SET xyz_class = 'Y' WHERE cov_pct >= 30 AND cov_pct < 70;
UPDATE benchmarks_cache SET xyz_class = 'Z' WHERE cov_pct >= 70 OR cov_pct IS NULL;

-- ───────────────────────────────────────────────────────────────────────────
-- STEP 4: ABC — per SKU total volume across all stores
-- ───────────────────────────────────────────────────────────────────────────
UPDATE benchmarks_cache bc
SET abc_class = ranks.abc
FROM (
  SELECT
    sku_code,
    CASE
      WHEN SUM(total) OVER (ORDER BY total DESC
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::FLOAT
           / NULLIF(SUM(total) OVER (), 0) <= 0.70 THEN 'A'
      WHEN SUM(total) OVER (ORDER BY total DESC
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::FLOAT
           / NULLIF(SUM(total) OVER (), 0) <= 0.90 THEN 'B'
      ELSE 'C'
    END AS abc
  FROM (
    SELECT sku_code, SUM(COALESCE(qty_sold,0)) AS total
    FROM sales_history GROUP BY sku_code
  ) t
) ranks
WHERE bc.sku_code = ranks.sku_code;

-- ───────────────────────────────────────────────────────────────────────────
-- STEP 5: SKU Category — in priority order (each overwrites previous)
-- ───────────────────────────────────────────────────────────────────────────

-- 5a. Start everyone as Regular
UPDATE benchmarks_cache SET sku_category = 'Regular';

-- 5b. FastMovers — high weekly velocity (A or B class perfumes/oils/regular SKUs)
-- These are NEVER overridden by Seasonal — they get a smaller Eid multiplier in JS
UPDATE benchmarks_cache
SET sku_category = 'FastMover'
WHERE weekly_avg >= 15;

-- 5c. Seasonal — ONLY explicitly seasonal product families (gift sets, bakhoor sets, dakhoon)
-- CoV condition REMOVED — regular perfumes can have high CoV but are not Eid-driven gift items
UPDATE benchmarks_cache
SET sku_category = 'Seasonal'
WHERE
  sku_code LIKE 'BX%'
  OR sku_code LIKE 'AG%'
  OR sku_code IN (
    'SP0009','SP0029','SP0037','SP0038','SP0039',
    'SP0013','SP0012','SP0005','SP0030','SP0031',
    'D00001','D00002','D00003','D00004','D00005','D00006','D00007','D00008'
  );

-- 5d. DeadStock — check ACTUAL sales_history for last 3 months, not stale benchmark date
UPDATE benchmarks_cache bc
SET sku_category = 'DeadStock'
WHERE
  (bc.weekly_avg IS NULL OR bc.weekly_avg = 0)
  OR NOT EXISTS (
    SELECT 1 FROM sales_history sh
    WHERE sh.sku_code   = bc.sku_code
      AND sh.store_code = bc.store_code
      AND sh.qty_sold   > 0
      AND TO_DATE(sh.month_year, 'YYYY-MM') >= (CURRENT_DATE - INTERVAL '3 months')
  );

-- ───────────────────────────────────────────────────────────────────────────
-- STEP 6: Verify results
-- ───────────────────────────────────────────────────────────────────────────
SELECT
  sku_category,
  abc_class,
  xyz_class,
  COUNT(*)                    AS rows,
  ROUND(AVG(weekly_avg),1)    AS avg_weekly,
  ROUND(AVG(cov_pct),1)       AS avg_cov,
  ROUND(AVG(peak_month_avg),1) AS avg_peak_month
FROM benchmarks_cache
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
