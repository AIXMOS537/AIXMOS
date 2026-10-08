'use strict';

const http = require('http');
const { execFileSync } = require('child_process');
const { loadConfig, ensureDirs, ROOT, KILL_FILE } = require('./paths');
const { probeFda } = require('./chatdb');
const { probeLiteLLM, probeOllama } = require('./llm-local');
const { isKilled } = require('./gates');
const { familyOwnerOverlap } = require('./policy');
const { handleInbound, sendState } = require('./pipeline');
const { readNewInbound, advanceCursor } = require('./chatdb');
const { sendViaMessages } = require('./send-imessage');
const { recordPoll, functionalHealth } = require('./pollstate');

let LIVE_POLLER = false; // true only inside the --live loop, where poll state is real

const PORT = parseInt(process.env.RELAY_PORT || '8790', 10);
const BIND = process.env.RELAY_BIND || '127.0.0.1';
const STALE_MS = 12 * 60 * 1000;

function launchAgentState() {
  try {
    execFileSync('launchctl', ['print', `gui/${process.getuid()}/com.tmmt.imessage-relay`], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    return 'loaded';
  } catch {
    return 'not_loaded';
  }
}

async function statusPayload() {
  const config = loadConfig();
  const fda = probeFda();
  const litellm = await probeLiteLLM(config.llm.litellm_url);
  const ollama = await probeOllama(config.llm.ollama_url);
  const familyOverlap = familyOwnerOverlap(config.owner_handles);
  const send = sendState(config, process.env);
  const sendEnabled = send.allow_send;
  const functional = functionalHealth({
    pollMs: config.poll_ms || 5000,
    killed: isKilled(),
    sendEnabled,
    processRunning: true,
    inProcess: LIVE_POLLER,
  });
  return {
    // ok = FUNCTIONAL health (inbound actually processed), not "chat.db opens" (P1-C).
    ok: functional.state === 'HEALTHY',
    health_state: functional.state,
    functional,
    service: 'text-my-mac',
    cursor_not_required: true,
    family_owner_overlap_checked: familyOverlap.checked,
    family_owner_overlap_count: familyOverlap.overlaps.length,
    family_owner_overlap_note: familyOverlap.note || null,
    auto_send_assistant: send.auto_send_assistant,
    auto_field: config.auto_field !== false,
    safe_mode: config.safe_mode !== false,
    allow_send: sendEnabled,
    kill: isKilled(),
    kill_file: KILL_FILE,
    fda,
    fda_hint: fda.ok
      ? 'chat.db readable in this process'
      : 'Grant Full Disk Access to /usr/local/bin/node (not Cursor). Then: me on',
    litellm,
    ollama,
    t1_allowlist_count: (config.t1_allowlist || []).length,
    t3_senders_count: (config.t3_senders || []).length,
    root: ROOT,
    launchagent: launchAgentState(),
    health: `${BIND}:${PORT}`,
  };
}

function startHealthServer() {
  const server = http.createServer(async (req, res) => {
    const json = (code, obj) => {
      res.writeHead(code, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(obj));
    };
    if (req.method === 'GET' && (req.url === '/health' || req.url === '/status')) {
      const payload = await statusPayload();
      return json(payload.health_state === 'FAILED' ? 503 : 200, payload);
    }
    if (req.method === 'POST' && req.url === '/send') {
      return json(403, {
        ok: false,
        error: 'http_send_disabled',
        detail: 'HTTP /send stays off. Live replies go through Messages.app only, T1 only.',
      });
    }
    return json(404, { ok: false, error: 'not found' });
  });
  server.listen(PORT, BIND, () => {
    console.log(`text-my-mac health on ${BIND}:${PORT} (HTTP send disabled; T1 Messages send via osascript)`);
  });
  server.on('error', (err) => {
    if (err && err.code === 'EADDRINUSE') {
      console.log(`health port ${PORT} in use — poller continues without HTTP`);
      return;
    }
    throw err;
  });
  return server;
}

function isStale(msg) {
  if (!msg || !msg.at) return false;
  const t = Date.parse(msg.at);
  if (!Number.isFinite(t)) return false;
  return Date.now() - t > STALE_MS;
}

async function processLiveOnce() {
  ensureDirs();
  const config = loadConfig();
  const batch = readNewInbound({ limit: 10 });
  if (!batch.ok) {
    return { ok: false, error: batch.error, hint: batch.hint };
  }
  const adapters = {
    send: async ({ to, text }) => {
      try {
        return await sendViaMessages(to, text);
      } catch (err) {
        return { ok: false, via: 'draft', reason: String(err.message || err).slice(0, 180) };
      }
    },
  };
  const results = [];
  let maxRow = 0;
  for (const msg of batch.messages) {
    if (!msg.text) {
      if (msg.rowid > maxRow) maxRow = msg.rowid;
      continue;
    }
    const skip_send = isStale(msg) ? 'stale_backlog' : null;
    const r = await handleInbound(
      { id: String(msg.rowid), from: msg.from, text: msg.text, guid: msg.guid, service: msg.service, skip_send },
      { config, adapters }
    );
    results.push({
      rowid: msg.rowid,
      tier: r.tier,
      action: r.action,
      sent: r.actuallySent === true,
      reason: r.reason,
    });
    if (msg.rowid > maxRow) maxRow = msg.rowid;
  }
  if (maxRow > 0) advanceCursor(maxRow);
  const sent = results.filter((x) => x.sent).length;
  return { ok: true, processed: results.length, sent, results };
}

function warnFamilyOwnerOverlap(config) {
  const overlap = familyOwnerOverlap(config.owner_handles);
  if (!overlap.checked) {
    console.log(`family/owner overlap check: ${overlap.note}`);
    return;
  }
  if (overlap.overlaps.length) {
    console.warn(
      `WARNING: owner_handles has ${overlap.overlaps.length} entr${overlap.overlaps.length === 1 ? 'y' : 'ies'} ` +
      'that also appear on the FAMILY_NUMBERS roster (~/.config/tmmt/content-team.env). ' +
      'A family number in owner_handles would be eligible for MASTER exec. Review ' +
      '~/.config/tmmt/owner-handles.env and imessage-assistant/config.json owner_handles.'
    );
  } else {
    console.log(`family/owner overlap check: clean (0 of ${overlap.familyCount} family handles overlap owner_handles)`);
  }
}

/** Startup line states ACTUAL send posture — never claims auto-send that is off. No customer data. */
function startupStateLine(config, env = process.env) {
  const s = sendState(config, env);
  return `LIVE poller: READ MODE ON | SEND ${s.allow_send ? 'ENABLED' : 'DISABLED'} | ` +
    `AUTO-REPLY ${s.auto_send_assistant ? 'ENABLED' : 'DISABLED'} | SAFE_MODE ${s.safe_mode ? 'ON' : 'OFF'} | ` +
    `KILL ${isKilled(env) ? 'ON' : 'OFF'} | T2 draft | T3 never`;
}

async function liveLoop() {
  LIVE_POLLER = true;
  console.log(startupStateLine(loadConfig(), process.env));
  console.log('Kill: touch ~/.config/tmmt/imessage-assistant/KILL   or   me kill');
  warnFamilyOwnerOverlap(loadConfig());
  for (;;) {
    if (isKilled()) {
      console.log('kill switch on — sleeping');
    } else {
      try {
        const r = await processLiveOnce();
        recordPoll(r);
        if (!r.ok) console.log(new Date().toISOString(), 'poll:', r.error, r.hint || '');
        else if (r.processed) console.log(`processed ${r.processed} sent ${r.sent || 0}`);
      } catch (err) {
        recordPoll({ ok: false, error: err.message });
        console.error(new Date().toISOString(), 'poll error:', err.message);
      }
    }
    const ms = loadConfig().poll_ms || 5000;
    await new Promise((ok) => setTimeout(ok, ms));
  }
}

module.exports = { statusPayload, startHealthServer, processLiveOnce, liveLoop, warnFamilyOwnerOverlap, startupStateLine };
