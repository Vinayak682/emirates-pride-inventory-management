"""
Emirates Pride — Full Transfer History Parser + Uploader
Source: RptItemWiseStockTransfer (15).xlsx  (Jan 2026 – Jun 2026)

Classifies ALL transfer types:
  WH_TO_STORE      — FG Warehouse → Store (replenishments)
  STORE_TO_STORE   — Inter-store redistribution
  WH_TO_HO         — WH → Head Office (Saudi/Oman pre-staging)
  HO_OUTBOUND      — Head Office → outbound (Saudi/Oman dispatch)
  WH_TO_ECOMM      — WH → E-commerce warehouse
  RETURN_TO_WH     — Store → WH (returns)
  FNF_TO_WH        — FNF Production → FG Warehouse (inbound production)

Uploads to Supabase 'replenishment_history' table.

Usage:
    python parse_transfer_history.py
"""

import re, sys, os, json
from datetime import datetime
from collections import defaultdict

SUPABASE_URL = "https://ncszurcrkngjcjqsowln.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5jc3p1cmNya25namNqcXNvd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NjA4NTgsImV4cCI6MjA5MzAzNjg1OH0.i5cPlP7JTTCKMXuFqI81WXbjQa71qBkRBZEBvNf6ZmM"

FILE = r"C:\Users\AMALKANDATHIL\Downloads\RptItemWiseStockTransfer (15).xlsx"

STORE_CODES = {
    'A0001','A0002','A0003','A0004','A0005','A0007','A0008','A0009','A0010','A0011',
    'AL001','AL002','AL003','AL004','AL005','AL006',
    'DX001','DX003','DX004','DX005','DX006','DX008',
    'RK001','RK002','FJ001','FJ0001','SH001','AJ001','PS_YAS',
    'BAS001','YMK001','BAW001','MAK001',
    'OM001','OM002','OM_ASL001',
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_loc_code(loc):
    """Extract store/location code from 'CODE - Name , City' format."""
    if not loc:
        return None
    m = re.match(r'^([A-Z0-9_]+)\s*[-\s]', str(loc).strip())
    return m.group(1).strip() if m else str(loc).strip()[:12]

def parse_sku(item_str):
    """Extract SKU code from 'CODE - Product Name' format."""
    if not item_str:
        return None
    m = re.match(r'^([A-Z0-9]+)\s*-', str(item_str).strip())
    return m.group(1).strip() if m else str(item_str).strip()[:14]

def parse_product_name(item_str):
    """Extract product name from 'CODE - Product Name' format."""
    if not item_str:
        return None
    s = str(item_str).strip()
    m = re.match(r'^[A-Z0-9]+\s*-\s*(.+)', s)
    return m.group(1).strip() if m else s

def classify_transfer(from_loc, to_loc):
    """Classify transfer type based on from/to location codes."""
    fc = parse_loc_code(from_loc)
    tc = parse_loc_code(to_loc)
    if not fc or not tc:
        return 'UNKNOWN'
    if fc == 'STR01':
        if tc in STORE_CODES:    return 'WH_TO_STORE'
        if tc == 'EPP_ECOM':     return 'WH_TO_ECOMM'
        if tc == 'STR02':        return 'WH_TO_FNF'
        if tc == '0001':         return 'WH_TO_HO'
        return 'WH_OTHER'
    if fc in STORE_CODES:
        if tc in STORE_CODES:   return 'STORE_TO_STORE'
        if tc == 'STR01':       return 'RETURN_TO_WH'
        if tc == '0001':        return 'STORE_TO_HO'
        if tc == 'EPP_ECOM':    return 'STORE_TO_ECOMM'
        return 'STORE_OTHER'
    if fc == '0001':             return 'HO_OUTBOUND'
    if fc == 'STR02':            return 'FNF_TO_WH'
    return f'OTHER'

def map_dispatch_type(transfer_type):
    """Map internal transfer type to the dispatch_type field."""
    mapping = {
        'WH_TO_STORE':    'Regular',
        'STORE_TO_STORE': 'Redistribution',
        'WH_TO_HO':       'KSA_Oman_Staging',
        'HO_OUTBOUND':    'KSA_Oman_Dispatch',
        'WH_TO_ECOMM':    'Ecommerce',
        'RETURN_TO_WH':   'Return',
        'FNF_TO_WH':      'Production_Inbound',
        'WH_TO_FNF':      'FNF_Transfer',
        'STORE_TO_ECOMM': 'Ecommerce',
    }
    return mapping.get(transfer_type, 'Other')

# ── Parse Excel ───────────────────────────────────────────────────────────────

def parse_file():
    try:
        import openpyxl
    except ImportError:
        print("Installing openpyxl..."); os.system("pip install openpyxl")
        import openpyxl

    print(f"Reading {FILE} ...")
    wb = openpyxl.load_workbook(FILE, read_only=True, data_only=True)
    ws = wb.active
    raw_rows = list(ws.iter_rows(values_only=True))

    # Data starts at row index 16 (0-based)
    data_rows = [r for r in raw_rows[16:] if len(r) > 26 and r[1]
                 and str(r[1]).strip() not in ('', 'Date', 'Date     ')]
    print(f"  {len(data_rows):,} data rows found")

    records = []
    skipped = 0
    summary = defaultdict(lambda: {'rows': 0, 'units': 0})

    for r in data_rows:
        raw_date = str(r[1]).strip().split()[0]
        try:
            d = datetime.strptime(raw_date, '%d-%b-%Y')
            dispatch_date = d.strftime('%Y-%m-%d')
            month_year    = d.strftime('%Y-%m')
        except Exception:
            skipped += 1
            continue

        qty = float(r[24] or 0)
        if qty <= 0:
            skipped += 1
            continue

        transfer_type = classify_transfer(r[8], r[11])
        dispatch_type = map_dispatch_type(transfer_type)
        from_code = parse_loc_code(r[8])
        to_code   = parse_loc_code(r[11])
        sku       = parse_sku(r[18])
        prod_name = parse_product_name(r[18])
        doc_no    = str(r[2] or '').strip()
        remarks   = str(r[27] or '').strip()

        # For WH→Store: store_code = to_code
        # For Store→Store: store_code = to_code (receiving store)
        # For HO outbound/WH→HO: store_code = from_code or 'HO'
        if transfer_type == 'WH_TO_STORE':
            store_code = to_code
        elif transfer_type == 'STORE_TO_STORE':
            store_code = to_code   # receiving store
        elif transfer_type == 'RETURN_TO_WH':
            store_code = from_code
        elif transfer_type in ('WH_TO_HO', 'HO_OUTBOUND'):
            store_code = 'HO_RESERVE'
        elif transfer_type == 'WH_TO_ECOMM':
            store_code = 'EPP_ECOM_DXB'
        elif transfer_type == 'FNF_TO_WH':
            store_code = 'WH_EPP'
        else:
            store_code = to_code or from_code or 'UNKNOWN'

        records.append({
            'dispatch_ref':   doc_no or None,
            'dispatch_date':  dispatch_date,
            'month_year':     month_year,
            'store_code':     store_code,
            'from_code':      from_code,
            'to_code':        to_code,
            'sku_code':       sku,
            'product_name':   prod_name,
            'qty_dispatched': int(qty),
            'dispatch_type':  dispatch_type,
            'transfer_type':  transfer_type,
            'notes':          remarks if remarks else None,
        })
        summary[transfer_type]['rows']  += 1
        summary[transfer_type]['units'] += int(qty)

    print(f"\n  Parsed: {len(records):,} records  |  Skipped: {skipped:,}")
    print("\n  TRANSFER TYPE SUMMARY:")
    print(f"  {'Type':<22} {'Rows':>7} {'Units':>12}")
    print("  " + "-"*44)
    for typ, v in sorted(summary.items(), key=lambda x: -x[1]['units']):
        print(f"  {typ:<22} {v['rows']:>7,}  {v['units']:>11,}")

    return records

# ── Print detailed summary ────────────────────────────────────────────────────

def print_summary(records):
    monthly = defaultdict(lambda: defaultdict(int))
    store_repl = defaultdict(int)
    ho_skus = defaultdict(int)

    for r in records:
        monthly[r['month_year']][r['transfer_type']] += r['qty_dispatched']
        if r['transfer_type'] == 'WH_TO_STORE':
            store_repl[r['store_code']] += r['qty_dispatched']
        if r['transfer_type'] in ('HO_OUTBOUND', 'WH_TO_HO'):
            ho_skus[r['sku_code']] += r['qty_dispatched']

    print("\n  MONTHLY BREAKDOWN (units):")
    print(f"  {'Month':<10} {'WH->Store':>11} {'S2S':>8} {'ReturnWH':>9} {'WH->Ecomm':>10} {'WH->HO':>8} {'HO_Out':>8}")
    for m in sorted(monthly.keys()):
        d = monthly[m]
        print(f"  {m:<10} {d.get('WH_TO_STORE',0):>11,} {d.get('STORE_TO_STORE',0):>8,} {d.get('RETURN_TO_WH',0):>9,} {d.get('WH_TO_ECOMM',0):>10,} {d.get('WH_TO_HO',0):>8,} {d.get('HO_OUTBOUND',0):>8,}")

    print("\n  TOP STORES (WH replenishments):")
    for sc, qty in sorted(store_repl.items(), key=lambda x: -x[1])[:15]:
        print(f"  {sc:<14}  {qty:>8,} units")

    print("\n  TOP 15 SKUs in KSA/Oman reservations (WH->HO + HO_Outbound):")
    for sk, qty in sorted(ho_skus.items(), key=lambda x: -x[1])[:15]:
        print(f"  {sk:<14}  {qty:>8,} units")

# ── Generate SQL ──────────────────────────────────────────────────────────────

def generate_sql(records, out_path):
    print(f"\n  Generating SQL -> {out_path}")

    # Only include store-relevant records (exclude FNF production inbound)
    upload_records = [r for r in records if r['transfer_type'] != 'FNF_TO_WH']
    print(f"  Records for upload: {len(upload_records):,} (excludes FNF_TO_WH production inbound)")

    lines = [
        "-- Emirates Pride Transfer History Upload",
        f"-- Source: RptItemWiseStockTransfer (15).xlsx",
        f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"-- Records: {len(upload_records):,}",
        "",
        "BEGIN;",
        "",
        "INSERT INTO replenishment_history",
        "  (dispatch_ref, dispatch_date, month_year, store_code, sku_code,",
        "   product_name, qty_dispatched, dispatch_type, notes)",
        "VALUES",
    ]

    def esc(v):
        if v is None: return 'NULL'
        return "'" + str(v).replace("'", "''")[:200] + "'"

    value_rows = []
    for r in upload_records:
        ref = esc(r['dispatch_ref'])
        dt  = esc(r['dispatch_date'])
        my  = esc(r['month_year'])
        sc  = esc(r['store_code'])
        sk  = esc(r['sku_code'])
        pn  = esc(r['product_name'])
        qty = str(r['qty_dispatched'])
        typ = esc(r['dispatch_type'])
        nt  = esc(r['notes'])
        value_rows.append(f"  ({ref},{dt},{my},{sc},{sk},{pn},{qty},{typ},{nt})")

    lines.append(",\n".join(value_rows))
    lines.append("")
    lines.append("ON CONFLICT (dispatch_ref, dispatch_date, store_code, sku_code)")
    lines.append("  WHERE dispatch_ref IS NOT NULL")
    lines.append("  DO UPDATE SET")
    lines.append("    qty_dispatched = EXCLUDED.qty_dispatched,")
    lines.append("    dispatch_type  = EXCLUDED.dispatch_type,")
    lines.append("    notes          = EXCLUDED.notes;")
    lines.append("")
    lines.append("COMMIT;")
    lines.append("")
    lines.append("-- Verification:")
    lines.append("SELECT transfer_type_summary.* FROM (")
    lines.append("  SELECT dispatch_type, COUNT(*) rows, SUM(qty_dispatched) units")
    lines.append("  FROM replenishment_history")
    lines.append("  GROUP BY dispatch_type ORDER BY units DESC")
    lines.append(") transfer_type_summary;")

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"  SQL file size: {size_mb:.1f} MB")

# ── Upload via Supabase REST API ──────────────────────────────────────────────

def upload_to_supabase(records):
    try:
        import urllib.request
    except ImportError:
        pass

    upload_records = [r for r in records if r['transfer_type'] != 'FNF_TO_WH']
    print(f"\n  Uploading {len(upload_records):,} records to Supabase ...")

    # Remove internal fields before upload
    clean = []
    for r in upload_records:
        clean.append({
            'dispatch_ref':   r['dispatch_ref'],
            'dispatch_date':  r['dispatch_date'],
            'month_year':     r['month_year'],
            'store_code':     r['store_code'],
            'sku_code':       r['sku_code'],
            'product_name':   r['product_name'],
            'qty_dispatched': r['qty_dispatched'],
            'dispatch_type':  r['dispatch_type'],
            'notes':          r['notes'],
        })

    CHUNK = 500
    headers = {
        'Content-Type':  'application/json',
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Prefer':        'resolution=merge-duplicates',
    }
    url = f"{SUPABASE_URL}/rest/v1/replenishment_history"

    success = 0
    for i in range(0, len(clean), CHUNK):
        chunk = clean[i:i+CHUNK]
        payload = json.dumps(chunk).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                success += len(chunk)
                print(f"  [{i+len(chunk):>6}/{len(clean)}] OK", end='\r')
        except Exception as e:
            body = e.read().decode() if hasattr(e, 'read') else str(e)
            print(f"\n  ERROR at chunk {i}: {body[:200]}")
            return False

    print(f"\n  Successfully uploaded {success:,} records")
    return True

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("EMIRATES PRIDE — Transfer History Parser")
    print("=" * 60)

    records = parse_file()
    print_summary(records)

    sql_path = r"C:\Users\AMALKANDATHIL\Downloads\transfer_history_upload.sql"
    generate_sql(records, sql_path)

    print("\n" + "=" * 60)
    print("OPTIONS:")
    print("  1. Upload directly to Supabase via API (recommended for small batches)")
    print("  2. Use the generated SQL file in Supabase SQL Editor")
    print(f"     SQL file: {sql_path}")
    print("=" * 60)

    choice = input("\nUpload directly to Supabase now? (y/n): ").strip().lower()
    if choice == 'y':
        ok = upload_to_supabase(records)
        if ok:
            print("\nDone! Refresh the Replenishment tab in sop-portal.html to see the data.")
        else:
            print(f"\nAPI upload had issues. Use the SQL file instead:\n  {sql_path}")
    else:
        print(f"\nSQL file ready. Paste it in Supabase SQL Editor:")
        print(f"  https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql")
        print(f"  File: {sql_path}")
        upload_records = [r for r in records if r['transfer_type'] != 'FNF_TO_WH']
        print(f"\n  Total records to upload: {len(upload_records):,}")
        wh_store = sum(1 for r in upload_records if r['transfer_type'] == 'WH_TO_STORE')
        s2s      = sum(1 for r in upload_records if r['transfer_type'] == 'STORE_TO_STORE')
        ho       = sum(1 for r in upload_records if r['transfer_type'] in ('WH_TO_HO','HO_OUTBOUND'))
        print(f"  WH -> Store:             {wh_store:,}")
        print(f"  Store -> Store:          {s2s:,}")
        print(f"  KSA/Oman Reservations:   {ho:,}")
