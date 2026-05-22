#!/usr/bin/env node
const { runInteractiveAgent } = require('./lib/agent-cli');
runInteractiveAgent('fly_guy', { hint: 'FLY GUY — comms support under C.H.U.M.M.O voice.' }).catch(e => {
  console.error(e.message);
  process.exit(1);
});
