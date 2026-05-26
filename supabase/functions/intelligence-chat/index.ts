import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

const SYSTEM_PROMPT = `You are the Emirates Pride Intelligence Assistant — an AI copilot for supply chain, inventory, and sales operations at Emirates Pride Perfumes, a luxury fragrance company with 35+ retail outlets across UAE and Oman.

You have access to real-time data including:
- Monthly sales history per SKU per store (qty_sold)
- Inventory benchmarks: weekly velocity, 30-day/90-day averages, min/max thresholds
- Transfer (delivery) history per SKU per store
- Area Manager weekly stock requests and issues

Your role is to answer questions about:
- Sales performance (by store, SKU, month, region, trend)
- Stock levels, replenishment needs, stockout risks
- Demand planning: fast movers, slow movers, dead stock
- Delivery/transfer history and overdue routes
- Area Manager requests and outstanding issues
- Production pipeline and warehouse coverage
- Seasonal demand patterns (Ramadan, Eid, DSF, National Day surges)

Guidelines:
- Be concise and action-oriented. Lead with the answer, support with data.
- Use bullet points and short tables for comparisons. Avoid long paragraphs.
- When identifying risks, be specific (store name, SKU, weeks of cover remaining).
- Translate data into decisions: "Store X needs Y units of SKU Z this week."
- If data is insufficient to answer confidently, say so and suggest what data would help.
- Currency: AED. Dates: DD/MM/YYYY or Month-YYYY format.`

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const { message, conversation_history = [] } = await req.json()

    if (!message || typeof message !== 'string') {
      return new Response(JSON.stringify({ error: 'message is required' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    )

    // Fetch context data in parallel
    const [salesRes, benchRes, transferRes, amRes] = await Promise.all([
      supabase.from('sales_history').select('sku_code,store_code,month_year,qty_sold').order('month_year', { ascending: false }).limit(600),
      supabase.from('benchmarks_cache').select('sku_code,store_code,weekly_avg,l30d_qty,l90d_avg,min_monthly,max_monthly,last_sale_month,months_tracked').order('weekly_avg', { ascending: false }).limit(200),
      supabase.from('transfer_history').select('sku_code,store_code,month_year,qty_transferred,frequency').order('month_year', { ascending: false }).limit(300),
      supabase.from('am_weekly_requests').select('*').order('created_at', { ascending: false }).limit(50),
    ])

    // Summarise sales by store
    const salesByStore: Record<string, Record<string, number>> = {}
    for (const row of (salesRes.data || [])) {
      if (!salesByStore[row.store_code]) salesByStore[row.store_code] = {}
      salesByStore[row.store_code][row.month_year] = (salesByStore[row.store_code][row.month_year] || 0) + row.qty_sold
    }

    // Stockout alerts: high velocity + low recent qty
    const alerts = (benchRes.data || []).filter(b => b.weekly_avg > 5 && b.l30d_qty < b.weekly_avg * 2).slice(0, 15)

    const dataContext = `
--- SALES SUMMARY (by store, recent months) ---
${JSON.stringify(salesByStore, null, 2)}

--- TOP FAST MOVERS (by weekly velocity) ---
${JSON.stringify((benchRes.data || []).slice(0, 30), null, 2)}

--- POTENTIAL STOCKOUT ALERTS ---
${JSON.stringify(alerts, null, 2)}

--- RECENT TRANSFERS ---
${JSON.stringify((transferRes.data || []).slice(0, 80), null, 2)}

--- AREA MANAGER REQUESTS ---
${JSON.stringify((amRes.data || []).slice(0, 30), null, 2)}
`

    const geminiKey = Deno.env.get('GEMINI_API_KEY')!
    const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${geminiKey}`

    // Build Gemini contents array from conversation history
    const contents = []

    for (const turn of conversation_history.slice(-6)) {
      contents.push({
        role: turn.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: turn.content }],
      })
    }

    contents.push({
      role: 'user',
      parts: [{ text: `[LIVE DATA SNAPSHOT]\n${dataContext}\n\n[USER QUESTION]\n${message}` }],
    })

    const geminiRes = await fetch(geminiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents,
        generationConfig: { temperature: 0.3, maxOutputTokens: 1500 },
      }),
    })

    if (!geminiRes.ok) {
      const err = await geminiRes.text()
      throw new Error(`Gemini API error: ${geminiRes.status} — ${err}`)
    }

    const geminiData = await geminiRes.json()
    const reply = geminiData.candidates?.[0]?.content?.parts?.[0]?.text || 'No response generated.'

    return new Response(JSON.stringify({ reply }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })

  } catch (err) {
    console.error('intelligence-chat error:', err)
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
  }
})
