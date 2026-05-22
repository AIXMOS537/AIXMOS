#!/usr/bin/env node
/**
 * CHUMMO <-> GHL webhook bridge.
 *
 * GHL workflow fires HTTP POST -> this server -> calls AIXMOS agent (via lib/llm.js)
 * with the right system prompt -> returns the drafted message as JSON.
 *
 * GHL then writes the draft into a custom field on the contact (the team approves
 * and sends from GHL, keeping outbound at Level A per policy).
 *
 *   POST /draft           body: { agent, channel, context }  -> generic
 *   POST /draft/sms       body: { agent?, context }          -> shortcut, defaults chummo
 *   POST /draft/email     body: { agent?, context }          -> shortcut, defaults chummo
 *   GET  /health
 *
 * Auth: X-Webhook-Secret header must equal env GHL_WEBHOOK_SHARED_SECRET.
 *
 * Env:
 *   PORT                            default 4099
 *   GHL_WEBHOOK_SHARED_SECRET       required (any random 32+ chars)
 *   AIXMOS_LLM_BACKEND              claude | ollama | auto (inherits from agent network)
 *   ANTHROPIC_API_KEY               required if backend is claude/auto
 *   AIXMOS_AGENT_NETWORK_ROOT       default ../../  (path to the AIXMOS install root)
 *   CHUMMO_WEBHOOK_LOG_DIR          default ./logs
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = process.env.AIXMOS_AGENT_NETWORK_ROOT
  ? path.resolve(process.env.AIXMOS_AGENT_NETWORK_ROOT)
  : path.resolve(__dirname, '..', '..', '..');

const { generate } = require(path.join(ROOT, 'lib', 'llm'));
const prompts = require(path.join(ROOT, 'agents', 'prompts'));
const { loadAixmosEnv } = require(path.join(ROOT, 'lib', 'env'));
loadAixmosEnv();

const PORT = parseInt(process.env.PORT || '4099', 10);
const SHARED_SECRET = process.env.GHL_WEBHOOK_SHARED_SECRET || '';
const LOG_DIR = process.env.CHUMMO_WEBHOOK_LOG_DIR || path.join(__dirname, 'logs');
if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

const VALID_AGENTS = Object.keys(prompts);
const VALID_CHANNELS = new Set(['sms', 'email', 'dm', 'voicemail_script']);

function log(level, msg, extra) {
  const line = JSON.stringify({
    t: new Date().toISOString(),
    level,
    msg,
    ...(extra || {}),
  });
  console.log(line);
  const file = path.join(LOG_DIR, `chummo-ghl-${new Date().toISOString().slice(0, 10)}.log`);
  try { fs.appendFileSync(file, line + '\n'); } catch {}
}

function json(res, code, body) {
  const payload = JSON.stringify(body);
  res.writeHead(code, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

async function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on('data', c => {
      chunks.push(c);
      total += c.length;
      if (total > 200_000) {
        reject(new Error('payload too large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (chunks.length === 0) return resolve({});
      try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
      catch (e) { reject(new Error('invalid JSON: ' + e.message)); }
    });
    req.on('error', reject);
  });
}

function authed(req) {
  if (!SHARED_SECRET) return false;
  const got = (req.headers['x-webhook-secret'] || '').toString();
  return got === SHARED_SECRET;
}

function buildPrompt({ agent, channel, context }) {
  const ctx = context || {};
  const lines = [];
  lines.push(`CHANNEL: ${channel}`);
  if (ctx.first_name) lines.push(`NAME: ${ctx.first_name}`);
  if (ctx.last_name) lines.push(`LAST: ${ctx.last_name}`);
  if (ctx.vertical) lines.push(`VERTICAL: ${ctx.vertical}`);
  if (ctx.geo) lines.push(`GEO: ${ctx.geo}`);
  if (ctx.lifecycle) lines.push(`LIFECYCLE: ${ctx.lifecycle}`);
  if (ctx.source) lines.push(`SOURCE: ${ctx.source}`);
  if (ctx.last_action) lines.push(`LAST ACTION: ${ctx.last_action}`);
  if (ctx.score_baseline != null) lines.push(`SCORE BASELINE: ${ctx.score_baseline}`);
  if (ctx.last_score != null) lines.push(`LAST SCORE: ${ctx.last_score}`);
  if (ctx.intent) lines.push(`INTENT: ${ctx.intent}`);
  if (ctx.notes) lines.push(`NOTES: ${ctx.notes}`);
  if (ctx.offer) lines.push(`OFFER: ${ctx.offer}`);
  else lines.push(`OFFER: $97/mo AIXMOS membership — free credit repair for life + 10-agent AIXMOS network access. $7 for 14-day trial.`);
  lines.push('');
  if (channel === 'sms') {
    lines.push(`Write ONE SMS only. Under 160 chars. Strict ${agent.toUpperCase()} voice. No links unless OFFER explicitly says to include one. Output only the SMS.`);
  } else if (channel === 'email') {
    lines.push(`Write ONE email. Subject line first, blank line, then body. 3 short paragraphs max. Strict ${agent.toUpperCase()} voice. Output only the email.`);
  } else if (channel === 'dm') {
    lines.push(`Write ONE DM under 200 chars. Strict ${agent.toUpperCase()} voice. Output only the DM.`);
  } else if (channel === 'voicemail_script') {
    lines.push(`Write a voicemail script under 30 seconds spoken. Conversational. Output only the script.`);
  }
  return lines.join('\n');
}

async function handleDraft(req, res, defaults = {}) {
  if (!authed(req)) { log('warn', 'auth_failed', { ip: req.socket.remoteAddress }); return json(res, 401, { error: 'unauthorized' }); }
  let body;
  try { body = await readBody(req); } catch (e) { return json(res, 400, { error: e.message }); }

  const agent = (body.agent || defaults.agent || 'chummo').toLowerCase();
  const channel = (body.channel || defaults.channel || 'sms').toLowerCase();
  const context = body.context || {};

  if (!VALID_AGENTS.includes(agent)) {
    return json(res, 400, { error: `unknown agent: ${agent}`, valid: VALID_AGENTS });
  }
  if (!VALID_CHANNELS.has(channel)) {
    return json(res, 400, { error: `unknown channel: ${channel}`, valid: Array.from(VALID_CHANNELS) });
  }

  const system = prompts[agent];
  const userPrompt = buildPrompt({ agent, channel, context });
  const maxTokens = channel === 'sms' || channel === 'dm' ? 250 : 700;

  const started = Date.now();
  try {
    const draft = await generate({ system, prompt: userPrompt, maxTokens });
    const trimmed = (draft || '').trim();
    const len = trimmed.length;
    const ok = channel === 'sms' ? len > 0 && len <= 320 : len > 0;
    const took_ms = Date.now() - started;
    log('info', 'draft_ok', { agent, channel, len, took_ms, vertical: context.vertical, lifecycle: context.lifecycle });
    return json(res, 200, {
      draft: trimmed,
      length: len,
      length_ok: ok,
      agent,
      channel,
      backend: (process.env.AIXMOS_LLM_BACKEND || 'claude').toLowerCase(),
      took_ms,
    });
  } catch (err) {
    const took_ms = Date.now() - started;
    log('error', 'draft_failed', { agent, channel, took_ms, error: err.message });
    return json(res, 502, { error: err.message, agent, channel });
  }
}

const server = http.createServer(async (req, res) => {
  const url = req.url || '/';

  if (req.method === 'GET' && (url === '/health' || url === '/')) {
    return json(res, 200, {
      ok: true,
      service: 'chummo-ghl-webhook',
      version: '1.0.0',
      backend: (process.env.AIXMOS_LLM_BACKEND || 'claude').toLowerCase(),
      agents: VALID_AGENTS,
    });
  }

  if (req.method === 'POST' && url === '/draft') return handleDraft(req, res);
  if (req.method === 'POST' && url === '/draft/sms') return handleDraft(req, res, { channel: 'sms' });
  if (req.method === 'POST' && url === '/draft/email') return handleDraft(req, res, { channel: 'email' });
  if (req.method === 'POST' && url === '/draft/dm') return handleDraft(req, res, { channel: 'dm' });

  return json(res, 404, { error: 'not_found', path: url, method: req.method });
});

server.listen(PORT, () => {
  log('info', 'started', { port: PORT, root: ROOT, agents: VALID_AGENTS.length, has_secret: !!SHARED_SECRET });
  if (!SHARED_SECRET) {
    console.error('\nWARNING: GHL_WEBHOOK_SHARED_SECRET is not set — all requests will be rejected.\n');
  }
});

process.on('SIGINT', () => { log('info', 'shutdown', { signal: 'SIGINT' }); process.exit(0); });
process.on('SIGTERM', () => { log('info', 'shutdown', { signal: 'SIGTERM' }); process.exit(0); });
