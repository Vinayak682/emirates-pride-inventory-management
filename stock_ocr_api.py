#!/usr/bin/env python3
"""
Emirates Pride — Stock Sheet OCR Server
Uses Google Gemini Vision (FREE — no credit card needed)

SETUP (one time):
  1. Go to https://aistudio.google.com/apikey
  2. Sign in with your Google account → click "Create API Key" → copy it
  3. Double-click start_stock_scanner.bat
  4. Paste key in Settings on the web page

Run: python stock_ocr_api.py  (or use start_stock_scanner.bat)
"""

import os, sys, json, re, threading, webbrowser, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ── Auto-install google-genai (new SDK) if needed ──────────────────
try:
    from google import genai
    from google.genai import types as gtypes
except ImportError:
    print("Installing Google Gemini SDK (first time only)...")
    os.system(f'"{sys.executable}" -m pip install -q google-genai')
    from google import genai
    from google.genai import types as gtypes

PORT         = 5001
SUPABASE_URL = 'https://ncszurcrkngjcjqsowln.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5jc3p1cmNya25namNqcXNvd2xuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0NjA4NTgsImV4cCI6MjA5MzAzNjg1OH0.i5cPlP7JTTCKMXuFqI81WXbjQa71qBkRBZEBvNf6ZmM'

STORES = [
    # Abu Dhabi
    {'code':'A0001', 'name':'Bawabat al Sharq Mall Shop'},
    {'code':'A0002', 'name':'Bawabat al Sharq Mall Kiosk'},
    {'code':'BAS001','name':'Bawabat al Sharq Kiosk ASL'},
    {'code':'A0003', 'name':'Dalma Mall Shop'},
    {'code':'A0004', 'name':'Dalma Mall Kiosk'},
    {'code':'A0005', 'name':'Deerfield Mall Kiosk'},
    {'code':'A0009', 'name':'Yas Mall Podium'},
    {'code':'A0007', 'name':'Yas Mall Kiosk 2'},
    {'code':'A0008', 'name':'Yas Mall Kiosk 3'},
    {'code':'YMK001','name':'Yas Mall ASL'},
    # Al Ain
    {'code':'AL001', 'name':'Al Ain Mall Kiosk'},
    {'code':'AL002', 'name':'Bawadi Mall Kiosk 1'},
    {'code':'AL003', 'name':'Bawadi Mall Kiosk 2'},
    {'code':'BAW001','name':'Bawadi Mall ASL'},
    {'code':'AL004', 'name':'Jimi Mall Shop'},
    {'code':'AL006', 'name':'Makhani Zakhar Mall Shop'},
    {'code':'MAK001','name':'Makhani Zakhar Mall ASL'},
    # Dubai
    {'code':'DX001', 'name':'Dubai Mall Shop'},
    {'code':'DX004', 'name':'Mall of the Emirates Kiosk'},
    {'code':'DX005', 'name':'Mirdif City Centre Kiosk'},
    {'code':'DX006', 'name':'Dubai Hills Mall Shop'},
    # Northern Emirates
    {'code':'RK001', 'name':'Manar Mall Shop'},
    {'code':'RK002', 'name':'Manar Mall Kiosk'},
    {'code':'FJ001', 'name':'Fujairah City Centre Kiosk'},
    {'code':'FJ001A','name':'Fujairah City Centre ASL'},
    {'code':'SH001', 'name':'Zahia City Centre Kiosk'},
    {'code':'AJ001', 'name':'Ajman City Centre Kiosk'},
    # Oman
    {'code':'OM001',    'name':'Mall of Oman'},
    {'code':'OM002',    'name':'Muscat City Centre'},
    {'code':'OM_ASL001','name':'ASL Mall of Oman'},
]

COLUMN_MAP = {
    'opening':'op', 'wh_received':'wh', 'store_in':'si',
    'sold':'so', 'transfer_out':'tr', 'writeoff':'wo', 'balance':'bl'
}

# ── OCR Prompt ────────────────────────────────────────────────────
def build_prompt(store_code, date, n_images):
    return f"""You are reading Emirates Pride Perfumes stock register sheets.
Store: {store_code}  |  Date: {date}  |  Images: {n_images}

EXTRACT every product row. The sheet has these columns (order may vary):
SKU Code | Product Name | Opening Stock | WH Received | Store-In | Sold | Transfer Out | Write-Off | SOH / Balance (Closing Stock)

MOST IMPORTANT: The SOH / Balance (closing stock) column is the LAST column — this is the physical stock on hand count. Read it with maximum accuracy.

VALID SKU CODE PREFIXES: AP, AO, AH, AG, AC, B, C, D, O, SP, BX, C, AL
(Examples: AP001, AO005, B00001, C00002, D00001, O00001, SP001, AL001)

ACCURACY RULES — READ CAREFULLY:
- Numbers: distinguish 1 vs 7 | 0 vs 6 | 3 vs 8 | 5 vs 6 (stock qty is usually 0–200)
- Empty cell = 0. Truly illegible cell = null.
- SOH should equal: Opening + WH_received + Store_in - Sold - Transfer_out - Write_off
- If the sheet SOH doesn't match this formula, set balance_check to "MISMATCH"
- Do NOT skip any row. Include every product visible.
- If multiple images are pages of the same sheet, combine all rows (no duplicates).
- Product codes on the sheet may be short (e.g. "C002" = C00002, "B001" = B00001) — expand them.

RETURN ONLY THIS JSON — no markdown, no extra text, just the JSON:
{{
  "sheet_date": "{date}",
  "store_hint": "any store name or code visible on the sheet",
  "overall_confidence": 0.95,
  "items": [
    {{
      "sku_code": "AP001",
      "product_name": "Product Name as written",
      "opening": 10,
      "wh_received": 5,
      "store_in": 0,
      "sold": 3,
      "transfer_out": 0,
      "writeoff": 0,
      "balance": 12,
      "balance_check": "OK",
      "row_confidence": 0.97
    }}
  ],
  "total_skus": 1,
  "issues": ["describe any problems here"]
}}"""

# ── Gemini OCR ────────────────────────────────────────────────────
def run_gemini_ocr(api_key, images, store_code, date):
    client = genai.Client(api_key=api_key)

    # Build content parts: images + prompt
    def build_contents(img_list):
        parts = []
        for img in img_list:
            parts.append(gtypes.Part.from_bytes(
                data=__import__('base64').b64decode(img['data']),
                mime_type=img.get('mime_type', 'image/jpeg')
            ))
        parts.append(gtypes.Part.from_text(text=build_prompt(store_code, date, len(img_list))))
        return parts

    # Pass 1: Gemini 2.5 Flash Lite (fast, cheap)
    print(f"      → Pass 1: Gemini 2.5 Flash Lite...")
    resp   = client.models.generate_content(model='gemini-2.5-flash-lite', contents=build_contents(images))
    parsed = _parse_json(resp.text)

    # Pass 2: Gemini 2.5 Flash if confidence low (better accuracy)
    if not parsed or (parsed.get('overall_confidence', 0) < 0.80):
        reason = 'parse failed' if not parsed else f"{int((parsed.get('overall_confidence',0))*100)}% conf"
        print(f"      → Pass 2: Gemini 2.5 Flash ({reason})...")
        resp   = client.models.generate_content(model='gemini-2.5-flash', contents=build_contents(images))
        parsed = _parse_json(resp.text)

    return parsed

# ── HTTP Handler ──────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass  # suppress access logs

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/':
            try:
                html_file = os.path.join(os.path.dirname(__file__), 'stock-ocr-upload.html')
                with open(html_file, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self._cors()
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self._json({'error': 'stock-ocr-upload.html not found'}, 404)
        elif path == '/stores':
            self._json(STORES)
        elif path == '/ping':
            self._json({'ok': True})
        else:
            self._json({'error': 'Not found'}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = json.loads(self.rfile.read(length))
        except Exception as e:
            self._json({'error': f'Bad request: {e}'}, 400)
            return

        if   self.path == '/ocr':  self._handle_ocr(body)
        elif self.path == '/save': self._handle_save(body)
        else: self._json({'error': 'Not found'}, 404)

    def _handle_ocr(self, body):
        api_key    = body.get('api_key', '').strip()
        images     = body.get('images', [])
        store_code = body.get('store_code', 'UNKNOWN')
        date       = body.get('date', datetime.now().strftime('%Y-%m-%d'))

        if not api_key:
            self._json({'ok': False, 'error': 'Google Gemini API key required. Get it free at aistudio.google.com/apikey'}); return
        if not images:
            self._json({'ok': False, 'error': 'No images provided'}); return

        print(f"\n  [OCR] {store_code} | {date} | {len(images)} image(s)")

        try:
            parsed = run_gemini_ocr(api_key, images, store_code, date)

            if not parsed:
                self._json({'ok': False, 'error': 'Could not read the stock sheet. Try a clearer, brighter photo.'}); return

            items   = _validate(parsed.get('items', []))
            low_conf = [i['sku_code'] for i in items
                        if i.get('row_confidence', 1) < 0.80 or i.get('balance_check') == 'MISMATCH']

            conf = parsed.get('overall_confidence', 0)
            print(f"  [OCR] ✓ {len(items)} SKUs | {int(conf*100)}% conf | {len(low_conf)} review rows")

            self._json({
                'ok': True,
                'items': items,
                'overall_confidence': conf,
                'low_confidence_skus': low_conf,
                'issues': parsed.get('issues', []),
                'total_skus': len(items),
            })

        except Exception as e:
            err = str(e)
            print(f"  [OCR] ERROR: {err}")
            # Friendly error messages
            if 'API_KEY_INVALID' in err or 'invalid' in err.lower() or '400' in err:
                err = 'Invalid Gemini API key. Get a free key at aistudio.google.com/apikey'
            elif 'quota' in err.lower() or 'QUOTA' in err or '429' in err or 'RESOURCE_EXHAUSTED' in err:
                err = 'Quota limit reached. Wait a minute and try again, or check billing at aistudio.google.com.'
            elif '404' in err or 'NOT_FOUND' in err:
                err = 'Gemini model not available. Contact support.'
            self._json({'ok': False, 'error': err})

    def _handle_save(self, body):
        store_code = body.get('store_code')
        date       = body.get('date')
        items      = body.get('items', [])
        mode       = body.get('mode', 'quick')   # 'quick' = SOH only, 'full' = all columns

        if not store_code or not date or not items:
            self._json({'error': 'Missing store_code, date, or items'}, 400); return

        # Quick mode: only save balance (SOH). Full mode: save all columns.
        save_cols = {'balance': 'bl'} if mode == 'quick' else COLUMN_MAP

        cells = []
        for item in items:
            sku = (item.get('sku_code') or '').strip()
            if not sku: continue
            for field, col in save_cols.items():
                val = item.get(field)
                if val is not None and str(val).strip() != '':
                    try:
                        cells.append({'store_code': store_code, 'date': date,
                                      'sku_code': sku, 'col': col, 'val': int(val)})
                    except (ValueError, TypeError):
                        pass

        if not cells:
            self._json({'ok': False, 'error': 'No valid data to save'}); return

        saved = 0
        try:
            for i in range(0, len(cells), 500):
                batch   = cells[i:i+500]
                payload = json.dumps(batch).encode('utf-8')
                req     = urllib.request.Request(
                    f'{SUPABASE_URL}/rest/v1/stock_cells',
                    data=payload,
                    headers={
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}',
                        'Content-Type': 'application/json',
                        'Prefer': 'resolution=merge-duplicates,return=minimal',
                    },
                    method='POST'
                )
                try:
                    urllib.request.urlopen(req)
                    saved += len(batch)
                except urllib.error.HTTPError as e:
                    body_err = e.read().decode()
                    self._json({'ok': False, 'error': f'Database error: {body_err}'}); return

            print(f"  [SAVE] ✓ {store_code} | {date} | {saved} cells → Supabase")
            self._json({'ok': True, 'cells_saved': saved, 'skus_saved': len(items)})

        except Exception as e:
            self._json({'ok': False, 'error': str(e)})


# ── Helpers ───────────────────────────────────────────────────────
def _parse_json(text):
    try:
        m = re.search(r'\{[\s\S]*\}', text or '')
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None

def _validate(items):
    for item in items:
        for col in ['opening','wh_received','store_in','sold','transfer_out','writeoff','balance']:
            v = item.get(col)
            if v is None:
                item[col] = None
            else:
                try:   item[col] = max(0, int(v))
                except: item[col] = None

        nums = [item.get(c) for c in ['opening','wh_received','store_in','sold','transfer_out','writeoff']]
        if all(v is not None for v in nums):
            expected = nums[0] + nums[1] + nums[2] - nums[3] - nums[4] - nums[5]
            balance  = item.get('balance')
            if balance is not None and abs(expected - balance) > 1:
                item['balance_check']    = 'MISMATCH'
                item['balance_expected'] = expected
                item['row_confidence']   = min(item.get('row_confidence', 0.9), 0.55)
            else:
                item['balance_check'] = 'OK'
                if item.get('balance') is None:
                    item['balance'] = expected
    return items


if __name__ == '__main__':
    server = HTTPServer(('localhost', PORT), Handler)
    url    = f'http://localhost:{PORT}'
    print(f'\n{"="*55}')
    print(f'  Emirates Pride Stock OCR Server (Gemini Edition)')
    print(f'  FREE — no credit card, 1,500 scans/day')
    print(f'  Running at: {url}')
    print(f'  Press Ctrl+C to stop')
    print(f'{"="*55}\n')
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
