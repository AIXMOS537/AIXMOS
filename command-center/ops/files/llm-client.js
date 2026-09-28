/**
 * Ollama-first LLM client with optional Anthropic fallback.
 * Set AI_PROVIDER=ollama|anthropic|auto (default: auto).
 */
const OLLAMA_BASE = (process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434').replace(/\/$/, '');
const AI_PROVIDER = (process.env.AI_PROVIDER || 'auto').toLowerCase();

let Anthropic;
function getAnthropicClient() {
  if (!Anthropic) {
    try {
      Anthropic = require('@anthropic-ai/sdk');
    } catch {
      throw new Error('Missing @anthropic-ai/sdk. Run: npm install @anthropic-ai/sdk');
    }
  }
  return new Anthropic.default();
}

async function ollamaReachable() {
  try {
    const res = await fetch(`${OLLAMA_BASE}/api/tags`, { signal: AbortSignal.timeout(4000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function resolveOllamaModel() {
  if (process.env.OLLAMA_MODEL) return process.env.OLLAMA_MODEL;
  const res = await fetch(`${OLLAMA_BASE}/api/tags`);
  if (!res.ok) throw new Error(`Ollama tags failed: ${res.status}`);
  const data = await res.json();
  const name = data.models?.[0]?.name;
  if (!name) throw new Error('No Ollama models pulled. Run: ollama pull qwen2.5-coder:14b');
  return name;
}

async function chatOllama({ system, userMessage, maxTokens = 1000 }) {
  const model = await resolveOllamaModel();
  const messages = [];
  if (system) messages.push({ role: 'system', content: system });
  messages.push({ role: 'user', content: userMessage });

  const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      messages,
      stream: false,
      think: false,
      options: { num_predict: maxTokens },
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Ollama ${res.status}: ${errText.slice(0, 200)}`);
  }

  const data = await res.json();
  const text = data.message?.content ?? '';
  if (!text.trim()) {
    throw new Error(
      data.done_reason === 'length'
        ? 'Ollama hit token limit — increase maxTokens or set OLLAMA_MODEL to a smaller model'
        : 'Ollama returned empty response'
    );
  }
  return { text, provider: 'ollama', model };
}

async function chatAnthropic({ system, userMessage, maxTokens = 1000 }) {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error('ANTHROPIC_API_KEY not set');
  }
  const client = getAnthropicClient();
  const model = process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-20250514';
  const response = await client.messages.create({
    model,
    max_tokens: maxTokens,
    system: system || undefined,
    messages: [{ role: 'user', content: userMessage }],
  });
  return { text: response.content[0].text, provider: 'anthropic', model };
}

async function getAiStatus() {
  let ollamaOk = await ollamaReachable();
  let ollamaModel = null;
  if (ollamaOk) {
    try {
      ollamaModel = await resolveOllamaModel();
    } catch {
      ollamaOk = false;
    }
  }
  const hasAnthropic = !!process.env.ANTHROPIC_API_KEY;
  let active = 'none';
  if (AI_PROVIDER === 'ollama' && ollamaOk) active = 'ollama';
  else if (AI_PROVIDER === 'anthropic' && hasAnthropic) active = 'anthropic';
  else if (AI_PROVIDER === 'auto') {
    if (ollamaOk) active = 'ollama';
    else if (hasAnthropic) active = 'anthropic';
  } else if (AI_PROVIDER === 'ollama' && !ollamaOk && hasAnthropic) active = 'anthropic';
  return { ollamaOk, ollamaModel, hasAnthropic, active, baseUrl: OLLAMA_BASE };
}

async function chatCompletion(opts) {
  const { system, userMessage, maxTokens } = opts;

  if (AI_PROVIDER === 'anthropic') {
    return chatAnthropic(opts);
  }
  if (AI_PROVIDER === 'ollama') {
    return chatOllama(opts);
  }

  if (await ollamaReachable()) {
    try {
      return await chatOllama({ system, userMessage, maxTokens });
    } catch (err) {
      if (process.env.ANTHROPIC_API_KEY) {
        console.warn(`Ollama failed (${err.message}); using Anthropic.`);
        return chatAnthropic(opts);
      }
      throw err;
    }
  }

  if (process.env.ANTHROPIC_API_KEY) {
    return chatAnthropic(opts);
  }

  throw new Error(
    'No AI available. Start Ollama: ollama serve — or set ANTHROPIC_API_KEY for cloud fallback.'
  );
}

async function requireAiAvailable(exitOnFail = true) {
  const status = await getAiStatus();
  if (status.active === 'none') {
    const msg =
      'No AI provider ready.\n' +
      '  Local:  ollama serve  (then: ollama pull qwen2.5-coder:14b)\n' +
      '  Cloud:  export ANTHROPIC_API_KEY=...';
    if (exitOnFail) {
      console.error(msg);
      process.exit(1);
    }
    return { ok: false, status, message: msg };
  }
  return { ok: true, status };
}

module.exports = {
  chatCompletion,
  getAiStatus,
  requireAiAvailable,
  ollamaReachable,
};
