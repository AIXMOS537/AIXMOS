'use strict';
/**
 * The claims gate must be watched REFUSING, not merely present.
 *
 * Every case below is drawn from a real failure or a real rule: the invented prices are the
 * actual strings a clean white-label install produced on 2026-09-19 ("$199", "$125 + $50"),
 * and each vertical case cites the same rule that vertical's FORGE compliance.md cites.
 *
 * The negative controls matter as much as the refusals. A gate that blocks everything gets
 * switched off in week two, and a switched-off gate protects nobody.
 */

const { test, describe } = require('node:test');
const assert = require('node:assert');
const { checkClaims, assertClaimsOk, explain } = require('../lib/claims');

const NO_CARD = { business_name: 'Beltway Mobile Detail', lines: [], notes: [], rate_card: [] };
const WITH_CARD = {
  business_name: 'Beltway Mobile Detail',
  lines: [], notes: [],
  rate_card: [
    { item: 'Mobile detail', price: '$125' },
    { item: 'Ceramic coating', price: '$899' },
    { item: 'Fleet discount', price: '15%' },
  ],
};

describe('an install with NO rate card cannot quote a price', () => {
  test('the exact draft the local model produced is refused', () => {
    const r = checkClaims(
      'Marcus, $175 to detail your 2019 Tahoe (base $125 + $50 for rough interior).',
      { profile: NO_CARD },
    );
    assert.equal(r.ok, false);
    const found = r.violations.map(v => v.found);
    assert.ok(found.includes('$175'), 'must catch $175');
    assert.ok(found.includes('$125'), 'must catch $125');
    assert.ok(found.includes('$50'), 'must catch $50');
  });

  test('the refusal says WHY — that nothing can verify it', () => {
    const r = checkClaims('That will be $199.', { profile: NO_CARD });
    assert.equal(r.ok, false);
    assert.match(r.violations[0].why, /NO rate card/);
  });

  test('a draft with no price at all passes — the gate is not a blanket block', () => {
    const r = checkClaims(
      "Marcus, we can take the Tahoe this week. Let me check the rate and come right back to you.",
      { profile: NO_CARD },
    );
    assert.equal(r.ok, true, explain(r));
  });
});

describe('an install WITH a rate card may quote it, and only it', () => {
  test('a price on the card passes', () => {
    const r = checkClaims('Mobile detail is $125 — want me to book you?', { profile: WITH_CARD });
    assert.equal(r.ok, true, explain(r));
  });

  test('a price NOT on the card is refused even though a card exists', () => {
    const r = checkClaims('I can do it for $140 today.', { profile: WITH_CARD });
    assert.equal(r.ok, false);
    assert.equal(r.violations[0].found, '$140');
    assert.match(r.violations[0].why, /not on this install's rate card/);
  });

  test('formatting does not let an amount through — $1,299.00 vs 1299', () => {
    const card = { ...WITH_CARD, rate_card: [{ item: 'Wrap', price: '$1,299.00' }] };
    assert.equal(checkClaims('The wrap is $1299.', { profile: card }).ok, true);
    assert.equal(checkClaims('The wrap is $1,299.00.', { profile: card }).ok, true);
    assert.equal(checkClaims('The wrap is $1,300.', { profile: card }).ok, false);
  });

  test('"dollars" and "bucks" are not a loophole', () => {
    assert.equal(checkClaims('It runs 140 dollars.', { profile: WITH_CARD }).ok, false);
    assert.equal(checkClaims('About 140 bucks.', { profile: WITH_CARD }).ok, false);
  });

  test('a percentage off the card is refused', () => {
    assert.equal(checkClaims('I can give you 15% off.', { profile: WITH_CARD }).ok, true);
    assert.equal(checkClaims('I can give you 40% off.', { profile: WITH_CARD }).ok, false);
  });
});

describe('quoting the customer back is not inventing a price', () => {
  test("an amount the customer named is allowed in the reply", () => {
    const r = checkClaims(
      "You mentioned a budget of $200 — I can work with that, let me confirm the exact figure.",
      { profile: NO_CARD, context: 'my budget is about $200 for the whole thing' },
    );
    assert.equal(r.ok, true, explain(r));
  });

  test('a DIFFERENT amount is still refused even with context present', () => {
    const r = checkClaims('For $450 we can do the full package.', {
      profile: NO_CARD, context: 'my budget is about $200',
    });
    assert.equal(r.ok, false);
    assert.equal(r.violations[0].found, '$450');
  });
});

describe('unverifiable claims are refused in every vertical', () => {
  const cases = [
    ['results are guaranteed', /guarantee/i],
    ['this is completely risk-free', /risk/i],
    ['we promise you will love it', /promise/i],
    ['we are the cheapest in town', /cheapest/i],
  ];
  for (const [draft, re] of cases) {
    test(`refuses: "${draft}"`, () => {
      const r = checkClaims(draft, { profile: NO_CARD });
      assert.equal(r.ok, false);
      assert.match(r.violations[0].found, re);
    });
  }
});

describe('per-vertical rules follow the industry pack', () => {
  const v = (pack) => ({ ...NO_CARD, industry_pack: pack });

  test('med_spa refuses a cure claim and a named treatment', () => {
    assert.equal(checkClaims('this will cure your acne', { profile: v('med_spa') }).ok, false);
    assert.equal(checkClaims('your Botox appointment is Tuesday', { profile: v('med_spa') }).ok, false);
  });

  test('med_spa rules do NOT fire for a detailer', () => {
    assert.equal(checkClaims('your appointment is Tuesday', { profile: v('auto_detail') }).ok, true);
    assert.equal(checkClaims('we use a laser thickness gauge', { profile: v('auto_detail') }).ok, true);
  });

  test('real_estate refuses fair-housing coded language', () => {
    assert.equal(checkClaims("it's in a really safe neighborhood", { profile: v('real_estate') }).ok, false);
    assert.equal(checkClaims('great area with good schools', { profile: v('real_estate') }).ok, false);
  });

  test('real_estate allows describing the property itself', () => {
    const r = checkClaims('Three bedrooms, updated kitchen, south-facing yard.', { profile: v('real_estate') });
    assert.equal(r.ok, true, explain(r));
  });

  test('credit_funding refuses deletion and score-point claims', () => {
    assert.equal(checkClaims('we can remove those from your credit report', { profile: v('credit_funding') }).ok, false);
    assert.equal(checkClaims('expect about 80 points', { profile: v('credit_funding') }).ok, false);
    assert.equal(checkClaims('we can set you up with a CPN', { profile: v('credit_funding') }).ok, false);
  });

  test('ecom_dtc refuses invented scarcity and urgency', () => {
    assert.equal(checkClaims('only 3 left in stock!', { profile: v('ecom_dtc') }).ok, false);
    assert.equal(checkClaims('offer expires in 20 minutes', { profile: v('ecom_dtc') }).ok, false);
  });

  test('an unknown industry_pack still gets the core rules', () => {
    const r = checkClaims('results guaranteed', { profile: { ...NO_CARD, industry_pack: 'not_a_pack' } });
    assert.equal(r.ok, false);
  });
});

describe('the gate fails CLOSED', () => {
  test('a malformed profile does not read as "anything goes"', () => {
    const r = checkClaims('That will be $199.', { profile: {} });
    assert.equal(r.ok, false);
  });

  test('assertClaimsOk THROWS rather than returning a falsy result', () => {
    assert.throws(
      () => assertClaimsOk('That will be $199.', { profile: NO_CARD }),
      (e) => e.code === 'CLAIMS_REFUSED' && e.violations.length > 0,
    );
  });

  test('the thrown error names what to fix, not just that it broke', () => {
    try {
      assertClaimsOk('$199, guaranteed.', { profile: NO_CARD });
      assert.fail('should have thrown');
    } catch (e) {
      assert.match(e.message, /\$199/);
      assert.match(e.message, /guarantee/i);
    }
  });

  test('an explicitly allowed phrase passes — the escape hatch works', () => {
    const p = { ...NO_CARD, claims: { allow_phrases: ['guarantee'] } };
    assert.equal(checkClaims('our workmanship guarantee covers this', { profile: p }).ok, true);
  });
});

describe('negative controls — the gate must not block ordinary work', () => {
  const clean = [
    "Hi Marcus, we can take the Tahoe Thursday morning. Want me to hold it?",
    "Thanks for coming in today — hope the car's treating you well.",
    "Your appointment is confirmed for 9am. Reply R to reschedule.",
    "I'll check with the owner on that and come straight back to you.",
  ];
  for (const draft of clean) {
    test(`passes: "${draft.slice(0, 44)}…"`, () => {
      const r = checkClaims(draft, { profile: NO_CARD });
      assert.equal(r.ok, true, explain(r));
    });
  }

  test('an empty draft is not a violation', () => {
    assert.equal(checkClaims('', { profile: NO_CARD }).ok, true);
  });
});
