-- ============================================================
-- mac_dispatch table — phone-to-Mac task dispatch
-- Run in: Supabase SQL Editor → https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln
-- ============================================================

CREATE TABLE IF NOT EXISTS mac_dispatch (
  id            BIGSERIAL PRIMARY KEY,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  instruction   TEXT        NOT NULL,
  status        TEXT        DEFAULT 'pending'   CHECK (status IN ('pending','running','done','failed')),
  result        TEXT,
  executed_at   TIMESTAMPTZ,
  source        TEXT        DEFAULT 'dispatch'  -- 'dispatch' | 'remote'
);

-- Index so the poller only scans pending rows
CREATE INDEX IF NOT EXISTS idx_mac_dispatch_status ON mac_dispatch (status, created_at DESC);

-- Enable Row Level Security
ALTER TABLE mac_dispatch ENABLE ROW LEVEL SECURITY;

-- Policy: anon key can INSERT new tasks (phone submits with anon key)
CREATE POLICY "anon_insert" ON mac_dispatch
  FOR INSERT TO anon
  WITH CHECK (true);

-- Policy: anon key can SELECT own status updates (for status polling from phone)
CREATE POLICY "anon_select" ON mac_dispatch
  FOR SELECT TO anon
  USING (true);

-- Policy: anon key can UPDATE status (poller marks as running/done/failed)
CREATE POLICY "anon_update" ON mac_dispatch
  FOR UPDATE TO anon
  USING (true)
  WITH CHECK (true);
