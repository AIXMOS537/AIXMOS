'use strict';

const fs = require('fs');
const { KILL_FILE, RATE_FILE, loadJson } = require('./paths');

function isKilled(env = process.env) {
  if (env.IMESSAGE_KILL === '1' || env.IMESSAGE_KILL === 'true') return true;
  try {
    return fs.existsSync(KILL_FILE);
  } catch {
    return true;
  }
}

function hourBucket(now = Date.now()) {
  return Math.floor(now / 3600000);
}

function loadRate() {
  return loadJson(RATE_FILE, {
    hour: 0,
    drafts: 0,
    sends: 0,
    ownerExecs: 0,
    perSender: {},
    perSenderSend: {},
    perSenderOwner: {},
  });
}

function saveRate(state) {
  fs.writeFileSync(RATE_FILE, JSON.stringify(state), { mode: 0o600 });
}

function allowRate(kind, sender, config, now = Date.now()) {
  const hour = hourBucket(now);
  let state = loadRate();
  if (state.hour !== hour) {
    state = {
      hour,
      drafts: 0,
      sends: 0,
      ownerExecs: 0,
      perSender: {},
      perSenderSend: {},
      perSenderOwner: {},
    };
  }
  if (!state.perSenderSend) state.perSenderSend = {};
  if (!state.perSenderOwner) state.perSenderOwner = {};
  if (typeof state.ownerExecs !== 'number') state.ownerExecs = 0;
  const limits = config.rate || {};
  const senderKey = sender || 'unknown';
  if (kind === 'draft') {
    const per = state.perSender[senderKey] || 0;
    if (state.drafts >= (limits.drafts_per_hour || 40)) return { ok: false, reason: 'drafts_per_hour', state };
    if (per >= (limits.per_sender_per_hour || 10)) return { ok: false, reason: 'per_sender_per_hour', state };
  }
  if (kind === 'send') {
    const per = state.perSenderSend[senderKey] || 0;
    if (state.sends >= (limits.sends_per_hour || 20)) return { ok: false, reason: 'sends_per_hour', state };
    if (per >= (limits.per_sender_sends_per_hour || 4)) return { ok: false, reason: 'per_sender_sends_per_hour', state };
  }
  if (kind === 'owner_exec') {
    const per = state.perSenderOwner[senderKey] || 0;
    if (state.ownerExecs >= (limits.owner_execs_per_hour || 5)) {
      return { ok: false, reason: 'owner_execs_per_hour', state };
    }
    if (per >= (limits.per_sender_owner_execs_per_hour || 5)) {
      return { ok: false, reason: 'per_sender_owner_execs_per_hour', state };
    }
  }
  return { ok: true, state };
}

function consumeRate(kind, sender, config, now = Date.now()) {
  const gate = allowRate(kind, sender, config, now);
  if (!gate.ok) return gate;
  const state = gate.state;
  const senderKey = sender || 'unknown';
  if (!state.perSenderSend) state.perSenderSend = {};
  if (!state.perSenderOwner) state.perSenderOwner = {};
  if (typeof state.ownerExecs !== 'number') state.ownerExecs = 0;
  if (kind === 'draft') {
    state.drafts += 1;
    state.perSender[senderKey] = (state.perSender[senderKey] || 0) + 1;
  }
  if (kind === 'send') {
    state.sends += 1;
    state.perSenderSend[senderKey] = (state.perSenderSend[senderKey] || 0) + 1;
  }
  if (kind === 'owner_exec') {
    state.ownerExecs += 1;
    state.perSenderOwner[senderKey] = (state.perSenderOwner[senderKey] || 0) + 1;
  }
  saveRate(state);
  return { ok: true, state };
}

module.exports = { isKilled, hourBucket, loadRate, saveRate, allowRate, consumeRate };
