#!/usr/bin/env node
/**
 * CHUMMO Pipeline Runner — batch leads across pipelines, generate messages,
 * delegate heavy cases to MOOSE + BRAIN.
 *
 * Usage:
 *   node chummo-run.js --source leads.csv
 *   node chummo-run.js --source ../../AIX_AI_COMMAND_SYSTEM/airtable_templates/Leads_Deals.csv
 *   node chummo-run.js --source ./data/leads/ --limit 10
 *   node chummo-run.js --source ghl --dry-run
 *   node chummo-run.js --source leads.csv --pipeline credit --skip-closed
 */

const fs = require('fs');
const path = require('path');
const { chatCompletion, requireAiAvailable } = require('../files/llm-client');
const { saveAgentContext } = require('../files/shared-utils');
const { CHUMMO_SYSTEM } = require('./lib/prompts');
const { resolveMessagePlan, delegationPlan, normalize } = require('./lib/stage-map');
const { loadLeads } = require('./lib/lead-sources');
const { delegateToMoose, delegateToBrain, sleep } = require('./lib/delegation');

const OUT_DIR = path.join(__dirname, 'output', 'runs');

function parseArgs(argv) {
  const opts = {
    source: null,
    limit: 0,
    dryRun: false,
    skipClosed: false,
    pipelineFilter: null,
    delayMs: 1500,
    delegate: true,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--source' && argv[i + 1]) opts.source = argv[++i];
    else if (a === '--limit' && argv[i + 1]) opts.limit = parseInt(argv[++i], 10);
    else if (a === '--pipeline' && argv[i + 1]) opts.pipelineFilter = normalize(argv[++i]);
    else if (a === '--delay' && argv[i + 1]) opts.delayMs = parseInt(argv[++i], 10);
    else if (a === '--dry-run') opts.dryRun = true;
    else if (a === '--skip-closed') opts.skipClosed = true;
    else if (a === '--no-delegate') opts.delegate = false;
    else if (a === '--help') opts.help = true;
  }
  return opts;
}

function printHelp() {
  console.log(`
CHUMMO Pipeline Runner (Ollama-first)

  node chummo-run.js --source <file.csv|folder|ghl> [options]

Options:
  --limit N          Process at most N leads
  --pipeline NAME    Only leads matching pipeline/business line
  --skip-closed      Skip closed won/lost/inactive
  --dry-run          Plan only, no AI calls
  --no-delegate      CHUMMO messages only (no MOOSE/BRAIN)
  --delay MS         Pause between AI calls (default 1500)

Env (GHL):
  GHL_API_KEY, GHL_LOCATION_ID

Env (AI):
  AI_PROVIDER=auto, OLLAMA_BASE_URL, ANTHROPIC_API_KEY

Example:
  node chummo-run.js --source leads.csv --limit 20
`);
}

function firstName(lead) {
  if (lead.first_name) return lead.first_name;
  const n = lead.name || 'there';
  return n.split(/\s+/)[0];
}

function buildChummoPrompt(lead, plan) {
  const name = firstName(lead);
  return `Write a ${plan.label} message for this lead:
NAME: ${name}
PIPELINE: ${plan.pipeline}
STAGE: ${plan.stage}
SITUATION: ${lead.notes || 'Not provided'}
SERVICE INTEREST: ${lead.business_line || lead.pipeline || 'Not sure yet'}
NEXT ACTION: ${lead.next_action || 'Not specified'}
NEXT ACTION DUE: ${lead.next_action_due || 'Not specified'}
OWNER: ${lead.owner || 'Unassigned'}
ESTIMATED VALUE: ${lead.estimated_value || 'Unknown'}
EXTRA: Source=${lead.source || 'unknown'}
Write the message now. CHUMMO voice only.`;
}

function shouldSkip(lead, opts) {
  const stage = normalize(lead.status);
  if (opts.skipClosed && /closed|inactive|exited|lost/.test(stage)) return true;
  if (opts.pipelineFilter) {
    const p = normalize(lead.pipeline || lead.business_line);
    if (p && !p.includes(opts.pipelineFilter) && opts.pipelineFilter !== p) return true;
  }
  if (!lead.name && !lead.first_name && !lead.email && !lead.phone) return true;
  return false;
}

function writeOutputs(runId, results, summary) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const jsonPath = path.join(OUT_DIR, `${runId}.json`);
  const mdPath = path.join(OUT_DIR, `${runId}-review.md`);

  fs.writeFileSync(jsonPath, JSON.stringify({ runId, summary, results }, null, 2));

  const lines = [
    `# CHUMMO Pipeline Run — ${runId}`,
    '',
    `| Metric | Count |`,
    `|--------|------:|`,
    `| Processed | ${summary.processed} |`,
    `| Skipped | ${summary.skipped} |`,
    `| CHUMMO drafts | ${summary.drafted} |`,
    `| MOOSE delegated | ${summary.moose} |`,
    `| BRAIN delegated | ${summary.brain} |`,
    `| Errors | ${summary.errors} |`,
    '',
    '---',
    '',
  ];

  for (const r of results) {
    lines.push(`## ${r.lead.name || r.lead.id} — ${r.plan.pipeline} / ${r.plan.stage}`);
    lines.push(`- **Message type:** ${r.plan.label} (${r.plan.channel})`);
    if (r.delegation?.reasons?.length) {
      lines.push(`- **Delegation:** ${r.delegation.reasons.join(', ')}`);
    }
    lines.push('');
    if (r.error) {
      lines.push(`> Error: ${r.error}`);
    } else if (r.draft) {
      lines.push('### CHUMMO draft\n');
      lines.push('```');
      lines.push(r.draft);
      lines.push('```\n');
    }
    if (r.moose) {
      lines.push('### MOOSE\n');
      lines.push('```');
      lines.push(r.moose);
      lines.push('```\n');
    }
    if (r.brain) {
      lines.push('### BRAIN handoff\n');
      lines.push('```');
      lines.push(r.brain);
      lines.push('```\n');
    }
    lines.push('---\n');
  }

  fs.writeFileSync(mdPath, lines.join('\n'));
  return { jsonPath, mdPath };
}

async function main() {
  const opts = parseArgs(process.argv);
  if (opts.help || !opts.source) {
    printHelp();
    process.exit(opts.source ? 0 : 1);
  }

  const ai = await requireAiAvailable();
  console.log(`\nCHUMMO Pipeline Runner — AI: ${ai.status.active} (${ai.status.ollamaModel || 'cloud'})\n`);

  console.log(`Loading leads from: ${opts.source}`);
  const leads = await loadLeads(opts.source);
  console.log(`Found ${leads.length} lead(s)\n`);

  const runId = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const results = [];
  const summary = { processed: 0, skipped: 0, drafted: 0, moose: 0, brain: 0, errors: 0 };

  let count = 0;
  for (const lead of leads) {
    if (opts.limit && count >= opts.limit) break;
    if (shouldSkip(lead, opts)) {
      summary.skipped++;
      continue;
    }

    summary.processed++;
    count++;
    const plan = resolveMessagePlan(lead);
    const delegation = delegationPlan(lead);

    console.log(`[${count}] ${lead.name || lead.id} — ${plan.pipeline}/${plan.stage} → ${plan.label}`);

    if (opts.dryRun) {
      results.push({ lead, plan, delegation, draft: null, dryRun: true });
      if (delegation.moose) console.log('       ↳ would delegate MOOSE');
      if (delegation.brain) console.log('       ↳ would delegate BRAIN');
      continue;
    }

    const entry = { lead, plan, delegation, draft: null, moose: null, brain: null, error: null };

    try {
      const res = await chatCompletion({
        system: CHUMMO_SYSTEM,
        userMessage: buildChummoPrompt(lead, plan),
        maxTokens: 1000,
      });
      entry.draft = res.text;
      entry.provider = res.provider;
      summary.drafted++;

      saveAgentContext('CHUMMO', {
        lead: lead.name,
        type: plan.label,
        pipeline: plan.pipeline,
        stage: plan.stage,
        message: res.text,
        batchRunId: runId,
      });

      if (opts.delegate && delegation.moose) {
        await sleep(opts.delayMs);
        const moose = await delegateToMoose(lead, res.text, plan);
        entry.moose = moose.text;
        summary.moose++;
        saveAgentContext('moose', {
          lead: lead.name,
          pipeline: plan.pipeline,
          output: moose.text,
          batchRunId: runId,
        });
      }

      if (opts.delegate && delegation.brain) {
        await sleep(opts.delayMs);
        const brain = await delegateToBrain(lead, res.text, { text: entry.moose }, plan);
        entry.brain = brain.text;
        summary.brain++;
        saveAgentContext('brain', {
          lead: lead.name,
          pipeline: plan.pipeline,
          output: brain.text,
          batchRunId: runId,
        });
      }
    } catch (err) {
      entry.error = err.message;
      summary.errors++;
      console.log(`       ✖ ${err.message}`);
    }

    results.push(entry);
    if (!opts.dryRun) await sleep(opts.delayMs);
  }

  const paths = writeOutputs(runId, results, summary);
  console.log('\nDone.');
  console.log(`  Review: ${paths.mdPath}`);
  console.log(`  JSON:   ${paths.jsonPath}`);
  console.log(
    `  Summary: ${summary.drafted} drafts, ${summary.moose} moose, ${summary.brain} brain, ${summary.errors} errors, ${summary.skipped} skipped\n`
  );
}

main().catch(err => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
