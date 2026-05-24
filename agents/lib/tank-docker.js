/**
 * TANK — auto-run hub-brain docker compose.
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawnSync } = require('child_process');

function remoteHost() { return (process.env.HUB_BRAIN_HOST || '').trim(); }

function getHubBrainDir(registry) {
  const composeFile =
    process.env.HUB_BRAIN_COMPOSE ||
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

function probeRemote(host) {
  const probes = [
    { name: 'open-webui', port: 3000 },
    { name: 'n8n',        port: 5678 },
  ];
  return probes.map(({ name, port }) => {
    const r = spawnSync('curl', ['-sS', '-o', '/dev/null', '-w', '%{http_code}',
      '--max-time', '5', `http://${host}:${port}/`], { encoding: 'utf8' });
    const code = parseInt((r.stdout || '').trim(), 10) || 0;
    return { name, port, code, ok: code >= 200 && code < 500 };
  });
}

function remoteStatus(host) {
  const results = probeRemote(host);
  const lines = results.map(p =>
    `  ${p.ok ? '✓' : '✗'} ${p.name.padEnd(10)} http://${host}:${p.port}  (HTTP ${p.code})`);
  return {
    ok: results.every(p => p.ok),
    status: 0,
    stdout: `Hub-brain (remote) on ${host}:\n${lines.join('\n')}`,
    stderr: '',
  };
}

function remoteRefuse(action, host) {
  return {
    ok: true,
    status: 0,
    stdout: `Hub-brain lives on ${host}. To ${action}, run TANK on that machine — not here.`,
    stderr: '',
  };
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
  const host = remoteHost();
  if (host) return remoteRefuse('start', host);
  const hubDir = getHubBrainDir(registry);
  return runCompose(hubDir, ['up', '-d', '--remove-orphans']);
}

function composeDown(registry) {
  const host = remoteHost();
  if (host) return remoteRefuse('stop', host);
  const hubDir = getHubBrainDir(registry);
  return runCompose(hubDir, ['down']);
}

function composePs(registry) {
  const host = remoteHost();
  if (host) return remoteStatus(host);
  const hubDir = getHubBrainDir(registry);
  return runCompose(hubDir, ['ps']);
}

function composeLogs(registry, tail = 40) {
  const host = remoteHost();
  if (host) return remoteRefuse('tail logs', host);
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
