#!/usr/bin/env node

const readline = require('readline');
const { ask, copyToClipboard, saveAgentContext, getAllAgentContext, sendText } = require('./shared-utils');

let Anthropic;
try {
  Anthropic = require('@anthropic-ai/sdk');
} catch {
  console.error('Missing dependency. Run: npm install @anthropic-ai/sdk');
  process.exit(1);
}

const client = new Anthropic.default();

const AGENTS = [
  {
    key: 'chummo',
    label: 'CHUMMO',
    desc: 'Messaging agent that writes outreach, follow-up, and client-facing copy.',
    options: [
      { title: 'Empathy first', description: 'Lead with the person, not the pitch. Short, conversational, human.' },
      { title: 'Urgent action', description: 'Create immediacy, move the lead toward a next step in the next 24 hours.' },
      { title: 'Value-focused', description: 'Frame the message around the specific result or benefit they unlock.' },
    ],
  },
  {
    key: 'moose',
    label: 'MOOSE',
    desc: 'Execution agent that identifies the exact operational tasks and next steps.',
    options: [
      { title: 'Quick triage', description: 'Pick the fastest practical path and assign what must happen now.' },
      { title: 'System build', description: 'Define the process, dependencies, and handoff points for execution.' },
      { title: 'Risk control', description: 'Focus on avoiding mistakes, confirming ownership, and reducing friction.' },
    ],
  },
  {
    key: 'vision',
    label: 'VISION',
    desc: 'Quality control agent that checks clarity, tone, and execution readiness.',
    options: [
      { title: 'Tight and clear', description: 'Keep only what is essential and make every instruction unambiguous.' },
      { title: 'High standard', description: 'Raise the language to premium while preserving speed and actionability.' },
      { title: 'Error-proof', description: 'Identify weak assumptions and rewrite to prevent misunderstandings.' },
    ],
  },
  {
    key: 'pipeline',
    label: 'PIPELINE',
    desc: 'Pipeline agent that determines lead priority and the best sequencing of work.',
    options: [
      { title: 'Top priorities', description: 'Sort what must happen first this week and why.' },
      { title: 'Bottleneck cleanup', description: 'Find the one place where work is stuck and remove it.' },
      { title: 'Growth path', description: 'Choose the next development step that scales revenue or capacity.' },
    ],
  },
  {
    key: 'operator',
    label: 'OPERATOR',
    desc: 'Operator briefing agent that turns strategy into a direct task handoff.',
    options: [
      { title: 'Call prep', description: 'Give the operator exactly what to say, ask, and record.' },
      { title: 'Client check-in', description: 'Outline the check-in plan and the exact follow-up asks.' },
      { title: 'Delivery launch', description: 'Make the first operational step clear and easy to execute.' },
    ],
  },
  {
    key: 'automation',
    label: 'AUTOMATION',
    desc: 'Automation agent that identifies which tasks can be systematized and how.',
    options: [
      { title: 'Quick wins', description: 'Highlight the first automations that save time immediately.' },
      { title: 'Workflow builder', description: 'Map the sequence, triggers, and action steps to automate.' },
      { title: 'Fail-safe', description: 'Add checks and escalation rules to prevent missed handoffs.' },
    ],
  },
];

const SYSTEM = `You are BRAIN — the synthesis and delegation engine for AIXMOS. You receive structured inputs from specialized agents and turn them into a single clear assignment plan for the team.

Your role:
- Confine the assignment: what is the exact problem, scope, and expected outcome?
- Organize the answers from each agent and turn them into owned tasks.
- Create one short text message for the team with the key delegation instructions.
- Use the tone of a commander who trusts the team but is precise and direct.

Output structure:
1) SCOPE: one sentence summarizing the assignment.
2) DELIVERABLES: three concrete outputs the team must produce.
3) TASKS: a numbered list with owner, timing, and exact action.
4) TEAM MESSAGE: a single message suitable for a text broadcast.
5) IF iMessage delivery is enabled, indicate the recipient handles or roles.`;

function println(text = '') { console.log(text); }
function hr(char = '─', len = 70) { println(char.repeat(len)); }
function print(text) { process.stdout.write(text); }

function buildAgentPrompt(agent, problem, context, params) {
  const lines = [
    `You are ${agent.label}. ${agent.desc}`,
    `Problem: ${problem}`,
    `Context: ${context}`,
    `Urgency: ${params.urgency || 'Not provided'}`,
    `Goal: ${params.goal || 'Not provided'}`,
    '',
    'Choose one of these three response approaches and explain why it fits best:',
  ];

  agent.options.forEach((option, index) => {
    lines.push(`${index + 1}. ${option.title} — ${option.description}`);
  });

  lines.push('',
    'Please respond in the following format:',
    'OPTION: 1 | 2 | 3',
    'RATIONALE: one short paragraph',
    'RESPONSE: the final answer for your agent, with the selected approach applied.',
  );

  return lines.join('\n');
}

function buildBrainPrompt(problem, context, agentResults) {
  const lines = [
    `Problem: ${problem}`,
    `Context: ${context}`,
    '',
    'Agent outputs:',
  ];

  agentResults.forEach(result => {
    lines.push(`-- ${result.label} --`);
    lines.push(result.output.trim());
    lines.push('');
  });

  lines.push('',
    'Using the information above, produce a single assignment plan with the requested structure.',
    'Do not invent extra roles or tasks beyond what the team can execute directly.',
  );

  return lines.join('\n');
}

async function runAgent(agent, problem, context, params) {
  const prompt = buildAgentPrompt(agent, problem, context, params);
  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1200,
    system: `You are ${agent.label}. ${agent.desc}`,
    messages: [{ role: 'user', content: prompt }],
  });
  return response.content[0].text;
}

async function runBrain(problem, context, agentResults) {
  const prompt = buildBrainPrompt(problem, context, agentResults);
  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1500,
    system: SYSTEM,
    messages: [{ role: 'user', content: prompt }],
  });
  return response.content[0].text;
}

async function main() {
  println();
  println('AIXMOS BRAIN ORCHESTRATOR');
  hr();

  if (!process.env.ANTHROPIC_API_KEY) {
    println('No API key found. Set ANTHROPIC_API_KEY and rerun.');
    process.exit(1);
  }

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  const problem = await ask(rl, 'Describe the core problem or client assignment: ');
  const context = await ask(rl, 'Any relevant context or background: ', true);
  const urgency = await ask(rl, 'Urgency (critical/moderate/low): ', true);
  const goal = await ask(rl, 'Desired outcome or target result: ', true);
  const team = await ask(rl, 'Who is available to execute this? (operators/executives/etc.): ', true);

  const agentResults = [];

  for (const agent of AGENTS) {
    println();
    hr();
    println(`RUNNING ${agent.label}`);
    hr();

    const output = await runAgent(agent, problem, context, { urgency, goal, team });
    println();
    println(output);
    println();

    saveAgentContext(agent.key, { problem, context, urgency, goal, team, output });
    println(`Saved ${agent.label} result to shared context.`);

    agentResults.push({ label: agent.label, output });
  }

  println();
  hr('═');
  println('SYNTHESIZING WITH BRAIN');
  hr('═');

  const brainOutput = await runBrain(problem, context, agentResults);
  println();
  println(brainOutput);
  println();

  saveAgentContext('brain', { problem, context, urgency, goal, team, output: brainOutput });
  println('Saved BRAIN output to shared context.');

  const copy = await ask(rl, 'Copy BRAIN output to clipboard? (y/n): ', true);
  if (copy.toLowerCase() === 'y') {
    const copied = copyToClipboard(brainOutput);
    println(copied ? 'Copied to clipboard.' : 'Unable to copy to clipboard.');
  }

  const deliver = await ask(rl, 'Send the team message via iMessage? (y/n): ', true);
  if (deliver.toLowerCase() === 'y') {
    const recipients = await ask(rl, 'Enter comma-separated iMessage handles (+number or email): ');
    const handles = recipients.split(',').map(s => s.trim()).filter(Boolean);
    const messageStart = brainOutput.match(/TEAM MESSAGE:(.*)/i);
    const text = messageStart ? messageStart[1].trim() : brainOutput;

    for (const recipient of handles) {
      const success = sendText(recipient, text);
      println(success ? `Sent iMessage to ${recipient}` : `Failed to send to ${recipient}`);
    }
  }

  rl.close();
}

main().catch(err => {
  console.error('Fatal error:', err.message);
  process.exit(1);
});
