const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const CONTEXT_FILE = path.join(__dirname, 'shared-context.json');

function readSharedContext() {
  try {
    const raw = fs.readFileSync(CONTEXT_FILE, 'utf8');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeSharedContext(state) {
  fs.writeFileSync(CONTEXT_FILE, JSON.stringify(state, null, 2), 'utf8');
}

function ensureSharedContext() {
  const dir = path.dirname(CONTEXT_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  if (!fs.existsSync(CONTEXT_FILE)) writeSharedContext({});
}

function ask(rl, question, optional = false) {
  return new Promise(resolve => {
    const label = optional ? ' (optional)' : '';
    rl.question(question + label, answer => resolve(answer.trim()));
  });
}

function copyToClipboard(text) {
  try {
    if (process.platform === 'win32') {
      execSync('clip', { input: text });
    } else if (process.platform === 'darwin') {
      execSync('pbcopy', { input: text });
    } else {
      execSync('xclip -selection clipboard', { input: text });
    }
    return true;
  } catch {
    return false;
  }
}

/** E.164-ish handle for Messages.app (US 10-digit → +1…) */
function normalizeIMessageHandle(raw) {
  const s = String(raw).trim().replace(/^@+/, '');
  if (!s) return '';
  if (s.includes('@')) return s;
  if (/^\+[1-9]\d{6,14}$/.test(s)) return s;
  const digits = s.replace(/\D/g, '');
  if (digits.length === 10) return `+1${digits}`;
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`;
  if (digits.length > 0) return `+${digits}`;
  return s;
}

function sendText(recipient, message) {
  if (process.platform !== 'darwin') return false;
  const buddy = normalizeIMessageHandle(recipient);
  if (!buddy || !message) return false;
  try {
    const script = `on run argv
  set theBuddy to item 1 of argv
  set theText to item 2 of argv
  tell application "Messages"
    set targetService to 1st service whose service type is iMessage
    set targetBuddy to buddy theBuddy of targetService
    send theText to targetBuddy
  end tell
end run`;
    execSync('osascript', ['-e', script, '--', buddy, message], {
      encoding: 'utf8',
      maxBuffer: 10 * 1024 * 1024,
    });
    return true;
  } catch (err) {
    const detail = err.stderr?.toString?.() || err.message || String(err);
    console.error(detail.trim());
    return false;
  }
}

function saveAgentContext(agent, data) {
  ensureSharedContext();
  const state = readSharedContext();
  if (!state[agent]) state[agent] = [];
  state[agent].push({ ...data, timestamp: new Date().toISOString() });
  writeSharedContext(state);
  return state[agent];
}

function getLastAgentContext(agent) {
  const state = readSharedContext();
  const list = state[agent] || [];
  return list[list.length - 1] || null;
}

function getAllAgentContext(agent) {
  const state = readSharedContext();
  return state[agent] || [];
}

module.exports = {
  ask,
  copyToClipboard,
  normalizeIMessageHandle,
  sendText,
  saveAgentContext,
  getLastAgentContext,
  getAllAgentContext,
  CONTEXT_FILE,
};
