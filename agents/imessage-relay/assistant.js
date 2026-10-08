#!/usr/bin/env node
'use strict';

/**
 * Text-My-Mac assistant — local, Cursor not required
 *
 *   node assistant.js --status
 *   node assistant.js --mock-test
 *   node assistant.js --live         poll + T1 auto-send via Messages.app
 *   node assistant.js --once
 *   node assistant.js --drafts
 */

const cmd = process.argv.includes('--mock-test') ? 'mock-test'
  : process.argv.includes('--safe-idle') ? 'safe-idle'
  : process.argv.includes('--live') ? 'live'
  : process.argv.includes('--once') ? 'once'
  : process.argv.includes('--drafts') ? 'drafts'
  : 'status';

async function main() {
  if (cmd === 'mock-test') {
    const { run } = require('./mock-test');
    const code = await run();
    process.exit(code);
  }

  const inbound = require('./lib/inbound');

  if (cmd === 'safe-idle') {
    inbound.startHealthServer();
    return;
  }

  if (cmd === 'once') {
    const r = await inbound.processLiveOnce();
    console.log(JSON.stringify(r, null, 2));
    process.exit(r.ok ? 0 : 2);
  }

  if (cmd === 'drafts') {
    const { DRAFTS_DIR } = require('./lib/paths');
    const fs = require('fs');
    const path = require('path');
    if (!fs.existsSync(DRAFTS_DIR)) {
      console.log('no drafts yet');
      process.exit(0);
    }
    const files = fs.readdirSync(DRAFTS_DIR).filter((f) => f.endsWith('.json')).sort().reverse().slice(0, 20);
    for (const f of files) {
      const rec = JSON.parse(fs.readFileSync(path.join(DRAFTS_DIR, f), 'utf8'));
      console.log(`${f}  tier=${rec.tier}  sent=${rec.sent}`);
      console.log(`  in:  ${(rec.inbound || '').slice(0, 120)}`);
      console.log(`  out: ${(rec.reply || '').slice(0, 200)}`);
      console.log('');
    }
    process.exit(0);
  }

  if (cmd === 'live') {
    const fs = require('fs');
    const { LOCK_FILE, ensureDirs } = require('./lib/paths');
    const { probeFda } = require('./lib/chatdb');
    ensureDirs();
    const take = () => {
      try {
        const fd = fs.openSync(LOCK_FILE, 'wx');
        fs.writeFileSync(fd, String(process.pid));
        fs.closeSync(fd);
        return true;
      } catch (err) {
        if (err.code !== 'EEXIST') throw err;
        try {
          const pid = Number(String(fs.readFileSync(LOCK_FILE, 'utf8')).trim());
          if (pid && pid !== process.pid) {
            process.kill(pid, 0);
            return false;
          }
        } catch {
          try { fs.unlinkSync(LOCK_FILE); } catch { /* retry */ }
          return take();
        }
        return false;
      }
    };
    for (;;) {
      const fda = probeFda();
      if (fda.ok) break;
      console.error('chat.db blocked in this process:', fda.error);
      console.error(fda.hint);
      await new Promise((ok) => setTimeout(ok, 20000));
    }
    while (!take()) {
      console.error('another live poller holds the lock — standby');
      await new Promise((ok) => setTimeout(ok, 30000));
    }
    process.on('exit', () => { try { fs.unlinkSync(LOCK_FILE); } catch { /* ignore */ } });
    inbound.startHealthServer();
    await inbound.liveLoop();
    return;
  }

  const s = await inbound.statusPayload();
  console.log(JSON.stringify(s, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
