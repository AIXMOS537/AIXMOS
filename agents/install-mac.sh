#!/bin/bash
# ═══════════════════════════════════════════════════════
# AIXMOS AGENT NETWORK — MAC INSTALLER (v3, 10 agents + offline-ready)
# Mirrors the full agent tree to ~/AIXMOS, creates per-agent aliases,
# configures API key, and tells you how to enable offline (Ollama) mode.
#
# RUN:
#   bash /Volumes/LEXAR/AIXMOS-AGENTS/install-mac.sh
#   (or)  bash install-mac.sh   from inside the AIXMOS-AGENTS folder
# ═══════════════════════════════════════════════════════

set -e
BLUE='\033[0;34m'; GREEN='\033[0;32m'; RED='\033[0;31m'
YELLOW='\033[1;33m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'
CYAN='\033[0;36m'

clear
echo ""
echo -e "${BLUE}${BOLD}  ╔════════════════════════════════════════════════════╗${RESET}"
echo -e "${BLUE}${BOLD}  ║  AIXMOS AGENT NETWORK — MAC INSTALLER (10 agents)  ║${RESET}"
echo -e "${BLUE}${BOLD}  ║  CHUMMO · MOOSE · CAPTAIN · WONDER WOMAN · VISION  ║${RESET}"
echo -e "${BLUE}${BOLD}  ║  JARVIS · TANK · FLY GUY · BOB · STICKS            ║${RESET}"
echo -e "${BLUE}${BOLD}  ╚════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${DIM}For the people. By the people.${RESET}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/AIXMOS"
echo -e "  ${DIM}Source:      $SCRIPT_DIR${RESET}"
echo -e "  ${DIM}Install to:  $INSTALL_DIR${RESET}"
echo ""

# ── STEP 1: NODE.JS ────────────────────────────────────
echo -e "  ${BOLD}[1/6] Checking Node.js...${RESET}"
if command -v node >/dev/null 2>&1; then
  echo -e "  ${GREEN}✓ Node.js installed: $(node --version)${RESET}"
else
  echo -e "  ${YELLOW}Node.js not found.${RESET}"
  if command -v brew >/dev/null 2>&1; then
    echo -e "  ${DIM}Installing via Homebrew...${RESET}"
    brew install node
  else
    echo -e "  ${YELLOW}Homebrew not found either.${RESET}"
    echo -e "  ${DIM}Install Node.js LTS from https://nodejs.org then re-run.${RESET}"
    exit 1
  fi
fi
echo ""

# ── STEP 2: MIRROR TREE ───────────────────────────────
echo -e "  ${BOLD}[2/6] Mirroring agent tree to $INSTALL_DIR...${RESET}"
mkdir -p "$INSTALL_DIR"
# rsync mirror, preserve state file
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude 'agents/rick.js' \
    --exclude 'aixmos-state.json' \
    --exclude '.DS_Store' \
    --exclude '.Spotlight-V100' \
    --exclude '.Trashes' \
    --exclude '.fseventsd' \
    "$SCRIPT_DIR/" "$INSTALL_DIR/"
else
  cp -R "$SCRIPT_DIR/." "$INSTALL_DIR/"
  # The rsync path excludes the owner-tier agent; this fallback must match it, or a
  # machine without rsync gets a copy the rsync path deliberately withholds.
  rm -f "$INSTALL_DIR/agents/rick.js"
fi
echo -e "  ${GREEN}✓ Tree mirrored. State file preserved.${RESET}"
echo ""

# ── STEP 3: NPM DEPS ──────────────────────────────────
echo -e "  ${BOLD}[3/6] Verifying node_modules...${RESET}"
cd "$INSTALL_DIR"
if [ -d "$INSTALL_DIR/node_modules/@anthropic-ai/sdk" ]; then
  echo -e "  ${GREEN}✓ node_modules already present${RESET}"
else
  echo -e "  ${DIM}Running npm install...${RESET}"
  npm install --silent
fi
echo ""

# ── STEP 4: API KEY ───────────────────────────────────
echo -e "  ${BOLD}[4/6] Anthropic API key...${RESET}"
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo -e "  ${YELLOW}No ANTHROPIC_API_KEY in environment.${RESET}"
  echo -e "  ${DIM}Get yours at https://console.anthropic.com${RESET}"
  echo ""
  read -p "  Paste your API key (or Enter to skip): " API_KEY
  if [ -n "$API_KEY" ]; then
    export ANTHROPIC_API_KEY="$API_KEY"
    for profile in ~/.zshrc ~/.bash_profile ~/.bashrc; do
      if [ -f "$profile" ] && ! grep -q "ANTHROPIC_API_KEY" "$profile"; then
        echo "export ANTHROPIC_API_KEY=\"$API_KEY\"" >> "$profile"
      fi
    done
    echo -e "  ${GREEN}✓ Key saved to shell profile(s)${RESET}"
  else
    echo -e "  ${DIM}Skipped. Set ANTHROPIC_API_KEY later or use offline mode.${RESET}"
  fi
else
  echo -e "  ${GREEN}✓ ANTHROPIC_API_KEY already set${RESET}"
fi
echo ""

# ── STEP 5: SHELL ALIASES FOR ALL 10 AGENTS ───────────
echo -e "  ${BOLD}[5/6] Creating shell aliases for all 10 agents...${RESET}"
ALIAS_BLOCK="
# AIXMOS Agent Network (10 agents)
alias aixmos='cd ~/AIXMOS && node orchestrator.js'
alias chummo='cd ~/AIXMOS && node orchestrator.js chummo'
alias moose='cd ~/AIXMOS && node moose.js'
alias captain='cd ~/AIXMOS && node captain.js'
alias ww='cd ~/AIXMOS && node wonderwoman.js'
alias vision='cd ~/AIXMOS && node vision.js'
alias jarvis='cd ~/AIXMOS && node jarvis.js'
alias tank='cd ~/AIXMOS && node tank.js'
alias flyguy='cd ~/AIXMOS && node flyguy.js'
alias bob='cd ~/AIXMOS && node bob.js'
alias sticks='cd ~/AIXMOS && node sticks.js'
alias brief='cd ~/AIXMOS && node briefing.js'
alias aixmos-tests='cd ~/AIXMOS && node test-all-agents.js --live'
alias aixmos-webhook='cd ~/AIXMOS/membership/services/chummo-ghl-webhook && node server.js'
# Offline-mode toggle
alias aixmos-offline='export AIXMOS_LLM_BACKEND=ollama; echo \"AIXMOS_LLM_BACKEND=ollama (session only). For permanent: add to ~/.zshrc\"'
alias aixmos-online='export AIXMOS_LLM_BACKEND=claude; echo \"AIXMOS_LLM_BACKEND=claude (session only)\"'
"
ADDED=false
for profile in ~/.zshrc ~/.bash_profile ~/.bashrc; do
  if [ -f "$profile" ]; then
    if ! grep -q "AIXMOS Agent Network (10 agents)" "$profile"; then
      echo "$ALIAS_BLOCK" >> "$profile"
      ADDED=true
    fi
  fi
done
if $ADDED; then
  echo -e "  ${GREEN}✓ Aliases added to shell profile(s)${RESET}"
  echo -e "  ${DIM}After terminal restart, type: aixmos / chummo / moose / etc.${RESET}"
else
  echo -e "  ${DIM}Aliases already present, skipped${RESET}"
fi
echo ""

# ── STEP 6: OPTIONAL SCHEDULE + OFFLINE NOTE ──────────
echo -e "  ${BOLD}[6/6] Optional: schedule morning brief at 7 AM via launchd...${RESET}"
read -p "  Set up auto morning brief at 7:00 AM? (y/n): " AUTO_SCHED
if [[ "$AUTO_SCHED" =~ ^[Yy]$ ]]; then
  PLIST_FILE="$HOME/Library/LaunchAgents/com.aixmos.briefing.plist"
  mkdir -p "$INSTALL_DIR/logs"
  cat > "$PLIST_FILE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aixmos.briefing</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which node)</string>
        <string>$INSTALL_DIR/briefing.js</string>
        <string>--silent</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>$ANTHROPIC_API_KEY</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>StartCalendarInterval</key>
    <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/briefing.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/briefing-error.log</string>
</dict>
</plist>
PLIST
  launchctl load "$PLIST_FILE" 2>/dev/null || true
  echo -e "  ${GREEN}✓ Morning brief scheduled daily at 7:00 AM${RESET}"
fi
echo ""

# ── DONE ──────────────────────────────────────────────
echo -e "  ${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${GREEN}${BOLD}  ✓ INSTALLED. Try it now:${RESET}"
echo -e "  ${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${BOLD}Open a new terminal, then:${RESET}"
echo -e "    ${CYAN}aixmos${RESET}            ${DIM}(master orchestrator menu)${RESET}"
echo -e "    ${CYAN}chummo${RESET}            ${DIM}(customer comms)${RESET}"
echo -e "    ${CYAN}brief${RESET}             ${DIM}(morning briefing)${RESET}"
echo -e "    ${CYAN}aixmos-tests${RESET}      ${DIM}(smoke test all 10 agents)${RESET}"
echo -e "    ${CYAN}aixmos-webhook${RESET}    ${DIM}(start CHUMMO-GHL webhook)${RESET}"
echo ""
echo -e "  ${BOLD}OFFLINE MODE (no internet required):${RESET}"
echo -e "    Install Ollama:  ${CYAN}brew install ollama && ollama serve &${RESET}"
echo -e "    Pull a model:    ${CYAN}ollama pull llama3.1:8b${RESET}"
echo -e "    Switch backend:  ${CYAN}aixmos-offline${RESET}    ${DIM}(or set AIXMOS_LLM_BACKEND=ollama)${RESET}"
echo ""
echo -e "  ${DIM}Files installed to: $INSTALL_DIR${RESET}"
echo -e "  ${DIM}Full guide:         $INSTALL_DIR/AIXMOS-GUIDE.pdf${RESET}"
echo ""
echo -e "  ${BLUE}For the people. By the people.${RESET}"
echo ""
