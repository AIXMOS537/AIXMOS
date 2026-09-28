/**
 * JARVIS → TMMT OS production agent panel (/api/agents/evaluate).
 * Maps local council output to VISION, TANK, FLY_GUY, BOB, STICKS votes.
 */

const prompts = require('../agents/prompts');
const { runAgent } = require('./runner');
const {
  openEvaluationSession,
  castAgentVote,
  getEvaluationSession,
  newSubjectId,
} = require('./tmmt-api');

const PANEL_AGENTS = ['vision', 'tank', 'fly_guy', 'bob', 'sticks'];

const PANEL_PROMPTS = {
  vision: prompts.vision,
  tank: `You are TANK on the production governance panel. Vote approve/reject/abstain on infrastructure and execution plans.
${prompts.tank.split('OUTPUT')[0]}`,
  fly_guy: prompts.fly_guy,
  bob: prompts.bob,
  sticks: prompts.sticks,
};

async function inferVote(agent, situation, jarvisBrief) {
  const system = `${PANEL_PROMPTS[agent]}

You are casting a formal panel vote. Reply in EXACTLY this format:
VOTE: approve | reject | abstain
RATIONALE: [one or two sentences]`;

  const user = `Situation:\n${situation}\n\nJARVIS brief:\n${jarvisBrief}\n\nCast your vote now.`;

  const out = await runAgent({ system, userPrompt: user, maxTokens: 400 });
  const voteMatch = out.match(/VOTE:\s*(approve|reject|abstain)/i);
  const rationaleMatch = out.match(/RATIONALE:\s*([\s\S]+)/i);
  const vote = (voteMatch?.[1] || 'abstain').toLowerCase();
  const rationale = (rationaleMatch?.[1] || out).trim().slice(0, 500);
  return { vote, rationale, raw: out };
}

/**
 * Open panel session and cast all 5 votes based on situation + optional JARVIS brief.
 */
async function runProductionVote(situation, opts = {}) {
  const subjectId = opts.subjectId || newSubjectId();
  const subjectType = opts.subjectType || 'jarvis_infrastructure';

  const jarvisBrief =
    opts.jarvisBrief ||
    (await runAgent({
      system: prompts.jarvis,
      userPrompt: `Situation:\n${situation}\n\nProduce JARVIS BRIEF only.`,
    }));

  const opened = await openEvaluationSession({
    subjectType,
    subjectId,
    metadata: {
      source: 'aixmos-agents',
      situation: situation.slice(0, 2000),
      jarvis_excerpt: jarvisBrief.slice(0, 1500),
    },
    requiredApprovals: opts.requiredApprovals ?? 3,
    panelSize: opts.panelSize ?? 5,
  });

  const sessionId = opened.session?.id;
  if (!sessionId) throw new Error('No session id returned from openEvaluationSession');

  const votes = [];
  for (const agent of PANEL_AGENTS) {
    const { vote, rationale } = await inferVote(agent, situation, jarvisBrief);
    const result = await castAgentVote({
      sessionId,
      agent,
      vote,
      rationale,
      payload: { source: 'jarvis-votes' },
    });
    votes.push({ agent, vote, rationale, result });
  }

  const final = await getEvaluationSession(sessionId);
  return {
    sessionId,
    subjectId,
    subjectType,
    jarvisBrief,
    votes,
    final,
  };
}

module.exports = { runProductionVote, PANEL_AGENTS };
