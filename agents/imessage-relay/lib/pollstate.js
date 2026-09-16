'use strict';

/**
 * Functional health for the live poller (2026-09-16, owner charter P1-C).
 *
 * The old /health only proved chat.db opened directly, while polling failed on the
 * temp working copy for 12 days and still said ok:true. This records what the poll
 * loop ACTUALLY did, so health answers "are inbound messages being processed?".
 * Never stores message bodies or handles.
 */

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { ROOT } = require('./paths');
const { CHAT_DB } = require('./chatdb');

const STATE_FILE = path.join(ROOT, 'poll-state.json');
const BACKLOG_GRACE_MS = 60 * 1000;

const state = {
  started_at: new Date().toISOString(),
  last_poll_at: null,
  last_poll_ok_at: null,
  consecutive_failures: 0,
  last_error: null,
  last_error_at: null,
  last_processed_at: null,
  last_processed_count: 0,
  processed_total: 0,
  sent_total: 0,
  backlog_since: null,
};

function persist() {
  try {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 1), { mode: 0o600 });
  } catch { /* health must never crash the poller */ }
}

/** Errors can echo a handle or address; health output must never carry one. */
function scrub(s) {
  return String(s)
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '<email>')
    .replace(/\+?\d[\d\s().-]{6,}\d/g, '<number>')
    .replace(/[A-Za-z0-9_-]{32,}/g, '<redacted>')
    .replace(/\s+/g, ' ')
    .slice(0, 160);
}

function recordPoll(result, nowMs = Date.now()) {
  const now = new Date(nowMs).toISOString();
  state.last_poll_at = now;
  if (result && result.ok) {
    state.last_poll_ok_at = now;
    state.consecutive_failures = 0;
    if (result.processed) {
      state.last_processed_at = now;
      state.last_processed_count = result.processed;
      state.processed_total += result.processed;
      state.sent_total += result.sent || 0;
    }
  } else {
    state.consecutive_failures += 1;
    state.last_error = scrub((result && result.error) || 'unknown');
    state.last_error_at = now;
  }
  persist();
}

function readCursor() {
  try {
    return Number(fs.readFileSync(path.join(ROOT, 'chatdb.cursor'), 'utf8')) || 0;
  } catch {
    return 0;
  }
}

/** Newest inbound message in the SOURCE db: proves source access + gives the backlog edge. */
function sourceInbound() {
  try {
    const out = execFileSync('/usr/bin/sqlite3', ['-readonly', CHAT_DB,
      'SELECT MAX(ROWID), MAX(date) FROM message WHERE is_from_me=0 AND item_type=0 AND is_system_message=0;'], {
      encoding: 'utf8', timeout: 5000, stdio: ['ignore', 'pipe', 'pipe'],
    }).trim();
    const [rowid, date] = out.split('|');
    return { ok: true, max_inbound_rowid: Number(rowid) || 0, max_inbound_apple_date: Number(date) || 0 };
  } catch (err) {
    return { ok: false, error: String((err.stderr && String(err.stderr)) || err.message).trim().slice(0, 160) };
  }
}

function appleToIso(n) {
  if (!n) return null;
  const ms = n > 1e12 ? Date.UTC(2001, 0, 1) + n / 1e6 : Date.UTC(2001, 0, 1) + n * 1e3;
  return new Date(ms).toISOString();
}

/**
 * HEALTHY | DEGRADED | FAILED | DISABLED_INTENTIONALLY | UNKNOWN
 * `inProcess` = true when called inside the live poller (state is live), false otherwise.
 */
function functionalHealth({ pollMs = 5000, killed = false, sendEnabled = false, processRunning = true, inProcess = true, now = Date.now() } = {}) {
  const src = sourceInbound();
  const cursor = readCursor();
  const reasons = [];
  let s = 'HEALTHY';
  const worst = (next) => {
    const rank = { HEALTHY: 0, DEGRADED: 1, UNKNOWN: 2, FAILED: 3 };
    if (rank[next] > rank[s]) s = next;
  };

  const lastPoll = state.last_poll_at ? Date.parse(state.last_poll_at) : 0;
  const lastOk = state.last_poll_ok_at ? Date.parse(state.last_poll_ok_at) : 0;
  const loopStaleMs = Math.max(60000, pollMs * 6);

  if (!processRunning) { worst('FAILED'); reasons.push('process_not_running'); }
  if (!src.ok) { worst('FAILED'); reasons.push('source_db_unreadable'); }
  if (inProcess && !killed) {
    if (!lastPoll && now - Date.parse(state.started_at) <= loopStaleMs) { worst('UNKNOWN'); reasons.push('starting_no_poll_yet'); }
    else if (!lastPoll || now - lastPoll > loopStaleMs) { worst('FAILED'); reasons.push('poll_loop_not_advancing'); }
    if (state.consecutive_failures >= 3) { worst('FAILED'); reasons.push('working_copy_or_poll_failing'); }
    else if (state.consecutive_failures > 0) { worst('DEGRADED'); reasons.push('recent_poll_failure'); }
  }

  let backlog = 0;
  if (src.ok) {
    backlog = Math.max(0, src.max_inbound_rowid - cursor);
    if (backlog > 0) {
      if (!state.backlog_since) state.backlog_since = new Date(now).toISOString();
      const age = now - Date.parse(state.backlog_since);
      if (!killed && age > BACKLOG_GRACE_MS) { worst('FAILED'); reasons.push('inbound_not_processed'); }
    } else {
      state.backlog_since = null;
    }
  }
  if (killed) { s = 'DISABLED_INTENTIONALLY'; reasons.push('kill_switch_on'); }

  return {
    state: s,
    reasons,
    process_running: processRunning,
    source_db_accessible: src.ok,
    working_copy_accessible: inProcess ? (lastOk > 0 && state.consecutive_failures < 3) : null,
    poll_loop_advancing: inProcess ? (lastPoll > 0 && now - lastPoll <= loopStaleMs) : null,
    last_poll_at: state.last_poll_at,
    last_successful_poll_at: state.last_poll_ok_at,
    last_successful_process_at: state.last_processed_at,
    last_inbound_event_at: src.ok ? appleToIso(src.max_inbound_apple_date) : null,
    cursor,
    unprocessed_inbound: backlog,
    backlog_since: state.backlog_since,
    consecutive_failures: state.consecutive_failures,
    last_error: state.last_error,
    last_error_at: state.last_error_at,
    processed_total: state.processed_total,
    sent_total: state.sent_total,
    send_enabled: sendEnabled,
  };
}

module.exports = { recordPoll, functionalHealth, scrub, STATE_FILE };
