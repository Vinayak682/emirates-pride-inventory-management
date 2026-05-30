"""
gen_soh_sql.py — generates fix_store_soh_may2026.sql
Run: python gen_soh_sql.py
Then paste the SQL into Supabase SQL Editor and run it.
"""
import openpyxl, os
from collections import defaultdict

FOLDER = r"C:\Users\AMALKANDATHIL\OneDrive - Emirates Pride Perfumes Trading\Desktop\Stock Report\Store Stock Report 24.05.2026"
OUT    = r"C:\Users\AMALKANDATHIL\Downloads\fix_store_soh_may2026.sql"

FILE_MAP = [
    ("AJMAN CITY CENTRE - 24-May-26.xlsx",              "AJ001",   "Ajman City Centre",        "UAE","EPP","2026-05-24"),
    ("AL AIN MALL - 25-May-26.xlsx",                    "AL001",   "Al Ain Mall",              "UAE","EPP","2026-05-25"),
    ("ASL BAS MALL - 24-May-26.xlsx",                   "BAS001",  "ASL BAS Mall",             "UAE","ASL","2026-05-24"),
    ("BAS KIOSK - 24-May-26.xlsx",                      "A0002",   "BAS Mall Kiosk",           "UAE","EPP","2026-05-24"),
    ("BAS SHOP - 24-May-26.xlsx",                       "A0001",   "BAS Mall Shop",            "UAE","EPP","2026-05-24"),
    ("BAS SHOP 2 - 24-May-26.xlsx",                     "A0010",   "BAS Mall Shop 2",          "UAE","EPP","2026-05-24"),
    ("BAWADI 1 - 24-May-26.xlsx",                       "AL002",   "Bawadi Mall Kiosk 1",      "UAE","EPP","2026-05-24"),
    ("BAWADI 2 - 25-May-26.xlsx",                       "AL003",   "Bawadi Mall Kiosk 2",      "UAE","EPP","2026-05-25"),
    ("BAWADI MALL - 24-May-26.xlsx",                    "BAW001",  "Bawadi Mall (ASL)",        "UAE","ASL","2026-05-24"),
    ("DALMA KIOSK - 24-May-26 (CSV Format).xlsx",       "A0004",   "Dalma Mall Kiosk",         "UAE","EPP","2026-05-24"),
    ("DALMA SHOP - 24-May-26 (Corrected).xlsx",         "A0003",   "Dalma Mall Shop",          "UAE","EPP","2026-05-24"),
    ("DUBAI HILLS MALL - 24-May-26 (Corrected).xlsx",   "DX006",   "Dubai Hills Mall",         "UAE","EPP","2026-05-24"),
    ("Dubai Shop Stock Movement Report - 24-May-26.xlsx","DX001",  "Dubai Mall Shop",          "UAE","EPP","2026-05-24"),
    ("FUJAIRAH CITY CENTRE - 24-May-26.xlsx",           "FJ0001",  "Fujairah City Centre (ASL)","UAE","ASL","2026-05-24"),
    ("JIMI MALL - 24-May-26 (Corrected).xlsx",          "AL004",   "Al Jimi Mall",             "UAE","EPP","2026-05-24"),
    ("MAKANI MALL - 25-May-26.xlsx",                    "MAK001",  "Makani Zakhar Mall (ASL)", "UAE","ASL","2026-05-25"),
    ("MAKANI SHOP - 24-May-26.xlsx",                    "AL006",   "Makani Zakhar Mall Shop",  "UAE","EPP","2026-05-24"),
    ("MALL OF EMIRATES - 24-May-26.xlsx",               "DX004",   "Mall of the Emirates",     "UAE","EPP","2026-05-24"),
    ("MANAR MALL SHOP - 24-May-26.xlsx",                "RK001",   "Manar Mall Shop",          "UAE","EPP","2026-05-24"),
    ("MIRDIF CITY CENTRE - 25-May-26.xlsx",             "DX005",   "Mirdif City Centre",       "UAE","EPP","2026-05-25"),
    ("YAS MALL - 24-May-26 (Corrected).xlsx",           "A0009",   "Yas Mall Podium",          "UAE","EPP","2026-05-24"),
    ("YAS MALL 3 - 25-May-26 (Corrected).xlsx",         "A0008",   "Yas Mall Kiosk 3",         "UAE","EPP","2026-05-25"),
    ("YAS MALL KIOSK 2 - 24-May-26 (Corrected).xlsx",  "A0007",   "Yas Mall Kiosk 2",         "UAE","EPP","2026-05-24"),
    ("YAS PROMOTIONS - 24-May-26 (Corrected).xlsx",     "PS_YAS",  "Yas Promotions",           "UAE","EPP","2026-05-24"),
    ("ZAHIA CITY CENTRE - 24-May-26.xlsx",              "SH001",   "Zahia City Centre",        "UAE","EPP","2026-05-24"),
]

SKU_MAP = {
    "white 100ml perfume":"C00002","maroon 100ml perfume":"C00004","navy 100ml perfume":"C00003",
    "violet 100ml perfume":"C00012","rose gold 100ml perfume":"C00014","blue 100ml perfume":"C00005",
    "green 100ml perfume":"C00010","red 100ml perfume":"C00011","black 100ml perfume":"C00006",
    "brown 100ml perfume":"C00007","orange 100ml perfume":"C00008","burgundy 100ml perfume":"C00009",
    "grey 100ml perfume":"C00013","pink 100ml perfume":"C00002",
    "amber bel oud":"B00003","amber bel oud paper box":"B00003",
    "peaceful life":"B00007","peaceful life paper box":"B00007",
    "mystery":"B00005","mystery paper box":"B00005",
    "midnight glow":"B00008","midnight glow paper box":"B00008",
    "master signature":"B00020","master signature paper box":"B00020","masters paper box":"B00020",
    "midnight bloom":"B00021","midnight bloom paper box":"B00021",
    "hidden leather":"B00015","hidden leather paper box":"B00015",
    "hidden tobacco":"B00018","hidden tobacco paper box":"B00018",
    "mysterious rose":"B00016","mysterious rose paper box":"B00016",
    "thekrayat":"B00017","thekrayat paper box":"B00017",
    "masters":"B00019","masters paper box(box 2 &3 bel)":"B00019",
    "noor al oud":"B00001","bakhoor noor al oud":"B00001","bakhoor original":"B00006","original":"B00006",
    "velvet pearl":"B00004","midnight moon":"B00009","silver water":"B00010","precious oud":"B00011",
    "safa":"B00012","dahab":"B00013","jasmine silk":"B00014","pure gold":"B00022","luxury":"B00023",
    "3 bel black box with 2 oil":"BX0002","3 bel black box":"BX0002","bx0002":"BX0002",
    "bod gift box":"BX0014","bx0014":"BX0014",
    "maroon set box":"SP0001","reflection set box":"SP0002","blue set box":"SP0003",
    "black set box":"SP0004","grey set box":"SP0005","gold set box":"SP0006","navy set box":"SP0007",
    "future bakhoor":"SP0030","future oud":"SP0031","master signature box":"SP0023",
    "midnight bloom box":"SP0037",
    "dakhoon al emarat":"D00001","dakhoon al emarat 100g":"D00001","dakhoon bukhoor":"D00002",
    "dakhoon amber":"D00003","dakhoon oud":"D00004","dakhoon rose":"D00005","dakhoon musk":"D00006",
    "dakhoon gold":"D00007","dakhoon special":"D00008","dakhoon premium":"D00009",
    "oud meydan":"O00001","oud amiri":"O00002","hindi khas":"O00003","mukhallat":"O00004",
    "safwa":"O00005","more of oud":"O00006","oud fakhamah":"O00007","oud emarat":"O00008",
    "qalah":"HR0001","qalah - heritage collection":"HR0001","hessa":"HR0002","hessa - heritage collection":"HR0002",
    "sapphire serenity":"RADA-006","velvet topaz":"RM2001","smoky jasper":"RM2003","silky crystal":"RM2004","royal garnet":"RM2005",
    "medkhan (small)":"AC0001","medkhan small":"AC0001","medkhan (large)":"AC0002","charcoal":"AC0003","lighter":"AC0004","picker":"AC0005","candle":"AC0006",
    "caramel luban":"AP012","caramel luban perfume":"AP012",
    "black vanilla 50ml":"AP001","black vanilla":"AP001","secret leather 50ml":"AP002","secret leather":"AP002",
    "white bouquet 50ml":"AP003","white bouquet":"AP003","leather intense 50ml":"AP004","leather intense":"AP004",
    "rich vanilla 50ml":"AP005","rich vanilla":"AP005","spicy sandal 50ml":"AP006","spicy sandal":"AP006",
    "velvet amber":"AP007","velvet amber 50ml":"AP007","dark musk":"AP008","dark musk 50ml":"AP008",
    "midnight berry":"AP009","golden oud":"AP010","rose fantasy":"AP011",
    "caramel luban oil":"AO012","black vanilla oil":"AO001","secret leather oil":"AO002",
    "white bouquet oil":"AO003","leather intense oil":"AO004","rich vanilla oil":"AO005",
    "spicy sandal oil":"AO006","velvet amber oil":"AO007","dark musk oil":"AO008",
    "black vanilla hair & body mist":"AH001","secret leather hair & body mist":"AH006",
    "white bouquet hair & body mist":"AH007","leather intense hair & body mist":"AH002",
    "rich vanilla hair & body mist":"AH003","spicy sandal hair & body mist":"AH004","velvet amber hair & body mist":"AH005",
    "asl gift set box":"AG001","asl 6pc perfume set":"AG011","asl 3 gift set box":"AG012",
    "bundle foldable gift box -2":"AG014","bundle foldable gift box -3":"AG015",
    "bundle foldable gift box -4":"AG017","asl gift box - velvet amber":"AG018","asl gift box - dark musk":"AG019",
    "white bouquet air freshener 250ml":"AAF002","white bouquet air freshner 250ml":"AAF002",
    "secret leather reed diffuser":"ARD001","white bouquet reed diffuser":"ARD003","sunbeam tanning oil":"ATO001",
}

def norm(s):
    if not s: return ""
    return str(s).lower().strip().replace("  "," ")

def lookup_sku(name):
    n = norm(name)
    if n in SKU_MAP: return SKU_MAP[n]
    for k, v in SKU_MAP.items():
        if len(k) > 7 and k in n: return v
    return None

def esc(s):
    if s is None: return "NULL"
    return "'" + str(s).replace("'","''") + "'"

all_rows = []
by_store = defaultdict(lambda:[0,0])

for (filename, sc, sn, reg, br, sd) in FILE_MAP:
    path = os.path.join(FOLDER, filename)
    if not os.path.exists(path):
        print(f"MISSING: {filename}")
        continue
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    raw = list(ws.iter_rows(values_only=True))
    wb.close()
    seen = set()
    for row in raw[1:]:
        if not row or len(row) < 3: continue
        cat  = str(row[0]).strip() if row[0] else ""
        prod = str(row[1]).strip() if row[1] else ""
        if not prod or prod.lower() in ("product",""): continue
        if prod in seen: continue
        seen.add(prod)
        try: qty = float(row[2]) if row[2] is not None else 0.0
        except: qty = 0.0
        sku = lookup_sku(prod)
        all_rows.append((sc,sn,reg,br,sd,sku,prod,cat,qty))
        by_store[sc][0] += 1
        by_store[sc][1] += qty

# Build SQL
lines = []
lines.append("-- ============================================================")
lines.append("-- Emirates Pride Perfumes — Store SOH Fix Upload")
lines.append("-- Source: Store Stock Report 24.05.2026 (25 store files)")
lines.append("-- Generated: 30 May 2026")
lines.append("-- Run in Supabase SQL Editor:")
lines.append("-- https://supabase.com/dashboard/project/ncszurcrkngjcjqsowln/sql")
lines.append("-- ============================================================")
lines.append("")
lines.append("-- STEP 1: Clear all store SOH rows (warehouse rows are kept)")
lines.append("DELETE FROM store_soh_snapshots")
lines.append("WHERE store_code NOT IN ('WH_EPP', 'WH_ASL');")
lines.append("")
lines.append("-- STEP 2: Insert " + str(len(all_rows)) + " rows from 25 store files")
lines.append("INSERT INTO store_soh_snapshots")
lines.append("  (store_code, store_name, region, brand, snapshot_date, sku_code, product_name, category, soh_qty)")
lines.append("VALUES")

vals = []
for (sc,sn,reg,br,sd,sku,prod,cat,qty) in all_rows:
    vals.append("  (%s,%s,%s,%s,%s,%s,%s,%s,%s)" % (
        esc(sc),esc(sn),esc(reg),esc(br),esc(sd),esc(sku),esc(prod),esc(cat),qty
    ))
lines.append(",\n".join(vals) + ";")
lines.append("")
lines.append("-- STEP 3: Verify — expected totals per store")
lines.append("SELECT store_code, store_name, COUNT(*) AS rows, ROUND(SUM(soh_qty)) AS total_units")
lines.append("FROM store_soh_snapshots")
lines.append("WHERE store_code NOT IN ('WH_EPP','WH_ASL')")
lines.append("GROUP BY store_code, store_name")
lines.append("ORDER BY store_code;")

sql = "\n".join(lines)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(sql)

print("SQL file written to: " + OUT)
print("Total rows: %d" % len(all_rows))
print()
print("Store | Rows | Total Units")
print("-" * 45)
grand_rows, grand_units = 0, 0
for code in sorted(by_store.keys()):
    r, u = by_store[code]
    print("  %-8s | %4d | %6d" % (code, r, int(u)))
    grand_rows += r; grand_units += u
print("-" * 45)
print("  %-8s | %4d | %6d" % ("TOTAL", grand_rows, int(grand_units)))
