# DEMAND PLANNING DASHBOARD — SETUP INSTRUCTIONS

## 🎯 OVERVIEW

This system stores 16+ months of sales history in Supabase and auto-calculates demand planning benchmarks. You'll upload new monthly sales data via a simple process, and benchmarks update automatically.

---

## 📋 STEP 1: CREATE SUPABASE TABLES

1. **Login to Supabase**: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln
2. **Go to**: SQL Editor (left sidebar)
3. **Click**: "+ New Query"
4. **Copy-paste** the entire contents of `create_tables.sql` (in this repo)
5. **Click**: "RUN" button
6. **Wait** ~5 seconds until you see "Success"

**What this creates:**
- `sales_history` table (17,267 rows of sales data)
- `transfer_history` table (for future consumption reports)
- `benchmarks_cache` table (1,458 SKU-store benchmarks)
- `data_uploads_log` table (audit trail)

---

## 📊 STEP 2: UPLOAD INITIAL SALES DATA

### Option A: Supabase UI (Easiest)

1. **Go to**: Table Editor → `sales_history` table
2. **Click**: "Insert" dropdown → "Import from JSON"
3. **Upload**: `sales_history_upload.json` (1.9 MB file in this repo)
4. **Wait** ~30 seconds
5. **Verify**: Table shows 17,267 rows

### Option B: Supabase CLI (Faster for large files)

```bash
# Install Supabase CLI if not installed
npm install -g supabase

# Login
supabase login

# Link project
supabase link --project-ref ncszurcrkngjcjqsowln

# Upload data
supabase db push --db-url "your_connection_string" < sales_history_upload.json
```

---

## 🎯 STEP 3: UPLOAD BENCHMARKS

**Same process as sales data:**

1. **Go to**: Table Editor → `benchmarks_cache` table
2. **Click**: "Insert" → "Import from JSON"
3. **Upload**: `benchmarks_upload.json` (403 KB in this repo)
4. **Verify**: Table shows 1,458 rows

---

## ✅ STEP 4: VERIFY IT WORKS

1. **Open**: https://vinayak682.github.io/emirates-pride-inventory-management/stock-register.html
2. **Login as MGR** (PIN: 9999)
3. **Click**: 📈 Demand Planning button
4. **Wait** 2-3 seconds for data to load
5. **You should see**:
   - 593 overstock items
   - 36 reorder priorities
   - Store performance scorecard with velocity metrics

**If you see an error:**
- Check browser console (F12) for errors
- Verify Supabase tables exist
- Verify data was uploaded (check row counts)

---

## 🔄 MONTHLY UPDATE PROCESS

### When you get new monthly sales data (e.g., May 2026):

**1. Prepare Excel file** (same format as before):
   - Product Code | Product Name | Store1 | Store2 | ...
   - Export from your ERP/BI system

**2. Run the Python script:**

```bash
python3 monthly_sales_upload.py May_2026_Sales.xlsx
```

This script will:
- Parse the Excel
- Match SKUs to stock codes
- Generate new sales records
- **INSERT** into Supabase `sales_history` table
- **RECALCULATE** all benchmarks
- **UPDATE** `benchmarks_cache` table
- Log the upload in `data_uploads_log`

**3. Dashboard auto-updates** — no manual refresh needed

---

## 🛡️ DATA PROTECTION & SECURITY

### ✅ What's Protected:

1. **Sales data is private** — Supabase Row Level Security (RLS) enabled
   - Only authenticated users can read
   - Only MGR role can write
   
2. **No public access** — Data only accessible via:
   - Your iPad app (authenticated)
   - Demand Planning Dashboard (MGR login required)

3. **Audit trail** — Every upload logged with:
   - Who uploaded (MGR/user)
   - When (timestamp)
   - How many rows inserted/updated
   - Success/error status

### 🔐 Supabase Security Settings:

**Already configured:**
- Anon key is READ-ONLY
- Service role key (WRITE access) NOT exposed in client code
- RLS policies prevent unauthorized writes

**To verify (optional):**
1. Go to: Supabase Dashboard → Authentication → Policies
2. Check: `sales_history` table has SELECT policy for `anon` role
3. Check: INSERT/UPDATE/DELETE require `authenticated` role

---

## 📁 FILE STRUCTURE

```
emirates-pride-inventory-management/
├── stock-register.html              # Main app (stores use this)
├── demand-planning-dashboard.html   # MGR dashboard (you use this)
├── create_tables.sql                # ONE-TIME: Create Supabase tables
├── sales_history_upload.json        # ONE-TIME: Initial 16 months data
├── benchmarks_upload.json           # ONE-TIME: Initial benchmarks
├── monthly_sales_upload.py          # MONTHLY: Upload new data
└── SETUP_INSTRUCTIONS.md            # This file
```

---

## 🚀 ADVANCED: WEEKLY CONSUMPTION REPORTS

### When you're ready to add transfer/consumption data:

**1. Export consumption report from ERP:**
   - Columns: SKU Code | Store Code | Month | Qty Transferred | Frequency
   
**2. Run:**
```bash
python3 upload_consumption_report.py April_2026_Consumption.xlsx
```

**3. This will:**
   - Populate `transfer_history` table
   - Refine benchmarks using transfer frequency
   - Improve reorder point calculations
   - Add "transfer volatility" metrics

---

## ❓ TROUBLESHOOTING

### Dashboard shows "No benchmark data found"
→ Check: Did you upload `benchmarks_upload.json` to `benchmarks_cache` table?
→ Verify: Run this query in Supabase SQL Editor:
```sql
SELECT COUNT(*) FROM benchmarks_cache;
```
Should return 1458 rows.

### Dashboard shows error "Failed to load from Supabase"
→ Check: Browser console (F12) for specific error
→ Verify: Supabase project is not paused (free tier pauses after 7 days inactivity)
→ Fix: Go to Supabase Dashboard → Settings → Pause project → click "Resume"

### Monthly upload script fails
→ Check: SKU mapping file is up to date
→ Check: Excel column names match expected format
→ Run: `python3 monthly_sales_upload.py --debug` for detailed logs

---

## 📞 SUPPORT

**If you hit issues:**
1. Check browser console (F12) for errors
2. Check Supabase logs: Dashboard → Logs → Realtime
3. Send screenshot of error + steps to reproduce

**Created:** May 7, 2026  
**Version:** 1.0  
**Maintainer:** Vinayak Bhadani (Demand Planner, EPP)
