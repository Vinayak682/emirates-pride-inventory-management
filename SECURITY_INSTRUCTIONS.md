# Emirates Pride Stock Register — Security Instructions
## Last Updated: 19 May 2026

---

## WHAT IS PROTECTED AND HOW

The stock register has 4 layers of security running at all times:

| Layer | What it does | Where it runs |
|-------|-------------|---------------|
| Session Tracking | Every login creates a unique session record | Supabase `store_sessions` table |
| Audit Log | Every cell change saved with old → new value | Supabase `audit_log` table |
| Anomaly Detection | Flags suspicious activity automatically | Inside `stock-register.html` JS |
| Email Alerts | Sends email to manager when anomaly detected | Supabase Edge Function (Resend) |

---

## ANOMALY THRESHOLDS (what triggers a flag)

| Anomaly | Threshold | Why |
|---------|-----------|-----|
| Off-hours access | Any login or edit after 10 PM or before 6 AM UAE time | No legitimate store activity should happen at these hours |
| Large quantity | Any single cell value above 100 units | Accidental or malicious data entry |
| Rapid fire edits | More than 25 cell changes in 60 seconds | Could indicate bulk data manipulation |
| Failed PIN attempts | 3 consecutive wrong PINs for same store | Someone trying to guess a store PIN |

To change these thresholds, update the `security_config` table in Supabase:
```sql
UPDATE security_config SET value = '30' WHERE key = 'max_writes_per_minute';
UPDATE security_config SET value = '150' WHERE key = 'large_qty_threshold';
UPDATE security_config SET value = '23' WHERE key = 'off_hours_start';
```

---

## HOW TO USE THE SECURITY LOG DASHBOARD

1. Open stock-register.html on any device
2. Log in with Manager PIN (9999)
3. Click **"All Stores Dashboard"** button in the top bar
4. Click **"🔐 Security Log"** button (red button, top right of dashboard)

### What you see:
- **Active Sessions** — who is logged in right now, which device (iPad/desktop), login time, last active time
- **Events log** — every LOGIN, LOGOUT, WRITE, FAILED_LOGIN with full details
- **Red rows** — flagged/suspicious entries with the reason shown

### Filters available:
- **All Stores / specific store** — filter to one store's activity
- **Today / Last 7 Days / Last 30 Days / All Time** — date range
- **Flagged Only** toggle — show only suspicious entries

---

## EMAIL ALERT SETUP

**Provider**: Resend (resend.com) — Free tier: 3,000 emails/month

**Secrets stored in Supabase** (Edge Functions → security-alert → Secrets):
| Secret Name | Value |
|-------------|-------|
| `RESEND_API_KEY` | API key from resend.com (starts with `re_`) |
| `ALERT_EMAIL` | Email address where alerts are sent |

**What the email looks like**:
- Subject: `🚨 Security Alert — DX001 | Off-hours activity at 23:14 UAE time`
- Body: Emirates Pride branded email with store name, action, record key, UAE timestamp
- Sent within seconds of the anomaly being detected
- 5-minute cooldown between alerts (prevents spam during legitimate bulk operations)

### To update the alert email address:
1. Go to Supabase → Edge Functions → Secrets
2. Find `ALERT_EMAIL` → click edit → change value → save

### To regenerate the Resend API key (do this if key is ever exposed):
1. Go to resend.com → log in
2. Click **API Keys** in left sidebar
3. Delete the old key
4. Click **Create API Key** → copy the new key
5. Go to Supabase → Edge Functions → Secrets → update `RESEND_API_KEY`

---

## SUPABASE TABLES REFERENCE

### `store_sessions`
Tracks every login session.
```
session_id   — unique ID for this login session
store_code   — which store logged in (e.g. DX001, MGR, AM_NORTH)
login_type   — store / mgr / am / wh
login_at     — when they logged in (UTC, convert to UAE = +4 hours)
last_active  — last heartbeat (updates every 5 minutes while active)
expires_at   — auto-expires after 10 hours
is_active    — true = currently logged in, false = logged out
user_agent   — browser/device info (shows iPad, Chrome, etc.)
```

### `audit_log`
Every event across all stores.
```
id           — unique entry number
session_id   — links back to store_sessions
store_code   — which store this event belongs to
operation    — LOGIN / LOGOUT / WRITE / FAILED_LOGIN / LOCK / APPROVE
record_key   — exact record changed e.g. "DX001/2026-05-19/AP001/sold"
old_value    — value before the change
new_value    — value after the change
changed_at   — timestamp (UTC)
is_flagged   — true if anomaly was detected
flag_reason  — explanation of why it was flagged
```

### Useful queries to run in Supabase SQL editor:

**See all activity today:**
```sql
SELECT store_code, operation, record_key, old_value, new_value, changed_at
FROM audit_log
WHERE changed_at >= CURRENT_DATE
ORDER BY changed_at DESC;
```

**See all flagged entries:**
```sql
SELECT store_code, operation, flag_reason, record_key, changed_at
FROM audit_log
WHERE is_flagged = true
ORDER BY changed_at DESC;
```

**See who is currently logged in:**
```sql
SELECT store_code, login_type, login_at, last_active, user_agent
FROM store_sessions
WHERE is_active = true
ORDER BY login_at DESC;
```

**See all changes to a specific store:**
```sql
SELECT operation, record_key, old_value, new_value, changed_at
FROM audit_log
WHERE store_code = 'DX001'
ORDER BY changed_at DESC
LIMIT 100;
```

**See all changes to a specific SKU:**
```sql
SELECT store_code, operation, old_value, new_value, changed_at
FROM audit_log
WHERE record_key LIKE '%AP001%'
ORDER BY changed_at DESC;
```

---

## GITHUB REPOSITORY SECURITY

**Repo**: `Vinayak682/emirates-pride-inventory-management` (PRIVATE)

| Protection | Status | Notes |
|------------|--------|-------|
| Private repo | ✅ Done | Source code not visible to public |
| 2FA on GitHub account | ✅ Done | Email + SMS |
| All-activity notifications | ✅ Done | Email on every push/change |
| Branch protection | Not set | Rely on manual review before merging |

### If you receive a GitHub activity email you did not expect:
1. Immediately go to GitHub → Settings → Security → **Review active sessions**
2. Click **"Revoke all other sessions"**
3. Change your GitHub password
4. Check the Supabase audit log for any suspicious database activity

---

## SERVER-SIDE BACKUP TRIGGER

In addition to the client-side audit log, there is a **Postgres trigger** (`trg_audit_stock_cells`) on the `stock_cells` table. This fires on every INSERT/UPDATE/DELETE directly in the database.

This means: even if someone bypasses the frontend entirely and writes directly to Supabase using the anon key, those changes are still logged in `audit_log` with `metadata.source = 'server_trigger'`.

To verify the trigger is active:
```sql
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_name = 'trg_audit_stock_cells';
```

---

## WHAT TO DO WHEN YOU RECEIVE A SECURITY ALERT EMAIL

1. **Read the flag reason** — is it expected? (e.g. a manager working late is normal)
2. **Open Manager Dashboard → 🔐 Security Log** — filter to that store and time
3. **Check the record key** — e.g. `DX001/2026-05-19/AP001/sold` — was this a legitimate edit?
4. **Check old → new value** — does the change make sense?
5. **Check active sessions** — is the session still open? Which device?

### If the change looks wrong:
- Note the exact record key and values
- Contact the store directly
- If data was corrupted: the old_value is saved in audit_log — you can restore it manually
- If someone's PIN was compromised: change that store's PIN in the STORES array in stock-register.html

---

## EDGE FUNCTION DEPLOYMENT (if ever needed again)

The Edge Function is deployed at:
`https://ncszurcrkngjcjqsowln.supabase.co/functions/v1/security-alert`

To redeploy after code changes:
1. Go to Supabase → Edge Functions → security-alert → Open Editor
2. Replace code with contents of `supabase/functions/security-alert/index.ts`
3. Click Deploy

---

## CONTACTS & CREDENTIALS REFERENCE

| Service | URL | Purpose |
|---------|-----|---------|
| Supabase Dashboard | supabase.com/dashboard/project/ncszurcrkngjcjqsowln | Database, Edge Functions, Secrets |
| Supabase SQL Editor | supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql | Run queries on audit_log |
| Resend Dashboard | resend.com | Email API key management |
| GitHub Repo | github.com/Vinayak682/emirates-pride-inventory-management | Source code (PRIVATE) |
| Live Site | vinayak682.github.io/emirates-pride-inventory-management/ | What iPads load |

---
*Document maintained by Claude (Demand Planning AI) | Emirates Pride Perfumes*
*Update this file whenever security configuration changes*
