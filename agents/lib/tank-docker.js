/**
 * TANK — auto-run hub-brain docker compose.
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawnSync } = require('child_process');

function getHubBrainDir(registry) {
  const composeFile =
    registry?.infrastructure_paths?.hub_brain_compose ||
    path.join(__dirname, '..', 'hub-brain', 'docker-compose.yml');
  return path.dirname(composeFile);
}

function dockerAvailable() {
  try {
    execSync('docker info', { stdio: 'pipe', timeout: 12000 });
    return true;
  } catch {
    return false;
  }
}

function runCompose(hubDir, args, opts = {}) {
  const composePath = path.join(hubDir, 'docker-compose.yml');
  if (!fs.existsSync(composePath)) {
    throw new Error(`docker-compose.yml not found: ${composePath}`);
  }

  const envFile = path.join(hubDir, '.env');
  const base = ['compose', '-f', composePath];
  if (fs.existsSync(envFile)) base.push('--env-file', envFile);

  const cmd = ['docker', ...base, ...args];
  const result = spawnSync(cmd[0], cmd.slice(1), {
    cwd: hubDir,
    encoding: 'utf8',
    timeout: opts.timeout || 300000,
    shell: process.platform === 'win32',
  });

  return {
    ok: result.status === 0,
    status: result.status,
    stdout: (result.stdout || '').trim(),
    stderr: (result.stderr || '').trim(),
    cmd: cmd.join(' '),
  };
}

function composeUp(registry) {
  const hubDir = getHubBrainDir(registry);
  return runCompose(hubDir, ['up', '-d', '--remove-orphans']);
}

function composeDown(registry) {
  const hubDir = getHubBrainDir(registry);
  return runCompose(hubDir, ['down']);
}

function composePs(registry) {
  const hubDir = getHubBrainDir(registry);
  return runCompose(hubDir, ['ps']);
}

function composeLogs(registry, tail = 40) {
  const hubDir = getHubBrainDir(registry);
  return runCompose(hubDir, ['logs', '--tail', String(tail)]);
}

module.exports = {
  getHubBrainDir,
  dockerAvailable,
  composeUp,
  composeDown,
  composePs,
  composeLogs,
};
