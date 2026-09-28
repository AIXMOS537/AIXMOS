/**
 * Supabase REST queries for STICKS overdue / SLA alerts.
 */

function supabaseConfig() {
  const url = (process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || '').replace(/\/$/, '');
  const key =
    process.env.SUPABASE_SERVICE_ROLE_KEY ||
    process.env.SUPABASE_SERVICE_KEY ||
    '';
  if (!url || !key) {
    throw new Error('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required');
  }
  return { url, key };
}

async function restGet(table, query = '') {
  const { url, key } = supabaseConfig();
  const q = query.startsWith('?') ? query : query ? `?${query}` : '';
  const res = await fetch(`${url}/rest/v1/${table}${q}`, {
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      Prefer: 'return=representation',
    },
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : [];
  } catch {
    throw new Error(`Supabase parse error: ${text.slice(0, 200)}`);
  }
  if (!res.ok) {
    throw new Error(data.message || data.error || `Supabase ${res.status}`);
  }
  return data;
}

async function safeGet(table, query) {
  try {
    return await restGet(table, query);
  } catch (e) {
    if (/relation.*does not exist|42P01/i.test(String(e.message))) return [];
    throw e;
  }
}

function isPastIso(iso) {
  if (!iso) return false;
  return new Date(iso).getTime() < Date.now();
}

function hoursAgo(iso) {
  if (!iso) return 9999;
  return (Date.now() - new Date(iso).getTime()) / 3600000;
}

/**
 * Collect overdue / at-risk rows for STICKS dashboard.
 */
async function fetchOverdueAlerts() {
  const now = new Date().toISOString();
  const alerts = [];

  // rental_ledger — pending/processing past due
  const ledger = await safeGet(
    'rental_ledger',
    'select=id,customer_email,booking_id,case_id,title,status,amount_cents,due_at,created_at&status=in.(pending,processing)&due_at=lt.' +
      encodeURIComponent(now) +
      '&order=due_at.asc&limit=100'
  );
  for (const row of ledger) {
    alerts.push({
      type: 'ledger_overdue',
      severity: 'critical',
      email: row.customer_email,
      title: row.title,
      due_at: row.due_at,
      amount_cents: row.amount_cents,
      booking_id: row.booking_id,
      case_id: row.case_id,
      id: row.id,
    });
  }

  // customer_payments — Overdue status (venture table)
  const payments = await safeGet(
    'customer_payments',
    'select=*&limit=200'
  );
  for (const row of payments) {
    const status = String(row.payment_status || row['Payment Status'] || '').toLowerCase();
    if (status === 'overdue') {
      alerts.push({
        type: 'payment_overdue',
        severity: 'critical',
        customer: row.customer || row.Customer,
        ghl_contact_id: row.ghl_contact_id || row['GHL Contact ID'],
        amount: row.amount_past_due || row.amout_past_due || row.amount || row.Amount,
        due_date: row.next_payment_due_date || row['Next Payment Due Date'],
        id: row.id,
        raw: row,
      });
    }
  }

  // cases — not closed/completed + stale > 24h
  const cases = await safeGet(
    'cases',
    'select=id,ref_code,customer_name,customer_email,status,updated_at,created_at&status=not.in.(completed,closed)&order=updated_at.asc&limit=100'
  );
  for (const row of cases) {
    const h = hoursAgo(row.updated_at);
    if (h >= 24) {
      alerts.push({
        type: 'case_stale',
        severity: h >= 72 ? 'critical' : 'warning',
        ref_code: row.ref_code,
        customer_name: row.customer_name,
        customer_email: row.customer_email,
        status: row.status,
        hours_stale: Math.round(h),
        id: row.id,
      });
    }
  }

  // client_alerts — unacknowledged
  const clientAlerts = await safeGet(
    'client_alerts',
    'select=id,customer_email,ghl_contact_id,alert_type,title,message,priority,due_at,created_at&acknowledged_at=is.null&order=created_at.asc&limit=50'
  );
  for (const row of clientAlerts) {
    const overdue = isPastIso(row.due_at);
    alerts.push({
      type: 'client_alert',
      severity: overdue ? 'critical' : row.priority === 'high' ? 'warning' : 'info',
      email: row.customer_email,
      ghl_contact_id: row.ghl_contact_id,
      title: row.title,
      message: row.message,
      due_at: row.due_at,
      id: row.id,
    });
  }

  // ghl_form_submissions — last 48h without case (needs response)
  const since = new Date(Date.now() - 48 * 3600000).toISOString();
  const forms = await safeGet(
    'ghl_form_submissions',
    `select=id,ghl_contact_id,form_name,created_at,case_id&case_id=is.null&created_at=gte.${encodeURIComponent(since)}&order=created_at.asc&limit=50`
  );
  for (const row of forms) {
    alerts.push({
      type: 'ghl_form_unlinked',
      severity: 'warning',
      ghl_contact_id: row.ghl_contact_id,
      form_name: row.form_name,
      created_at: row.created_at,
      id: row.id,
    });
  }

  // bookings — inquiry/quoted older than 4h (customer waiting)
  const bookingCutoff = new Date(Date.now() - 4 * 3600000).toISOString();
  const bookings = await safeGet(
    'bookings',
    `select=id,ref_code,customer_name,customer_email,customer_phone,status,created_at,updated_at&status=in.(inquiry,quoted)&created_at=lt.${encodeURIComponent(bookingCutoff)}&order=created_at.asc&limit=50`
  );
  for (const row of bookings) {
    alerts.push({
      type: 'booking_waiting',
      severity: 'warning',
      ref_code: row.ref_code,
      customer_name: row.customer_name,
      customer_email: row.customer_email,
      status: row.status,
      created_at: row.created_at,
      id: row.id,
    });
  }

  alerts.sort((a, b) => {
    const rank = { critical: 0, warning: 1, info: 2 };
    return (rank[a.severity] ?? 9) - (rank[b.severity] ?? 9);
  });

  return alerts;
}

module.exports = { fetchOverdueAlerts, restGet, safeGet, supabaseConfig };
