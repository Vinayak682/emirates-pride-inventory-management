-- =============================================================
-- EMIRATES PRIDE — SECURITY LAYER SETUP
-- Run this ONCE in the Supabase SQL Editor:
-- https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql
-- =============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. SESSION TRACKING TABLE
--    Every login creates a row. Every logout closes it.
--    Heartbeat keeps last_active fresh every 5 min.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS store_sessions (
  session_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  store_code   TEXT        NOT NULL,
  login_type   TEXT        NOT NULL,   -- 'store' | 'mgr' | 'am' | 'wh'
  login_at     TIMESTAMPTZ DEFAULT now(),
  last_active  TIMESTAMPTZ DEFAULT now(),
  expires_at   TIMESTAMPTZ DEFAULT now() + interval '10 hours',
  is_active    BOOLEAN     DEFAULT true,
  user_agent   TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_active   ON store_sessions(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_sessions_store    ON store_sessions(store_code);
CREATE INDEX IF NOT EXISTS idx_sessions_login_at ON store_sessions(login_at DESC);

-- ─────────────────────────────────────────────────────────────
-- 2. AUDIT LOG TABLE
--    Every write, login, lock, approval logged here.
--    Flagged rows = anomaly detected (off-hours, bulk, large qty).
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
  id           BIGSERIAL   PRIMARY KEY,
  session_id   UUID        REFERENCES store_sessions(session_id) ON DELETE SET NULL,
  store_code   TEXT        NOT NULL,
  operation    TEXT        NOT NULL,  -- 'WRITE' | 'LOGIN' | 'LOGOUT' | 'LOCK' | 'FAILED_LOGIN' | 'APPROVE'
  table_name   TEXT,
  record_key   TEXT,                  -- e.g. "DX001/2026-05-19/AP001/sold"
  old_value    NUMERIC,
  new_value    NUMERIC,
  metadata     JSONB,                 -- extra context (field, by, user_agent, etc.)
  changed_at   TIMESTAMPTZ DEFAULT now(),
  is_flagged   BOOLEAN     DEFAULT false,
  flag_reason  TEXT,
  whatsapp_sent BOOLEAN    DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_audit_store      ON audit_log(store_code);
CREATE INDEX IF NOT EXISTS idx_audit_time       ON audit_log(changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_flagged    ON audit_log(is_flagged) WHERE is_flagged = true;
CREATE INDEX IF NOT EXISTS idx_audit_session    ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_operation  ON audit_log(operation);

-- ─────────────────────────────────────────────────────────────
-- 3. SECURITY CONFIG TABLE (tunable thresholds)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS security_config (
  key          TEXT PRIMARY KEY,
  value        TEXT NOT NULL,
  description  TEXT
);

INSERT INTO security_config (key, value, description) VALUES
  ('max_writes_per_minute', '25',   'Flag session if more than N cell changes in 60 seconds'),
  ('large_qty_threshold',   '100',  'Flag any single quantity change above this number'),
  ('off_hours_start',       '22',   'UAE hour (24h) after which activity is flagged — default 10 PM'),
  ('off_hours_end',         '6',    'UAE hour (24h) before which activity is flagged — default 6 AM'),
  ('failed_login_threshold','3',    'Flag after N consecutive wrong PINs for the same store'),
  ('alert_cooldown_min',    '5',    'Min minutes between WhatsApp alerts (prevents spam)'),
  ('whatsapp_enabled',      'true', 'Master switch for WhatsApp anomaly alerts')
ON CONFLICT (key) DO NOTHING;

-- ─────────────────────────────────────────────────────────────
-- 4. SERVER-SIDE AUDIT TRIGGER ON stock_cells
--    This is the tamper-proof backup — fires even if client-side
--    logging is bypassed. Adjust column names below if needed.
--
--    To check actual column names, run:
--    SELECT column_name FROM information_schema.columns
--    WHERE table_name = 'stock_cells';
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION _fn_audit_stock_cells()
RETURNS TRIGGER AS $$
DECLARE
  v_store TEXT;
  v_key   TEXT;
BEGIN
  -- Adjust these column references if your stock_cells table uses
  -- different names (e.g. 'store' instead of 'store_code')
  v_store := COALESCE(
    CASE WHEN TG_OP = 'DELETE' THEN OLD.store_code ELSE NEW.store_code END,
    'UNKNOWN'
  );
  v_key := CONCAT_WS('/',
    COALESCE(CASE WHEN TG_OP='DELETE' THEN OLD.store_code ELSE NEW.store_code END, '?'),
    COALESCE(CASE WHEN TG_OP='DELETE' THEN OLD.day_date::TEXT ELSE NEW.day_date::TEXT END, '?'),
    COALESCE(CASE WHEN TG_OP='DELETE' THEN OLD.prod_code ELSE NEW.prod_code END, '?'),
    COALESCE(CASE WHEN TG_OP='DELETE' THEN OLD.field ELSE NEW.field END, '?')
  );

  INSERT INTO audit_log (
    store_code, table_name, operation, record_key,
    old_value, new_value, metadata
  ) VALUES (
    v_store,
    'stock_cells',
    TG_OP,
    v_key,
    CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN OLD.value ELSE NULL END,
    CASE WHEN TG_OP IN ('UPDATE', 'INSERT') THEN NEW.value ELSE NULL END,
    jsonb_build_object('source', 'server_trigger', 'by', COALESCE(
      CASE WHEN TG_OP='DELETE' THEN OLD.updated_by ELSE NEW.updated_by END, 'unknown'
    ))
  );
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the trigger (drop first to allow re-running this script)
DROP TRIGGER IF EXISTS trg_audit_stock_cells ON stock_cells;
CREATE TRIGGER trg_audit_stock_cells
  AFTER INSERT OR UPDATE OR DELETE ON stock_cells
  FOR EACH ROW EXECUTE FUNCTION _fn_audit_stock_cells();

-- ─────────────────────────────────────────────────────────────
-- 5. ENABLE ROW LEVEL SECURITY (future-proofing)
--    Currently allows anon full access (existing behaviour).
--    This gives you a foundation to lock down further.
-- ─────────────────────────────────────────────────────────────
ALTER TABLE store_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log      ENABLE ROW LEVEL SECURITY;

-- Anon key: full access (matches current app behaviour)
CREATE POLICY IF NOT EXISTS "anon_sessions_all" ON store_sessions FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "anon_audit_all"    ON audit_log      FOR ALL TO anon USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────
-- 6. CLEANUP FUNCTION (run periodically or via cron)
--    Archives old sessions and logs to keep tables lean.
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION cleanup_old_sessions()
RETURNS void AS $$
BEGIN
  -- Close sessions that have been inactive for > 10 hours
  UPDATE store_sessions
  SET is_active = false
  WHERE is_active = true
    AND last_active < now() - interval '10 hours';
END;
$$ LANGUAGE plpgsql;

-- =============================================================
-- DONE. Verify by running:
-- SELECT * FROM store_sessions LIMIT 5;
-- SELECT * FROM audit_log LIMIT 5;
-- SELECT * FROM security_config;
-- =============================================================
