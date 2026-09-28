#!/usr/bin/env node
/**
 * Standalone MOOSE pathway batch — same output as chummo-draft-leads --pathway-only.
 * Use when CHUMMO drafts already exist and you only need fresh action plans.
 */
const { spawnSync } = require('child_process');
const path = require('path');

const script = path.join(__dirname, 'chummo-draft-leads.js');
const args = ['--pathway-only', ...process.argv.slice(2)];
const r = spawnSync(process.execPath, [script, ...args], { stdio: 'inherit' });
process.exit(r.status ?? 1);
