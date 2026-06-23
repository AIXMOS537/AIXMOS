#!/usr/bin/env node
// Quick check — lists recent GHL opportunities so we can confirm stage IDs
const fs = require('fs');
const path = require('path');
const { loadAixmosEnv } = require('./lib/env');

const tmmt = path.resolve(__dirname, '../TMMT/.env');
if (fs.existsSync(tmmt)) {
  for (const line of fs.readFileSync(tmmt, 'utf8').split('\n')) {
    const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
}
loadAixmosEnv();

const KEY = process.env.GHL_API_KEY;
const LOC = process.env.GHL_LOCATION_ID;

if (!KEY || !LOC) { console.error('Missing GHL_API_KEY or GHL_LOCATION_ID'); process.exit(1); }

fetch(`https://services.leadconnectorhq.com/opportunities/search?location_id=${LOC}&limit=5`, {
  headers: { Authorization: `Bearer ${KEY}`, Version: '2021-07-28' }
})
.then(r => r.json())
.then(d => {
  const opps = d?.opportunities ?? [];
  console.log(`Total found: ${d?.meta?.total ?? '?'}`);
  opps.forEach(o => console.log({
    name: o.name,
    status: o.status,
    stage: o.pipelineStageId,
    value: o.monetaryValue,
    updated: o.updatedAt
  }));
})
.catch(e => console.error('Error:', e.message));
