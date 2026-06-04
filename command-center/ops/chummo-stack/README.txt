═══════════════════════════════════════════════════════
 AIXMOS · FLASH DRIVE
 CHUMMO + Portal + Training Vault
 For the people. By the people.
═══════════════════════════════════════════════════════

WHAT'S ON THIS DRIVE
─────────────────────────────────────────────────────
  chummo.js          The CHUMMO messaging agent (terminal)
  serve.js           Local web server (portal + landing page)
  start-mac.sh       Mac launcher — double-click or run in terminal
  start-windows.bat  Windows launcher — double-click
  package.json       Dependencies
  node_modules/      Pre-installed (no npm install needed)

  public/
    index.html       AIXMOS landing page
    apply.html       CHUMMO intake form
    thankyou.html    Post-submission page
    operator.html    Operator application page

  portal/
    index.html       Private 4-role portal (login required)

  files/
    operator-training.html  14-section operator manual
    intake-form.html        CHUMMO intake form (standalone)
    pipeline.html           GHL pipeline guide

═══════════════════════════════════════════════════════
INSTALL (READ FIRST ON ANY COMPUTER)
═══════════════════════════════════════════════════════

  See INSTALL.md at the USB root (one folder above this folder).
  Mac:   bash install.sh
  Win:   install.bat

═══════════════════════════════════════════════════════
HOW TO USE — MAC
═══════════════════════════════════════════════════════

OPTION A: Terminal messaging agent (CHUMMO)
  1. Open Terminal
  2. cd to USB (example: cd /Volumes/AIXMOS02/CHUMMOCLAUDEOS)
  3. bash start-mac.sh
  4. Follow the prompts

OPTION B: Full web portal + landing page
  1. cd to this folder on the USB
  2. node serve.js
  3. Open browser → http://localhost:3000
  4. Portal login → http://localhost:3000/portal
  NOTE: public/ and portal/ folders must exist or pages 404.

═══════════════════════════════════════════════════════
HOW TO USE — WINDOWS
═══════════════════════════════════════════════════════

OPTION A: Terminal messaging agent (CHUMMO)
  1. Double-click start-windows.bat (in this folder)
  2. Follow the prompts

OPTION B: Full web portal + landing page
  1. Open Command Prompt in this folder
  2. node serve.js
  3. Open browser → http://localhost:3000

═══════════════════════════════════════════════════════
FIRST TIME SETUP
═══════════════════════════════════════════════════════

1. Install Node.js from https://nodejs.org (LTS version)
2. Get your Anthropic API key from https://console.anthropic.com
3. Run the launcher — it will ask for your API key on first use
4. The key gets saved to your Mac/PC so you never enter it again

═══════════════════════════════════════════════════════
PORTAL AUTH (READ BEFORE DISTRIBUTING)
═══════════════════════════════════════════════════════

  portal/index.html is a PLACEHOLDER — no login gate yet.
  Do NOT put real passwords in README or HTML on a flash drive.

  Before sharing on a network or USB:
  1. Add auth (Supabase Auth, or server-side session in serve.js)
  2. Store credentials only in local .env (never commit / never print in docs)
  3. Rotate any password that was ever written in an old copy of this file

═══════════════════════════════════════════════════════
WHAT CHUMMO CAN WRITE
═══════════════════════════════════════════════════════

  1.  First outreach — SMS
  2.  First outreach — Email
  3.  Follow-up — SMS
  4.  Post-call recap — Email
  5.  Payment reminder — SMS
  6.  Upgrade conversation — Email
  7.  Re-engagement — SMS
  8.  Referral ask — SMS
  9.  Welcome — after payment
  10. Operator invite — Email

═══════════════════════════════════════════════════════
BRAIN ORCHESTRATOR
═══════════════════════════════════════════════════════

  Run the multi-agent brain flow locally from the root folder:
    node files/brain.js

  This workflow will:
  - run multiple AIXMOS agents in sequence
  - confine the assignment scope and options
  - synthesize a delegation plan for the team
  - optionally send the final team message via iMessage on macOS

═══════════════════════════════════════════════════════
SUPPORT
═══════════════════════════════════════════════════════

AIXMOS · Muhammad Taha
For the people. By the people.
Target: $10,000/month for every client.

═══════════════════════════════════════════════════════
