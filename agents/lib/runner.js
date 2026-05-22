#!/usr/bin/env node
/**
 * Shared LLM runner for all AIXMOS agents.
 * Backend (Claude / Ollama / auto) is selected by lib/llm.js via AIXMOS_LLM_BACKEND.
 */

const fs = require('fs');
const path = require('path');

const { generate, DEFAULT_CLAUDE_MODEL } = require('./llm');

const DEFAULT_MODEL = DEFAULT_CLAUDE_MODEL();

async function runAgent({ system, userPrompt, maxTokens = 2500 }) {
  return generate({ system, prompt: userPrompt, maxTokens });
}

function loadRegistry() {
  const p = path.join(__dirname, '..', 'agents', 'registry.json');
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function extractHandoff(output, tag) {
  const re = new RegExp(`${tag}:\\s*([\\s\\S]+?)(?=\\n[A-Z_]+_HANDOFF:|$)`, 'i');
  const m = output.match(re);
  return m ? m[1].trim() : null;
}

module.exports = { runAgent, loadRegistry, extractHandoff, DEFAULT_MODEL };
