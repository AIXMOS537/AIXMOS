#!/usr/bin/env node
/**
 * Batch: Supabase incoming_leads → CHUMMO draft + MOOSE client pathway (repeatable).
 *
 *   node chummo-draft-leads.js --limit 15
 *   node chummo-draft-leads.js --limit 10 --no-pathway   # CHUMMO only
 *   node chummo-draft-leads.js --pathway-only            # refresh MOOSE on today's files
 */

const fs = require('fs');
const path = require('path');
const { chatCompletion, requireAiAvailable } = require('../files/llm-client');
const { saveAgentContext } = require('../files/shared-utils');
const { CHUMMO_SYSTEM, MESSAGE_TYPES } = require('./chummo-system-prompt');
const {
  ROOT,
  loadProjectEnv,
  resolveSupabase,
  fetchIncomingLeads,
  firstName,
  slug,
} = require('./lib/supabase-leads');
const {
  generateClientPathway,
  extractChummoFromMarkdown,
  inferSource,
  inferBusinessLine,
} = require('./lib/moose-pathway');

const OUT_BASE = path.join(ROOT, 'TMMT MANAGEMENT/OPERATIONS/VA_LEAD_DRAFTS');

function parseArgs(argv) {
  const opts = {
    limit: 15,
    statuses: null,
    withPathway: true,
    pathwayOnly: false,
    delayMs: 2000,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--limit' && argv[i + 1]) opts.limit = parseInt(argv[++i], 10) || 15;
    else if (a === '--status' && argv[i + 1]) {
      opts.statuses = argv[++i].split(',').map(s => s.trim().toLowerCase());
    } else if (a === '--no-pathway') opts.withPathway = false;
    else if (a === '--pathway-only') {
      opts.pathwayOnly = true;
      opts.withPathway = true;
    } else if (a === '--delay' && argv[i + 1]) opts.delayMs = parseInt(argv[++i], 10);
  }
  return opts;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function pickMessageType(lead) {
  const status = String(lead.status || '').toLowerCase();
  const notes = String(lead.notes || '').toLowerCase();
  for (const m of MESSAGE_TYPES) {
    if (m.statuses?.some(s => status.includes(s) || notes.includes(s))) return m;
  }
  return MESSAGE_TYPES[0];
}

function buildUserPrompt(lead, msgType) {
  const name = firstName(lead.contact_name);
  return `Write a ${msgType.label} message for this lead:
NAME: ${name}
FULL NAME: ${lead.contact_name || 'Unknown'}
PHONE: ${lead.phone || 'Not provided'}
EMAIL: ${lead.email || 'Not provided'}
OPPORTUNITY: ${lead.opportunity_name || 'Rental inquiry'}
PRIORITY: ${lead.priority_level || 'Normal'}
PIPELINE STAGE: ${lead.status || 'New Lead'}
NOTES: ${lead.notes || 'None'}
Write the message now. CHUMMO voice only.`;
}

function buildLeadMarkdown(lead, msgType, message, pathway) {
  const sections = [
    `# ${lead.contact_name || 'Lead'} — ${msgType.label}`,
    '',
    '| Field | Value |',
    '|-------|-------|',
    `| Lead ID | ${lead.id} |`,
    `| Status | ${lead.status || '—'} |`,
    `| Phone | ${lead.phone || '—'} |`,
    `| Email | ${lead.email || '—'} |`,
    `| Priority | ${lead.priority_level || '—'} |`,
    '| VA role | **Pipeline & Sales** — CHUMMO send + MOOSE execute |',
    '',
    '## 1. Send this first (CHUMMO — approve before send)',
    '',
    '```',
    message,
    '```',
    '',
  ];

  if (pathway) {
    sections.push(
      '## 2. Execute this plan (MOOSE — Operator + Executive)',
      '',
      pathway,
      '',
      '### Operator checklist (today)',
      '',
      '- [ ] Log contact in GHL with tags from step 1',
      '- [ ] Send CHUMMO message (section 1)',
      '- [ ] Set follow-up task + 2hr reminder in GHL',
      '- [ ] Book or attempt book consultation calendar',
      '- [ ] Log outcome in shift template',
      ''
    );
  }

  sections.push('---', `*Generated ${new Date().toISOString()} · Do not auto-send*`, '');
  return sections.join('\n');
}

async function pathwayOnlyRun(opts) {
  const day = new Date().toISOString().slice(0, 10);
  const outDir = path.join(OUT_BASE, day);
  if (!fs.existsSync(outDir)) {
    console.log(`No folder for today: ${outDir}`);
    process.exit(0);
  }

  const files = fs.readdirSync(outDir).filter(f => f.endsWith('.md') && f !== 'INDEX.md');
  const limited = opts.limit ? files.slice(0, opts.limit) : files;
  console.log(`MOOSE pathways only → ${limited.length} file(s)\n`);

  for (const file of limited) {
    const filePath = path.join(outDir, file);
    const md = fs.readFileSync(filePath, 'utf8');
    const chummo = extractChummoFromMarkdown(md);
    const titleMatch = md.match(/^# (.+?) —/);
    const lead = {
      id: file.replace('.md', ''),
      contact_name: titleMatch ? titleMatch[1] : file,
      notes: '',
      status: 'New Lead',
    };
    process.stdout.write(`  ${lead.contact_name} pathway… `);
    try {
      const pathway = await generateClientPathway(lead, chummo, {
        firstName: firstName(lead.contact_name),
        source: inferSource(lead),
        businessLine: inferBusinessLine(lead),
      });
      const msgType = { label: 'First outreach — SMS' };
      const message = chummo || '[No CHUMMO draft in file]';
      fs.writeFileSync(filePath, buildLeadMarkdown(lead, msgType, message, pathway), 'utf8');
      console.log('done');
    } catch (err) {
      console.log(`fail: ${err.message}`);
    }
    await sleep(opts.delayMs);
  }
}

async function main() {
  const opts = parseArgs(process.argv);
  loadProjectEnv();

  const ai = await requireAiAvailable();
  console.log(`AI: ${ai.status.active}\n`);

  if (opts.pathwayOnly) {
    await pathwayOnlyRun(opts);
    return;
  }

  const sb = resolveSupabase();
  let leads = await fetchIncomingLeads(sb, opts.limit * 3);

  if (opts.statuses?.length) {
    leads = leads.filter(l =>
      opts.statuses.some(s => String(l.status || '').toLowerCase().includes(s))
    );
  }

  leads = leads.slice(0, opts.limit);
  if (leads.length === 0) {
    console.log('No leads matched. Check Supabase incoming_leads or --status filter.');
    process.exit(0);
  }

  const day = new Date().toISOString().slice(0, 10);
  const outDir = path.join(OUT_BASE, day);
  fs.mkdirSync(outDir, { recursive: true });

  const index = [];
  console.log(
    `Processing ${leads.length} leads → ${outDir}${opts.withPathway ? ' (CHUMMO + MOOSE)' : ' (CHUMMO only)'}\n`
  );

  for (const lead of leads) {
    const msgType = pickMessageType(lead);
    const name = firstName(lead.contact_name);
    process.stdout.write(`  ${name} chummo… `);

    let message = '';
    try {
      const res = await chatCompletion({
        system: CHUMMO_SYSTEM,
        userMessage: buildUserPrompt(lead, msgType),
        maxTokens: 800,
      });
      message = res.text.trim();
      saveAgentContext('CHUMMO', {
        lead: lead.contact_name,
        type: msgType.label,
        message,
        batchDay: day,
      });
    } catch (err) {
      message = `[DRAFT FAILED: ${err.message}]`;
    }
    console.log('ok');

    let pathway = null;
    if (opts.withPathway && !message.startsWith('[DRAFT FAILED')) {
      process.stdout.write(`       moose pathway… `);
      await sleep(opts.delayMs);
      try {
        pathway = await generateClientPathway(lead, message, {
          firstName: name,
          source: inferSource(lead),
          businessLine: inferBusinessLine(lead),
          notes: lead.notes,
        });
        saveAgentContext('MOOSE', {
          lead: lead.contact_name,
          mode: 'pathway',
          label: 'Build client pathway',
          output: pathway,
          batchDay: day,
        });
        console.log('ok');
      } catch (err) {
        pathway = `*[PATHWAY FAILED: ${err.message}]*`;
        console.log('fail');
      }
    }

    const fileName = `${slug(lead.contact_name)}-${String(lead.id).slice(0, 8)}.md`;
    fs.writeFileSync(
      path.join(outDir, fileName),
      buildLeadMarkdown(lead, msgType, message, pathway),
      'utf8'
    );
    index.push({
      name: lead.contact_name,
      file: fileName,
      type: msgType.label,
      status: lead.status,
      pathway: !!pathway && !pathway.startsWith('*['),
    });
  }

  const indexMd = [
    `# VA Lead Drafts — ${day}`,
    '',
    `Generated **${index.length}** packs (CHUMMO message + MOOSE action plan).`,
    '',
    '| Lead | Status | CHUMMO | MOOSE plan | File |',
    '|------|--------|--------|------------|------|',
    ...index.map(
      r =>
        `| ${r.name || '—'} | ${r.status || '—'} | ${r.type} | ${r.pathway ? '✓' : '—'} | [${r.file}](./${r.file}) |`
    ),
    '',
    '**VA flow:** Section 1 → send after approval. Section 2 → operator executes checklist + numbered plan.',
    '',
    '**Owner regenerate:** `node chummo-draft-leads.js --limit 15` or `--pathway-only` to refresh MOOSE only.',
    '',
  ].join('\n');

  fs.writeFileSync(path.join(outDir, 'INDEX.md'), indexMd, 'utf8');
  console.log(`\n✓ Done — ${index.length} leads → INDEX.md`);
}

main().catch(err => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
