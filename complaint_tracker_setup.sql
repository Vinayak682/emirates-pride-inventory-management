-- ══════════════════════════════════════════════════════════════════
-- EMIRATES PRIDE — Customer Complaint Tracker
-- Run this ONCE in Supabase SQL Editor
-- https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql
-- ══════════════════════════════════════════════════════════════════

-- 1. MAIN COMPLAINTS TABLE
CREATE TABLE IF NOT EXISTS customer_complaints (
  id                    UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  complaint_ref         TEXT UNIQUE NOT NULL,
  store_code            TEXT NOT NULL,
  store_name            TEXT,
  submitted_by          TEXT,
  submitted_at          TIMESTAMPTZ DEFAULT NOW(),
  customer_name         TEXT NOT NULL,
  customer_phone        TEXT,
  purchase_date         DATE,
  receipt_number        TEXT,
  sku_code              TEXT,
  product_name          TEXT,
  complaint_type        TEXT NOT NULL,
  complaint_description TEXT,
  status                TEXT NOT NULL DEFAULT 'pending',
  outcome               TEXT,           -- 'replacement' | 'repair' | 'rejection' | NULL
  resolution_notes      TEXT,
  attachments           JSONB DEFAULT '[]',
  timeline              JSONB DEFAULT '[]',
  actioned_by           TEXT,
  actioned_at           TIMESTAMPTZ,
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- 2. INDEXES
CREATE INDEX IF NOT EXISTS idx_cc_store      ON customer_complaints(store_code);
CREATE INDEX IF NOT EXISTS idx_cc_status     ON customer_complaints(status);
CREATE INDEX IF NOT EXISTS idx_cc_ref        ON customer_complaints(complaint_ref);
CREATE INDEX IF NOT EXISTS idx_cc_submitted  ON customer_complaints(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_cc_outcome    ON customer_complaints(outcome);

-- 3. RLS
ALTER TABLE customer_complaints ENABLE ROW LEVEL SECURITY;

-- Allow anon to read and write (store PIN auth is handled in JS)
DROP POLICY IF EXISTS "anon_read"   ON customer_complaints;
DROP POLICY IF EXISTS "anon_insert" ON customer_complaints;
DROP POLICY IF EXISTS "anon_update" ON customer_complaints;

CREATE POLICY "anon_read"   ON customer_complaints FOR SELECT TO anon USING (true);
CREATE POLICY "anon_insert" ON customer_complaints FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "anon_update" ON customer_complaints FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- 4. VERIFY
SELECT 'customer_complaints table created ✓' AS result;
SELECT COUNT(*) AS complaint_count FROM customer_complaints;

-- ══════════════════════════════════════════════════════════════════
-- SUPABASE STORAGE SETUP (do this in the Supabase Dashboard UI)
-- ══════════════════════════════════════════════════════════════════
--
-- Go to: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/storage/buckets
--
-- 1. Click "New Bucket"
-- 2. Name: complaint-evidence
-- 3. Check "Public bucket" (so uploaded files can be viewed in the complaint detail)
-- 4. Click "Save"
--
-- Then add a storage policy:
-- Go to Storage > Policies > complaint-evidence bucket
-- Add policy: Allow anon INSERT (upload)
-- SQL for that:
--
-- INSERT INTO storage.policies (name, bucket_id, operation, definition)
-- VALUES (
--   'anon_upload_complaint_evidence',
--   'complaint-evidence',
--   'INSERT',
--   'true'
-- );
--
-- OR simply set the bucket to public with full anon access via the UI toggles.
-- ══════════════════════════════════════════════════════════════════
