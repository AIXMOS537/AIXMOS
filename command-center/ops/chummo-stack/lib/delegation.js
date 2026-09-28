const path = require('path');
const { chatCompletion } = require(path.join(__dirname, '../../files/llm-client'));
const { MOOSE_DELEGATE_SYSTEM, BRAIN_DELEGATE_SYSTEM } = require('./prompts');

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function delegateToMoose(lead, chummoDraft, plan) {
  const name = lead.first_name || lead.name?.split(' ')[0] || lead.name || 'Lead';
  const prompt = `Lead: ${name}
Pipeline: ${plan.pipeline} | Stage: ${plan.stage}
Value: ${lead.estimated_value || 'unknown'}
Notes: ${lead.notes || 'none'}
CHUMMO draft (${plan.label}):
---
${chummoDraft}
---
Produce MOOSE output for this lead.`;

  const res = await chatCompletion({
    system: MOOSE_DELEGATE_SYSTEM,
    userMessage: prompt,
    maxTokens: 800,
  });
  return { agent: 'moose', ...res };
}

async function delegateToBrain(lead, chummoDraft, mooseOutput, plan) {
  const prompt = `High-priority lead assignment.
Name: ${lead.name}
Pipeline: ${plan.pipeline} | Stage: ${plan.stage}
CHUMMO message:
${chummoDraft}
MOOSE execution notes:
${mooseOutput?.text || 'none'}
Synthesize operator handoff.`;

  const res = await chatCompletion({
    system: BRAIN_DELEGATE_SYSTEM,
    userMessage: prompt,
    maxTokens: 500,
  });
  return { agent: 'brain', ...res };
}

module.exports = { delegateToMoose, delegateToBrain, sleep };
