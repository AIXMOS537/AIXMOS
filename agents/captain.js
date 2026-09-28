#!/usr/bin/env node
const { runInteractiveAgent } = require('./lib/agent-cli');
runInteractiveAgent('captain', { hint: 'CAPTAIN — priorities, routing, Rubik\'s cube moves.' }).catch(e => {
  console.error(e.message);
  process.exit(1);
});
