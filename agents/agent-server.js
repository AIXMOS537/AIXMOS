#!/usr/bin/env node
/**
 * AIXMOS agent HTTP host.
 *   GET  /healthz                        -> {ok, backend, model}
 *   GET  /agents                         -> registry
 *   POST /agent/:name  { prompt, max_tokens? }
 *   POST /council      { situation, max_tokens? }   -> VISION -> CAPTAIN -> MOOSE chain
 *
 * Bound to 0.0.0.0:7777 (publish to 127.0.0.1:7777 from compose).
 */

const http = require('http');
const { timingSafeEqual } = require('crypto');
const { loadAixmosEnv } = require('./lib/env');
const llm = require('./lib/llm');
const prompts = require('./agents/prompts');
const { runAgent, loadRegistry } = require('./lib/runner');

loadAixmosEnv();

const PORT = parseInt(process.env.AIX_AGENT_PORT || '7777', 10);
// Bind localhost-only by default. Set AIX_AGENT_HOST=0.0.0.0 explicitly to
// expose to the network (e.g. compose forwarding, Tailscale tunnel). The
// prior default of 0.0.0.0 made it trivially reachable on any LAN.
const HOST = process.env.AIX_AGENT_HOST || '127.0.0.1';
const KNOWN_AGENTS = Object.keys(prompts);
const AUTH_TOKEN = (process.env.AIX_AGENT_TOKEN || '').trim();

// Fail-closed at startup. The prior implementation logged "auth=OPEN (no
// token set)" and accepted ALL requests when AIX_AGENT_TOKEN was empty —
// a single misconfigured deploy was a free-LLM-tokens vending machine.
if (!AUTH_TOKEN || AUTH_TOKEN.length < 16) {
  console.error('[aix-agent-host] FATAL: AIX_AGENT_TOKEN must be set and at least 16 characters');
  console.error('[aix-agent-host]        generate one with:  openssl rand -hex 32');
  process.exit(1);
}

const OPEN_PATHS = new Set(['/', '/healthz']);
const AUTH_BUF = Buffer.from(AUTH_TOKEN, 'utf8');

function constantEq(provided) {
  if (typeof provided !== 'string') return false;
  const pBuf = Buffer.from(provided, 'utf8');
  if (pBuf.length !== AUTH_BUF.length) return false;
  try { return timingSafeEqual(pBuf, AUTH_BUF); }
  catch { return false; }
}

function checkAuth(req, url) {
  if (OPEN_PATHS.has(url.pathname)) return true;
  // Bearer header only. The prior `?token=` query string fallback leaked
  // the token via Referer headers, browser history, and reverse-proxy
  // access logs — the exact "copy a URL out of someone's browser" attack
  // we want to prevent.
  const header = req.headers['authorization'] || '';
  const m = header.match(/^Bearer\s+(.+)$/i);
  return !!m && constantEq(m[1].trim());
}

function send(res, status, body) {
  const payload = typeof body === 'string' ? body : JSON.stringify(body);
  res.writeHead(status, {
    'content-type': typeof body === 'string' ? 'text/plain' : 'application/json',
    'content-length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); }
      catch (e) { reject(new Error(`invalid JSON body: ${e.message}`)); }
    });
    req.on('error', reject);
  });
}

async function handleAgent(name, body) {
  if (!KNOWN_AGENTS.includes(name)) {
    const err = new Error(`unknown agent '${name}'. known: ${KNOWN_AGENTS.join(', ')}`);
    err.status = 404;
    throw err;
  }
  const prompt = (body.prompt || body.input || body.userPrompt || '').toString().trim();
  if (!prompt) {
    const err = new Error('missing "prompt" in body');
    err.status = 400;
    throw err;
  }
  const maxTokens = parseInt(body.max_tokens || body.maxTokens || '1500', 10);
  const t0 = Date.now();
  const output = await runAgent({ system: prompts[name], userPrompt: prompt, maxTokens });
  return {
    agent: name,
    backend: llm.backend(),
    model: llm.backend() === 'ollama' ? llm.DEFAULT_OLLAMA_MODEL() : llm.DEFAULT_CLAUDE_MODEL(),
    latency_ms: Date.now() - t0,
    output,
  };
}

async function handleCouncil(body) {
  const situation = (body.situation || body.prompt || '').toString().trim();
  if (!situation) {
    const err = new Error('missing "situation" in body');
    err.status = 400;
    throw err;
  }
  const maxTokens = parseInt(body.max_tokens || body.maxTokens || '1200', 10);
  const t0 = Date.now();
  const vision = await runAgent({
    system: prompts.vision,
    userPrompt: `Situation:\n${situation}\n\nGo/no-go and long-term fit.`,
    maxTokens,
  });
  if (/NO-GO\s*[❌X]/i.test(vision)) {
    return { decision: 'NO-GO', vision, latency_ms: Date.now() - t0 };
  }
  const captain = await runAgent({
    system: prompts.captain,
    userPrompt: `Situation:\n${situation}\n\nVISION said:\n${vision}\n\nRoute the cube.`,
    maxTokens,
  });
  const moose = await runAgent({
    system: prompts.moose,
    userPrompt: `Situation:\n${situation}\n\nCAPTAIN said:\n${captain}\n\nExecute without hesitation.`,
    maxTokens,
  });
  return {
    decision: 'GO',
    backend: llm.backend(),
    latency_ms: Date.now() - t0,
    vision,
    captain,
    moose,
  };
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const method = req.method.toUpperCase();
  try {
    if (!checkAuth(req, url)) {
      return send(res, 401, { error: 'unauthorized — provide Authorization: Bearer <token>' });
    }
    if (method === 'GET' && url.pathname === '/healthz') {
      return send(res, 200, {
        ok: true,
        backend: llm.backend(),
        ollama_host: llm.OLLAMA_HOST(),
        ollama_model: llm.DEFAULT_OLLAMA_MODEL(),
        claude_model: llm.DEFAULT_CLAUDE_MODEL(),
        agents: KNOWN_AGENTS,
      });
    }
    if (method === 'GET' && url.pathname === '/agents') {
      let registry = null;
      try { registry = loadRegistry(); } catch (_) { /* optional */ }
      return send(res, 200, { agents: KNOWN_AGENTS, registry });
    }
    const agentMatch = url.pathname.match(/^\/agent\/([a-z0-9_-]+)\/?$/i);
    if (method === 'POST' && agentMatch) {
      const body = await readBody(req);
      const result = await handleAgent(agentMatch[1], body);
      return send(res, 200, result);
    }
    if (method === 'POST' && url.pathname === '/council') {
      const body = await readBody(req);
      const result = await handleCouncil(body);
      return send(res, 200, result);
    }
    if (method === 'GET' && url.pathname === '/') {
      return send(res, 200, {
        service: 'aixmos-agent-host',
        try: [
          'GET  /healthz',
          'GET  /agents',
          'POST /agent/<name>  {prompt}',
          'POST /council       {situation}',
        ],
        agents: KNOWN_AGENTS,
      });
    }
    return send(res, 404, { error: 'not found', path: url.pathname });
  } catch (err) {
    const status = err.status || 500;
    return send(res, status, { error: err.message, agent: agentMatch && agentMatch[1] });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`[aix-agent-host] listening on http://${HOST}:${PORT}`);
  console.log(`[aix-agent-host] backend=${llm.backend()} ollama=${llm.OLLAMA_HOST()} model=${llm.DEFAULT_OLLAMA_MODEL()}`);
  console.log(`[aix-agent-host] auth=bearer-token (constant-time compare)`);
  console.log(`[aix-agent-host] agents: ${KNOWN_AGENTS.join(', ')}`);
});
