"""
fix_store_soh_upload.py
=======================
Re-reads all 28 store Excel files from the Store Stock Report folder,
maps product names → SKU codes, deletes stale Supabase rows, and
re-uploads clean data to store_soh_snapshots.

Run: python fix_store_soh_upload.py
"""

import openpyxl, os, json, urllib.request, urllib.parse, sys

# ── CONFIG ─────────────────────────────────────────────────────────────────
SB_URL  = "https://ncszurcrkngjcjqsowln.supabase.co"
SB_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5jc3p1cmNya25namNqcXNvd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NjA4NTgsImV4cCI6MjA5MzAzNjg1OH0.i5cPlP7JTTCKMXuFqI81WXbjQa71qBkRBZEBvNf6ZmM"
FOLDER  = r"C:\Users\AMALKANDATHIL\OneDrive - Emirates Pride Perfumes Trading\Desktop\Stock Report\Store Stock Report 24.05.2026"

# ── FILE → STORE MAPPING ───────────────────────────────────────────────────
# Each entry: (filename_pattern, store_code, store_name, region, brand, snapshot_date)
FILE_MAP = [
    ("AJMAN CITY CENTRE - 24-May-26.xlsx",              "AJ001",   "Ajman City Centre",        "UAE",    "EPP", "2026-05-24"),
    ("AL AIN MALL - 25-May-26.xlsx",                    "AL001",   "Al Ain Mall",               "UAE",    "EPP", "2026-05-25"),
    ("ASL BAS MALL - 24-May-26.xlsx",                   "BAS001",  "ASL BAS Mall",              "UAE",    "ASL", "2026-05-24"),
    ("BAS KIOSK - 24-May-26.xlsx",                      "A0002",   "BAS Mall Kiosk",            "UAE",    "EPP", "2026-05-24"),
    ("BAS SHOP - 24-May-26.xlsx",                       "A0001",   "BAS Mall Shop",             "UAE",    "EPP", "2026-05-24"),
    ("BAS SHOP 2 - 24-May-26.xlsx",                     "A0010",   "BAS Mall Shop 2",           "UAE",    "EPP", "2026-05-24"),
    ("BAWADI 1 - 24-May-26.xlsx",                       "AL002",   "Bawadi Mall Kiosk 1",       "UAE",    "EPP", "2026-05-24"),
    ("BAWADI 2 - 25-May-26.xlsx",                       "AL003",   "Bawadi Mall Kiosk 2",       "UAE",    "ASL", "2026-05-25"),
    ("BAWADI MALL - 24-May-26.xlsx",                    "BAW001",  "Bawadi Mall (ASL)",         "UAE",    "ASL", "2026-05-24"),
    ("DALMA KIOSK - 24-May-26 (CSV Format).xlsx",       "A0004",   "Dalma Mall Kiosk",          "UAE",    "EPP", "2026-05-24"),
    ("DALMA SHOP - 24-May-26 (Corrected).xlsx",         "A0003",   "Dalma Mall Shop",           "UAE",    "EPP", "2026-05-24"),
    ("DUBAI HILLS MALL - 24-May-26 (Corrected).xlsx",   "DX006",   "Dubai Hills Mall",          "UAE",    "EPP", "2026-05-24"),
    ("Dubai Shop Stock Movement Report - 24-May-26.xlsx","DX001",  "Dubai Mall Shop",           "UAE",    "EPP", "2026-05-24"),
    ("FUJAIRAH CITY CENTRE - 24-May-26.xlsx",           "FJ0001",  "Fujairah City Centre (ASL)","UAE",    "ASL", "2026-05-24"),
    ("JIMI MALL - 24-May-26 (Corrected).xlsx",          "AL004",   "Al Jimi Mall",              "UAE",    "EPP", "2026-05-24"),
    ("MAKANI MALL - 25-May-26.xlsx",                    "MAK001",  "Makani Zakhar Mall (ASL)",  "UAE",    "ASL", "2026-05-25"),
    ("MAKANI SHOP - 24-May-26.xlsx",                    "AL006",   "Makani Zakhar Mall Shop",   "UAE",    "EPP", "2026-05-24"),
    ("MALL OF EMIRATES - 24-May-26.xlsx",               "DX004",   "Mall of the Emirates",      "UAE",    "EPP", "2026-05-24"),
    ("MANAR MALL SHOP - 24-May-26.xlsx",                "RK001",   "Manar Mall Shop",           "UAE",    "EPP", "2026-05-24"),
    ("MIRDIF CITY CENTRE - 25-May-26.xlsx",             "DX005",   "Mirdif City Centre",        "UAE",    "EPP", "2026-05-25"),
    ("YAS MALL - 24-May-26 (Corrected).xlsx",           "A0009",   "Yas Mall Podium",           "UAE",    "EPP", "2026-05-24"),
    ("YAS MALL 3 - 25-May-26 (Corrected).xlsx",         "A0008",   "Yas Mall Kiosk 3",          "UAE",    "EPP", "2026-05-25"),
    ("YAS MALL KIOSK 2 - 24-May-26 (Corrected).xlsx",  "A0007",   "Yas Mall Kiosk 2",          "UAE",    "EPP", "2026-05-24"),
    ("YAS PROMOTIONS - 24-May-26 (Corrected).xlsx",     "PS_YAS",  "Yas Promotions",            "UAE",    "EPP", "2026-05-24"),
    ("ZAHIA CITY CENTRE - 24-May-26.xlsx",              "SH001",   "Zahia City Centre",         "UAE",    "EPP", "2026-05-24"),
]

# ── SKU MAP: product_name (lowercase, normalised) → SKU code ───────────────
# Covers EPP CATS + ASL + accessories/consumables
SKU_MAP = {
    # ── EPP 100ml Perfumes (Caballo) ──────────────────────────────────────
    "white 100ml perfume": "C00002",
    "maroon 100ml perfume": "C00004",
    "navy 100ml perfume": "C00003",
    "violet 100ml perfume": "C00012",
    "rose gold 100ml perfume": "C00014",
    "blue 100ml perfume": "C00005",
    "green 100ml perfume": "C00010",
    "red 100ml perfume": "C00011",
    "black 100ml perfume": "C00006",
    "brown 100ml perfume": "C00007",
    "orange 100ml perfume": "C00008",
    "burgundy 100ml perfume": "C00009",
    "grey 100ml perfume": "C00013",
    "pink 100ml perfume": "C00002",  # alias

    # ── EPP Bakhoor / Paper Box (Bel) ─────────────────────────────────────
    "amber bel oud": "B00003",
    "amber bel oud paper box": "B00003",
    "amber bel oud paper box(box 2 &3 bel)": "B00003",
    "peaceful life": "B00007",
    "peaceful life paper box": "B00007",
    "peaceful life paper box(box 2 &3 bel)": "B00007",
    "mystery": "B00005",
    "mystery paper box": "B00005",
    "mystery paper box(box 2 &3 bel)": "B00005",
    "midnight glow": "B00008",
    "midnight glow paper box": "B00008",
    "midnight glow paper box(box 2 &3 bel)": "B00008",
    "master signature": "B00020",
    "master signature paper box": "B00020",
    "master signature paper box(box 2 &3 bel)": "B00020",
    "masters paper box": "B00020",
    "midnight bloom": "B00021",
    "midnight bloom paper box": "B00021",
    "midnight bloom paper box(box 2 &3 bel)": "B00021",
    "hidden leather": "B00015",
    "hidden leather paper box": "B00015",
    "hidden leather paper box(box 2 &3 bel)": "B00015",
    "hidden tobacco": "B00018",
    "hidden tobacco paper box": "B00018",
    "hidden tobacco paper box(box 2 &3 bel)": "B00018",
    "mysterious rose": "B00016",
    "mysterious rose paper box": "B00016",
    "mysterious rose paper box(box 2 &3 bel)": "B00016",
    "thekrayat": "B00017",
    "thekrayat paper box": "B00017",
    "thekrayat paper box(box 2 &3 bel)": "B00017",
    "masters": "B00019",
    "masters paper box": "B00019",
    "masters paper box(box 2 &3 bel)": "B00019",
    "bakhoor noor al oud": "B00001",
    "noor al oud": "B00001",
    "bakhoor original": "B00006",
    "original": "B00006",
    "bakhoor amber": "B00002",
    "velvet pearl": "B00004",
    "bakhoor velvet pearl": "B00004",
    "bakhoor midnight moon": "B00009",
    "midnight moon": "B00009",
    "bakhoor silver water": "B00010",
    "silver water": "B00010",
    "bakhoor precious oud": "B00011",
    "precious oud": "B00011",
    "bakhoor safa": "B00012",
    "safa": "B00012",
    "bakhoor dahab": "B00013",
    "dahab": "B00013",
    "bakhoor jasmine silk": "B00014",
    "jasmine silk": "B00014",
    "velvet rose": "B00016",
    "pure gold": "B00022",
    "luxury": "B00023",

    # ── Set Boxes (BX) ────────────────────────────────────────────────────
    "3 bel black box with 2 oil": "BX0002",
    "3 bel black box": "BX0002",
    "3 bel black box with 2 oil (bx0002)": "BX0002",
    "3 bel box with 2 oil": "BX0002",
    "bx0002": "BX0002",
    "bod gift box": "BX0014",
    "bod gift box (bx0014)": "BX0014",
    "bx0014": "BX0014",
    "maroon set box": "SP0001",
    "reflection set box": "SP0002",
    "blue set box": "SP0003",
    "black set box": "SP0004",
    "grey set box": "SP0005",
    "gold set box": "SP0006",
    "navy set box": "SP0007",
    "future bakhoor": "SP0030",
    "future oud": "SP0031",
    "more of oud": "O00006",
    "more of oud set": "SP0008",
    "master signature box": "SP0023",
    "master signature box (box 2 &3 bel)": "SP0023",
    "midnight bloom box": "SP0037",
    "midnight bloom paper box(box 2 &3 bel)": "B00021",

    # ── Dakhoon ───────────────────────────────────────────────────────────
    "dakhoon al emarat": "D00001",
    "dakhoon al emarat 100g": "D00001",
    "d00001": "D00001",
    "dakhoon bukhoor": "D00002",
    "dakhoon amber": "D00003",
    "dakhoon oud": "D00004",
    "dakhoon rose": "D00005",
    "dakhoon musk": "D00006",
    "dakhoon gold": "D00007",
    "dakhoon special": "D00008",
    "dakhoon premium": "D00009",

    # ── Oud Oils ──────────────────────────────────────────────────────────
    "oud meydan": "O00001",
    "oud amiri": "O00002",
    "hindi khas": "O00003",
    "hindi khas oud": "O00003",
    "mukhallat": "O00004",
    "safwa": "O00005",
    "more of oud oil": "O00006",
    "oud fakhamah": "O00007",
    "oud emarat": "O00008",

    # ── Heritage / CPO ────────────────────────────────────────────────────
    "qalah": "HR0001",
    "qalah - heritage collection": "HR0001",
    "qalah heritage": "HR0001",
    "hessa": "HR0002",
    "hessa - heritage collection": "HR0002",
    "hessa heritage": "HR0002",

    # ── Rada collection ───────────────────────────────────────────────────
    "sapphire serenity": "RADA-006",
    "sapphire serenity 65ml": "RADA-006",
    "velvet topaz": "RM2001",
    "velvet topaz perfume": "RM2001",
    "smoky jasper": "RM2003",
    "smoky jasper perfume": "RM2003",
    "silky crystal": "RM2004",
    "silky crystal perfume": "RM2004",
    "royal garnet": "RM2005",
    "royal garnet perfume": "RM2005",

    # ── Accessories / Consumables ─────────────────────────────────────────
    "medkhan (small)": "AC0001",
    "medkhan small": "AC0001",
    "medkhan (large)": "AC0002",
    "medkhan large": "AC0002",
    "charcoal": "AC0003",
    "lighter": "AC0004",
    "picker": "AC0005",
    "candle": "AC0006",
    "incense burner": "AC0007",
    "shopping bag s": "BAG-S",
    "shopping bag m": "BAG-M",
    "shopping bag l": "BAG-L",
    "shopping bag xl": "BAG-XL",
    "tissue paper": "TISSUE",

    # ── ASL Perfumes (AP series) ──────────────────────────────────────────
    "caramel luban": "AP012",
    "caramel luban perfume": "AP012",
    "black vanilla 50ml": "AP001",
    "black vanilla": "AP001",
    "secret leather 50ml": "AP002",
    "secret leather": "AP002",
    "white bouquet 50ml": "AP003",
    "white bouquet": "AP003",
    "leather intense 50ml": "AP004",
    "leather intense": "AP004",
    "rich vanilla 50ml": "AP005",
    "rich vanilla": "AP005",
    "spicy sandal 50ml": "AP006",
    "spicy sandal": "AP006",
    "velvet amber": "AP007",
    "velvet amber 50ml": "AP007",
    "dark musk": "AP008",
    "dark musk 50ml": "AP008",
    "midnight berry": "AP009",
    "midnight berry 50ml": "AP009",
    "golden oud": "AP010",
    "golden oud 50ml": "AP010",
    "rose fantasy": "AP011",
    "rose fantasy 50ml": "AP011",

    # ── ASL Oils (AO series) ──────────────────────────────────────────────
    "caramel luban oil": "AO012",
    "caramel luban oil 6ml": "AO012",
    "black vanilla oil": "AO001",
    "secret leather oil": "AO002",
    "white bouquet oil": "AO003",
    "leather intense oil": "AO004",
    "rich vanilla oil": "AO005",
    "spicy sandal oil": "AO006",
    "velvet amber oil": "AO007",
    "dark musk oil": "AO008",
    "midnight berry oil": "AO009",
    "golden oud oil": "AO010",
    "rose fantasy oil": "AO011",

    # ── ASL Hair & Body Mist (AH series) ─────────────────────────────────
    "black vanilla hair & body mist": "AH001",
    "black vanilla mist": "AH001",
    "secret leather hair & body mist": "AH006",
    "secret leather mist": "AH006",
    "white bouquet hair & body mist": "AH007",
    "white bouquet mist": "AH007",
    "leather intense hair & body mist": "AH002",
    "leather intense mist": "AH002",
    "rich vanilla hair & body mist": "AH003",
    "rich vanilla mist": "AH003",
    "spicy sandal hair & body mist": "AH004",
    "spicy sandal mist": "AH004",
    "velvet amber hair & body mist": "AH005",
    "velvet amber mist": "AH005",

    # ── ASL Gift Sets (AG series) ─────────────────────────────────────────
    "asl gift set box": "AG001",
    "asl gift box": "AG001",
    "asl 6pc perfume set": "AG011",
    "asl 3 gift set box": "AG012",
    "asl 3 pcs discovery set": "ADS03",
    "discovery set": "ADS01",
    "asl ramadan gift set gift box": "AG016",
    "bundle foldable gift box -2": "AG014",
    "bundle foldable gift box -3": "AG015",
    "bundle foldable gift box -4": "AG017",
    "box 3 perfumes and 3 hair mist": "AG012",
    "asl gift box - velvet amber": "AG018",
    "asl gift box - dark musk": "AG019",

    # ── ASL Reed Diffusers / Other ────────────────────────────────────────
    "white bouquet air freshener 250ml": "AAF002",
    "white bouquet air freshner 250ml": "AAF002",
    "secret leather reed diffuser": "ARD001",
    "white bouquet reed diffuser": "ARD003",
    "sunbeam tanning oil": "ATO001",
}

# ── HELPERS ────────────────────────────────────────────────────────────────
def norm(s):
    """Normalise product name for lookup."""
    if not s:
        return ""
    return str(s).lower().strip()\
        .replace(" ", " ")\
        .replace("  ", " ")\
        .replace("’", "'")\
        .replace("‘", "'")

def lookup_sku(name):
    n = norm(name)
    if n in SKU_MAP:
        return SKU_MAP[n]
    # Partial match — try if normalised name starts with a known key
    for k, v in SKU_MAP.items():
        if n == k or (len(k) > 6 and k in n):
            return v
    return None

def sb_request(method, path, body=None, extra_headers=None):
    url = SB_URL + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            resp = r.read()
            return resp.decode() if resp else ""
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()}"

# ── MAIN ───────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  Emirates Pride — Store SOH Re-Upload (fix_store_soh_upload.py)")
    print("=" * 65)

    all_rows = []
    store_summaries = []

    for (filename, store_code, store_name, region, brand, snap_date) in FILE_MAP:
        path = os.path.join(FOLDER, filename)
        if not os.path.exists(path):
            print(f"  [SKIP] File not found: {filename}")
            continue

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        raw_rows = list(ws.iter_rows(values_only=True))
        wb.close()

        # Parse: skip header row, expect (Category, Product, SOH)
        parsed = []
        unmatched = []
        for row in raw_rows[1:]:
            if not row or len(row) < 3:
                continue
            category = str(row[0]).strip() if row[0] else ""
            product  = str(row[1]).strip() if row[1] else ""
            try:
                soh_qty = float(row[2]) if row[2] is not None else 0.0
            except (TypeError, ValueError):
                soh_qty = 0.0

            if not product or product.lower() in ("product", ""):
                continue

            sku = lookup_sku(product)
            if not sku:
                unmatched.append(product)
                sku = "UNMAPPED"  # still upload with product name, no sku_code

            parsed.append({
                "store_code":    store_code,
                "store_name":    store_name,
                "region":        region,
                "brand":         brand,
                "snapshot_date": snap_date,
                "sku_code":      sku if sku != "UNMAPPED" else None,
                "product_name":  product,
                "category":      category,
                "soh_qty":       soh_qty,
            })

        total_units = sum(r["soh_qty"] for r in parsed)
        mapped      = sum(1 for r in parsed if r["sku_code"])
        store_summaries.append((store_code, store_name, len(parsed), mapped, total_units, len(unmatched)))
        all_rows.extend(parsed)

        status = "OK" if len(unmatched) == 0 else f"WARN {len(unmatched)} unmapped"
        print(f"  [{status:20}] {store_code:8} {store_name[:28]:28} | {len(parsed):4} rows | {int(total_units):>6} units")
        if unmatched:
            for u in unmatched[:5]:
                print(f"               Unmapped: {u}")
            if len(unmatched) > 5:
                print(f"               ... and {len(unmatched)-5} more")

    print(f"\n  Total rows to upload: {len(all_rows)}")
    print(f"  Total stores: {len(store_summaries)}")

    # ── STEP 1: Check if old store rows exist (anon role cannot delete — user must run SQL)
    print("\n  Checking for existing store rows in Supabase...")
    check = sb_request("GET", "/rest/v1/store_soh_snapshots?store_code=not.in.(WH_EPP,WH_ASL)&select=store_code&limit=1")
    has_old_data = check and check != "[]" and not check.startswith("HTTP")
    if has_old_data:
        print("\n  !! OLD DATA EXISTS in store_soh_snapshots.")
        print("  !! The anon API key cannot delete rows — you must run this SQL in Supabase first:")
        print()
        print("  ─────────────────────────────────────────────────────────────")
        print("  DELETE FROM store_soh_snapshots")
        print("  WHERE store_code NOT IN ('WH_EPP', 'WH_ASL');")
        print("  ─────────────────────────────────────────────────────────────")
        print()
        print(f"  Open: https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql")
        print()
        ans = input("  Have you run the DELETE SQL above? (y/n): ").strip().lower()
        if ans != "y":
            print("  Aborted. Run the SQL first, then re-run this script.")
            return
    else:
        print("  No old store rows found. Proceeding with insert.")

    # ── STEP 2: Deduplicate by (store_code, snapshot_date, product_name) — keep highest qty
    seen_keys = {}
    for r in all_rows:
        k = (r["store_code"], r["snapshot_date"], r["product_name"])
        if k not in seen_keys or (r["soh_qty"] or 0) > (seen_keys[k]["soh_qty"] or 0):
            seen_keys[k] = r
    deduped = list(seen_keys.values())
    dupes_removed = len(all_rows) - len(deduped)
    if dupes_removed:
        print(f"  Removed {dupes_removed} duplicate product rows (same product name in same store)")

    # ── STEP 3: Upload in batches of 500
    print(f"\n  Uploading {len(deduped)} rows in batches of 500...")
    BATCH = 500
    total_uploaded = 0
    for i in range(0, len(deduped), BATCH):
        batch = deduped[i:i+BATCH]
        result = sb_request(
            "POST",
            "/rest/v1/store_soh_snapshots",
            body=batch,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        if result.startswith("HTTP"):
            print(f"    ERROR batch {i//BATCH + 1}: {result}")
        else:
            total_uploaded += len(batch)
            print(f"    Batch {i//BATCH + 1}: uploaded {len(batch)} rows (total: {total_uploaded})")

    # ── STEP 3: Summary
    print("\n" + "=" * 65)
    print("  UPLOAD SUMMARY")
    print("=" * 65)
    print(f"  {'Store':8} {'Name':28} {'Rows':>5} {'SKUs':>5} {'Units':>7} {'Unmap':>5}")
    print(f"  {'-'*65}")
    grand_units = 0
    for (code, name, rows, mapped, units, unmap) in store_summaries:
        print(f"  {code:8} {name[:28]:28} {rows:>5} {mapped:>5} {int(units):>7} {unmap:>5}")
        grand_units += units
    print(f"  {'-'*65}")
    print(f"  {'TOTAL':37} {sum(s[2] for s in store_summaries):>5}       {int(grand_units):>7}")
    print(f"\n  DONE. Total uploaded: {total_uploaded} rows")
    print("  S&OP Portal Inventory tab will now show correct data.")

if __name__ == "__main__":
    main()
