import { describe, it, expect } from 'vitest';
import { selectLane, UnknownLaneError } from '../src/lanes.js';

describe('selectLane', () => {
  it('serves the requested lane when entitled and funded', () => {
    const d = selectLane({ requested: 'paid', maxLane: 'paid', balance: 100 });
    expect(d).toMatchObject({ lane: 'paid', cost: 5, degraded: false });
  });

  it('caps a caller at their entitlement', () => {
    const d = selectLane({ requested: 'paid', maxLane: 'hosted', balance: 100 });
    expect(d).toMatchObject({ lane: 'hosted', degraded: true, reason: 'above-entitlement' });
  });

  // The behavior this whole design exists for: running out of credit must not
  // read to the user as the product being broken.
  it('degrades instead of failing when credit runs out', () => {
    const d = selectLane({ requested: 'paid', maxLane: 'paid', balance: 0 });
    expect(d).toMatchObject({ lane: 'hosted', cost: 0, degraded: true, reason: 'insufficient-credit' });
  });

  it('falls through to local when the free hosted tier is rate limited', () => {
    const d = selectLane({
      requested: 'paid', maxLane: 'paid', balance: 0, hostedAvailable: false,
    });
    expect(d.lane).toBe('local');
    expect(d.cost).toBe(0);
  });

  it('never silently accepts an unknown lane', () => {
    expect(() => selectLane({ requested: 'gpu-cluster', maxLane: 'paid', balance: 1 }))
      .toThrow(UnknownLaneError);
  });
});
