═══════════════════════════════════════════════════════
 AIXMOS AGENT NETWORK v2.0
 Five agents. One system. Lock and key.
 For the people. By the people.
═══════════════════════════════════════════════════════

THE FIVE AGENTS
───────────────────────────────────────────────────────
  CHUMMO        Messaging — outreach, follow-ups, welcome
  MOOSE         Execution — pathways, tasks, SOPs, briefs
  VISION        Quality control — reviews before sending
  CAPTAIN       Accountability — shield checks, audits
  WONDER WOMAN  Ops + fix — responds to Cap's flags

═══════════════════════════════════════════════════════
INSTALL — ONE COMMAND
═══════════════════════════════════════════════════════

  Mac:     bash install-mac.sh
  Windows: install-windows.bat   (or double-click)

═══════════════════════════════════════════════════════
RUN
═══════════════════════════════════════════════════════

  Mac (after install):
    aixmos      all 5 agents
    chummo      CHUMMO only
    moose       MOOSE only
    vision      VISION only
    captain     Captain only
    ww          Wonder Woman only
    brief       Morning brief
    contacts    Contact manager

  Windows (Desktop shortcuts created by installer):
    AIXMOS.bat          all 5 agents
    chummo.bat          CHUMMO
    moose.bat           MOOSE
    vision.bat          VISION
    captain.bat         Captain
    wonder-woman.bat    Wonder Woman
    morning-brief.bat   Morning brief

  Git Bash / Terminal (direct):
    node orchestrator.js
    node chummo.js
    node vision.js
    node briefing.js
    node contacts.js
    node scheduler.js

═══════════════════════════════════════════════════════
LOCK AND KEY PIPELINE
═══════════════════════════════════════════════════════

  CHUMMO → MOOSE → CAPTAIN → WONDER WOMAN → VISION

  Each agent passes context to the next automatically.
  State stored in: aixmos-state.json

═══════════════════════════════════════════════════════
FIRST TIME CHECKLIST
═══════════════════════════════════════════════════════

  1. Run install script
  2. Get API key: console.anthropic.com
  3. node setup.js (configure Telegram etc.)
  4. node contacts.js (add your first leads)
  5. node orchestrator.js (start the network)

═══════════════════════════════════════════════════════
  AIXMOS · For the people. By the people.
═══════════════════════════════════════════════════════
