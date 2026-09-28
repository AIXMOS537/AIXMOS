/**
 * Lane selection.
 *
 * The problem this solves: when every request goes to a paid API, cost scales
 * linearly with usage. Success makes the unit economics worse. That is a bad
 * shape for a business to be in.
 *
 * A lane is a tier of inference with a different cost and a different owner:
 *
 *   local  — a model you serve yourself (Ollama, vLLM). Marginal cost 0.
 *   hosted — a free-tier hosted provider. Marginal cost 0, but rate limited.
 *   paid   — a frontier API. Real money per call.
 *
 * Callers ask for a capability, not a vendor. The router picks the cheapest
 * lane that satisfies the request and that the caller is still entitled to.
 */

/** Ordered cheapest-first. Order is the routing preference. */
export const LANES = ['local', 'hosted', 'paid'];

/** Credits charged per call, by lane. Local inference costs nothing to run. */
export const LANE_COST = { local: 0, hosted: 0, paid: 5 };

/** Comparable rank, so "at most this lane" is expressible as a number. */
export const LANE_RANK = { local: 0, hosted: 1, paid: 2 };

export class UnknownLaneError extends Error {
  constructor(lane) {
    super(`Unknown lane: ${JSON.stringify(lane)}`);
    this.name = 'UnknownLaneError';
  }
}

/**
 * Choose a lane for one request.
 *
 * The key decision here is what happens when a caller is out of credit. The
 * obvious implementation returns 402 and stops. That is the wrong behavior:
 * it converts a billing state into an outage, and the person on the other end
 * experiences it as the product being broken.
 *
 * Instead, an out-of-credit caller degrades to the cheapest lane that costs
 * nothing to serve. They lose capability, not access. In practice this turned
 * a support burden into a non-event.
 *
 * @param {object}  req
 * @param {string}  req.requested  Lane the caller asked for.
 * @param {string}  req.maxLane    Ceiling this caller is entitled to.
 * @param {number}  req.balance    Credits remaining.
 * @param {boolean} [req.hostedAvailable=true]  False when the free tier is rate limited.
 * @returns {{lane: string, cost: number, degraded: boolean, reason: string}}
 */
export function selectLane({ requested, maxLane, balance, hostedAvailable = true }) {
  if (!(requested in LANE_RANK)) throw new UnknownLaneError(requested);
  if (!(maxLane in LANE_RANK)) throw new UnknownLaneError(maxLane);

  // A caller may never exceed their entitlement, whatever they asked for.
  let lane = LANE_RANK[requested] > LANE_RANK[maxLane] ? maxLane : requested;
  let degraded = lane !== requested;
  let reason = degraded ? 'above-entitlement' : 'as-requested';

  // Paid lane requires credit. No credit degrades rather than fails.
  if (lane === 'paid' && balance < LANE_COST.paid) {
    lane = hostedAvailable ? 'hosted' : 'local';
    degraded = true;
    reason = 'insufficient-credit';
  }

  // The free hosted tier is rate limited upstream and will not always be there.
  // Falling back to self-hosted keeps the request served.
  if (lane === 'hosted' && !hostedAvailable) {
    lane = 'local';
    degraded = true;
    reason = reason === 'as-requested' ? 'hosted-unavailable' : reason;
  }

  return { lane, cost: LANE_COST[lane], degraded, reason };
}
