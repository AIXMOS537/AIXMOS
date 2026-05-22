/**
 * Load AIXMOS / TMMT env from local files (does not override existing process.env).
 */

const fs = require('fs');
const path = require('path');

function loadEnvFile(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return;
  const text = fs.readFileSync(filePath, 'utf8');
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 1) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = val;
  }
}

function loadAixmosEnv() {
  const root = path.join(__dirname, '..');
  const registryPath = path.join(root, 'agents', 'registry.json');
  let tmmtOs = '';
  try {
    const reg = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
    tmmtOs = reg.infrastructure_paths?.tmmt_os || '';
  } catch {
    /* ignore */
  }

  const candidates = [
    path.join(root, '.env'),
    path.join(root, 'config', 'aixmos.env'),
    tmmtOs ? path.join(tmmtOs, '.env.local') : '',
    tmmtOs ? path.join(tmmtOs, '.env') : '',
    path.join(
      path.dirname(tmmtOs || root),
      '..',
      'AUTOMATIONS',
      '.env'
    ),
  ].filter(Boolean);

  for (const p of candidates) loadEnvFile(p);
}

function requireEnv(keys) {
  const missing = keys.filter(k => !(process.env[k] || '').trim());
  if (missing.length) {
    throw new Error(`Missing env: ${missing.join(', ')} — set in AIXMOS-AGENTS/.env or tmmt-os/.env.local`);
  }
}

/**
 * Backend-aware check for the configured LLM. Loads env first.
 *   ollama → no key required (reachability fails at call time if Ollama is down)
 *   auto   → no key required (falls back to ollama if Claude unavailable)
 *   claude → ANTHROPIC_API_KEY required
 */
function requireLLMBackend() {
  loadAixmosEnv();
  const backend = (process.env.AIXMOS_LLM_BACKEND || 'claude').toLowerCase();
  if (backend === 'ollama' || backend === 'auto') return backend;
  if (!(process.env.ANTHROPIC_API_KEY || '').trim()) {
    throw new Error('ANTHROPIC_API_KEY is not set (AIXMOS_LLM_BACKEND=claude). Set the key or switch backend to ollama/auto in .env.');
  }
  return backend;
}

module.exports = { loadAixmosEnv, loadEnvFile, requireEnv, requireLLMBackend };
