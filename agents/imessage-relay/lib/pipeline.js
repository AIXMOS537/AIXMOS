'use strict';

const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { classify, t3CannedDraft, canonHandle, digits, inList } = require('./policy');
const { isKilled, allowRate, consumeRate } = require('./gates');
const { draftReply } = require('./llm-local');
const { writeDraft, markDraftSent, audit } = require('./store');
const { hashHandle } = require('./chatdb');

const TEXT_EXEC = path.join(os.homedir(), '.config', 'tmmt', 'text-exec.sh');

function runOwnerExec(text) {
  try {
    const out = execFileSync('/bin/bash', [TEXT_EXEC, String(text || '')], {
      encoding: 'utf8',
      timeout: 120000,
      env: { ...process.env, PATH: '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin' },
    });
    return String(out || '').trim().slice(0, 3500) || "I'm on it.";
  } catch (err) {
    return `Rick hit a wall running that: ${String(err.message || err).slice(0, 180)}`;
  }
}

function isIMessageService(service) {
  return String(service || '').toLowerCase() === 'imessage';
}

const SIG = '\n— Rick (Taha\'s assistant)';

function withAssistantSignature(text) {
  const body = String(text || '').trim();
  if (!body) return body;
  if (/—\s*Rick/i.test(body)) return body;
  return body + SIG;
}

function sendAllowed(cls, config, env = process.env) {
  if (isKilled(env)) return { ok: false, reason: 'kill_switch' };
  if (cls.tier === 'T3') return { ok: false, reason: 'tier_T3' };
  if (cls.tier === 'T2') return { ok: false, reason: 'tier_T2' };
  if (cls.tier !== 'T1') return { ok: false, reason: `tier_${cls.tier}` };
  const auto = config.auto_send_assistant === true || env.IMESSAGE_AUTO_ASSISTANT === '1';
  const allow = config.allow_send === true || env.IMESSAGE_ALLOW_SEND === '1' || auto;
  if (!allow) return { ok: false, reason: 'allow_send_off' };
  if (config.safe_mode !== false && !auto) return { ok: false, reason: 'safe_mode' };
  return { ok: true };
}

function skipSendDestination(from) {
  const raw = String(from || '').trim();
  if (!raw) return 'no_handle';
  if (raw.startsWith('chat') || raw.includes(';')) return 'group_chat';
  const d = digits(raw);
  if (d.length >= 4 && d.length <= 6) return 'short_code';
  return null;
}

/**
 * Core inbound handler. Default action is draft.
 * Live Messages.app send only when adapters.send is provided AND every gate passes.
 */
async function handleInbound(msg, { config, adapters, env, now } = {}) {
  const cfg = config || {};
  const e = env || process.env;
  const from = msg.from || '';
  const text = msg.text || '';
  const id = msg.id || msg.guid || msg.rowid || 'msg';

  if (isKilled(e)) {
    const out = { action: 'blocked', reason: 'kill_switch', sent: false, tier: null };
    audit({ event: 'blocked', reason: 'kill_switch', id, from });
    return out;
  }

  const cls = classify({ from, text }, cfg);
  const ownerHandle = inList(from, cfg.owner_handles);
  const imessageOk = isIMessageService(msg.service);
  // T3 (family/money/legal) always wins — a mis-added owner_handles entry
  // must not bypass "never auto". SMS/RCS sender-ID is spoofable; only
  // iMessage (Apple-ID authenticated) may trigger MASTER exec.
  const owner = ownerHandle && imessageOk && cls.tier !== 'T3';

  // ── THALAMUS + AMYGDALA front door (2026-09-08). Runs before rate limits, before
  // any LLM draft. Rules-first threat scan; family (T3) is routed to Rick -> Taha and
  // never gets a model vote. HIGH = blocked + ESCALATED file (escalation-watch pings
  // Taha). Kill switch: THALAMUS_GATE=off or ~/.rick/brain/thalamus/OFF. If the gate
  // binary is missing or crashes, the pipeline continues exactly as before.
  let brainRoute = null;
  try {
    const gateBin = path.join(os.homedir(), '.rick', 'bin', 'thalamus-gate');
    if (fs.existsSync(gateBin)) {
      const senderTier = cls.tier === 'T3' ? 'family' : (owner ? 'owner' : (cls.tier === 'T1' ? 'inner-circle' : 'public'));
      const raw = execFileSync('/usr/bin/python3', [gateBin, 'imessage', senderTier, String(text)], { timeout: 30000, encoding: 'utf8' });
      const g = JSON.parse(String(raw || '{}').trim().split('\n').pop());
      brainRoute = { route: g.route, urgency: g.urgency, threat: g.threat, threat_type: g.threat_type };
      if (g.halt === true) {
        const out = { action: 'blocked', reason: `amygdala_${g.threat_type || 'HIGH'}`, sent: false, tier: cls.tier, brain: brainRoute };
        audit({ event: 'blocked', reason: out.reason, id, from, tier: cls.tier, brain: brainRoute });
        return out;
      }
    }
  } catch (err) {
    audit({ event: 'gate_error', reason: String(err && err.message || err).slice(0, 160), id, from, tier: cls.tier });
  }
  const rateDraft = allowRate('draft', canonHandle(from), cfg, now);
  if (!rateDraft.ok) {
    const out = { action: 'blocked', reason: rateDraft.reason, sent: false, tier: cls.tier };
    audit({ event: 'blocked', reason: rateDraft.reason, id, from, tier: cls.tier });
    return out;
  }

  if (owner) {
    const rateOwner = allowRate('owner_exec', canonHandle(from), cfg, now);
    if (!rateOwner.ok) {
      const out = { action: 'blocked', reason: rateOwner.reason, sent: false, tier: cls.tier, owner: true };
      audit({ event: 'blocked', reason: rateOwner.reason, id, from, tier: cls.tier, backend: 'owner-exec' });
      return out;
    }
  }

  let reply;
  let backend = null;
  if (cls.tier === 'T3') {
    reply = t3CannedDraft();
    backend = 'canned';
  } else if (owner) {
    const exec = adapters && typeof adapters.ownerExec === 'function'
      ? adapters.ownerExec
      : (t) => runOwnerExec(t);
    reply = await Promise.resolve(exec(text));
    backend = 'owner-exec';
    consumeRate('owner_exec', canonHandle(from), cfg, now);
  } else if (adapters && typeof adapters.llm === 'function') {
    const gen = await adapters.llm({ inboundText: text, tier: cls.tier, config: cfg });
    reply = gen.text;
    backend = gen.backend;
  } else {
    const gen = await draftReply({ inboundText: text, tier: cls.tier, config: cfg });
    reply = gen.text;
    backend = gen.backend;
  }

  if (cls.tier === 'T1') reply = withAssistantSignature(reply);

  // ── NEUROPLASTICITY (2026-09-08): judge this draft against the ask in a detached process and
  // train the thalamus' routing synapses. Never blocks the pipeline. Family (T3) drafts are canned,
  // so they are not judged. Kill switch: ~/.rick/brain/thalamus/NO-LEARN.
  try {
    const judgeBin = path.join(os.homedir(), '.rick', 'bin', 'cingulate-judge');
    const noLearn = path.join(os.homedir(), '.rick', 'brain', 'thalamus', 'NO-LEARN');
    if (brainRoute && brainRoute.route && cls.tier !== 'T3' && reply && fs.existsSync(judgeBin) && !fs.existsSync(noLearn)) {
      const { spawn } = require('child_process');
      const child = spawn('/usr/bin/python3', [judgeBin, 'imessage', String(brainRoute.route), String(text), String(reply)], { detached: true, stdio: 'ignore' });
      child.unref();
    }
  } catch (err) {
    audit({ event: 'judge_error', reason: String(err && err.message || err).slice(0, 160), id, from });
  }

  consumeRate('draft', canonHandle(from), cfg, now);
  const saved = writeDraft({
    id,
    tier: cls.tier,
    from,
    inbound: text,
    reply,
    backend,
    action: 'draft',
  });

  const destSkip = skipSendDestination(from);
  const sendCls = owner ? { ...cls, tier: 'T1' } : cls;
  const gate = destSkip ? { ok: false, reason: destSkip } : sendAllowed(sendCls, cfg, e);
  let sent = false;
  let action = 'draft';
  let sendReason = gate.reason || 'draft_default';

  if (msg.skip_send) {
    sendReason = msg.skip_send;
  } else if (gate.ok) {
    const rateSend = allowRate('send', canonHandle(from), cfg, now);
    if (!rateSend.ok) {
      sendReason = rateSend.reason;
    } else if (adapters && typeof adapters.send === 'function') {
      const result = await adapters.send({ to: from, text: reply });
      sent = !!(result && result.ok && result.via !== 'draft');
      action = sent ? 'sent' : 'draft';
      sendReason = sent ? 'adapter_sent' : (result && result.reason) || 'adapter_draft';
      if (sent) {
        consumeRate('send', canonHandle(from), cfg, now);
        markDraftSent(saved.file);
      }
    } else {
      sendReason = 'no_send_adapter';
    }
  }

  audit({
    event: action,
    reason: sendReason,
    id,
    from,
    from_hash: hashHandle(from),
    tier: cls.tier,
    backend,
    sent,
    inbound: text,
  });

  return {
    action,
    reason: sendReason,
    sent: false,
    actuallySent: sent,
    tier: cls.tier,
    allowlisted: cls.allowlisted,
    owner,
    ownerHandle,
    ownerBlockedReason: ownerHandle && !owner
      ? (cls.tier === 'T3' ? 'tier_T3' : (imessageOk ? null : 'sms_unauthenticated'))
      : null,
    classifyReason: cls.reason,
    reply,
    backend,
    draftFile: saved.file,
  };
}

module.exports = { handleInbound, sendAllowed, withAssistantSignature, skipSendDestination, isIMessageService };
