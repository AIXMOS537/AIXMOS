const path = require('path');
const { chatCompletion } = require(path.join(__dirname, '../../files/llm-client'));

const MOOSE_PATHWAY_SYSTEM = `You are MOOSE — the AIXMOS execution agent. You build client pathways after CHUMMO hands off a lead.

ABOUT AIXMOS:
- Workforce infrastructure for everyday entrepreneurs; founder Muhammad Taha
- Target: $10,000/month for every client; 90-day pathway standard
- Services: $97/mo Membership, $397 LLC, $500-$1K Credit Guidance (GUIDE), $3,750 Base Infrastructure, $7,500 Enterprise, $15K Car Rental in a Box, $25K E-Commerce, $50K Full Ecosystem

ORGANIZATION:
- OPERATOR: field contact, GHL logging, outbound, call prep
- EXECUTIVE: closing, onboarding, Level 3 escalations
- MOOSE: GHL calendar/automation setup, systems, sequences
- MUHAMMAD: Level 4 only — brief with proposed solution

MOOSE OUTPUT RULES:
- Battle plan only — numbered steps, owners, timing (TODAY / WITHIN 24HRS / THIS WEEK / MONTH 1)
- Every step names owner: OPERATOR / EXECUTIVE / MOOSE / MUHAMMAD
- GHL-specific actions (tags, pipelines, automations, calendar, nurture)
- Include exact CHUMMO script in step 2 when provided
- End with **MOOSE NOTE:** (3-5 bullet rules: status deadlines, nurture, daily check)
- No fluff. English only.`;

function buildPathwayPrompt(lead, chummoDraft, meta = {}) {
  const name = meta.firstName || lead.contact_name?.split(/\s+/)[0] || 'Lead';
  const lines = [
    'Generate a full ACTION PLAN: BUILD CLIENT PATHWAY (INSTIGATOR: CHUMMO HANDOFF).',
    '',
    'Use this exact structure:',
    '**ACTION PLAN: BUILD CLIENT PATHWAY (INSTIGATOR: CHUMMO HANDOFF)**',
    `**TARGET:** ${name} (${meta.source || lead.opportunity_name || 'Lead'})`,
    '**OWNER:** OPERATOR (Initial Contact) -> EXECUTIVE (Closing/Onboarding)',
    '**TIMING:** IMMEDIATE (TODAY)',
    '',
    'Then 7-9 numbered sections covering:',
    '1. CRITICAL DATA INTEGRATION (GHL tags, source, verify contact)',
    '2. IMMEDIATE OUTBOUND (CHUMMO script verbatim + 2hr follow-up protocol)',
    '3. CALENDAR INFRASTRUCTURE (MOOSE — GHL calendar, reminders, nurture if decline)',
    '4. CALL AGENDA & TOOLING (operator prep, upsell deck in pipeline)',
    '5. DURING THE CALL (diagnose, align, propose $3,750 base + credit guide)',
    '6. POST-CALL CONVERSION (proposal, invoices, abandoned cart SMS)',
    '7. ONBOARDING TRIGGER (payment → active client, portal, week 1 check-in)',
    '8. UPGRADE PATHWAY (month 1 conditions for higher tiers)',
    '9. ESCALATION PROTOCOL (Level 2 executive call if 3 failed booking attempts)',
    '**MOOSE NOTE:** cold nurture + daily 9AM pipeline check',
    '',
    'LEAD DATA:',
    `Name: ${lead.contact_name || name}`,
    `Phone: ${lead.phone || 'unknown'}`,
    `Email: ${lead.email || 'unknown'}`,
    `Status: ${lead.status || 'New Lead'}`,
    `Opportunity: ${lead.opportunity_name || '—'}`,
    `Priority: ${lead.priority_level || '—'}`,
    `Notes: ${lead.notes || meta.notes || '—'}`,
    `Business line: ${meta.businessLine || 'credit'}`,
    `Source channel: ${meta.source || 'Instagram'}`,
  ];

  if (chummoDraft) {
    lines.push('', 'CHUMMO HANDOFF MESSAGE (use verbatim in step 2):', '---', chummoDraft, '---');
  }

  lines.push('', 'Tailor tags, offers, and nurture to notes. If rental/dealer lead, adjust pipeline names accordingly.');
  return lines.join('\n');
}

async function generateClientPathway(lead, chummoDraft, meta = {}) {
  const res = await chatCompletion({
    system: MOOSE_PATHWAY_SYSTEM,
    userMessage: buildPathwayPrompt(lead, chummoDraft, meta),
    maxTokens: 2500,
  });
  return res.text.trim();
}

function extractChummoFromMarkdown(md) {
  const m = md.match(/## Draft \(CHUMMO[\s\S]*?```\n([\s\S]*?)```/);
  return m ? m[1].trim() : '';
}

function inferSource(lead) {
  const blob = `${lead.notes || ''} ${lead.opportunity_name || ''}`.toLowerCase();
  if (/instagram|ig\b/.test(blob)) return 'IG Lead';
  if (/whatsapp|wa\b/.test(blob)) return 'WhatsApp';
  if (/ghl|gohighlevel/.test(blob)) return 'GHL';
  if (/referral/.test(blob)) return 'Referral';
  return lead.opportunity_name || 'Inbound';
}

function inferBusinessLine(lead) {
  const blob = `${lead.notes || ''} ${lead.opportunity_name || ''}`.toLowerCase();
  if (/rental|turo|vehicle/.test(blob)) return 'rentals';
  if (/dealer|dealership/.test(blob)) return 'dealer';
  if (/credit|funding|llc/.test(blob)) return 'credit';
  return 'credit';
}

module.exports = {
  generateClientPathway,
  extractChummoFromMarkdown,
  inferSource,
  inferBusinessLine,
  MOOSE_PATHWAY_SYSTEM,
};
