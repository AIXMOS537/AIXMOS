/**
 * Worker entry point.
 *
 * Exposes an OpenAI-compatible POST /v1/chat/completions so existing clients
 * point at this gateway by changing a base URL and nothing else. The gateway
 * then decides which lane actually serves the request.
 *
 * Two things this buys beyond cost control:
 *   - Provider keys stay server-side. No client device ever holds one, so
 *     rotating a key is one deploy rather than a fleet-wide chase.
 *   - Lane policy is one place. Changing what a role is entitled to does not
 *     require touching, rebuilding, or redeploying any caller.
 */

import { selectLane, LANE_COST } from './lanes.js';
import { secretsMatch, sanitizeId } from './auth.js';
export { Ledger } from './ledger.js';

const FREE_CALLS_PER_DAY = 100;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return json({ ok: true });
    }

    if (url.pathname !== '/v1/chat/completions' || request.method !== 'POST') {
      return json({ error: 'not found' }, 404);
    }

    const account = sanitizeId(request.headers.get('x-account') || '');
    const secret = request.headers.get('authorization')?.replace(/^Bearer\s+/i, '') || '';
    if (!account) return json({ error: 'missing account' }, 400);

    const expected = await env.ACCOUNTS.get(`secret:${account}`);
    if (!expected || !(await secretsMatch(secret, expected))) {
      return json({ error: 'unauthorized' }, 401);
    }

    const body = await request.json().catch(() => ({}));
    const ledger = ledgerFor(env, account);

    const { balance } = await ledger({ op: 'balance' });
    const maxLane = (await env.ACCOUNTS.get(`maxlane:${account}`)) || 'hosted';

    const decision = selectLane({
      requested: body.lane || 'paid',
      maxLane,
      balance,
      hostedAvailable: env.HOSTED_AVAILABLE !== 'false',
    });

    // Free lanes are metered by call count rather than credit, so one account
    // cannot turn "costs us nothing per call" into "costs us a machine".
    if (decision.cost === 0) {
      const day = new Date().toISOString().slice(0, 10);
      const cap = await ledger({ op: 'freecap', day, limit: FREE_CALLS_PER_DAY });
      if (!cap.ok) return json({ error: 'daily free limit reached', used: cap.used }, 429);
    } else {
      // Charge before serving. Charging after means a crash mid-request is a
      // free call, and those are exactly the requests most likely to crash.
      const charge = await ledger({ op: 'charge', cost: decision.cost });
      if (!charge.ok) return json({ error: 'insufficient credit' }, 402);
    }

    const completion = await callLane(decision.lane, body, env);

    return json({
      ...completion,
      _lane: decision.lane,
      _degraded: decision.degraded,
      _reason: decision.reason,
    });
  },
};

function ledgerFor(env, account) {
  const stub = env.LEDGER.get(env.LEDGER.idFromName(account));
  return (op) =>
    stub
      .fetch('https://ledger/op', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(op),
      })
      .then((r) => r.json());
}

/** Dispatch to the upstream that backs a lane. */
async function callLane(lane, body, env) {
  const upstream = {
    local: { url: env.LOCAL_URL, key: null },
    hosted: { url: env.HOSTED_URL, key: env.HOSTED_KEY },
    paid: { url: env.PAID_URL, key: env.PAID_KEY },
  }[lane];

  const headers = { 'content-type': 'application/json' };
  if (upstream.key) headers.authorization = `Bearer ${upstream.key}`;

  const response = await fetch(upstream.url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ model: body.model, messages: body.messages }),
  });

  return response.json();
}

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}
