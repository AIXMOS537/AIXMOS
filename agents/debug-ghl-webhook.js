require('./lib/env').loadAixmosEnv();
const url = (process.env.TMMT_OPS_URL || '').replace(/\/$/, '');
const secret = process.env.GHL_OVERDUE_WEBHOOK_SECRET || process.env.GHL_WEBHOOK_SECRET || '';
console.log('TMMT_OPS_URL', url || '(missing)');
console.log('webhook_secret_set', !!secret, 'len', secret.length);
(async () => {
  const res = await fetch(url + '/api/webhooks/ghl/overdue', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(secret ? { 'X-GHL-Secret': secret } : {}),
    },
    body: JSON.stringify({
      contact_id: 'TEST_SMOKE_DO_NOT_TAG',
      customer_name: 'Smoke Test',
      source: 'sticks-agent-debug',
    }),
  });
  const text = await res.text();
  console.log('probe_status', res.status);
  console.log('probe_body', text.slice(0, 300));
})().catch(e => console.error('probe_error', e.message));
