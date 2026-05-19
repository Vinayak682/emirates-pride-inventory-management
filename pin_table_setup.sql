-- =============================================================
-- EMIRATES PRIDE — PIN SECURITY MIGRATION
-- Step 1: Run THIS file in Supabase SQL Editor first
-- Step 2: Then run pin_inserts.sql (NEVER commit that file to git)
-- =============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. CREATE store_pins TABLE
--    No RLS policy = anon role CANNOT read this table at all
--    Only the verify function (SECURITY DEFINER) can access it
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS store_pins (
  store_code  TEXT        PRIMARY KEY,
  pin         TEXT        NOT NULL,
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Block ALL direct access from anon key
ALTER TABLE store_pins ENABLE ROW LEVEL SECURITY;
-- Intentionally NO policies created — zero access for anon role

-- ─────────────────────────────────────────────────────────────
-- 2. VERIFICATION FUNCTION
--    App calls this with (store_code, pin_entered)
--    Returns only TRUE or FALSE — actual PIN never leaves DB
--    SECURITY DEFINER = runs as postgres, bypasses RLS
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION verify_store_pin(p_code TEXT, p_pin TEXT)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM store_pins
    WHERE store_code = p_code
    AND   pin        = p_pin
  );
$$;

-- Allow anon to CALL the function (but still cannot read the table)
GRANT EXECUTE ON FUNCTION verify_store_pin(TEXT, TEXT) TO anon;

-- ─────────────────────────────────────────────────────────────
-- 3. PIN UPDATE FUNCTION (for when you need to change a PIN)
--    Only callable with service role key — not from the app
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_store_pin(p_code TEXT, p_new_pin TEXT)
RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  INSERT INTO store_pins (store_code, pin, updated_at)
  VALUES (p_code, p_new_pin, now())
  ON CONFLICT (store_code)
  DO UPDATE SET pin = p_new_pin, updated_at = now();
$$;

-- Only service role can call this (NOT anon)
REVOKE EXECUTE ON FUNCTION update_store_pin(TEXT, TEXT) FROM anon;
GRANT  EXECUTE ON FUNCTION update_store_pin(TEXT, TEXT) TO service_role;

-- =============================================================
-- DONE. Now run pin_inserts.sql in the SQL editor.
-- NEVER commit pin_inserts.sql to GitHub.
-- =============================================================
