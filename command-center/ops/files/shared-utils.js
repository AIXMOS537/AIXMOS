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

function sendText(recipient, message) {
  if (process.platform !== 'darwin') return false;
  try {
    const escaped = message.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n');
    const script = `tell application "Messages"
      set targetService to 1st service whose service type = iMessage
      set targetBuddy to buddy "${recipient}" of targetService
      send "${escaped}" to targetBuddy
    end tell`;
    execSync(`osascript -e ${JSON.stringify(script)}`);
    return true;
  } catch {
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
  sendText,
  saveAgentContext,
  getLastAgentContext,
  getAllAgentContext,
  CONTEXT_FILE,
};
