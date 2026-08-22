'use strict';

/**
 * Local $0 brain: try LiteLLM :4000, fall back to Ollama :11434.
 * Never calls paid cloud APIs.
 */

async function fetchJson(url, body, timeoutMs) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: ac.signal,
    });
    const text = await res.text();
    let json;
    try { json = text ? JSON.parse(text) : {}; } catch { json = { raw: text }; }
    return { ok: res.ok, status: res.status, json, text };
  } finally {
    clearTimeout(t);
  }
}

async function probeLiteLLM(base) {
  const url = `${String(base || '').replace(/\/$/, '')}/health`;
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 1500);
    const res = await fetch(url, { signal: ac.signal });
    clearTimeout(t);
    return { ok: res.ok, status: res.status };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

async function probeOllama(base) {
  const url = `${String(base || '').replace(/\/$/, '')}/api/tags`;
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 2000);
    const res = await fetch(url, { signal: ac.signal });
    clearTimeout(t);
    if (!res.ok) return { ok: false, status: res.status };
    const json = await res.json();
    const models = (json.models || []).map((m) => m.name);
    return { ok: true, models };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

async function callLiteLLM({ base, model, system, prompt, maxTokens }) {
  const url = `${String(base).replace(/\/$/, '')}/v1/chat/completions`;
  const r = await fetchJson(url, {
    model: model || 'ollama/llama3.2:3b',
    messages: [
      ...(system ? [{ role: 'system', content: system }] : []),
      { role: 'user', content: prompt },
    ],
    max_tokens: maxTokens || 180,
    temperature: 0.3,
  }, 4000);
  if (!r.ok) throw new Error(`LiteLLM ${r.status}: ${(r.text || '').slice(0, 180)}`);
  const content = r.json?.choices?.[0]?.message?.content;
  if (!content) throw new Error('LiteLLM empty completion');
  return String(content).trim();
}

async function callOllama({ base, model, system, prompt, maxTokens }) {
  const url = `${String(base).replace(/\/$/, '')}/api/chat`;
  const r = await fetchJson(url, {
    model,
    messages: [
      ...(system ? [{ role: 'system', content: system }] : []),
      { role: 'user', content: prompt },
    ],
    stream: false,
    options: { num_predict: maxTokens || 180, temperature: 0.3 },
  }, 45000);
  if (!r.ok) throw new Error(`Ollama ${r.status}: ${(r.text || '').slice(0, 180)}`);
  const content = (r.json.message && r.json.message.content) || r.json.response || '';
  if (!content) throw new Error('Ollama empty completion');
  return String(content).trim();
}

async function generateLocal({ system, prompt, config }) {
  const llm = (config && config.llm) || {};
  const litellm = llm.litellm_url || 'http://127.0.0.1:4000';
  const ollama = llm.ollama_url || 'http://127.0.0.1:11434';
  const model = llm.ollama_model || 'llama3.2:3b';
  const maxTokens = llm.max_tokens || 180;
  let lastErr;
  try {
    const text = await callLiteLLM({ base: litellm, model: `ollama/${model}`, system, prompt, maxTokens });
    return { text, backend: 'litellm', model };
  } catch (err) {
    lastErr = err;
  }
  try {
    const text = await callOllama({ base: ollama, model, system, prompt, maxTokens });
    return { text, backend: 'ollama', model, litellmError: lastErr ? lastErr.message : undefined };
  } catch (err) {
    throw new Error(`local LLM failed (LiteLLM: ${lastErr ? lastErr.message : 'n/a'}; Ollama: ${err.message})`);
  }
}

const SMS_SYSTEM_T1 = [
  'You are Rick, Taha\'s local Mac assistant. Taha is in the field doing physical work.',
  'Answer as HIS ASSISTANT, never as Taha. Never impersonate Taha.',
  'Reply in 1-3 short SMS sentences. Plain English. No markdown.',
  'Never commit money, quotes, prices, signatures, legal, or family plans.',
  'Never claim you sent, paid, signed, or called anyone.',
  'If you cannot help, say Taha will follow up when he is back.',
  'Do not include a signature; the system appends one.',
].join(' ');

const SMS_SYSTEM_T2 = [
  'You are Rick drafting a reply for Taha to review and send himself.',
  'Write in Taha\'s voice, 1-3 short SMS sentences. Plain English. No markdown.',
  'This is a DRAFT. Never claim it was sent.',
  'Do not invent prices, payments, or signatures.',
].join(' ');

const SMS_SYSTEM = SMS_SYSTEM_T2;

async function draftReply({ inboundText, tier, config }) {
  const system = tier === 'T1' ? SMS_SYSTEM_T1 : SMS_SYSTEM_T2;
  const prompt = `Incoming ${tier} text:\n"""${String(inboundText || '').slice(0, 800)}"""\n\nWrite the reply only.`;
  return generateLocal({ system, prompt, config });
}

module.exports = {
  probeLiteLLM,
  probeOllama,
  callLiteLLM,
  callOllama,
  generateLocal,
  draftReply,
  SMS_SYSTEM,
  SMS_SYSTEM_T1,
  SMS_SYSTEM_T2,
};
