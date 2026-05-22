#!/usr/bin/env node
/**
 * Simple "Ask the Brain" — one question, plain answer.
 */

const readline = require('readline');
const { loadAixmosEnv } = require('./lib/env');
const prompts = require('./agents/prompts');
const { runAgent } = require('./lib/runner');

loadAixmosEnv();

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

function ask(q) {
  return new Promise(r => rl.question(q, a => r(a.trim())));
}

function simplify(text) {
  return text
    .replace(/\*\*/g, '')
    .replace(/^#+\s/gm, '')
    .slice(0, 4000);
}

async function main() {
  console.log('');
  console.log('  Ask the Brain anything about your business.');
  console.log('  (Example: Who needs a car? What should I do today?)');
  console.log('');

  try { require('./lib/env').requireLLMBackend(); }
  catch (e) {
    console.log(`  ${e.message}`);
    console.log('');
    rl.close();
    process.exit(1);
  }

  const question = await ask('  Your question: ');
  if (!question) {
    console.log('  (Nothing typed — try again.)');
    rl.close();
    return;
  }

  console.log('');
  console.log('  Thinking...');
  console.log('');

  try {
    const answer = await runAgent({
      system: `${prompts.jarvis}

Answer in plain English. Short sentences. No jargon.
Use numbered steps if there is more than one thing to do.
Rentals and customers come first.`,
      userPrompt: question,
      maxTokens: 1500,
    });
    console.log('  ─────────────────────────────────────');
    console.log(simplify(answer));
    console.log('  ─────────────────────────────────────');
  } catch (e) {
    console.log('  Something went wrong:', e.message);
  }

  console.log('');
  rl.close();
}

main();
