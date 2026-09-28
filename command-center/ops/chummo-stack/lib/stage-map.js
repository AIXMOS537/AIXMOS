/**
 * Map CRM pipeline + stage → CHUMMO message type + optional agent delegation.
 * Keys are normalized: lowercase, collapsed spaces.
 */

const MESSAGE_TYPES = {
  first_sms: 'First outreach — SMS',
  first_email: 'First outreach — Email',
  followup_sms: 'Follow-up — SMS',
  postcall_email: 'Post-call recap — Email',
  payment_sms: 'Payment reminder — SMS',
  upgrade_email: 'Upgrade conversation — Email',
  reengage_sms: 'Re-engagement — SMS',
  referral_sms: 'Referral ask — SMS',
  welcome_msg: 'Welcome — after payment',
  operator_invite: 'Operator invite — Email',
};

function normalize(s) {
  return String(s || '')
    .toLowerCase()
    .trim()
    .replace(/[_/]+/g, ' ')
    .replace(/\s+/g, ' ');
}

/** @type {Record<string, { key: keyof typeof MESSAGE_TYPES, channel: 'sms'|'email' }>} */
const STAGE_MAP = {
  // AIX / credit corporate funnel
  'new lead': { key: 'first_sms', channel: 'sms' },
  contacted: { key: 'followup_sms', channel: 'sms' },
  'scorecard completed': { key: 'followup_sms', channel: 'sms' },
  'appointment booked': { key: 'followup_sms', channel: 'sms' },
  'call booked': { key: 'followup_sms', channel: 'sms' },
  'no-show': { key: 'reengage_sms', channel: 'sms' },
  qualified: { key: 'postcall_email', channel: 'email' },
  'consultation completed': { key: 'postcall_email', channel: 'email' },
  'not qualified': { key: 'reengage_sms', channel: 'sms' },
  'proposal sent': { key: 'upgrade_email', channel: 'email' },
  negotiation: { key: 'upgrade_email', channel: 'email' },
  'contract sent': { key: 'upgrade_email', channel: 'email' },
  'paid onboarded': { key: 'welcome_msg', channel: 'sms' },
  'payment received': { key: 'welcome_msg', channel: 'sms' },
  'closed won': { key: 'welcome_msg', channel: 'sms' },
  onboarding: { key: 'welcome_msg', channel: 'sms' },
  'closed lost': { key: 'reengage_sms', channel: 'sms' },
  'closed inactive': { key: 'reengage_sms', channel: 'sms' },
  paused: { key: 'reengage_sms', channel: 'sms' },
  exited: { key: 'reengage_sms', channel: 'sms' },
  // Rental / GHL rental stages
  inquiry: { key: 'first_sms', channel: 'sms' },
  qualifying: { key: 'followup_sms', channel: 'sms' },
  'payment pending': { key: 'payment_sms', channel: 'sms' },
  booked: { key: 'welcome_msg', channel: 'sms' },
  // Dealer pipeline
  'appointment set': { key: 'followup_sms', channel: 'sms' },
  showed: { key: 'postcall_email', channel: 'email' },
  'application in': { key: 'upgrade_email', channel: 'email' },
  'approved conditional': { key: 'upgrade_email', channel: 'email' },
  'sold placed': { key: 'welcome_msg', channel: 'sms' },
  lost: { key: 'reengage_sms', channel: 'sms' },
  // Operator / partner
  'operator candidate': { key: 'operator_invite', channel: 'email' },
  'partner candidate': { key: 'operator_invite', channel: 'email' },
  'upgrade ready': { key: 'upgrade_email', channel: 'email' },
};

const PIPELINE_PREFIX = {
  rentals: 'rental',
  rental: 'rental',
  dealer: 'dealer',
  'dealer sales': 'dealer',
  credit: 'credit',
  membership: 'credit',
  aixmos: 'credit',
};

const DEFAULT_MESSAGE = { key: 'followup_sms', channel: 'sms' };

function parseEstimatedValue(lead) {
  const raw = lead.estimated_value ?? lead.value ?? lead['Estimated Value'] ?? 0;
  const n = parseFloat(String(raw).replace(/[^0-9.]/g, ''));
  return Number.isFinite(n) ? n : 0;
}

function isOverdue(dueStr) {
  const m = String(dueStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return false;
  const due = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return due < today;
}

function resolveMessagePlan(lead) {
  const pipeline = normalize(lead.pipeline || lead.pipeline_name || lead.business_line || lead['Business Line']);
  const stage = normalize(lead.status || lead.stage || lead.ghl_stage || lead['Status']);
  const prefixed = pipeline ? `${PIPELINE_PREFIX[pipeline] || pipeline}::${stage}` : '';
  const plan =
    (prefixed && STAGE_MAP[prefixed]) ||
    STAGE_MAP[stage] ||
    DEFAULT_MESSAGE;
  return {
    ...plan,
    label: MESSAGE_TYPES[plan.key],
    stage,
    pipeline: pipeline || 'default',
  };
}

function delegationPlan(lead) {
  const stage = normalize(lead.status || lead.stage || lead['Status']);
  const value = parseEstimatedValue(lead);
  const notes = String(lead.notes || lead.Notes || '');
  const overdue = lead.next_action_due || lead['Next Action Due'];
  const daysSinceTouch = lead.last_touch_date || lead['Last Touch Date'];

  const reasons = [];
  let moose = false;
  let brain = false;

  if (value >= 3750) {
    moose = true;
    reasons.push(`high_value:${value}`);
  }
  if (
    ['negotiation', 'proposal sent', 'contract sent', 'funding denied rework', 'escalation'].includes(stage)
  ) {
    moose = true;
    reasons.push(`stage:${stage}`);
  }
  if (/escalat|complaint|legal|stuck|chargeback|refund/i.test(notes)) {
    moose = true;
    brain = true;
    reasons.push('notes_flag');
  }
  if (isOverdue(overdue) && stage !== 'closed won' && stage !== 'closed lost') {
    moose = true;
    reasons.push('overdue_next_action');
  }
  if (value >= 15000 || (moose && /multiple|partnership|enterprise/i.test(notes))) {
    brain = true;
    reasons.push('brain_complex');
  }

  return { moose, brain, reasons };
}

module.exports = {
  MESSAGE_TYPES,
  normalize,
  resolveMessagePlan,
  delegationPlan,
  parseEstimatedValue,
};
