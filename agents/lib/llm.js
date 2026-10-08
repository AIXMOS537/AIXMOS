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
 *   AIXMOS_MODEL           Claude model id  (default claude-opus-5)
 *   OLLAMA_MODEL           Ollama model tag — NO default that assumes an install;
 *                          set it to a tag `ollama list` actually shows on THIS box.
 *   OLLAMA_HOST            Ollama base URL  (default http://localhost:11434)
 *   AIXMOS_GATEWAY_URL     Gateway base URL (e.g. https://aixmos-gateway.<acct>.workers.dev)
 *   AIXMOS_GATEWAY_SECRET  Per-role secret; keep in ~/.config/tmmt/*.env, NEVER in the repo
 *   AIXMOS_GATEWAY_TIER    Requested lane: free|haiku|sonnet|opus (default free = $0)
 */

const { loadAixmosEnv } = require('./env');

let Anthropic;
try { Anthropic = require('@anthropic-ai/sdk'); } catch { /* optional in offline-only mode */ }

const DEFAULT_CLAUDE_MODEL = () => process.env.AIXMOS_MODEL || 'claude-opus-5';
// Was 'llama3.1:8b' — a tag installed on NEITHER the M1 nor BRAINIAC, so the local
// lane failed silently the moment anyone selected it. A free lane pointed at a model
// that does not exist is worse than no free lane: it looks configured and returns nothing.
const DEFAULT_OLLAMA_MODEL = () => process.env.OLLAMA_MODEL || 'qwen3:14b';
// Floor for local generation. Below ~2000 a reasoning model can burn the entire
// budget on hidden thinking and return nothing. Raise for long-form local work.
const MIN_LOCAL_PREDICT = parseInt(process.env.OLLAMA_MIN_PREDICT, 10) || 2000;
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
    // A REASONING model (qwen3, deepseek-r1, gpt-oss) spends num_predict inside
    // <think> BEFORE it writes a visible word. Give it a small budget and it runs
    // out mid-thought and returns 200 OK with content: "" — no error, no warning.
    // Measured 2026-09-19, qwen3:14b, same prompt x4: num_predict 600 -> 2/4 EMPTY;
    // num_predict 2500 -> 0/4. So floor the budget rather than trusting the caller.
    // (num_ctx is set too, but it was NOT the cause — the budget was.)
    options: {
      num_predict: Math.max(maxTokens || 2000, MIN_LOCAL_PREDICT),
      num_ctx: parseInt(process.env.OLLAMA_NUM_CTX, 10) || 16384,
    },
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
  const text = (data.message && data.message.content) || data.response || '';
  // An empty completion is a FAILURE, not a result. Returning '' here let an agent
  // report success while producing nothing — the caller cannot tell the difference
  // between "the model had nothing to say" and "the lane is broken". Fail loud.
  if (!text.trim()) {
    throw new Error(
      `Ollama returned an EMPTY completion (model=${body.model}, num_predict=${body.options.num_predict}, `
      + `done_reason=${data.done_reason || 'unknown'}). A reasoning model likely spent the whole `
      + `budget inside <think>. Raise maxTokens/OLLAMA_MIN_PREDICT, or use a non-reasoning model.`
    );
  }
  return text;
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
