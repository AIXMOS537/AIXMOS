'use strict';
const { test, describe } = require('node:test');
const assert = require('node:assert');
const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DNC = path.join(os.homedir(), '.aixmos', 'do-not-contact.json');

function doctor() {
  try {
    const out = execFileSync('bash', ['bin/aixmos', 'doctor'], { cwd: ROOT, encoding: 'utf8' });
    return { code: 0, out };
  } catch (e) {
    return { code: e.status, out: (e.stdout || '') + (e.stderr || '') };
  }
}

describe('the launcher tells the truth about this machine', () => {
  test('doctor exits 0 and says Ready when nothing is wrong', () => {
    try { fs.unlinkSync(DNC); } catch {}
    const r = doctor();
    assert.equal(r.code, 0);
    assert.match(r.out, /Ready/);
  });

  test('an unreadable do-not-contact list makes doctor FAIL, not warn', () => {
    // The gate fails closed, so every send would be refused. The launcher must say so
    // up front rather than letting someone find out mid-campaign.
    fs.mkdirSync(path.dirname(DNC), { recursive: true });
    fs.writeFileSync(DNC, '{ not json');
    const r = doctor();
    try { fs.unlinkSync(DNC); } catch {}
    assert.equal(r.code, 1, 'doctor must exit non-zero');
    assert.match(r.out, /UNREADABLE/);
  });

  test('doctor reports sending as OFF when the relay is unconfigured', () => {
    const r = doctor();
    assert.match(r.out, /nothing can send|sending is OFF/);
  });

  test('an unknown agent is refused, not silently ignored', () => {
    try {
      execFileSync('bash', ['bin/aixmos', 'notanagent'], { cwd: ROOT, encoding: 'utf8' });
      assert.fail('should have exited non-zero');
    } catch (e) {
      assert.match((e.stdout || '') + (e.stderr || ''), /no such agent/);
    }
  });

  test('--help lists the real agent names', () => {
    const out = execFileSync('bash', ['bin/aixmos', '--help'], { cwd: ROOT, encoding: 'utf8' });
    for (const a of ['chummo', 'moose', 'vision', 'sticks']) assert.match(out, new RegExp(a));
  });
});
