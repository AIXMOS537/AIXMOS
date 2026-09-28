/**
 * STICKS — scan Supabase + push overdue signals to GHL via TMMT OS.
 */

const fs = require('fs');
const path = require('path');
const { fetchOverdueAlerts } = require('./supabase-ops');
const { pushGhlOverdue } = require('./tmmt-api');
const state = require('../state');

function formatReport(alerts) {
  const lines = ['STICKS SLA REPORT', '═'.repeat(40)];
  const counts = { critical: 0, warning: 0, info: 0 };
  for (const a of alerts) counts[a.severity] = (counts[a.severity] || 0) + 1;
  lines.push(`Total: ${alerts.length} | 🔴 ${counts.critical || 0} | 🟡 ${counts.warning || 0} | 🟢 ${counts.info || 0}`);
  lines.push('');
  for (const a of alerts.slice(0, 40)) {
    const icon = a.severity === 'critical' ? '🔴' : a.severity === 'warning' ? '🟡' : '🟢';
    lines.push(`${icon} [${a.type}] ${a.customer_name || a.customer || a.email || a.ref_code || a.id}`);
    if (a.due_at) lines.push(`   due: ${a.due_at}`);
    if (a.hours_stale) lines.push(`   stale: ${a.hours_stale}h`);
    if (a.ghl_contact_id) lines.push(`   ghl: ${a.ghl_contact_id}`);
  }
  if (alerts.length > 40) lines.push(`… +${alerts.length - 40} more`);
  return lines.join('\n');
}

async function scanOverdue() {
  const alerts = await fetchOverdueAlerts();
  const report = formatReport(alerts);
  state.updateAgent('sticks', {
    last_mode: 'scan',
    last_output: report.substring(0, 2000),
    alert_count: alerts.length,
    scanned_at: new Date().toISOString(),
  });
  return { alerts, report };
}

async function pushOverdueToGhl({ dryRun = false } = {}) {
  const { alerts } = await scanOverdue();
  const paymentAlerts = alerts.filter(a => a.type === 'payment_overdue' && a.ghl_contact_id);
  const results = { sent: 0, skipped: 0, errors: [] };

  for (const a of paymentAlerts) {
    const payload = {
      contact_id: String(a.ghl_contact_id),
      customer_name: a.customer,
      amount_due: a.amount,
      due_date: a.due_date ? String(a.due_date).slice(0, 10) : undefined,
      source: 'sticks-agent',
    };
    if (dryRun) {
      results.skipped += 1;
      continue;
    }
    try {
      await pushGhlOverdue(payload);
      results.sent += 1;
    } catch (e) {
      results.errors.push({ contact_id: a.ghl_contact_id, error: e.message });
    }
  }

  // Ledger rows: try ghl_contacts lookup by email (optional second pass)
  const ledgerNoGhl = alerts.filter(a => a.type === 'ledger_overdue' && a.email);
  for (const a of ledgerNoGhl.slice(0, 20)) {
    results.skipped += 1; // logged in report; map email→ghl in Supabase or GHL_CONTACT_MAP_JSON
  }

  state.updateAgent('sticks', {
    last_mode: 'push_ghl',
    ghl_push: results,
  });

  return { alerts, results, report: formatReport(alerts) };
}

function saveReportToFile(report) {
  const out = path.join(__dirname, '..', 'logs');
  if (!fs.existsSync(out)) fs.mkdirSync(out, { recursive: true });
  const file = path.join(out, `sticks-${Date.now()}.txt`);
  fs.writeFileSync(file, report, 'utf8');
  return file;
}

module.exports = { scanOverdue, pushOverdueToGhl, formatReport, saveReportToFile };
