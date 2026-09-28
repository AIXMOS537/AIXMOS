/**
 * TMMT OS HTTP client — agent evaluate panel + GHL overdue webhook.
 */

const crypto = require('crypto');

function baseUrl() {
  const url = (process.env.TMMT_OPS_URL || process.env.NEXT_PUBLIC_APP_URL || '').replace(/\/$/, '');
  if (!url) throw new Error('TMMT_OPS_URL is not set');
  return url;
}

function agentSecret() {
  const s = process.env.AGENT_WEBHOOK_SECRET;
  if (!s) throw new Error('AGENT_WEBHOOK_SECRET is not set');
  return s;
}

function ghlSecret() {
  return (
    process.env.GHL_OVERDUE_WEBHOOK_SECRET ||
    process.env.GHL_WEBHOOK_SECRET ||
    ''
  );
}

async function postJson(urlPath, body, headers = {}) {
  const url = `${baseUrl()}${urlPath}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let json;
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  if (!res.ok) {
    const err = new Error(json.error || res.statusText || `HTTP ${res.status}`);
    err.status = res.status;
    err.body = json;
    throw err;
  }
  return json;
}

async function openEvaluationSession({ subjectType, subjectId, metadata, requiredApprovals, panelSize }) {
  return postJson(
    '/api/agents/evaluate',
    {
      action: 'open',
      subject_type: subjectType,
      subject_id: subjectId,
      required_approvals: requiredApprovals,
      panel_size: panelSize,
      metadata: metadata || {},
    },
    { 'X-Agent-Secret': agentSecret() }
  );
}

async function castAgentVote({ sessionId, agent, vote, rationale, payload }) {
  return postJson(
    '/api/agents/evaluate',
    {
      action: 'vote',
      session_id: sessionId,
      agent,
      vote,
      rationale,
      payload: payload || {},
    },
    { 'X-Agent-Secret': agentSecret() }
  );
}

async function getEvaluationSession(sessionId) {
  return postJson(
    '/api/agents/evaluate',
    { action: 'get', session_id: sessionId },
    { 'X-Agent-Secret': agentSecret() }
  );
}

async function pushGhlOverdue(payload) {
  const secret = ghlSecret();
  const headers = secret ? { 'X-GHL-Secret': secret } : {};
  return postJson('/api/webhooks/ghl/overdue', payload, headers);
}

function newSubjectId() {
  return crypto.randomUUID();
}

module.exports = {
  baseUrl,
  openEvaluationSession,
  castAgentVote,
  getEvaluationSession,
  pushGhlOverdue,
  newSubjectId,
};
