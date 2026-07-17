AIXMOS AGENT NETWORK - LOAD FIRST

WINDOWS
1. Copy this whole folder to your flash drive.
2. On the target computer, open the folder.
3. Double-click LOAD-ME-FIRST-WINDOWS.bat.
4. If asked for an AIXMOS API key, paste it in.
5. Use the Desktop launchers that get created:
   - AIXMOS.bat
   - chummo.bat
   - moose.bat
   - vision.bat
   - captain.bat
   - wonder-woman.bat
   - morning-brief.bat

DIRECT RUN
If you do not want to install, open a terminal in this folder and run:

  node orchestrator.js

Other direct commands:

  node chummo.js
  node moose.js
  node vision.js
  node captain.js
  node wonderwoman.js
  node briefing.js
  node contacts.js
  node scheduler.js

REQUIREMENTS
- Node.js must be installed.
- ANTHROPIC_API_KEY must be set or entered during install.

NOTES
- Dependencies are included in node_modules for quick loading.
- If node_modules is missing, install-windows.bat runs npm install.
- Agent state is saved in aixmos-state.json.
- Saved outputs go into the outbox folder.
