#!/usr/bin/env node
/** One-time helper: mark phones as reminded today from a remind-overdue send log. */
const fs = require('fs');
const path = require('path');
const state = require('./state');
const { toE164 } = require('./lib/sender');

const logPath = process.argv[2] || path.join(__dirname, '..', 'ai-brain-setup', 'logs', 'step-Overdue-reminders-SEND.txt');
if (!fs.existsSync(logPath)) {
  console.error('Log not found:', logPath);
  process.exit(1);
}

const text = fs.readFileSync(logPath, 'utf8');
let count = 0;
for (const line of text.split('\n')) {
  const m = line.match(/^\s*SENT\s+(\+\d+)\s+(.+?)\s+\(via\s+(\w+)/i);
  if (!m) continue;
  const phone = toE164(m[1]);
  if (!phone) continue;
  if (state.wasRemindedToday(phone)) continue;
  state.recordReminder(phone, { name: m[2].trim(), channel: m[3], id: 'backfill' });
  count += 1;
  console.log('backfilled', phone, m[2].trim());
}
console.log(`Backfilled ${count} reminder(s) for ${state.reminderDayKey()}`);
