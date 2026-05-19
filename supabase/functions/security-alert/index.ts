/**
 * Emirates Pride — Security Alert Edge Function
 * Sends a WhatsApp message when an anomaly is detected.
 *
 * DEPLOYMENT:
 *   supabase functions deploy security-alert --project-ref ncszurcrkngjcjqsowln
 *
 * ENVIRONMENT VARIABLES (set in Supabase dashboard → Edge Functions → Secrets):
 *
 *   Option A — WATI (recommended for UAE businesses):
 *     WATI_API_ENDPOINT = https://live-mt-server.wati.io/YOUR_TENANT_ID/api/v1
 *     WATI_API_KEY      = your-wati-bearer-token
 *     ALERT_PHONE       = 971XXXXXXXXX  (no + prefix, e.g. 971501234567)
 *
 *   Option B — Twilio:
 *     TWILIO_ACCOUNT_SID = ACxxxxxxxxxx
 *     TWILIO_AUTH_TOKEN  = your-auth-token
 *     TWILIO_FROM        = whatsapp:+14155238886
 *     TWILIO_TO          = whatsapp:+971XXXXXXXXX
 *
 * The function auto-detects which provider to use based on which vars are set.
 */

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface AlertPayload {
  store: string;
  operation: string;
  flag_reason: string;
  record_key?: string;
  session_id?: string;
  timestamp: string;
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const payload: AlertPayload = await req.json();

    const message = buildMessage(payload);
    const sent = await sendWhatsApp(message);

    return new Response(JSON.stringify({ ok: true, sent }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[security-alert]', err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});

function buildMessage(p: AlertPayload): string {
  const uaeTime = new Date(p.timestamp).toLocaleString('en-GB', {
    timeZone: 'Asia/Dubai',
    day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  return [
    `🚨 *Emirates Pride — Security Alert*`,
    ``,
    `⚠️ *${p.flag_reason}*`,
    ``,
    `📍 Store: ${p.store}`,
    `🔧 Action: ${p.operation}`,
    p.record_key ? `📦 Record: ${p.record_key}` : null,
    `🕐 Time (UAE): ${uaeTime}`,
    p.session_id ? `🔑 Session: ${p.session_id.slice(0, 8)}…` : null,
    ``,
    `Please review the Security Audit Log in your Manager Dashboard.`,
  ].filter(Boolean).join('\n');
}

async function sendWhatsApp(message: string): Promise<boolean> {
  const watiEndpoint = Deno.env.get('WATI_API_ENDPOINT');
  const watiKey      = Deno.env.get('WATI_API_KEY');
  const alertPhone   = Deno.env.get('ALERT_PHONE');

  const twilioSid    = Deno.env.get('TWILIO_ACCOUNT_SID');
  const twilioToken  = Deno.env.get('TWILIO_AUTH_TOKEN');
  const twilioFrom   = Deno.env.get('TWILIO_FROM');
  const twilioTo     = Deno.env.get('TWILIO_TO');

  // ── Option A: WATI ───────────────────────────────────────────────
  if (watiEndpoint && watiKey && alertPhone) {
    const resp = await fetch(`${watiEndpoint}/sendSessionMessage/${alertPhone}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${watiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messageText: message }),
    });
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`WATI failed ${resp.status}: ${txt.slice(0, 200)}`);
    }
    return true;
  }

  // ── Option B: Twilio ─────────────────────────────────────────────
  if (twilioSid && twilioToken && twilioFrom && twilioTo) {
    const auth = btoa(`${twilioSid}:${twilioToken}`);
    const body = new URLSearchParams({
      From: twilioFrom,
      To:   twilioTo,
      Body: message,
    });
    const resp = await fetch(
      `https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: body.toString(),
      }
    );
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error(`Twilio failed ${resp.status}: ${txt.slice(0, 200)}`);
    }
    return true;
  }

  // No provider configured — log and continue without failing
  console.warn('[security-alert] No WhatsApp provider configured. Set WATI_* or TWILIO_* env vars.');
  return false;
}
