const fs = require('fs');
const path = require('path');

function parseCsvLine(line) {
  const out = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else inQuotes = !inQuotes;
    } else if (ch === ',' && !inQuotes) {
      out.push(cur.trim());
      cur = '';
    } else cur += ch;
  }
  out.push(cur.trim());
  return out;
}

function loadCsv(filePath) {
  const text = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (lines.length < 2) return [];
  const headers = parseCsvLine(lines[0]).map(h => h.trim());
  return lines.slice(1).map(line => {
    const cells = parseCsvLine(line);
    /** @type {Record<string, string>} */
    const row = {};
    headers.forEach((h, i) => {
      row[h] = cells[i] ?? '';
    });
    return normalizeLeadRow(row);
  });
}

function normalizeLeadRow(row) {
  const get = (...keys) => {
    for (const k of keys) {
      if (row[k] != null && String(row[k]).trim()) return String(row[k]).trim();
      const found = Object.keys(row).find(
        rk => rk.toLowerCase().replace(/\s+/g, ' ') === k.toLowerCase()
      );
      if (found && String(row[found]).trim()) return String(row[found]).trim();
    }
    return '';
  };

  return {
    id: get('id', 'Lead ID', 'ghl_contact_id', 'Contact ID') || `row-${Math.random().toString(36).slice(2, 9)}`,
    name: get('name', 'Lead Name', 'contact_name', 'customer_name', 'First Name', 'full_name'),
    first_name: get('first_name', 'First Name'),
    email: get('email', 'Email', 'customer_email'),
    phone: get('phone', 'Phone', 'customer_phone'),
    status: get('status', 'Status', 'stage', 'ghl_stage', 'Pipeline Stage'),
    pipeline: get('pipeline', 'pipeline_name', 'Pipeline', 'business_line', 'Business Line'),
    business_line: get('business_line', 'Business Line'),
    source: get('source', 'Source'),
    owner: get('owner', 'Owner'),
    estimated_value: get('estimated_value', 'Estimated Value', 'value'),
    next_action: get('next_action', 'Next Action'),
    next_action_due: get('next_action_due', 'Next Action Due'),
    last_touch_date: get('last_touch_date', 'Last Touch Date'),
    notes: get('notes', 'Notes', 'Objection'),
    raw: row,
  };
}

function loadJson(filePath) {
  const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const list = Array.isArray(data) ? data : data.leads || data.contacts || data.records || [];
  return list.map(row => (row.raw ? row : normalizeLeadRow(row)));
}

async function loadFromGhl(env) {
  const apiKey = env.GHL_API_KEY || env.GOHIGHLEVEL_API_KEY;
  const locationId = env.GHL_LOCATION_ID;
  if (!apiKey || !locationId) {
    throw new Error('GHL_API_KEY and GHL_LOCATION_ID required for --source ghl');
  }

  const base = 'https://services.leadconnectorhq.com';
  const headers = {
    Authorization: `Bearer ${apiKey}`,
    Version: '2021-07-28',
    Accept: 'application/json',
  };

  const leads = [];
  let url = `${base}/opportunities/search?location_id=${locationId}&limit=100`;
  let pages = 0;

  while (url && pages < 20) {
    const res = await fetch(url, { headers });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`GHL API ${res.status}: ${t.slice(0, 300)}`);
    }
    const body = await res.json();
    const opps = body.opportunities || body.data || [];
    for (const o of opps) {
      leads.push(
        normalizeLeadRow({
          id: o.id || o.contactId,
          name: o.name || o.contact?.name || o.contactName,
          email: o.contact?.email,
          phone: o.contact?.phone,
          status: o.status || o.pipelineStage || o.stage,
          pipeline: o.pipelineName || o.pipeline,
          estimated_value: o.monetaryValue ?? o.value,
          notes: o.notes,
        })
      );
    }
    url = body.meta?.nextPageUrl || null;
    pages++;
  }

  return leads;
}

function loadLeads(source, env = process.env) {
  const resolved = path.resolve(source);

  if (source === 'ghl' || source === '--ghl') {
    return loadFromGhl(env);
  }

  if (!fs.existsSync(resolved)) {
    throw new Error(`Source not found: ${resolved}`);
  }

  const stat = fs.statSync(resolved);
  if (stat.isDirectory()) {
    const files = fs
      .readdirSync(resolved)
      .filter(f => /\.(csv|json)$/i.test(f))
      .map(f => path.join(resolved, f));
    return files.flatMap(f => (f.endsWith('.json') ? loadJson(f) : loadCsv(f)));
  }

  if (resolved.endsWith('.json')) return loadJson(resolved);
  if (resolved.endsWith('.csv')) return loadCsv(resolved);

  throw new Error('Source must be .csv, .json, a folder of those, or ghl');
}

module.exports = { loadLeads, normalizeLeadRow, loadCsv };
