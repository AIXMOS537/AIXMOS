/**
 * Multi-backend LLM abstraction for AIXMOS agents.
 *
 *   AIXMOS_LLM_BACKEND=claude   (default) — Anthropic cloud API (DIRECT, uncapped)
 *   AIXMOS_LLM_BACKEND=ollama            — local Ollama runtime
 *   AIXMOS_LLM_BACKEND=auto              — try Claude, fall back to Ollama
 *   AIXMOS_LLM_BACKEND=gateway           — route via aixmos-gateway (Cloudflare Worker).
 *                                          Spend is CAPPED per-role server-side; out of
 *                                          tokens auto-drops to free Ollama/Workers-AI.
 *                                          Preferred for routine agent traffic = ~$0.
 *
 * Tunables:
 *   AIXMOS_MODEL           Claude model id  (default claude-sonnet-4-6)
 *   OLLAMA_MODEL           Ollama model tag (default llama3.1:8b)
 *   OLLAMA_HOST            Ollama base URL  (default http://localhost:11434)
 *   AIXMOS_GATEWAY_URL     Gateway base URL (e.g. https://aixmos-gateway.<acct>.workers.dev)
 *   AIXMOS_GATEWAY_SECRET  Per-role secret; keep in ~/.config/tmmt/*.env, NEVER in the repo
 *   AIXMOS_GATEWAY_TIER    Requested lane: free|haiku|sonnet|opus (default free = $0)
 */

const { loadAixmosEnv } = require('./env');

let Anthropic;
try { Anthropic = require('@anthropic-ai/sdk'); } catch { /* optional in offline-only mode */ }

const DEFAULT_CLAUDE_MODEL = () => process.env.AIXMOS_MODEL || 'claude-sonnet-4-6';
const DEFAULT_OLLAMA_MODEL = () => process.env.OLLAMA_MODEL || 'llama3.1:8b';
const OLLAMA_HOST = () => (process.env.OLLAMA_HOST || 'http://localhost:11434').replace(/\/$/, '');
const GATEWAY_URL = () => (process.env.AIXMOS_GATEWAY_URL || '').replace(/\/$/, '');
const GATEWAY_TIER = () => process.env.AIXMOS_GATEWAY_TIER || 'free';

function backend() {
  return (process.env.AIXMOS_LLM_BACKEND || 'claude').toLowerCase();
}

async function callClaude({ system, prompt, maxTokens, model }) {
  loadAixmosEnv();
  if (!Anthropic) throw new Error('Anthropic SDK missing — run: npm install @anthropic-ai/sdk');
  if (!process.env.ANTHROPIC_API_KEY) throw new Error('ANTHROPIC_API_KEY is not set');
  const client = new Anthropic.default();
  const res = await client.messages.create({
    model: model || DEFAULT_CLAUDE_MODEL(),
    max_tokens: maxTokens || 2000,
    system,
    messages: [{ role: 'user', content: prompt }],
  });
  return res.content[0].text;
}

async function callOllama({ system, prompt, maxTokens, model }) {
  loadAixmosEnv();
  if (typeof fetch !== 'function') {
    throw new Error('global fetch missing — Ollama backend needs Node.js 18+');
  }
  const url = `${OLLAMA_HOST()}/api/chat`;
  const body = {
    model: model || DEFAULT_OLLAMA_MODEL(),
    messages: [
      ...(system ? [{ role: 'system', content: system }] : []),
      { role: 'user', content: prompt },
    ],
    stream: false,
    options: { num_predict: maxTokens || 2000 },
  };
  let res;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw new Error(`Ollama not reachable at ${OLLAMA_HOST()} — runtime running? (${err.message})`);
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`Ollama ${res.status}: ${detail.slice(0, 300)}`);
  }
  const data = await res.json();
  return (data.message && data.message.content) || data.response || '';
}

async function callGateway({ system, prompt, maxTokens, tier }) {
  loadAixmosEnv();
  if (typeof fetch !== 'function') {
    throw new Error('global fetch missing — gateway backend needs Node.js 18+');
  }
  const base = GATEWAY_URL();
  if (!base) throw new Error('AIXMOS_GATEWAY_URL is not set');
  const secret = process.env.AIXMOS_GATEWAY_SECRET;
  if (!secret) throw new Error('AIXMOS_GATEWAY_SECRET is not set (keep it in ~/.config/tmmt/*.env)');

  // The gateway sets the system prompt server-side (per-secret persona) and
  // forwards `messages` straight to Anthropic on the paid lane — where a
  // `system`-role entry would 400 (Anthropic messages accept only user/assistant).
  // So fold any caller `system` into the user turn as leading context instead.
  const userContent = system ? `${system}\n\n${prompt}` : prompt;
  const messages = [{ role: 'user', content: userContent }];
  let res;
  try {
    res = await fetch(base, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-aixmos-auth': secret },
      body: JSON.stringify({ messages, tier: tier || GATEWAY_TIER(), max_tokens: maxTokens || 1024 }),
    });
  } catch (err) {
    throw new Error(`Gateway not reachable at ${base} (${err.message})`);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(`Gateway ${res.status}: ${(data && data.error) || 'request failed'}`);
  }
  // Free lane returns { text }; paid lane returns the raw Anthropic body { content:[{text}] }.
  if (typeof data.text === 'string' && data.text) return data.text;
  if (Array.isArray(data.content) && data.content[0]) return data.content[0].text || '';
  return '';
}

async function generate(opts) {
  loadAixmosEnv();
  const mode = backend();
  if (mode === 'ollama') return callOllama(opts);
  if (mode === 'gateway') return callGateway(opts);
  if (mode === 'auto') {
    try { return await callClaude(opts); }
    catch (err) {
      if (process.env.AIXMOS_DEBUG) {
        console.error(`[llm] claude path failed (${err.message}) — falling back to ollama`);
      }
      return callOllama(opts);
    }
  }
  return callClaude(opts);
}

module.exports = {
  generate,
  callClaude,
  callOllama,
  callGateway,
  backend,
  DEFAULT_CLAUDE_MODEL,
  DEFAULT_OLLAMA_MODEL,
  OLLAMA_HOST,
  GATEWAY_URL,
  GATEWAY_TIER,
};
