const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../../..');

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const raw = fs.readFileSync(filePath, 'utf8');
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const i = t.indexOf('=');
    if (i < 1) continue;
    const key = t.slice(0, i).trim();
    let val = t.slice(i + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = val;
  }
}

function loadProjectEnv() {
  loadEnvFile(path.join(ROOT, 'TMMT MANAGEMENT/tmmt-os/.env.local'));
  loadEnvFile(path.join(ROOT, 'AIX_AI_COMMAND_SYSTEM/.env'));
}

function resolveSupabase() {
  const url =
    process.env.COMMAND_CENTER_SUPABASE_URL ||
    process.env.SUPABASE_URL ||
    process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key =
    process.env.COMMAND_CENTER_SUPABASE_SERVICE_KEY ||
    process.env.SUPABASE_KEY ||
    process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error(
      'Missing Supabase credentials in TMMT MANAGEMENT/tmmt-os/.env.local'
    );
  }
  return { url: url.replace(/\/$/, ''), key };
}

async function fetchIncomingLeads({ url, key }, limit) {
  const params = new URLSearchParams({
    select:
      'id,contact_name,phone,email,opportunity_name,priority_level,notes,status,created_on',
    order: 'created_on.desc',
    limit: String(Math.min(limit * 3, 100)),
  });
  const res = await fetch(`${url}/rest/v1/incoming_leads?${params}`, {
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      Accept: 'application/json',
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Supabase ${res.status}: ${err.slice(0, 300)}`);
  }
  return res.json();
}

function firstName(contactName) {
  if (!contactName) return 'there';
  return String(contactName).trim().split(/\s+/)[0] || 'there';
}

function slug(s) {
  return String(s || 'lead')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40);
}

module.exports = {
  ROOT,
  loadProjectEnv,
  resolveSupabase,
  fetchIncomingLeads,
  firstName,
  slug,
};
