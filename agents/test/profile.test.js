'use strict';
const { test, describe } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.join(__dirname, '..');

/**
 * Tokens that belong to ONE operation and must never reach a client's agent.
 * If any of these shows up in a rendered prompt, the pack is not white-label.
 */
const OWNER_TOKENS = [
  /\bTMMT\b/i,
  /\bMUHAMMAD\b/i,
  /\bTaha\b/i,
  /Auto Services/i,
  /\$97\s*\/?\s*(month|mo)/i,
  /10K\/month/i,
  /leadconnectorhq/i,
];

/** Strip comments so we test what the model sees, not what we wrote about it. */
function codeOnly(file) {
  return fs.readFileSync(path.join(ROOT, file), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n').filter(l => !/^\s*(\/\/|\*)/.test(l)).join('\n');
}

describe('no client ever meets the pack author\'s business', () => {
  for (const file of ['orchestrator.js', 'agents/prompts.js']) {
    test(`${file} carries no owner-specific identity in code`, () => {
      const src = codeOnly(file);
      for (const re of OWNER_TOKENS) {
        assert.equal(re.test(src), false, `${file} still contains ${re}`);
      }
    });
  }

  test('every RENDERED agent prompt names nobody by default', () => {
    // This is the one that matters: what the model is actually handed.
    const prompts = require('../agents/prompts');
    const names = Object.keys(prompts).filter(k => typeof prompts[k] === 'string');
    assert.ok(names.length >= 5, `expected several prompts, got ${names.length}`);
    for (const name of names) {
      for (const re of OWNER_TOKENS) {
        assert.equal(re.test(prompts[name]), false, `prompt "${name}" leaks ${re}`);
      }
    }
  });
});

describe('the default profile assumes nothing', () => {
  const { businessContext, ownerLabel, loadProfile } = require('../lib/profile');

  test('with no profile file it names no business and forbids inventing one', () => {
    const ctx = businessContext();
    assert.match(ctx, /never invent|not been told/i);
    assert.equal(/riverside|acme|example/i.test(ctx), false, 'must not name a placeholder business');
  });

  test('the task owner is a role, never a person', () => {
    assert.equal(ownerLabel(), 'OWNER');
  });

  test('a malformed profile falls back to naming nothing, not to half-parsed junk', () => {
    const tmp = path.join(os.tmpdir(), `aixmos-bad-${Date.now()}.json`);
    fs.writeFileSync(tmp, '{ not json');
    process.env.AIXMOS_PROFILE = tmp;
    delete require.cache[require.resolve('../lib/profile')];
    const p = require('../lib/profile');
    assert.equal(p.loadProfile().source, 'invalid');
    assert.match(p.businessContext(), /never invent|not been told/i);
    delete process.env.AIXMOS_PROFILE;
    delete require.cache[require.resolve('../lib/profile')];
    fs.unlinkSync(tmp);
  });
});

describe('a client profile actually reaches the agents', () => {
  test('the business name, lines and rules are rendered', () => {
    const tmp = path.join(os.tmpdir(), `aixmos-good-${Date.now()}.json`);
    fs.writeFileSync(tmp, JSON.stringify({
      business_name: 'Riverside Auto Rentals',
      what_we_do: 'weekly rentals for rideshare drivers',
      owner_label: 'DANA',
      lines: [{ name: 'Weekly rentals', detail: 'gig drivers', tone: 'direct' }],
      notes: ['Never quote a price not on the rate card.'],
    }, null, 2));
    process.env.AIXMOS_PROFILE = tmp;
    delete require.cache[require.resolve('../lib/profile')];
    const p = require('../lib/profile');

    const ctx = p.businessContext();
    assert.match(ctx, /Riverside Auto Rentals/);
    assert.match(ctx, /weekly rentals for rideshare drivers/);
    assert.match(ctx, /Weekly rentals/);
    assert.match(ctx, /Never quote a price not on the rate card/);
    assert.equal(p.ownerLabel(), 'DANA');
    // And still no trace of whoever built the pack.
    for (const re of OWNER_TOKENS) assert.equal(re.test(ctx), false, `leaks ${re}`);

    delete process.env.AIXMOS_PROFILE;
    delete require.cache[require.resolve('../lib/profile')];
    fs.unlinkSync(tmp);
  });
});
