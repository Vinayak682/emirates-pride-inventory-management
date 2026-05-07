#!/usr/bin/env python3
"""
Monthly Sales Upload Script for Emirates Pride Perfumes
Usage: python3 monthly_sales_upload.py April_2026_Sales.xlsx
"""

import sys
import openpyxl
import json
import requests
from datetime import datetime
from collections import defaultdict

SUPABASE_URL = "https://ncszurcrkngjcjqsowln.supabase.co"
SUPABASE_SERVICE_KEY = "YOUR_SERVICE_ROLE_KEY_HERE"  # Replace with actual service key

# Store mapping (same as before)
STORE_MAP = {
    "Al Zahia City Centre": "SH001",
    "Makani Mall Shop": "AL006",
    "Pro_Stand_Manar Mall": "RK002",
    "Ajman - City Centre": "AJ001",
    "Al Ain Mall": "AL001",
    "Al Badia": None,  # Excluded
    "Bawabat Al Sharq Shop": "A0001",
    "Bawabat Al Sharq Mall – Shop 2": "A0002",
    "Bawadi Mall - (1)": "AL002",
    "Bawadi Mall - (2)": "AL003",
    "Bawbat Al Sherq (1)": "BAS001",
    "Bawbat Al Sherq (2)": "BAS001",
    "Dalma Mall": "A0004",
    "Dalma Mall Shop": "A0003",
    "Deerfields Mall": "A0005",
    "Dubai Hills Mall": "DX006",
    "Dubai Mall Kiosk": "DX001",
    "Dubai Mall Shop": "DX001",
    "Fujairah": "FJ001",
    "Fujairah - City Centre": "FJ001",
    "Jimi Mall": "AL004",
    "JIMI Mall Shop": "AL004",
    "Makani Mall": "AL006",
    "Mall Of Emirates": "DX004",
    "Manar Mall": "RK002",
    "Manar Mall Shop": "RK001",
    "Mirdif - City Centre": "DX005",
    "Yas Mall (1)": "A0009",
    "Yas Mall (2)": "A0007",
    "Yas Mall (3)": "A0008",
    # Add all store mappings...
}

def upload_to_supabase(table, data):
    """Upload data to Supabase table"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code in [200, 201]:
        return True
    else:
        print(f"❌ Supabase error: {response.status_code} - {response.text}")
        return False

def parse_excel_sales(filepath):
    """Parse monthly sales Excel file"""
    print(f"📂 Reading: {filepath}")
    
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    
    # TODO: Add Excel parsing logic here
    # (Copy from previous upload_sales_to_supabase.py)
    
    return []

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 monthly_sales_upload.py <excel_file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print("="*60)
    print("MONTHLY SALES UPLOAD — Emirates Pride Perfumes")
    print("="*60)
    
    # Parse Excel
    sales_records = parse_excel_sales(filepath)
    
    if not sales_records:
        print("❌ No sales data found")
        sys.exit(1)
    
    print(f"\n✅ Parsed {len(sales_records)} sales records")
    
    # Upload to Supabase
    print("\n📤 Uploading to Supabase...")
    
    success = upload_to_supabase('sales_history', sales_records)
    
    if success:
        print("✅ Upload complete!")
        print("\n📊 Benchmarks will auto-recalculate on next dashboard load")
    else:
        print("❌ Upload failed")
        sys.exit(1)
