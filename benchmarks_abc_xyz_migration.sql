-- ═══════════════════════════════════════════════════════════════════════════
-- Emirates Pride — ABC×XYZ SKU Classifier
-- Run this ONCE in Supabase SQL Editor (no Python needed)
-- Takes ~10 seconds. Safe to re-run — all UPDATEs are idempotent.
-- ═══════════════════════════════════════════════════════════════════════════

-- STEP 1: Add new columns (safe — IF NOT EXISTS)
ALTER TABLE benchmarks_cache
  ADD COLUMN IF NOT EXISTS abc_class      TEXT    DEFAULT 'C',
  ADD COLUMN IF NOT EXISTS xyz_class      TEXT    DEFAULT 'X',
  ADD COLUMN IF NOT EXISTS sku_category   TEXT    DEFAULT 'Regular',
  ADD COLUMN IF NOT EXISTS peak_month_avg NUMERIC DEFAULT 0,
  ADD COLUMN IF NOT EXISTS cov_pct        NUMERIC DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_bench_category ON benchmarks_cache(sku_category);
CREATE INDEX IF NOT EXISTS idx_bench_abc      ON benchmarks_cache(abc_class);

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 2: Classify all SKUs and update benchmarks_cache in one query
-- ═══════════════════════════════════════════════════════════════════════════
WITH

-- Monthly sales per SKU-store
monthly AS (
  SELECT
    sku_code,
    store_code,
    month_year,
    SUM(COALESCE(qty_sold, 0)) AS mq
  FROM sales_history
  GROUP BY sku_code, store_code, month_year
),

-- Stats per SKU-store: mean, stddev, CoV, peak-month avg
sku_store_stats AS (
  SELECT
    sku_code,
    store_code,
    COUNT(*)                                              AS months_n,
    ROUND(AVG(mq)::NUMERIC, 2)                           AS avg_monthly,
    ROUND(STDDEV(mq)::NUMERIC, 2)                        AS std_monthly,
    CASE WHEN AVG(mq) > 0
         THEN ROUND((STDDEV(mq) / AVG(mq) * 100)::NUMERIC, 1)
         ELSE NULL END                                   AS cov_pct,
    -- Average of top-2 months (Eid/Ramadan peak baseline)
    ROUND((
      SELECT AVG(v) FROM (
        SELECT mq AS v FROM monthly m2
        WHERE m2.sku_code = m.sku_code AND m2.store_code = m.store_code
        ORDER BY mq DESC LIMIT 2
      ) t
    )::NUMERIC, 1)                                       AS peak_month_avg
  FROM monthly m
  GROUP BY sku_code, store_code
),

-- Total units sold per SKU across all stores (for ABC)
sku_totals AS (
  SELECT sku_code, SUM(COALESCE(qty_sold,0)) AS total
  FROM sales_history
  GROUP BY sku_code
),

-- ABC: cumulative revenue share → A ≤70%, B ≤90%, C rest
abc AS (
  SELECT
    sku_code,
    CASE
      WHEN SUM(total) OVER (ORDER BY total DESC
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
           ::FLOAT / NULLIF(SUM(total) OVER (), 0) <= 0.70 THEN 'A'
      WHEN SUM(total) OVER (ORDER BY total DESC
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
           ::FLOAT / NULLIF(SUM(total) OVER (), 0) <= 0.90 THEN 'B'
      ELSE 'C'
    END AS abc_class
  FROM sku_totals
),

-- Final classification join
classified AS (
  SELECT
    s.sku_code,
    s.store_code,
    COALESCE(a.abc_class, 'C')                           AS abc_class,

    -- XYZ: X = stable (CoV<30), Y = variable (30-70), Z = irregular (>70 or <3 months)
    CASE
      WHEN s.months_n < 3      THEN 'Z'
      WHEN s.cov_pct < 30      THEN 'X'
      WHEN s.cov_pct < 70      THEN 'Y'
      ELSE                          'Z'
    END                                                   AS xyz_class,

    s.cov_pct,
    COALESCE(s.peak_month_avg, 0)                        AS peak_month_avg,

    -- SKU Category (combines XYZ + known seasonal families + dead stock)
    CASE
      -- Dead stock: no weekly_avg in benchmarks OR last sale > 4 months ago
      WHEN bc.weekly_avg IS NULL OR bc.weekly_avg = 0     THEN 'DeadStock'
      WHEN bc.last_sale_month IS NOT NULL
           AND TO_DATE(bc.last_sale_month, 'YYYY-MM')
               < (CURRENT_DATE - INTERVAL '4 months')    THEN 'DeadStock'

      -- Seasonal: gift-set / bakhoor-set families OR high CoV
      WHEN s.sku_code LIKE 'BX%'
        OR s.sku_code LIKE 'AG%'
        OR s.sku_code IN (
             'SP0009','SP0029','SP0037','SP0038','SP0039',
             'SP0013','SP0012','SP0005','SP0030','SP0031'
           )
        OR (s.cov_pct > 70 AND s.months_n >= 3)          THEN 'Seasonal'

      -- FastMover: high weekly rate and relatively stable
      WHEN bc.weekly_avg >= 20
           AND CASE WHEN s.months_n < 3 THEN 'Z'
                    WHEN s.cov_pct < 30 THEN 'X'
                    WHEN s.cov_pct < 70 THEN 'Y'
                    ELSE 'Z' END IN ('X','Y')             THEN 'FastMover'

      ELSE 'Regular'
    END                                                   AS sku_category

  FROM sku_store_stats s
  LEFT JOIN abc a            ON a.sku_code    = s.sku_code
  LEFT JOIN benchmarks_cache bc
                             ON bc.sku_code   = s.sku_code
                            AND bc.store_code = s.store_code
)

-- STEP 3: Apply to benchmarks_cache
UPDATE benchmarks_cache bc
SET
  abc_class      = c.abc_class,
  xyz_class      = c.xyz_class,
  sku_category   = c.sku_category,
  peak_month_avg = c.peak_month_avg,
  cov_pct        = c.cov_pct
FROM classified c
WHERE bc.sku_code   = c.sku_code
  AND bc.store_code = c.store_code;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 4: Verify — shows breakdown of what was classified
-- ═══════════════════════════════════════════════════════════════════════════
SELECT
  sku_category,
  abc_class,
  xyz_class,
  COUNT(*)              AS rows,
  ROUND(AVG(cov_pct),1) AS avg_cov_pct
FROM benchmarks_cache
WHERE sku_category IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
