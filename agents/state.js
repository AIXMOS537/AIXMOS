const fs = require('fs');
const path = require('path');

const STATE_FILE = path.join(__dirname, 'aixmos-state.json');

function now() {
  return new Date().toISOString();
}

function blank() {
  return {
    created_at: now(),
    updated_at: now(),
    sessions: [],
    handoffs: [],
    flagged_payments: [],
    agents: {
      chummo: {},
      moose: {},
      captain: {},
      wonder_woman: {},
      vision: {},
      tank: {},
      fly_guy: {},
      bob: {},
      sticks: {},
      jarvis: {}
    }
  };
}

function load() {
  try {
    if (!fs.existsSync(STATE_FILE)) return blank();
    return { ...blank(), ...JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')) };
  } catch {
    return blank();
  }
}

function save(state) {
  const next = { ...blank(), ...state, updated_at: now() };
  fs.writeFileSync(STATE_FILE, JSON.stringify(next, null, 2));
  return next;
}

function reset() {
  return save(blank());
}

function startSession() {
  const s = load();
  s.sessions = Array.isArray(s.sessions) ? s.sessions : [];
  s.sessions.push({ started_at: now() });
  return save(s);
}

function updateAgent(agent, patch) {
  const s = load();
  s.agents = s.agents || {};
  s.agents[agent] = {
    ...(s.agents[agent] || {}),
    ...patch,
    last_run: now(),
    runs: ((s.agents[agent] || {}).runs || 0) + 1
  };
  return save(s);
}

function setHandoff(from, to, content, label) {
  const s = load();
  s.handoffs = Array.isArray(s.handoffs) ? s.handoffs : [];
  s.handoffs.push({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    from,
    to,
    content,
    label: label || `${from} to ${to}`,
    active: true,
    created_at: now(),
    used_at: null
  });
  return save(s);
}

function getHandoff(to) {
  const s = load();
  return (s.handoffs || []).find(h => h.to === to && h.active) || null;
}

function useHandoff(to) {
  const s = load();
  const h = (s.handoffs || []).find(h => h.to === to && h.active);
  if (h) {
    h.active = false;
    h.used_at = now();
  }
  return save(s);
}

function getSummary() {
  const s = load();
  const agents = s.agents || {};
  const active_handoffs = (s.handoffs || []).filter(h => h.active);
  const flagged_payments = s.flagged_payments || [];
  const total_runs = Object.values(agents).reduce((sum, a) => sum + (a.runs || 0), 0);

  return {
    chummo_lead: agents.chummo?.last_lead || '-',
    chummo_last: agents.chummo?.last_run || 'Never',
    moose_mode: agents.moose?.last_mode || '-',
    moose_last: agents.moose?.last_run || 'Never',
    captain_score: agents.captain?.score || '-',
    captain_last: agents.captain?.last_run || 'Never',
    ww_mode: agents.wonder_woman?.last_mode || '-',
    ww_last: agents.wonder_woman?.last_run || 'Never',
    vision_last: agents.vision?.last_run || 'Never',
    tank_last: agents.tank?.last_run || 'Never',
    bob_last: agents.bob?.last_run || 'Never',
    sticks_last: agents.sticks?.last_run || 'Never',
    jarvis_last: agents.jarvis?.last_run || 'Never',
    jarvis_mode: agents.jarvis?.last_mode || '-',
    active_handoffs,
    flagged_payments,
    total_runs
  };
}

module.exports = {
  load,
  save,
  reset,
  startSession,
  updateAgent,
  setHandoff,
  getHandoff,
  useHandoff,
  getSummary
};
