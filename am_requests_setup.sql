-- ══════════════════════════════════════════════════════════════════
-- EMIRATES PRIDE — AM HUB TABLES SETUP
-- Run this in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql
-- ══════════════════════════════════════════════════════════════════

-- ── TABLE 1: Weekly Stock Requests (from am-stock-request.html form) ──
CREATE TABLE IF NOT EXISTS am_weekly_requests (
  id              BIGSERIAL PRIMARY KEY,
  request_ref     TEXT NOT NULL UNIQUE,           -- e.g. AMR-20260520-1234
  am_code         TEXT NOT NULL,                  -- AM_HESSIN / AM_IMAD / AM_ELMAT
  am_name         TEXT NOT NULL,
  store_code      TEXT NOT NULL,                  -- DX001, A0001, etc.
  store_name      TEXT NOT NULL,
  week_starting   DATE NOT NULL,
  items           JSONB NOT NULL DEFAULT '[]',    -- [{code, en, ar, qty, cat}]
  notes           TEXT DEFAULT '',
  status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','dispatched','cancelled')),
  submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  approved_by     TEXT,
  approved_at     TIMESTAMPTZ,
  dispatched_by   TEXT,
  dispatched_at   TIMESTAMPTZ,
  dispatch_notes  TEXT
);

-- ── TABLE 2: AM Feedback Sessions (call / WhatsApp logs) ──
CREATE TABLE IF NOT EXISTS am_feedback_sessions (
  id              BIGSERIAL PRIMARY KEY,
  am_code         TEXT NOT NULL,                  -- AM_HESSIN / AM_IMAD / AM_ELMAT
  am_name         TEXT NOT NULL,
  session_date    DATE NOT NULL,
  session_type    TEXT NOT NULL DEFAULT 'Call' CHECK (session_type IN ('Call','WhatsApp','Meeting','Visit')),
  duration_mins   INTEGER,
  stock_notes     TEXT DEFAULT '',                -- What was discussed re: stock
  tester_notes    TEXT DEFAULT '',                -- Tester feedback
  sales_notes     TEXT DEFAULT '',                -- Sales feedback
  general_notes   TEXT DEFAULT '',                -- Other feedback / suggestions
  action_items    TEXT DEFAULT '',                -- Follow-up actions agreed
  logged_by       TEXT DEFAULT 'Amal',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── TABLE 3: AM Issues Log (issue tracker per store) ──
CREATE TABLE IF NOT EXISTS am_issues_log (
  id              BIGSERIAL PRIMARY KEY,
  am_code         TEXT NOT NULL,
  am_name         TEXT NOT NULL,
  store_code      TEXT,
  store_name      TEXT,
  category        TEXT NOT NULL DEFAULT 'Stock' CHECK (category IN ('Stock','Sales','Testers','Packaging','Staff','Other')),
  title           TEXT NOT NULL,                  -- Short description
  details         TEXT DEFAULT '',                -- Full details
  severity        TEXT NOT NULL DEFAULT 'Medium' CHECK (severity IN ('Low','Medium','High','Critical')),
  status          TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','In Progress','Resolved','Closed')),
  raised_date     DATE NOT NULL DEFAULT CURRENT_DATE,
  resolved_date   DATE,
  resolution      TEXT DEFAULT '',
  logged_by       TEXT DEFAULT 'Amal',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── RLS: Allow anon read + insert for all 3 tables ──
ALTER TABLE am_weekly_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE am_feedback_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE am_issues_log ENABLE ROW LEVEL SECURITY;

-- am_weekly_requests: anyone can insert (AM form), only anon can read (manager dashboard)
CREATE POLICY "anon_insert_requests"   ON am_weekly_requests FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon_read_requests"     ON am_weekly_requests FOR SELECT TO anon USING (true);
CREATE POLICY "anon_update_requests"   ON am_weekly_requests FOR UPDATE TO anon USING (true);

-- am_feedback_sessions: manager-only in practice (same anon key, no PIN check at DB level)
CREATE POLICY "anon_all_sessions"      ON am_feedback_sessions FOR ALL TO anon USING (true) WITH CHECK (true);

-- am_issues_log: manager-only in practice
CREATE POLICY "anon_all_issues"        ON am_issues_log        FOR ALL TO anon USING (true) WITH CHECK (true);

-- ── INDEXES for fast queries ──
CREATE INDEX IF NOT EXISTS idx_amreq_am_code    ON am_weekly_requests (am_code);
CREATE INDEX IF NOT EXISTS idx_amreq_status     ON am_weekly_requests (status);
CREATE INDEX IF NOT EXISTS idx_amreq_week       ON am_weekly_requests (week_starting DESC);
CREATE INDEX IF NOT EXISTS idx_amsess_am_code   ON am_feedback_sessions (am_code);
CREATE INDEX IF NOT EXISTS idx_amsess_date      ON am_feedback_sessions (session_date DESC);
CREATE INDEX IF NOT EXISTS idx_amiss_am_code    ON am_issues_log (am_code);
CREATE INDEX IF NOT EXISTS idx_amiss_status     ON am_issues_log (status);

-- ── VERIFY (run after setup) ──
-- SELECT table_name FROM information_schema.tables WHERE table_name IN ('am_weekly_requests','am_feedback_sessions','am_issues_log');
