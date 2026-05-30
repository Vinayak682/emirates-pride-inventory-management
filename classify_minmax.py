"""
Emirates Pride — ABC×XYZ SKU Classifier + Min/Max Enhancer
============================================================
Adds to benchmarks_cache:
  abc_class     (A/B/C)  — revenue contribution tier
  xyz_class     (X/Y/Z)  — demand consistency tier
  sku_category  (FastMover/Seasonal/Regular/DeadStock)
  peak_month_avg  — avg of top-2 sales months (used as Eid baseline)
  cov_pct       — coefficient of variation %

Run once (or monthly after uploading new sales data):
  pip install requests
  python classify_minmax.py
"""

import math, json, urllib.request, urllib.parse, sys

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL = 'https://ncszurcrkngjcjqsowln.supabase.co'
ANON_KEY     = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5jc3p1cmNya25namNqcXNvd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NjA4NTgsImV4cCI6MjA5MzAzNjg1OH0.i5cPlP7JTTCKMXuFqI81WXbjQa71qBkRBZEBvNf6ZmM'

HEADERS = {
    'apikey': ANON_KEY,
    'Authorization': 'Bearer ' + ANON_KEY,
    'Content-Type': 'application/json',
}

# SKU families always treated as Seasonal regardless of CoV (gift sets, bakhoor sets)
SEASONAL_SKU_PREFIXES = ('BX', 'AG', 'SP0')
SEASONAL_SKU_EXACT    = {'BX0002','BX0014','BX0011','BX0015','SP0009','SP0029',
                          'SP0037','SP0038','SP0039','SP0013','SP0012'}

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch(path):
    url = SUPABASE_URL + path
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def patch(table, row_id, payload):
    url  = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}"
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={**HEADERS, 'Prefer': 'return=minimal'}, method='PATCH')
    try:
        with urllib.request.urlopen(req) as r:
            pass
    except Exception as e:
        print(f'  PATCH error id={row_id}: {e}')

def stdev(values):
    n = len(values)
    if n < 2: return 0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)

def cov(values):
    """Coefficient of variation as %"""
    if not values: return 0
    mean = sum(values) / len(values)
    if mean == 0: return 0
    return round(stdev(values) / mean * 100, 1)

def is_seasonal_sku(sku_code):
    if sku_code in SEASONAL_SKU_EXACT: return True
    return any(sku_code.startswith(p) for p in SEASONAL_SKU_PREFIXES)

# ── Step 1: Load sales_history ────────────────────────────────────────────────
print('Loading sales_history...')
sales_raw = []
offset = 0
while True:
    chunk = fetch(f'/rest/v1/sales_history?select=sku_code,store_code,month_year,qty_sold&limit=5000&offset={offset}')
    if not chunk: break
    sales_raw.extend(chunk)
    if len(chunk) < 5000: break
    offset += 5000
print(f'  {len(sales_raw):,} rows loaded')

# ── Step 2: Build monthly dict per (sku, store) ───────────────────────────────
from collections import defaultdict
monthly = defaultdict(lambda: defaultdict(int))  # (sku, store) → {month: qty}
sku_total = defaultdict(int)                      # sku → total across all stores

for r in sales_raw:
    sku, store, month, qty = r['sku_code'], r['store_code'], r['month_year'], r.get('qty_sold') or 0
    monthly[(sku, store)][month] += qty
    sku_total[sku] += qty

# ── Step 3: ABC classification — per SKU across all stores ────────────────────
print('Computing ABC classification...')
sorted_skus   = sorted(sku_total.items(), key=lambda x: -x[1])
grand_total   = sum(v for _, v in sorted_skus) or 1
cumulative    = 0
abc_map       = {}  # sku → A/B/C
for sku, vol in sorted_skus:
    cumulative += vol
    pct = cumulative / grand_total
    abc_map[sku] = 'A' if pct <= 0.70 else 'B' if pct <= 0.90 else 'C'

# ── Step 4: Load benchmarks_cache ─────────────────────────────────────────────
print('Loading benchmarks_cache...')
benches = fetch('/rest/v1/benchmarks_cache?select=id,sku_code,store_code,weekly_avg,last_sale_month&limit=5000')
print(f'  {len(benches):,} benchmark rows')

# ── Step 5: Classify each benchmark row ───────────────────────────────────────
print('Classifying...')

from datetime import datetime, date
today = date.today()

updates = []
for b in benches:
    sku   = b['sku_code'] or ''
    store = b['store_code'] or ''
    key   = (sku, store)
    w_avg = b.get('weekly_avg') or 0

    months_data = monthly.get(key, {})
    vals        = list(months_data.values())   # monthly qty list

    # ── CoV ──────────────────────────────────────────────────────────────────
    cov_val = cov(vals) if len(vals) >= 3 else 999

    # ── XYZ ──────────────────────────────────────────────────────────────────
    if len(vals) < 3:
        xyz = 'Z'
    elif cov_val < 30:
        xyz = 'X'
    elif cov_val < 70:
        xyz = 'Y'
    else:
        xyz = 'Z'

    # ── ABC ──────────────────────────────────────────────────────────────────
    abc = abc_map.get(sku, 'C')

    # ── Peak month avg (top-2 months) ────────────────────────────────────────
    top2 = sorted(vals, reverse=True)[:2]
    peak_avg = round(sum(top2) / len(top2), 1) if top2 else 0

    # ── Dead Stock check ────────────────────────────────────────────────────
    dead = False
    if b.get('last_sale_month'):
        try:
            last = datetime.strptime(b['last_sale_month'], '%Y-%m').date().replace(day=1)
            months_since = (today.year - last.year) * 12 + today.month - last.month
            if months_since >= 4:
                dead = True
        except Exception:
            pass
    if w_avg == 0 and not vals:
        dead = True

    # ── SKU Category ─────────────────────────────────────────────────────────
    if dead:
        cat = 'DeadStock'
    elif is_seasonal_sku(sku) or xyz == 'Z':
        cat = 'Seasonal'
    elif w_avg >= 20 and xyz in ('X', 'Y'):
        cat = 'FastMover'
    else:
        cat = 'Regular'

    updates.append({
        'id':             b['id'],
        'abc_class':      abc,
        'xyz_class':      xyz,
        'sku_category':   cat,
        'peak_month_avg': peak_avg,
        'cov_pct':        round(cov_val, 1) if cov_val != 999 else None,
    })

# ── Step 6: Summary before patching ──────────────────────────────────────────
from collections import Counter
cats = Counter(u['sku_category'] for u in updates)
abcs = Counter(u['abc_class'] for u in updates)
xyzs = Counter(u['xyz_class'] for u in updates)

print(f'\n  Category breakdown:')
for k, v in cats.most_common():
    print(f'    {k:<12} {v:>5} rows')
print(f'\n  ABC: {dict(abcs)}')
print(f'  XYZ: {dict(xyzs)}')
print(f'\n  Total to update: {len(updates)}\n')

# ── Step 7: Patch benchmarks_cache ────────────────────────────────────────────
print('Patching benchmarks_cache...')
for i, u in enumerate(updates):
    row_id = u.pop('id')
    patch('benchmarks_cache', row_id, u)
    if (i + 1) % 100 == 0:
        print(f'  {i+1}/{len(updates)} updated...')

print(f'\nDone. {len(updates)} rows classified.')
print('Now run the S&OP portal → Stock Guide — Min/Max will auto-use categories.')
