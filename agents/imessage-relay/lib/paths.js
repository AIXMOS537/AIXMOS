'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const HOME = process.env.HOME || os.homedir();
const ROOT = process.env.IMESSAGE_ASSISTANT_ROOT || path.join(HOME, '.config', 'tmmt', 'imessage-assistant');
const CHAT_DB = path.join(HOME, 'Library', 'Messages', 'chat.db');
const MIRROR_DB = path.join(ROOT, 'chat.mirror.db');
const KILL_FILE = path.join(ROOT, 'KILL');
const AUDIT_FILE = path.join(ROOT, 'audit.jsonl');
const CURSOR_FILE = path.join(ROOT, 'chatdb.cursor');
const RATE_FILE = path.join(ROOT, 'rate.json');
const DRAFTS_DIR = path.join(ROOT, 'drafts');
const CONFIG_FILE = path.join(ROOT, 'config.json');
const LOCK_FILE = path.join(ROOT, 'live.lock');
const EXAMPLE_CONFIG = path.join(__dirname, '..', 'config.example.json');
// Family/team roster lives outside this app — the content-team pipeline owns
// FAMILY_NUMBERS as its "never bot, never DM" list. We only read it to warn
// if owner_handles (MASTER exec eligibility) ever overlaps with it.
const FAMILY_ROSTER_FILE = path.join(HOME, '.config', 'tmmt', 'content-team.env');

function ensureDirs() {
  fs.mkdirSync(DRAFTS_DIR, { recursive: true, mode: 0o700 });
  fs.mkdirSync(ROOT, { recursive: true, mode: 0o700 });
}

function loadJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

function defaultConfig() {
  return loadJson(EXAMPLE_CONFIG, {
    safe_mode: true,
    allow_send: false,
    poll_ms: 5000,
    llm: {
      litellm_url: 'http://127.0.0.1:4000',
      ollama_url: 'http://127.0.0.1:11434',
      ollama_model: 'llama3.2:3b',
      max_tokens: 180,
    },
    t1_allowlist: [],
    t3_senders: [],
    owner_handles: [],
    auto_send_assistant: false,
    auto_field: true,
    rate: {
      drafts_per_hour: 40,
      sends_per_hour: 20,
      per_sender_per_hour: 10,
      per_sender_sends_per_hour: 4,
    },
  });
}

function loadOwnerHandles(overlayHandles) {
  const fromConfig = Array.isArray(overlayHandles) ? overlayHandles : [];
  const envFile = path.join(HOME, '.config', 'tmmt', 'owner-handles.env');
  let fromEnv = [];
  try {
    const raw = fs.readFileSync(envFile, 'utf8');
    fromEnv = raw
      .split(/\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#'));
  } catch {
    fromEnv = [];
  }
  return [...new Set([...fromConfig, ...fromEnv])];
}

/**
 * Read FAMILY_NUMBERS out of the content-team pipeline's env file, if present.
 * Shell-style `KEY="a,b,c"` or `KEY=a,b,c`. Never throws — a missing/odd file
 * just means "not discoverable," not a crash.
 */
function loadFamilyHandles() {
  let raw;
  try {
    raw = fs.readFileSync(FAMILY_ROSTER_FILE, 'utf8');
  } catch {
    return { found: false, handles: [] };
  }
  const m = raw.match(/^\s*FAMILY_NUMBERS\s*=\s*"([^"]*)"/m) || raw.match(/^\s*FAMILY_NUMBERS\s*=\s*(\S*)/m);
  const val = m ? String(m[1] || '').trim() : '';
  const handles = val ? val.split(',').map((s) => s.trim()).filter(Boolean) : [];
  return { found: true, handles };
}

function loadConfig() {
  const base = defaultConfig();
  const overlay = loadJson(CONFIG_FILE, {});
  return {
    ...base,
    ...overlay,
    llm: { ...base.llm, ...(overlay.llm || {}) },
    rate: { ...base.rate, ...(overlay.rate || {}) },
    t1_allowlist: overlay.t1_allowlist || base.t1_allowlist || [],
    t3_senders: overlay.t3_senders || base.t3_senders || [],
    owner_handles: loadOwnerHandles(overlay.owner_handles || base.owner_handles || []),
    safe_mode: overlay.safe_mode !== false,
    allow_send: overlay.allow_send === true || overlay.auto_send_assistant === true,
    auto_send_assistant: overlay.auto_send_assistant === true,
    auto_field: overlay.auto_field !== false,
  };
}

module.exports = {
  HOME,
  ROOT,
  CHAT_DB,
  MIRROR_DB,
  KILL_FILE,
  AUDIT_FILE,
  CURSOR_FILE,
  RATE_FILE,
  DRAFTS_DIR,
  CONFIG_FILE,
  LOCK_FILE,
  EXAMPLE_CONFIG,
  FAMILY_ROSTER_FILE,
  ensureDirs,
  loadJson,
  loadConfig,
  defaultConfig,
  loadFamilyHandles,
};
