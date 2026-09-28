import { describe, it, expect } from 'vitest';

/**
 * These tests demonstrate the bug that motivates the Durable Object, rather
 * than only asserting that the fixed version works. The first test is expected
 * to show a wallet leak; that is the point of it.
 *
 * Both implementations run against the same in-memory store with an artificial
 * await between read and write, standing in for the real network hop to
 * storage. No Cloudflare runtime is needed to see the difference.
 */

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

function makeStore() {
  const data = new Map();
  return {
    async get(k) { await tick(); return data.get(k); },
    async put(k, v) { await tick(); data.set(k, v); },
  };
}

/** The naive read-check-write, as written against KV. */
function naiveCharge(store) {
  return async (cost) => {
    const balance = (await store.get('balance')) || 0;
    if (balance < cost) return { ok: false, balance };
    await store.put('balance', balance - cost);
    return { ok: true, balance: balance - cost };
  };
}

/**
 * The same logic, serialized per account — which is what a Durable Object
 * gives you structurally, via a single-threaded instance with input-gated
 * storage. Modelled here as a promise chain.
 */
function serializedCharge(store) {
  let queue = Promise.resolve();
  return (cost) => {
    const result = queue.then(async () => {
      const balance = (await store.get('balance')) || 0;
      if (balance < cost) return { ok: false, balance };
      await store.put('balance', balance - cost);
      return { ok: true, balance: balance - cost };
    });
    queue = result.then(() => {}, () => {});
    return result;
  };
}

describe('concurrent debits', () => {
  it('naive read-check-write double-spends under concurrency', async () => {
    const store = makeStore();
    await store.put('balance', 100);
    const charge = naiveCharge(store);

    const results = await Promise.all(Array.from({ length: 20 }, () => charge(5)));
    const approved = results.filter((r) => r.ok).length;
    const finalBalance = await store.get('balance');

    // Every call is approved: 20 x 5 = 100 credits of service delivered.
    expect(approved).toBe(20);
    // But the wallet only records a single debit. 95 credits were given away.
    expect(finalBalance).toBe(95);
    expect(finalBalance).not.toBe(100 - approved * 5);
  });

  it('serialized debits stay exact under the same concurrency', async () => {
    const store = makeStore();
    await store.put('balance', 100);
    const charge = serializedCharge(store);

    const results = await Promise.all(Array.from({ length: 20 }, () => charge(5)));
    const approved = results.filter((r) => r.ok).length;
    const finalBalance = await store.get('balance');

    expect(approved).toBe(20);
    expect(finalBalance).toBe(0);
    expect(finalBalance).toBe(100 - approved * 5);
  });

  it('serialized debits refuse to overdraw', async () => {
    const store = makeStore();
    await store.put('balance', 20);
    const charge = serializedCharge(store);

    const results = await Promise.all(Array.from({ length: 10 }, () => charge(5)));

    expect(results.filter((r) => r.ok).length).toBe(4);   // 4 x 5 = 20
    expect(results.filter((r) => !r.ok).length).toBe(6);  // rest correctly denied
    expect(await store.get('balance')).toBe(0);
  });
});
