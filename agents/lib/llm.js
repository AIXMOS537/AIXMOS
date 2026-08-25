/**
 * Dual-backend LLM abstraction for AIXMOS agents.
 *
 *   AIXMOS_LLM_BACKEND=ollama   (default) — local Ollama runtime, FREE
 *   AIXMOS_LLM_BACKEND=claude            — Anthropic cloud API (costs credits)
 *   AIXMOS_LLM_BACKEND=auto              — try Claude, fall back to Ollama
 *
 * Tunables:
 *   AIXMOS_MODEL       Claude model id  (default claude-sonnet-4-6)
 *   OLLAMA_MODEL       Ollama model tag (default llama3.1:8b)
 *   OLLAMA_HOST        Ollama base URL  (default http://localhost:11434)
 */

const { loadAixmosEnv } = require('./env');

let Anthropic;
try { Anthropic = require('@anthropic-ai/sdk'); } catch { /* optional in offline-only mode */ }

const DEFAULT_CLAUDE_MODEL = () => process.env.AIXMOS_MODEL || 'claude-sonnet-4-6';
const DEFAULT_OLLAMA_MODEL = () => process.env.OLLAMA_MODEL || 'llama3.1:8b';
// Normalize OLLAMA_HOST so it is always a *dialable* client URL.
// The same env var doubles as the server's bind address (e.g. 0.0.0.0:11434
// to listen on all interfaces for Tailscale/remote access), but 0.0.0.0 is
// not a connectable host and a bare host:port has no scheme to parse.
const OLLAMA_HOST = () => {
  let raw = (process.env.OLLAMA_HOST || 'http://localhost:11434').trim();
  if (!/^https?:\/\//i.test(raw)) raw = `http://${raw}`;       // add missing scheme
  raw = raw.replace(/\/\/0\.0\.0\.0(?=[:/]|$)/, '//127.0.0.1'); // 0.0.0.0 -> loopback for dialing
  return raw.replace(/\/$/, '');
};

function backend() {
  // Default to FREE LOCAL (ollama) so no machine ever silently burns cloud
  // credits. To use paid cloud, set AIXMOS_LLM_BACKEND=claude ON PURPOSE.
  return (process.env.AIXMOS_LLM_BACKEND || 'ollama').toLowerCase();
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

async function generate(opts) {
  loadAixmosEnv();
  const mode = backend();
  if (mode === 'ollama') return callOllama(opts);
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
  backend,
  DEFAULT_CLAUDE_MODEL,
  DEFAULT_OLLAMA_MODEL,
  OLLAMA_HOST,
};
