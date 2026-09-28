#!/usr/bin/env node
/**
 * Lightweight infrastructure health scan (no Docker API required).
 */

const fs = require('fs');
const http = require('http');
const path = require('path');
const { execSync } = require('child_process');

function loadRegistry() {
  return JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'agents', 'registry.json'), 'utf8')
  );
}

function fileExists(p) {
  try {
    return fs.existsSync(p);
  } catch {
    return false;
  }
}

function probeHttp(port, pathName = '/') {
  return new Promise(resolve => {
    const req = http.request(
      { hostname: '127.0.0.1', port, path: pathName, method: 'GET', timeout: 2000 },
      res => resolve({ ok: res.statusCode < 500, status: res.statusCode })
    );
    req.on('error', () => resolve({ ok: false, status: 0 }));
    req.on('timeout', () => {
      req.destroy();
      resolve({ ok: false, status: 0 });
    });
    req.end();
  });
}

function probeDocker() {
  try {
    execSync('docker info', { stdio: 'pipe', timeout: 8000 });
    return { ok: true, detail: 'docker reachable' };
  } catch (e) {
    return { ok: false, detail: e.message?.split('\n')[0] || 'docker not running' };
  }
}

async function runInfraScan() {
  const reg = loadRegistry();
  const paths = reg.infrastructure_paths || {};
  const checks = [];

  checks.push({
    name: 'ANTHROPIC_API_KEY',
    ok: !!process.env.ANTHROPIC_API_KEY,
    detail: process.env.ANTHROPIC_API_KEY ? 'set' : 'missing',
  });

  for (const [key, p] of Object.entries(paths)) {
    checks.push({ name: key, ok: fileExists(p), detail: p });
  }

  const docker = probeDocker();
  checks.push({ name: 'docker', ...docker });

  const n8n = await probeHttp(5678);
  checks.push({ name: 'n8n:5678', ok: n8n.ok, detail: `status ${n8n.status}` });

  const chummoPort = await probeHttp(3000);
  checks.push({ name: 'chummo:3000', ok: chummoPort.ok, detail: `status ${chummoPort.status}` });

  return checks;
}

module.exports = { runInfraScan };
