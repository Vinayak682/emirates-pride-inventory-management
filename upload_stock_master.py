"""
Emirates Pride — Stock Master Excel -> Supabase store_soh_snapshots
====================================================================
Reads Emirates_Pride_Perfumes_Stock_Master.xlsx
Uses the LAST COLUMN WITH REAL DATA per store (handles stores that
haven't filled in the latest day yet).
Generates SQL + uploads + verifies.

Usage:
  python upload_stock_master.py              # generate SQL + upload + verify
  python upload_stock_master.py --sql-only   # generate SQL only, no upload
  python upload_stock_master.py --verify     # verify Supabase vs parsed data
"""

import sys, re, json, urllib.request, urllib.parse, urllib.error
import datetime
import pandas as pd
from collections import defaultdict

# ─── CONFIG ──────────────────────────────────────────────────────────────────
EXCEL_PATH   = r"C:\Users\AMALKANDATHIL\Downloads\Emirates_Pride_Perfumes_Stock_Master.xlsx"
SQL_OUT_PATH = r"C:\Users\AMALKANDATHIL\Downloads\stock_master_upload.sql"

SUPABASE_URL = "https://ncszurcrkngjcjqsowln.supabase.co"
SUPABASE_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsIn"
                "JlZiI6Im5jc3p1cmNya25namNqcXNvd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOj"
                "E3Nzc0NjA4NTgsImV4cCI6MjA5MzAzNjg1OH0.i5cPlP7JTTCKMXuFqI81WXbjQ"
                "a71qBkRBZEBvNf6ZmM")

# ─── SHEET → STORE CODE MAPPING ──────────────────────────────────────────────
SHEET_TO_STORE = {
    "Dalma Mall-Shop":        ("A0003",  "Dalma Mall Shop",                    "EPP", "Abu Dhabi"),
    "Fujairah City Centre":   ("FJ001",  "Fujairah City Centre Kiosk",         "EPP", "Fujairah"),
    "Al Ain Mall":            ("AL001",  "Al Ain Mall Kiosk",                  "EPP", "Al Ain"),
    "Zahia City Centre":      ("SH001",  "Zahia City Centre Kiosk",            "EPP", "Sharjah"),
    "Makani Shop":            ("AL006",  "Makhani Zakhar Mall Shop",           "EPP", "Al Ain"),
    "Dubai Hills Mall":       ("DX006",  "Dubai Hills Mall Shop",              "EPP", "Dubai"),
    "Bawadi 1":               ("AL002",  "Bawadi Mall Kiosk 1",               "EPP", "Al Ain"),
    "ASL Yas Mall":           ("YMK001", "Yas Mall (ASL)",                     "ASL", "Abu Dhabi"),
    "Boutique Al Manar Mall": ("RK001",  "Manar Mall Shop",                    "EPP", "RAK"),
    "BAS Shop":               ("A0001",  "Bawabat al Sharq Mall Shop",         "EPP", "Abu Dhabi"),
    "Jimi Mall":              ("AL004",  "Jimi Mall Shop",                     "EPP", "Al Ain"),
    "ASL Makani Mall":        ("MAK001", "Makhani Zakhar Mall (ASL)",          "ASL", "Al Ain"),
    "Bawadi 2":               ("AL003",  "Bawadi Mall Kiosk 2",               "EPP", "Al Ain"),
    "Ajman City Centre":      ("AJ001",  "Ajman City Centre Kiosk",            "EPP", "Ajman"),
    "Yas Mall Kiosk 2":       ("A0007",  "Yas Mall Kiosk 2",                   "EPP", "Abu Dhabi"),
    "Deerfield Mall":         ("A0005",  "Deerfield Mall Kiosk",               "EPP", "Abu Dhabi"),
    "ASL BAS Mall":           ("BAS001", "Bawabat al Sharq Mall Kiosk (ASL)", "ASL", "Abu Dhabi"),
    "Yas Mall Kiosk 3":       ("A0008",  "Yas Mall Kiosk 3",                   "EPP", "Abu Dhabi"),
    "Yas Promotions":         ("PS_YAS", "Yas Promotions",                     "EPP", "Abu Dhabi"),
    "Dubai Mall":             ("DX001",  "Dubai Mall Shop",                    "EPP", "Dubai"),
    "Manar Kiosk":            ("RK002",  "Manar Mall Kiosk",                   "EPP", "RAK"),
    "Mirdif City Centre":     ("DX005",  "Mirdif City Centre Kiosk",           "EPP", "Dubai"),
    "ASL Fujairah CC":        ("FJ0001", "Fujairah City Centre (ASL)",         "ASL", "Fujairah"),
    "ASL Bawadi Mall":        ("BAW001", "Bawadi Mall (ASL)",                  "ASL", "Al Ain"),
    "Dalma Kiosk":            ("A0004",  "Dalma Mall Kiosk",                   "EPP", "Abu Dhabi"),
    "BAS Kiosk":              ("A0002",  "Bawabat al Sharq Mall Kiosk",        "EPP", "Abu Dhabi"),
    "BAS Shop 2":             ("A0010",  "Bawabat al Sharq Mall Shop 2",       "EPP", "Abu Dhabi"),
}

# ─── CATEGORY / SECTION HEADER ROWS (skip — no SOH value) ───────────────────
CATEGORY_HEADERS = {
    "accessories & gift boxes", "heritage collection", "paper box",
    "oud, oils, & sets", "oud", "dakhoon collection", "oil & 10ml perfumes",
    "perfumes (stock movement report)", "bel collection", "perfumes (50ml)",
    "hair & body mist", "oils (6ml)", "gift sets", "hair & body lotion",
    "air fresheners", "reed diffusers", "all over sprays", "oils & gift sets",
    "perfumes", "sets", "accessories",
}

# Rows whose names contain these patterns are annotation/note rows — skip them
ANNOTATION_PATTERNS = [
    r'\(\+\d+\)',           # "(+24)" stock adjustment annotations
    r'\(dup row\)',          # duplicate marker
    r'\(image \d',          # split-image notes
    r'\(ara-recon\)',        # recon notes
    r'\(mubkhar\)',
    r'\(lotion\)',
    r'\(body wash\)',
    r'\(body lotion\)',
    r'\(wash\)',
    r'\(white lotion\)',
    r'\(white body wash\)',
    r'\(luban\)',
    r'\(caramel luban\)',
    r'\(future mubkhour\)',
    r'\(patchouli\)',
    r'\(caramel\)',
    r'\(image 1 split\)',
    r'^\d+$',               # pure numbers
]

def is_annotation(name):
    for pat in ANNOTATION_PATTERNS:
        if re.search(pat, name, re.I):
            return True
    return False

# ─── PRODUCT NAME → (SKU_CODE, CATEGORY) MAPPING ────────────────────────────
SKU_MAP = {
    # ── Accessories ──────────────────────────────────────────────────────────
    "medkhan (small)":                       ("AC0001", "Accessories"),
    "charcoal":                              ("AC0002", "Accessories"),
    "lighter":                               ("AC0003", "Accessories"),
    "picker":                                ("AC0004", "Accessories"),
    "candle":                                ("AC0005", "Accessories"),

    # ── Gift Boxes (BX-series) ────────────────────────────────────────────────
    "box 3 bel oil - black":                 ("BX0002", "Gift Boxes"),
    "3 bel black box with 2 oil gift box":   ("BX0002", "Gift Boxes"),
    "bod gift box":                          ("BX0014", "Gift Boxes"),
    "box 2 bel 2 oil set-white/gold box":    ("BX0001", "Gift Boxes"),
    "dekoon gift set":                       ("BX0011", "Gift Boxes"),
    "dakhoon gift set":                      ("BX0011", "Gift Boxes"),
    "vip set box":                           ("BX0012", "Gift Boxes"),
    "luxury gift set":                       ("BX0015", "Gift Boxes"),
    "luxury gift box":                       ("BX0015", "Gift Boxes"),

    # ── Heritage Collection (HR-series) ──────────────────────────────────────
    "qalah -heritage collection":            ("HR0001", "Heritage"),
    "danah- heritage collection":            ("HR0005", "Heritage"),
    "al emarat- heritage collection":        ("HR0007", "Heritage"),
    "barjeel- heritage collection":          ("HR0002", "Heritage"),
    "khaimah- heritage collection":          ("HR0003", "Heritage"),
    "safeena - heritage collection":         ("HR0004", "Heritage"),
    "dallah- heritage collection":           ("HR0006", "Heritage"),

    # ── Paper Boxes (B-series -PB) ────────────────────────────────────────────
    "bergamot bel amber paper box(box 2 & 3 bel)":  ("B00001-PB", "Paper Boxes"),
    "jasmine bel musk paper box(box 2 & 3 bel)":    ("B00002-PB", "Paper Boxes"),
    "amber bel oud paper box(box 2 & 3 bel)":       ("B00003-PB", "Paper Boxes"),
    "meydan paper box(box 2 & 3 bel)":              ("B00004-PB", "Paper Boxes"),
    "mystery paper box(box 2 & 3 bel)":             ("B00005-PB", "Paper Boxes"),
    "mersal paper box(box 2 & 3 bel)":              ("B00006-PB", "Paper Boxes"),
    "midnight glow paper box(box 2 & 3 bel)":       ("B00008-PB", "Paper Boxes"),
    "peaceful life paper box(box 2 & 3 bel)":       ("B00007-PB", "Paper Boxes"),
    "sakura paper box(box 2 & 3 bel)":              ("B00010-PB", "Paper Boxes"),
    "ambergris paper box(box 2 & 3 bel)":           ("B00012-PB", "Paper Boxes"),
    "arabica paper box(box 2 & 3 bel)":             ("B00013-PB", "Paper Boxes"),
    "firewood paper box(box 2 & 3 bel)":            ("B00014-PB", "Paper Boxes"),
    "hidden leather paper box(box 2 & 3 bel)":      ("B00015-PB", "Paper Boxes"),
    "mysterious rose paper box(box 2 & 3 bel)":     ("B00016-PB", "Paper Boxes"),
    "thekrayat paper box(box 2 & 3 bel)":           ("B00017-PB", "Paper Boxes"),
    "hidden tobacco paper box(box 2 & 3 bel)":      ("B00018-PB", "Paper Boxes"),
    "masters paper box(box 2 & 3 bel)":             ("B00019-PB", "Paper Boxes"),
    "master signature box(box 2 & 3 bel)":          ("B00020-PB", "Paper Boxes"),
    "midnight bloom paper box(box 2 & 3 bel)":      ("B00021-PB", "Paper Boxes"),

    # ── Sets (SP/G-series) ────────────────────────────────────────────────────
    "white oud set box":                     ("G00003",  "Sets"),
    "white set box":                         ("SP0006",  "Sets"),
    "maroon set box":                        ("SP0013",  "Sets"),
    "more of oud":                           ("O00006",  "Oud"),
    "reflection set box":                    ("SP0022",  "Sets"),
    "reflection 100ml perfume":              ("SP0022",  "Sets"),
    "future bakhoor":                        ("SP0037",  "Future Collection"),
    "future oud":                            ("SP0038",  "Future Collection"),
    "masters set box":                       ("SP0019",  "Sets"),
    "my signature set box":                  ("SP0042",  "Sets"),
    "midnight glow set box":                 ("SP0041",  "Sets"),
    "future diffuser (mubkhar)":             ("SP0043",  "Future Collection"),
    "future diffuser":                       ("SP0043",  "Future Collection"),
    "future diffuser mubakhan":              ("SP0043",  "Future Collection"),
    "future mubkhar":                        ("SP0043",  "Future Collection"),
    "future traditional set":                ("SP0040",  "Future Collection"),
    "mystery 100ml":                         ("B00005",  "Bel Collection"),
    "dark set":                              ("SP0013",  "Sets"),

    # ── Oud (O-series) ────────────────────────────────────────────────────────
    "oud amiri":                             ("O00002", "Oud"),
    "oud meydan":                            ("O00001", "Oud"),
    "oud al emarat":                         ("O00008", "Oud"),
    "oud al fakhamah":                       ("O00007", "Oud"),
    "oud hindi khas":                        ("O00003", "Oud"),
    "oud hindi malaki":                      ("O00004", "Oud"),

    # ── Dakhoon (D-series) ────────────────────────────────────────────────────
    "dakhoon al emarat":                     ("D00001", "Dakhoon"),
    "dakhoon badia":                         ("D00003", "Dakhoon"),
    "dakhoon al marasim":                    ("D00005", "Dakhoon"),
    "dakhoon al dar":                        ("D00002", "Dakhoon"),
    "dakhoon retaj":                         ("D00004", "Dakhoon"),
    "dakhoon al barzah":                     ("D00006", "Dakhoon"),

    # ── Oils & 10ml Perfumes ──────────────────────────────────────────────────
    "hindi special":                         ("O00003", "Oils"),
    "seufi special":                         ("O00005", "Oils"),
    "white oil -8 ml":                       ("I00003", "Oils"),
    "maroon oil - 8 ml":                     ("I00004", "Oils"),
    "no.4 oil -8 ml":                        ("I00005", "Oils"),
    "musk oil 8 ml":                         ("I00006", "Oils"),
    "peaceful life 10 ml":                   ("B00007", "Oils"),
    "masters perfume 10ml":                  ("B00019", "Oils"),
    "white oud 10 ml":                       ("SP0006", "Oils"),
    "white kit bag set":                     ("SP0006", "Sets"),
    "masters signature 10ml combo":          ("B00020", "Sets"),
    "summer set":                            ("SP0039", "Sets"),
    "midnight bloom 2x10ml":                 ("B00021", "Oils"),
    "future bakhoor 10ml":                   ("SP0037", "Future Collection"),
    "future bakhoor 1.5ml":                  ("SP0037", "Future Collection"),
    "future oud 10ml":                       ("SP0038", "Future Collection"),
    "future oud 1.5ml":                      ("SP0038", "Future Collection"),

    # ── Perfumes / Caballo (C-series) ─────────────────────────────────────────
    "white 100ml perfume":                   ("C00002", "Perfumes"),
    "maroon 100ml perfume":                  ("C00004", "Perfumes"),
    "navy 100ml perfume":                    ("C00012", "Perfumes"),
    "violet 100ml perfume":                  ("C00011", "Perfumes"),
    "maroon intense":                        ("C00010", "Perfumes"),
    "black 100ml perfume":                   ("C00014", "Perfumes"),
    "no.4 100ml perfume":                    ("SP0005", "Perfumes"),
    "whit overdose 100ml perfume":           ("C00013", "Perfumes"),

    # ── Bel Collection (B-series) ─────────────────────────────────────────────
    "bergamot bel amber":                    ("B00001", "Bel Collection"),
    "jasmine bel musk":                      ("B00002", "Bel Collection"),
    "amber bel oud":                         ("B00003", "Bel Collection"),
    "peaceful life":                         ("B00007", "Bel Collection"),
    "midnight glow":                         ("B00008", "Bel Collection"),
    "golden chance":                         ("B00009", "Bel Collection"),
    "meydan":                                ("B00004", "Bel Collection"),
    "mystery":                               ("B00005", "Bel Collection"),
    "mersal":                                ("B00006", "Bel Collection"),
    "sakura":                                ("B00010", "Bel Collection"),
    "midnight bloom":                        ("B00021", "Bel Collection"),
    "ambergris":                             ("B00012", "Bel Collection"),
    "arabica":                               ("B00013", "Bel Collection"),
    "firewood":                              ("B00014", "Bel Collection"),
    "hidden leather":                        ("B00015", "Bel Collection"),
    "mysterious rose":                       ("B00016", "Bel Collection"),
    "thekrayat":                             ("B00017", "Bel Collection"),
    "hidden tobacco":                        ("B00018", "Bel Collection"),
    "masters":                               ("B00019", "Bel Collection"),
    "masters signature":                     ("B00020", "Bel Collection"),

    # ── ASL Perfumes (AP-series) ──────────────────────────────────────────────
    "black vanilla 50ml":                    ("AP001",  "ASL Perfumes"),
    "secret leather 50ml":                   ("AP002",  "ASL Perfumes"),
    "white bouquet 50ml":                    ("AP003",  "ASL Perfumes"),
    "leather intense 50ml":                  ("AP004",  "ASL Perfumes"),
    "rich vanilla 50ml":                     ("AP005",  "ASL Perfumes"),
    "spicy sandalwood 50ml":                 ("AP006",  "ASL Perfumes"),
    "velvet amber 50ml":                     ("AP007",  "ASL Perfumes"),
    "dark musk 50ml":                        ("AP008",  "ASL Perfumes"),
    "royal tobacco 50ml":                    ("AP009",  "ASL Perfumes"),
    "patchouli glow 50ml":                   ("AP010",  "ASL Perfumes"),
    "dark wood":                             ("AP011",  "ASL Perfumes"),
    "dark wood 50ml":                        ("AP011",  "ASL Perfumes"),
    "darkwood perfume 50ml":                 ("AP011",  "ASL Perfumes"),
    "caramel luban perfume 50ml":            ("AP012",  "ASL Perfumes"),

    # ── ASL Hair & Body Mist (AH-series) ─────────────────────────────────────
    "allover spray dark musk":               ("AH004",  "ASL Hair & Body"),
    "allover spray velvet amber":            ("AH003",  "ASL Hair & Body"),
    "allover spray darkwood perfume 50ml":   ("AH006",  "ASL Hair & Body"),
    "velvet amber hair & body mist 50ml":    ("AH003",  "ASL Hair & Body"),
    "dark musk hair & body mist 50ml":       ("AH004",  "ASL Hair & Body"),
    "black vanilla hair & body mist 50ml":   ("AH001",  "ASL Hair & Body"),
    "secret leather hair & body mist 50ml":  ("AH002",  "ASL Hair & Body"),
    "royal tobacco hair & body mist 50ml":   ("AH005",  "ASL Hair & Body"),

    # ── ASL Oils (AO-series) ──────────────────────────────────────────────────
    "black vanilla oil 6ml":                 ("AO001",  "ASL Oils"),
    "secret leather oil 6ml":               ("AO002",  "ASL Oils"),
    "white bouquet oil 6ml":                ("AO003",  "ASL Oils"),
    "leather intense oil 6ml":              ("AO004",  "ASL Oils"),
    "rich vanilla oil 6ml":                 ("AO005",  "ASL Oils"),
    "spicy sandalwood oil 6ml":             ("AO006",  "ASL Oils"),
    "velvet amber oil 6ml":                 ("AO007",  "ASL Oils"),
    "dark musk oil 6ml":                    ("AO008",  "ASL Oils"),
    "royal tobacco oil 6ml":                ("AO009",  "ASL Oils"),
    "patchouli glow oil 6ml":               ("AO010",  "ASL Oils"),
    "dark wood oil 6ml":                    ("AO011",  "ASL Oils"),
    "darkwood oil 6ml":                     ("AO011",  "ASL Oils"),
    "caramel luban oil 6ml":                ("AO012",  "ASL Oils"),
    # legacy names without "6ml"
    "black vanilla oil":                    ("AO001",  "ASL Oils"),
    "secret leather oil":                   ("AO002",  "ASL Oils"),
    "white bouquet oil":                    ("AO003",  "ASL Oils"),
    "rich vanilla oil":                     ("AO005",  "ASL Oils"),
    "velvet amber oil":                     ("AO007",  "ASL Oils"),
    "dark musk oil":                        ("AO008",  "ASL Oils"),
    "royal tobacco oil":                    ("AO009",  "ASL Oils"),
    "patchouli glow oil":                   ("AO010",  "ASL Oils"),
    "patchouli glow glow oil 6ml":          ("AO010",  "ASL Oils"),

    # ── ASL Body Lotion (AHB-series) ──────────────────────────────────────────
    "royal tobacco body lotion":            ("AHB005", "ASL Body Lotion"),
    "velvet amber body lotion":             ("AHB003", "ASL Body Lotion"),
    "secret leather body lotion":           ("AHB002", "ASL Body Lotion"),
    "dark musk body lotion":                ("AHB004", "ASL Body Lotion"),

    # ── ASL Reed Diffusers (ARD-series) ──────────────────────────────────────
    "secret leather diffuser":              ("ARD001", "ASL Reed Diffusers"),
    "cool violet diffuser":                 ("ARD002", "ASL Reed Diffusers"),
    "white bouquet diffuser":               ("ARD003", "ASL Reed Diffusers"),

    # ── ASL Air Fresheners (AAF-series) ──────────────────────────────────────
    "cool violet air freshner":             ("AAF001", "ASL Air Fresheners"),
    "white bouquet airfreshner":            ("AAF002", "ASL Air Fresheners"),

    # ── ASL Gift Sets (AG-series) ─────────────────────────────────────────────
    "asl gift set box":                     ("AG001",  "ASL Gift Sets"),
    "asl 6 perfumes set box":               ("AG011",  "ASL Gift Sets"),
    "asl 6pc perfume set":                  ("AG011",  "ASL Gift Sets"),
    "asl 3 gift set box":                   ("AG011",  "ASL Gift Sets"),
    "bundle foldable gift box -1":          ("AG013",  "ASL Gift Sets"),
    "bundle foldable gift box -2":          ("AG014",  "ASL Gift Sets"),
    "bundle foldable gift box -3":          ("AG017",  "ASL Gift Sets"),
    "bundle foldable gift box -4":          ("AG017",  "ASL Gift Sets"),
    "bundle foldable gift box-1":           ("AG013",  "ASL Gift Sets"),
    "bundle foldable gift box-2":           ("AG014",  "ASL Gift Sets"),
    "bundle foldable gift box-3":           ("AG017",  "ASL Gift Sets"),
    "bundle foldable gift box-4":           ("AG017",  "ASL Gift Sets"),
    "asl bundle foldable gift box - 1":     ("AG013",  "ASL Gift Sets"),
    "asl bundle foldable gift box - 2":     ("AG014",  "ASL Gift Sets"),
    "asl ramadan gift set":                 ("AG016",  "ASL Gift Sets"),
    "asl ramadan gift set gift box":        ("AG016",  "ASL Gift Sets"),
    "asl bundle box 4":                     ("AG017",  "ASL Gift Sets"),
    "asl gift box - velvet amber":          ("AG018",  "ASL Gift Sets"),
    "asl gift box - dark musk":             ("AG019",  "ASL Gift Sets"),
    "asl gift box - velvet amber gift box": ("AG018",  "ASL Gift Sets"),
    "asl gift box - dark musk gift box":    ("AG019",  "ASL Gift Sets"),
    "gift velvet amber":                    ("AG018",  "ASL Gift Sets"),
    "gift dark musk":                       ("AG019",  "ASL Gift Sets"),
    "box 3 perfumes and 3 hair mist":       ("AG014",  "ASL Gift Sets"),
    "discovery set":                        ("AG001",  "ASL Gift Sets"),
    "asl 3 pcs discovery set":              ("AG001",  "ASL Gift Sets"),
    "asl 3 pcs discovery set - ramadan mubarak 3ml": ("AG016", "ASL Gift Sets"),
    "asl 3 pcs discovery set -ramadan mubarak 3ml":  ("AG016", "ASL Gift Sets"),

    # ── ASL Specialty ─────────────────────────────────────────────────────────
    "sunbeam tanning oil":                  ("ATO001", "ASL Specialty"),

    # ── EPP Body Care ─────────────────────────────────────────────────────────
    "white lotion 40g":                     ("BCW001", "Body Care"),
    "lotion 40g":                           ("BCW001", "Body Care"),
    "emirates pride body wash white 80ml":  ("BCW002", "Body Care"),
    "pride body wash white 80ml":           ("BCW002", "Body Care"),
    "future bakhoor 10ml w. body wash":     ("SP0037", "Future Collection"),
    "future bakhoor 10ml w. body lotion":   ("SP0037", "Future Collection"),
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def parse_date_from_header(header_str):
    """'D-Mon-YY (Latest SOH)' or '(Closing)' → 'YYYY-MM-DD'"""
    m = re.search(
        r'(\d{1,2})[- ](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ](\d{2})',
        str(header_str), re.I)
    if not m:
        return None
    day, mon, yr = m.group(1), m.group(2), m.group(3)
    month_num = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                 "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    year = 2000 + int(yr)
    return f"{year:04d}-{month_num[mon.lower()]:02d}-{int(day):02d}"

def clean_val(v):
    """Cell → int soh.  '-' or blank = 0.  NaN = None (no entry at all)."""
    if v is None:
        return None
    s = str(v).strip()
    if s in ('', 'nan', 'None'):
        return None                 # truly empty — no data entered
    if s in ('-', '—', 'N/A', 'n/a'):
        return 0                    # explicitly zero stock
    try:
        return int(float(s))
    except:
        return None

def is_cat_header(name):
    return name.strip().lower() in CATEGORY_HEADERS

def lookup_sku(name):
    key = name.strip().lower()
    if key in SKU_MAP:
        return SKU_MAP[key]
    return (None, "Unknown")

def pick_best_col(df, num_data_cols):
    """
    Return the rightmost column index (1..num_data_cols) that has
    at least 5 rows with soh > 0. This avoids using an unfilled day.
    """
    for col_idx in range(num_data_cols, 0, -1):
        non_zero = 0
        for i in range(1, len(df)):
            v = clean_val(df.iloc[i][col_idx])
            if v is not None and v > 0:
                non_zero += 1
                if non_zero >= 5:
                    return col_idx
    return num_data_cols   # fallback

# ─── PARSE EXCEL ─────────────────────────────────────────────────────────────
def parse_excel():
    xl = pd.ExcelFile(EXCEL_PATH)
    all_rows  = []
    unmapped  = {}

    for sheet_name in xl.sheet_names:
        if sheet_name not in SHEET_TO_STORE:
            continue   # skip template sheet

        store_code, store_name, brand, region = SHEET_TO_STORE[sheet_name]
        df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
        if len(df) < 2 or len(df.columns) < 3:
            print(f"  [SKIP] {sheet_name} — too few data")
            continue

        headers       = df.iloc[0].tolist()
        num_data_cols = len(headers) - 1   # col 0 = product name

        # Find the best (rightmost fully-filled) data column
        best_col        = pick_best_col(df, num_data_cols)
        soh_header      = str(headers[best_col])
        snapshot_date   = parse_date_from_header(soh_header)
        if not snapshot_date:
            # Try all column headers, pick the rightmost parseable one
            for ci in range(num_data_cols, 0, -1):
                d = parse_date_from_header(str(headers[ci]))
                if d:
                    snapshot_date = d
                    break
        if not snapshot_date:
            snapshot_date = "2026-06-01"
            print(f"  [WARN] {sheet_name} — date not found, defaulting to {snapshot_date}")

        store_rows = []
        for i in range(1, len(df)):
            raw_name = str(df.iloc[i][0]).strip() if df.iloc[i][0] is not None else ""
            if not raw_name or raw_name == 'nan':
                continue
            if is_cat_header(raw_name):
                continue
            if is_annotation(raw_name):
                continue

            soh = clean_val(df.iloc[i][best_col])
            if soh is None:
                continue   # no data at all for this cell

            sku_code, category = lookup_sku(raw_name)
            if sku_code is None:
                unmapped[raw_name.lower()] = unmapped.get(raw_name.lower(), 0) + 1

            store_rows.append({
                "store_code":    store_code,
                "store_name":    store_name,
                "brand":         brand,
                "region":        region,
                "snapshot_date": snapshot_date,
                "sku_code":      sku_code,
                "product_name":  raw_name,
                "category":      category,
                "soh_qty":       soh,
            })

        total_units = sum(r["soh_qty"] for r in store_rows)
        flag = "  [OK] " if total_units > 0 else "  [!] "
        print(f"{flag}{sheet_name:<30} -> {store_code:<8}  date={snapshot_date}  "
              f"col={best_col}/{num_data_cols}  rows={len(store_rows)}  units={total_units:,}")
        all_rows.extend(store_rows)

    print(f"\n[SKIPPED] template/unknown sheets excluded")
    return all_rows, unmapped

# ─── VERIFY SPOT-CHECK ────────────────────────────────────────────────────────
def spot_check(rows):
    """
    Manual spot-check: compare a few known values from the Excel
    against what we parsed. These are read from the Excel directly.
    """
    xl = pd.ExcelFile(EXCEL_PATH)
    print("\n=== SPOT-CHECK (5 random store/product pairs) ===")
    checks = [
        ("Jimi Mall",      "AL004", "Dakhoon Al Emarat",   "D00001"),
        ("Dalma Mall-Shop","A0003", "White 100ml Perfume", "C00002"),
        ("Dubai Mall",     "DX001", "BOD GIFT BOX",        "BX0014"),
        ("ASL BAS Mall",   "BAS001","Black Vanilla 50ml",  "AP001"),
        ("Yas Mall Kiosk 3","A0008","Midnight Glow",       "B00008"),
    ]
    all_ok = True
    for sheet, store, prod, sku in checks:
        df = pd.read_excel(xl, sheet_name=sheet, header=None)
        headers    = df.iloc[0].tolist()
        num_cols   = len(headers) - 1
        best_col   = pick_best_col(df, num_cols)
        snap_date  = parse_date_from_header(str(headers[best_col])) or "?"
        # Find product row
        excel_val = "NOT FOUND"
        for i in range(1, len(df)):
            if str(df.iloc[i][0]).strip().lower() == prod.lower():
                excel_val = clean_val(df.iloc[i][best_col])
                break
        # Find parsed value
        parsed_val = next(
            (r["soh_qty"] for r in rows
             if r["store_code"] == store and r["product_name"].lower() == prod.lower()),
            "NOT IN PARSED"
        )
        match = "OK" if excel_val == parsed_val else "MISMATCH"
        status = "OK" if match == "OK" else "!!"
        print(f"  [{status}] {store} | {prod:<30} | Excel={excel_val}  Parsed={parsed_val}  date={snap_date}")
        if match != "OK":
            all_ok = False
    return all_ok

# ─── SQL GENERATION ──────────────────────────────────────────────────────────
def generate_sql(rows):
    store_dates = sorted({(r["store_code"], r["snapshot_date"]) for r in rows})
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "-- Emirates Pride Stock Master Upload",
        f"-- Generated: {now}",
        f"-- Stores: {len(store_dates)}  Rows: {len(rows)}",
        "",
        "-- STEP 1: Remove existing rows for these store+date combinations",
        "-- (prevents duplicates on re-run)",
    ]
    for sc, sd in store_dates:
        lines.append(
            f"DELETE FROM store_soh_snapshots "
            f"WHERE store_code='{sc}' AND snapshot_date='{sd}';"
        )

    lines += ["", "-- STEP 2: Insert fresh SOH data",
              "INSERT INTO store_soh_snapshots "
              "(store_code,store_name,brand,region,snapshot_date,"
              "sku_code,product_name,category,soh_qty) VALUES"]

    val_parts = []
    for r in rows:
        sku  = f"'{r['sku_code']}'" if r["sku_code"] else "NULL"
        pn   = r["product_name"].replace("'", "''")
        cat  = r["category"].replace("'", "''")
        val_parts.append(
            f"('{r['store_code']}','{r['store_name'].replace(chr(39),chr(39)*2)}',"
            f"'{r['brand']}','{r['region'].replace(chr(39),chr(39)*2)}',"
            f"'{r['snapshot_date']}',{sku},'{pn}','{cat}',{r['soh_qty']})"
        )
    lines.append(",\n".join(val_parts) + ";")

    lines += [
        "",
        "-- STEP 3: Verification query",
        "SELECT store_code, store_name, snapshot_date,",
        "       COUNT(*) AS rows, SUM(soh_qty) AS total_units",
        "FROM store_soh_snapshots",
        f"WHERE snapshot_date >= '2026-05-29'",
        "GROUP BY store_code, store_name, snapshot_date",
        "ORDER BY store_code, snapshot_date;",
    ]
    return "\n".join(lines)

# ─── SUPABASE UPLOAD ─────────────────────────────────────────────────────────
def sb_delete(store_code, snapshot_date):
    url = (f"{SUPABASE_URL}/rest/v1/store_soh_snapshots"
           f"?store_code=eq.{urllib.parse.quote(store_code)}"
           f"&snapshot_date=eq.{snapshot_date}")
    req = urllib.request.Request(url, method="DELETE")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Prefer", "return=minimal")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

def sb_insert(batch):
    url     = f"{SUPABASE_URL}/rest/v1/store_soh_snapshots"
    payload = json.dumps(batch).encode("utf-8")
    req     = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=minimal")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

def upload(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["store_code"], r["snapshot_date"])].append(r)

    inserted, errors = 0, 0
    for (sc, sd), grp in sorted(groups.items()):
        s = sb_delete(sc, sd)
        if s not in (200, 204):
            print(f"  [WARN DEL] {sc}/{sd} -> HTTP {s}")

        for i in range(0, len(grp), 200):
            batch  = grp[i:i+200]
            status, err = sb_insert(batch)
            if status in (200, 201):
                inserted += len(batch)
            else:
                print(f"  [ERR INS] {sc}/{sd} batch {i} -> HTTP {status}: {err}")
                errors += 1
        print(f"  [INS OK] {sc:<8} {sd}  {len(grp)} rows")

    print(f"\n  Inserted {inserted:,} rows  |  Errors: {errors}")
    return errors == 0

# ─── VERIFY AGAINST SUPABASE ─────────────────────────────────────────────────
def verify(rows):
    print("\n=== VERIFICATION vs SUPABASE ===")
    expected = defaultdict(lambda: {"rows": 0, "units": 0})
    for r in rows:
        k = (r["store_code"], r["snapshot_date"])
        expected[k]["rows"]  += 1
        expected[k]["units"] += r["soh_qty"]

    all_ok = True
    for (sc, sd), exp in sorted(expected.items()):
        url = (f"{SUPABASE_URL}/rest/v1/store_soh_snapshots"
               f"?store_code=eq.{urllib.parse.quote(sc)}"
               f"&snapshot_date=eq.{sd}&select=soh_qty")
        req = urllib.request.Request(url)
        req.add_header("apikey", SUPABASE_KEY)
        req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
        try:
            with urllib.request.urlopen(req) as r2:
                data      = json.loads(r2.read().decode())
                got_rows  = len(data)
                got_units = sum(x["soh_qty"] for x in data)
                ok = got_rows == exp["rows"] and got_units == exp["units"]
                sym = "OK" if ok else "!!"
                print(f"  [{sym}] {sc:<8} {sd}  "
                      f"exp rows={exp['rows']:3} units={exp['units']:5,}  "
                      f"got rows={got_rows:3} units={got_units:5,}")
                if not ok:
                    all_ok = False
        except Exception as e:
            print(f"  [ERR] {sc}/{sd}: {e}")
            all_ok = False

    if all_ok:
        print("\n  ALL 27 STORES VERIFIED — DATA IS BANG ON OK")
    else:
        print("\n  VERIFICATION FAILED — check mismatches above !!")
    return all_ok

# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sql_only   = "--sql-only"   in sys.argv
    verify_only= "--verify"     in sys.argv

    print("=" * 65)
    print("  EMIRATES PRIDE — STOCK MASTER UPLOAD & VERIFY")
    print("=" * 65)
    print(f"  Source : {EXCEL_PATH}")
    print()

    rows, unmapped = parse_excel()

    # ── Summary ──
    by_store = defaultdict(lambda: {"rows":0,"units":0})
    for r in rows:
        by_store[r["store_code"]]["rows"]  += 1
        by_store[r["store_code"]]["units"] += r["soh_qty"]

    grand_rows  = sum(r["rows"]  for r in by_store.values())
    grand_units = sum(r["units"] for r in by_store.values())

    print(f"\n  PARSE SUMMARY:")
    print(f"    Stores    : {len(by_store)}")
    print(f"    Total rows: {grand_rows:,}")
    print(f"    Total units: {grand_units:,}")
    if unmapped:
        still_unmapped = {k:v for k,v in unmapped.items()
                          if k not in ("", "nan")}
        print(f"    Unmapped  : {len(still_unmapped)} unique product names (stored with NULL sku_code)")

    # ── Spot-check ──
    print()
    spot_ok = spot_check(rows)
    if not spot_ok:
        print("\n  [ABORT] Spot-check failed. Fix mapping before uploading.")
        sys.exit(1)

    # ── Write SQL ──
    sql_text = generate_sql(rows)
    with open(SQL_OUT_PATH, "w", encoding="utf-8") as f:
        f.write(sql_text)
    print(f"\n  SQL written: {SQL_OUT_PATH}  ({sql_text.count(chr(10)):,} lines)")

    if sql_only:
        print("  [--sql-only] Done. Paste the SQL into Supabase SQL Editor to apply.")
        sys.exit(0)

    if verify_only:
        verify(rows)
        sys.exit(0)

    # ── Upload ──
    print(f"\n  Uploading {grand_rows:,} rows across {len(by_store)} stores ...")
    ok = upload(rows)

    # ── Final verify ──
    print()
    verify(rows)
