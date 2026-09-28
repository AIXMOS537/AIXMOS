#!/usr/bin/env node
const { runInteractiveAgent } = require('./lib/agent-cli');
runInteractiveAgent('wonder_woman', { hint: 'WONDERWOMAN — trust, unpleasant CX, moral guard.' }).catch(e => {
  console.error(e.message);
  process.exit(1);
});
