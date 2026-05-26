import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

// ── Store location master ─────────────────────────────────────────
const STORE_MAP: Record<string, { name: string; region: string; country: string }> = {
  A0001: { name: 'Abu Dhabi 01',         region: 'Abu Dhabi',   country: 'UAE' },
  A0002: { name: 'Abu Dhabi 02',         region: 'Abu Dhabi',   country: 'UAE' },
  A0003: { name: 'Abu Dhabi 03',         region: 'Abu Dhabi',   country: 'UAE' },
  A0004: { name: 'Abu Dhabi 04',         region: 'Abu Dhabi',   country: 'UAE' },
  A0005: { name: 'Abu Dhabi 05',         region: 'Abu Dhabi',   country: 'UAE' },
  A0006: { name: 'Abu Dhabi 06',         region: 'Abu Dhabi',   country: 'UAE' },
  A0007: { name: 'Abu Dhabi 07',         region: 'Abu Dhabi',   country: 'UAE' },
  A0008: { name: 'Abu Dhabi 08',         region: 'Abu Dhabi',   country: 'UAE' },
  A0009: { name: 'Abu Dhabi 09',         region: 'Abu Dhabi',   country: 'UAE' },
  A0010: { name: 'Abu Dhabi 10',         region: 'Abu Dhabi',   country: 'UAE' },
  A0012: { name: 'Abu Dhabi 12',         region: 'Abu Dhabi',   country: 'UAE' },
  A0013: { name: 'Abu Dhabi 13',         region: 'Abu Dhabi',   country: 'UAE' },
  AJ001: { name: 'Ajman 01',             region: 'Ajman',       country: 'UAE' },
  AL001: { name: 'Al Ain 01',            region: 'Al Ain',      country: 'UAE' },
  AL002: { name: 'Al Ain 02',            region: 'Al Ain',      country: 'UAE' },
  AL003: { name: 'Al Ain 03',            region: 'Al Ain',      country: 'UAE' },
  AL004: { name: 'Al Ain 04',            region: 'Al Ain',      country: 'UAE' },
  AL006: { name: 'Al Ain 06',            region: 'Al Ain',      country: 'UAE' },
  AL008: { name: 'Al Ain 08',            region: 'Al Ain',      country: 'UAE' },
  ASL_A009:   { name: 'ASL Abu Dhabi 09',  region: 'Abu Dhabi', country: 'UAE' },
  ASL_A011:   { name: 'ASL Abu Dhabi 11',  region: 'Abu Dhabi', country: 'UAE' },
  ASL_AL004:  { name: 'ASL Al Ain 04',     region: 'Al Ain',    country: 'UAE' },
  ASL_AL007:  { name: 'ASL Al Ain 07',     region: 'Al Ain',    country: 'UAE' },
  ASL_BAW001: { name: 'ASL Bawadi Mall',   region: 'Al Ain',    country: 'UAE' },
  ASL_FJ001:  { name: 'ASL Fujairah 01',   region: 'Fujairah',  country: 'UAE' },
  ASL_FUJ001: { name: 'ASL Fujairah 02',   region: 'Fujairah',  country: 'UAE' },
  ASL_MAK001: { name: 'ASL Makamat',       region: 'Abu Dhabi', country: 'UAE' },
  ASL_YAS001: { name: 'ASL Yas Mall',      region: 'Abu Dhabi', country: 'UAE' },
  BAS001: { name: 'Bawadi Mall',           region: 'Al Ain',    country: 'UAE' },
  DX001:  { name: 'Dubai 01',              region: 'Dubai',     country: 'UAE' },
  DX001K: { name: 'Dubai 01K',             region: 'Dubai',     country: 'UAE' },
  DX003:  { name: 'Dubai 03',              region: 'Dubai',     country: 'UAE' },
  DX004:  { name: 'Dubai 04',              region: 'Dubai',     country: 'UAE' },
  DX005:  { name: 'Dubai 05',              region: 'Dubai',     country: 'UAE' },
  DX006:  { name: 'Dubai 06',              region: 'Dubai',     country: 'UAE' },
  FJ001:  { name: 'Fujairah 01',           region: 'Fujairah',  country: 'UAE' },
  FJ002:  { name: 'Fujairah 02',           region: 'Fujairah',  country: 'UAE' },
  OM001:     { name: 'Oman 01',            region: 'Muscat',    country: 'Oman' },
  OM002:     { name: 'Oman 02',            region: 'Muscat',    country: 'Oman' },
  OM_ASL001: { name: 'Oman ASL 01',        region: 'Muscat',    country: 'Oman' },
  PS_YAS: { name: 'Yas Island',            region: 'Abu Dhabi', country: 'UAE' },
  RK001:  { name: 'Ras Al Khaimah 01',     region: 'RAK',       country: 'UAE' },
  RK002:  { name: 'Ras Al Khaimah 02',     region: 'RAK',       country: 'UAE' },
  SH001:  { name: 'Sharjah 01',            region: 'Sharjah',   country: 'UAE' },
}

const SYSTEM_PROMPT = `You are the Emirates Pride Intelligence Assistant — an expert AI copilot for supply chain, inventory, and sales at Emirates Pride Perfumes. You serve 44 retail outlets across UAE and Oman.

STORE LOCATION REFERENCE:
- Oman stores: OM001 (Oman 01), OM002 (Oman 02), OM_ASL001 (Oman ASL 01) — all in Muscat
- Dubai stores: DX001, DX001K, DX003, DX004, DX005, DX006
- Abu Dhabi stores: A0001–A0013, ASL_A009, ASL_A011, ASL_MAK001, ASL_YAS001, PS_YAS
- Al Ain stores: AL001–AL008, ASL_AL004, ASL_AL007, ASL_BAW001, BAS001
- Fujairah stores: FJ001, FJ002, ASL_FJ001, ASL_FUJ001
- RAK stores: RK001, RK002
- Sharjah stores: SH001
- Ajman stores: AJ001

DATA AVAILABLE: 16 months of sales history (Jan 2025 – Apr 2026) across all stores and SKUs.

You will receive pre-aggregated data: monthly sales totals by store and by SKU. Use this to answer questions precisely.

CAPABILITIES:
- Sales analysis by store, region, country, month, SKU, trend
- Stockout risk and replenishment recommendations
- Fast movers, slow movers, dead stock identification
- Comparative analysis (store vs store, month vs month)
- Demand forecasting based on historical trends
- Excel data export — when asked for Excel/download, return data in this exact format at the END of your response:
[EXCEL_START]
Column1,Column2,Column3
value1,value2,value3
[EXCEL_END]

GUIDELINES:
- Answer precisely with numbers. "Oman Jan 2026 sales = X units" not vague estimates.
- When asked about a region/country, sum all stores in that region.
- Format numbers with commas (1,234 units).
- Use tables for comparisons. Be concise.
- For Excel requests, include the data block — the UI will auto-generate the download.`

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { message, conversation_history = [] } = await req.json()
    if (!message) return new Response(JSON.stringify({ error: 'message required' }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } })

    const supabase = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!)

    // Fetch ALL sales data aggregated (no 600-row limit — group by store+month)
    const { data: salesRaw } = await supabase
      .from('sales_history')
      .select('sku_code,store_code,month_year,qty_sold')
      .order('month_year', { ascending: false })
      .limit(5000)

    const { data: benchmarks } = await supabase
      .from('benchmarks_cache')
      .select('sku_code,store_code,weekly_avg,l30d_qty,l90d_avg,min_monthly,max_monthly,last_sale_month,months_tracked')
      .order('weekly_avg', { ascending: false })
      .limit(300)

    const { data: amRequests } = await supabase
      .from('am_weekly_requests')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(30)

    // Aggregate: monthly totals by store
    const byStoreMonth: Record<string, Record<string, number>> = {}
    // Aggregate: monthly totals by SKU
    const bySkuMonth: Record<string, Record<string, number>> = {}
    // Aggregate: store totals (all time)
    const storeTotal: Record<string, number> = {}
    // Aggregate: SKU totals (all time)
    const skuTotal: Record<string, number> = {}

    for (const r of (salesRaw || [])) {
      // Store-month
      if (!byStoreMonth[r.store_code]) byStoreMonth[r.store_code] = {}
      byStoreMonth[r.store_code][r.month_year] = (byStoreMonth[r.store_code][r.month_year] || 0) + r.qty_sold
      // SKU-month
      if (!bySkuMonth[r.sku_code]) bySkuMonth[r.sku_code] = {}
      bySkuMonth[r.sku_code][r.month_year] = (bySkuMonth[r.sku_code][r.month_year] || 0) + r.qty_sold
      // Totals
      storeTotal[r.store_code] = (storeTotal[r.store_code] || 0) + r.qty_sold
      skuTotal[r.sku_code] = (skuTotal[r.sku_code] || 0) + r.qty_sold
    }

    // Enrich store data with location
    const storeData = Object.entries(byStoreMonth).map(([code, months]) => ({
      store_code: code,
      store_name: STORE_MAP[code]?.name || code,
      region: STORE_MAP[code]?.region || 'Unknown',
      country: STORE_MAP[code]?.country || 'Unknown',
      monthly_sales: months,
      total_all_time: storeTotal[code] || 0,
    }))

    // Top 30 SKUs by total
    const topSkus = Object.entries(skuTotal)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 30)
      .map(([sku, total]) => ({ sku_code: sku, total_all_time: total, monthly: bySkuMonth[sku] }))

    // Stockout alerts
    const alerts = (benchmarks || [])
      .filter(b => +b.weekly_avg > 5 && +b.l30d_qty < +b.weekly_avg * 2)
      .slice(0, 10)
      .map(b => ({ ...b, store_name: STORE_MAP[b.store_code]?.name || b.store_code }))

    const dataContext = `
=== STORE SALES DATA (with location) ===
${JSON.stringify(storeData, null, 2)}

=== TOP 30 SKUS BY TOTAL SALES ===
${JSON.stringify(topSkus, null, 2)}

=== BENCHMARK / VELOCITY DATA ===
${JSON.stringify((benchmarks || []).slice(0, 50), null, 2)}

=== STOCKOUT ALERTS (high velocity, low stock) ===
${JSON.stringify(alerts, null, 2)}

=== AREA MANAGER REQUESTS ===
${JSON.stringify(amRequests || [], null, 2)}
`

    const messages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...conversation_history.slice(-6),
      { role: 'user', content: `[LIVE DATA]\n${dataContext}\n\n[QUESTION]\n${message}` },
    ]

    const groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${Deno.env.get('GROQ_API_KEY')}` },
      body: JSON.stringify({ model: 'llama-3.3-70b-versatile', messages, temperature: 0.2, max_tokens: 2000 }),
    })

    if (!groqRes.ok) throw new Error(`Groq error: ${groqRes.status} — ${await groqRes.text()}`)

    const groqData = await groqRes.json()
    const reply = groqData.choices?.[0]?.message?.content || 'No response.'

    // Detect Excel export request
    const hasExcel = reply.includes('[EXCEL_START]') && reply.includes('[EXCEL_END]')

    return new Response(JSON.stringify({ reply, has_excel: hasExcel }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })

  } catch (err) {
    console.error(err)
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
  }
})
