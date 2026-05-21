-- ============================================================
-- MIGRATION: AM Weekly Requests — Fulfillment + Approval Remarks
-- Run this in Supabase SQL Editor ONCE before using the new
-- Approve & Adjust feature in the Manager Hub.
-- Dashboard: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql
-- ============================================================

-- Add column to store manager-adjusted item quantities after approval.
-- Stores same JSONB structure as `items` but with fulfilled qty values.
ALTER TABLE am_weekly_requests
  ADD COLUMN IF NOT EXISTS fulfilled_items JSONB DEFAULT NULL;

-- Add column to store the manager's reason for any quantity adjustments.
-- e.g. "White 100ml out of stock — dispatching balance next week"
ALTER TABLE am_weekly_requests
  ADD COLUMN IF NOT EXISTS approval_remarks TEXT DEFAULT NULL;

-- Add column to store the full audit trail of every edit, draft save,
-- approval, and dispatch action taken on this request.
-- Each entry: { at, by, type, changes: [{code, en, from_qty, to_qty}], remarks }
ALTER TABLE am_weekly_requests
  ADD COLUMN IF NOT EXISTS edit_history JSONB DEFAULT '[]'::jsonb;

-- Verify the new columns are present:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'am_weekly_requests'
  AND column_name IN ('fulfilled_items','approval_remarks','edit_history');
