-- Supplier QC Portal — Supabase Setup
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql

-- ─── 1. SUPPLIERS ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS suppliers (
  id              BIGSERIAL PRIMARY KEY,
  supplier_code   TEXT NOT NULL UNIQUE,
  name            TEXT NOT NULL,
  country         TEXT,
  contact_name    TEXT,
  contact_email   TEXT,
  contact_phone   TEXT,
  material_types  TEXT[],  -- e.g. ['Fragrance Oil', 'Alcohol', 'Packaging']
  status          TEXT DEFAULT 'Active' CHECK (status IN ('Active','Inactive','Blacklisted')),
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 2. QC INSPECTIONS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS qc_inspections (
  id                BIGSERIAL PRIMARY KEY,
  inspection_ref    TEXT NOT NULL UNIQUE,  -- QC-2026-0001
  supplier_id       BIGINT REFERENCES suppliers(id),
  supplier_name     TEXT NOT NULL,         -- denormalised for easy querying
  shipment_ref      TEXT,                  -- PO / GRN reference
  inspection_date   DATE NOT NULL,
  inspector_name    TEXT NOT NULL,
  material_type     TEXT NOT NULL,         -- Fragrance Oil / Alcohol / Packaging / Other
  material_name     TEXT,                  -- product/item name
  batch_no          TEXT,
  qty_received      NUMERIC,
  qty_unit          TEXT DEFAULT 'kg',
  overall_result    TEXT NOT NULL CHECK (overall_result IN ('Pass','Fail','Partial Pass')),
  fail_reason       TEXT,
  action_required   TEXT CHECK (action_required IN ('None','Credit Note','Replacement','Both')),
  action_status     TEXT DEFAULT 'Pending' CHECK (action_status IN ('Pending','In Progress','Resolved','N/A')),
  notes             TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 3. QC LINE ITEMS (individual test parameters) ─────────────────────────
CREATE TABLE IF NOT EXISTS qc_line_items (
  id              BIGSERIAL PRIMARY KEY,
  inspection_id   BIGINT REFERENCES qc_inspections(id) ON DELETE CASCADE,
  parameter       TEXT NOT NULL,   -- 'Odour', 'Colour', 'Specific Gravity', etc.
  standard        TEXT,            -- expected value / spec
  actual          TEXT,            -- measured value
  result          TEXT NOT NULL CHECK (result IN ('Pass','Fail','N/A')),
  notes           TEXT
);

-- ─── 4. QC ACTIONS (Credit Notes & Replacements) ───────────────────────────
CREATE TABLE IF NOT EXISTS qc_actions (
  id                BIGSERIAL PRIMARY KEY,
  inspection_id     BIGINT REFERENCES qc_inspections(id) ON DELETE CASCADE,
  inspection_ref    TEXT NOT NULL,
  supplier_name     TEXT NOT NULL,
  action_type       TEXT NOT NULL CHECK (action_type IN ('Credit Note','Replacement')),
  reference_no      TEXT,          -- CN-2026-001 or REP-2026-001
  amount            NUMERIC,       -- for credit notes (AED)
  qty_replaced      NUMERIC,       -- for replacements
  qty_unit          TEXT,
  date_raised       DATE,
  date_expected     DATE,
  date_resolved     DATE,
  status            TEXT DEFAULT 'Pending' CHECK (status IN ('Pending','In Progress','Received','Resolved','Cancelled')),
  notes             TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 5. RLS POLICIES ───────────────────────────────────────────────────────
ALTER TABLE suppliers       ENABLE ROW LEVEL SECURITY;
ALTER TABLE qc_inspections  ENABLE ROW LEVEL SECURITY;
ALTER TABLE qc_line_items   ENABLE ROW LEVEL SECURITY;
ALTER TABLE qc_actions      ENABLE ROW LEVEL SECURITY;

-- Allow anon read + insert + update for all tables
CREATE POLICY "anon_all_suppliers"      ON suppliers      FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all_inspections"    ON qc_inspections FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all_line_items"     ON qc_line_items  FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon_all_actions"        ON qc_actions     FOR ALL TO anon USING (true) WITH CHECK (true);

-- ─── 6. SEED SUPPLIERS ─────────────────────────────────────────────────────
INSERT INTO suppliers (supplier_code, name, country, material_types, status) VALUES
  ('SUP001', 'Givaudan Middle East',     'Switzerland', ARRAY['Fragrance Oil', 'Aroma Chemicals'], 'Active'),
  ('SUP002', 'IFF Arabia',               'USA',         ARRAY['Fragrance Oil', 'Ingredients'],     'Active'),
  ('SUP003', 'Symrise Dubai',            'Germany',     ARRAY['Fragrance Oil', 'Natural Extracts'],'Active'),
  ('SUP004', 'Firmenich Gulf',           'Switzerland', ARRAY['Fragrance Oil'],                    'Active'),
  ('SUP005', 'Al Haramain Ingredients',  'UAE',         ARRAY['Oud Oil', 'Bakhoor Base'],          'Active'),
  ('SUP006', 'Arabian Oud Supplies',     'UAE',         ARRAY['Oud Oil', 'Agarwood'],              'Active'),
  ('SUP007', 'Gulf Packaging Co.',       'UAE',         ARRAY['Bottles', 'Caps', 'Packaging'],     'Active'),
  ('SUP008', 'Alkan Alcohol Trading',    'UAE',         ARRAY['Perfumery Alcohol'],                'Active')
ON CONFLICT (supplier_code) DO NOTHING;

-- ─── 7. INDEXES ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_qc_inspections_supplier  ON qc_inspections(supplier_id);
CREATE INDEX IF NOT EXISTS idx_qc_inspections_date      ON qc_inspections(inspection_date DESC);
CREATE INDEX IF NOT EXISTS idx_qc_inspections_result    ON qc_inspections(overall_result);
CREATE INDEX IF NOT EXISTS idx_qc_actions_status        ON qc_actions(status);
CREATE INDEX IF NOT EXISTS idx_qc_line_items_inspection ON qc_line_items(inspection_id);

-- Verify:
SELECT 'suppliers' AS tbl, COUNT(*) FROM suppliers
UNION ALL SELECT 'qc_inspections', COUNT(*) FROM qc_inspections
UNION ALL SELECT 'qc_line_items', COUNT(*) FROM qc_line_items
UNION ALL SELECT 'qc_actions', COUNT(*) FROM qc_actions;
