#!/usr/bin/env node
// PROJECT X — Live Ops Feed
// Pulls today's real numbers from GHL + Airtable and writes projectx-feed.json
// The RPG game reads this file on load to auto-award XP.
// READS ONLY — never sends anything externally. Safe to run any time.
// Run: node projectx-feed.js
// Cron: add to launchd or n8n for nightly auto-run (11pm local)

const fs   = require('fs');
const path = require('path');
const { loadAixmosEnv } = require('./lib/env');

// Load TMMT .env.local too (has GHL + Airtable keys)
const tmmt = path.resolve(__dirname, '../TMMT/.env');
if (fs.existsSync(tmmt)) {
  for (const line of fs.readFileSync(tmmt, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
}
loadAixmosEnv();

const GHL_KEY      = process.env.GHL_API_KEY;
const GHL_LOCATION = process.env.GHL_LOCATION_ID;
const AT_PAT       = process.env.AIRTABLE_PAT;
const AT_BASE      = process.env.AIRTABLE_BASE_ID;

const TODAY = new Date();
TODAY.setHours(0, 0, 0, 0);
const todayMs  = TODAY.getTime();
const todayISO = TODAY.toISOString().split('T')[0];

// ── helpers ────────────────────────────────────────────────────────────────

async function ghlGet(path) {
  if (!GHL_KEY || !GHL_LOCATION) return null;
  const res = await fetch(`https://services.leadconnectorhq.com${path}`, {
    headers: { Authorization: `Bearer ${GHL_KEY}`, Version: '2021-07-28' }
  });
  if (!res.ok) return null;
  return res.json();
}

async function atGet(table, params = '') {
  if (!AT_PAT || !AT_BASE) return null;
  const res = await fetch(
    `https://api.airtable.com/v0/${AT_BASE}/${encodeURIComponent(table)}?${params}`,
    { headers: { Authorization: `Bearer ${AT_PAT}` } }
  );
  if (!res.ok) return null;
  return res.json();
}

// ── data pulls ─────────────────────────────────────────────────────────────

async function getDeals() {
  // GHL opportunities won today
  try {
    const data = await ghlGet(
      `/opportunities/search?location_id=${GHL_LOCATION}&status=won&limit=100`
    );
    if (!data?.opportunities) return 0;
    return data.opportunities.filter(o => {
      const d = new Date(o.lastStatusChangeAt || o.updatedAt || 0);
      return d.getTime() >= todayMs;
    }).length;
  } catch { return 0; }
}

async function getTasks() {
  // Airtable tasks marked done today
  try {
    const filter = encodeURIComponent(
      `AND({Status}="Done", IS_AFTER({Last Modified}, '${todayISO}'))`
    );
    const data = await atGet('Tasks', `filterByFormula=${filter}&fields[]=Status`);
    return data?.records?.length ?? 0;
  } catch { return 0; }
}

async function getCalls() {
  // CHUMMO outreach log — count entries from today in state
  try {
    const statePath = path.join(__dirname, 'aixmos-state.json');
    if (!fs.existsSync(statePath)) return 0;
    const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    const log = state?.outreach_log ?? [];
    return log.filter(e => new Date(e.ts || e.time || 0).getTime() >= todayMs).length;
  } catch { return 0; }
}

async function getCollected() {
  // GHL payments collected today (from opportunities with monetary value)
  try {
    const data = await ghlGet(
      `/opportunities/search?location_id=${GHL_LOCATION}&status=won&limit=100`
    );
    if (!data?.opportunities) return 0;
    return data.opportunities
      .filter(o => new Date(o.lastStatusChangeAt || o.updatedAt || 0).getTime() >= todayMs)
      .reduce((sum, o) => sum + (parseFloat(o.monetaryValue) || 0), 0);
  } catch { return 0; }
}

// ── main ───────────────────────────────────────────────────────────────────

async function buildFeed() {
  console.log(`[ProjectX Feed] ${new Date().toLocaleString()} — pulling today's numbers...`);

  const [deals, tasks, calls, collected] = await Promise.all([
    getDeals(), getTasks(), getCalls(), getCollected()
  ]);

  const feed = {
    date:      todayISO,
    generated: new Date().toISOString(),
    deals,
    tasks,
    calls,
    collected,
    workouts: 0,   // manual — fill in the RPG or wire a health source
    prayers:  0,   // manual — fill in the RPG
  };

  const outPath = path.join(__dirname, 'projectx-feed.json');
  fs.writeFileSync(outPath, JSON.stringify(feed, null, 2));
  console.log('[ProjectX Feed] Written →', outPath);
  console.log(JSON.stringify(feed, null, 2));

  // Append to daily log
  const logPath = path.join(__dirname, 'logs', 'projectx-feed.log');
  if (fs.existsSync(path.dirname(logPath))) {
    fs.appendFileSync(logPath, JSON.stringify({ ...feed, _run: new Date().toISOString() }) + '\n');
  }

  return feed;
}

buildFeed().catch(e => { console.error('[ProjectX Feed] Error:', e.message); process.exit(1); });
