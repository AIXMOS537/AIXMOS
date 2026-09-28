/**
 * Atomic credit ledger, as a Cloudflare Durable Object.
 *
 * ── Why this is not a KV read-modify-write ──────────────────────────────────
 *
 * The obvious way to debit a wallet on Workers is:
 *
 *     const bal = parseInt(await KV.get(key));   // read
 *     if (bal < cost) return DENIED;             // check
 *     await KV.put(key, String(bal - cost));     // write
 *
 * That is a lost-update race, and on a request-per-isolate platform it is not
 * a rare one. Twenty concurrent calls against a balance of 100 all read 100,
 * all evaluate 100 >= 5, and all write 95. Twenty calls were served and one
 * debit was recorded. The wallet leaks, and the spend cap it was supposed to
 * enforce does not exist.
 *
 * Workers KV also makes this worse than a classic race: it is eventually
 * consistent, so a read can return a value that is already stale by more than
 * the width of the race window.
 *
 * A Durable Object fixes it structurally rather than probabilistically. One
 * instance exists per object name, it is single-threaded, and its storage is
 * input-gated: while an await on storage is in flight, no other event for that
 * object is delivered. Operations against one wallet therefore serialize, and
 * check-then-write is atomic without any lock the caller has to remember to take.
 *
 * The cost of this choice is real and worth stating: every operation on one
 * account is funnelled through one object, so a single hot account is a
 * throughput ceiling. That is the correct trade here — wallets are per-user and
 * a user's own calls are naturally serial — but it would be the wrong choice
 * for a global counter.
 */

export class Ledger {
  constructor(state) {
    this.state = state;
  }

  async fetch(request) {
    const body = await request.json().catch(() => ({}));
    const store = this.state.storage;

    switch (body.op) {
      case 'balance':
        return json({ balance: (await store.get('balance')) || 0 });

      case 'topup': {
        const amount = Math.max(0, Number(body.amount) || 0);
        const balance = ((await store.get('balance')) || 0) + amount;
        await store.put('balance', balance);
        return json({ balance });
      }

      // Atomic debit. The check and the write happen inside one turn of this
      // object's event loop, so no concurrent call can observe the pre-debit
      // balance and spend it a second time.
      case 'charge': {
        const cost = Math.max(0, Number(body.cost) || 0);
        const balance = (await store.get('balance')) || 0;
        if (balance < cost) return json({ ok: false, balance });
        await store.put('balance', balance - cost);
        return json({ ok: true, balance: balance - cost });
      }

      // Per-account daily cap on free-lane calls. Same atomicity requirement:
      // without it, a burst of parallel requests all pass the cap check.
      case 'freecap': {
        const key = `free:${body.day}`;
        const limit = Number(body.limit) || 0;
        const used = (await store.get(key)) || 0;
        if (used >= limit) return json({ ok: false, used });
        await store.put(key, used + 1);
        return json({ ok: true, used: used + 1 });
      }

      default:
        return json({ error: 'unknown op' }, 400);
    }
  }
}

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}
