#!/usr/bin/env node
const { runInteractiveAgent } = require('./lib/agent-cli');
runInteractiveAgent('bob', { hint: 'BOB — audit log, SOPs, documentation.' }).catch(e => {
  console.error(e.message);
  process.exit(1);
});
