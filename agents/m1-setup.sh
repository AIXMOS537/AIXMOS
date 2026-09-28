#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AIXMOS M1 MAC — ONE-SHOT SETUP
# Run on the M1 Mac (Rick / work Mac) from Terminal.
# Does everything: env, agents, GHL check, ProjectX feed, nightly cron.
# ═══════════════════════════════════════════════════════════
set -e

C_CYAN='\033[0;36m'; C_GREEN='\033[0;32m'; C_AMBER='\033[0;33m'
C_RED='\033[0;31m'; C_RESET='\033[0m'; C_BOLD='\033[1m'
log()  { echo -e "${C_CYAN}[AIXMOS]${C_RESET} $*"; }
ok()   { echo -e "${C_GREEN}[✓]${C_RESET} $*"; }
warn() { echo -e "${C_AMBER}[!]${C_RESET} $*"; }
die()  { echo -e "${C_RED}[✗]${C_RESET} $*"; exit 1; }

echo ""
echo -e "${C_BOLD}${C_CYAN}╔══════════════════════════════════════════╗${C_RESET}"
echo -e "${C_BOLD}${C_CYAN}║   AIXMOS M1 MAC — ONE-SHOT SETUP         ║${C_RESET}"
echo -e "${C_BOLD}${C_CYAN}╚══════════════════════════════════════════╝${C_RESET}"
echo ""

# ── 0. PREREQ CHECK ────────────────────────────────────────────────────────

log "Checking prerequisites..."
command -v node  >/dev/null || die "Node.js not found. Install from nodejs.org"
command -v npm   >/dev/null || die "npm not found."
command -v git   >/dev/null || die "git not found."
ok "Node $(node --version), npm $(npm --version)"

OLLAMA_OK=false
curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && OLLAMA_OK=true
if $OLLAMA_OK; then
  MODELS=$(curl -s http://localhost:11434/api/tags | node -e "process.stdin.resume();let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{const m=JSON.parse(d).models||[];console.log(m.map(x=>x.name).join(', '))}catch{console.log('unknown')}})")
  ok "Ollama LIVE — models: $MODELS"
else
  warn "Ollama not running on localhost:11434. Start it with: ollama serve"
fi

# ── 1. REPOS ───────────────────────────────────────────────────────────────

log "Setting up repos..."
mkdir -p ~/Projects

# TMMT
if [ -d ~/Projects/TMMT/.git ]; then
  ok "TMMT repo exists — pulling latest"
  git -C ~/Projects/TMMT pull --rebase --autostash 2>&1 | tail -3
else
  warn "TMMT repo not found at ~/Projects/TMMT"
  warn "Clone it: git clone https://github.com/AIxMOS537/TMMT.git ~/Projects/TMMT"
fi

# AIXMOS-AGENTS
if [ -d ~/Projects/AIXMOS-AGENTS/.git ]; then
  ok "AIXMOS-AGENTS repo exists — pulling latest"
  git -C ~/Projects/AIXMOS-AGENTS pull --rebase --autostash 2>&1 | tail -3
else
  warn "AIXMOS-AGENTS repo not found at ~/Projects/AIXMOS-AGENTS"
  warn "Clone it: git clone https://github.com/AIxMOS537/AIXMOS-AGENTS.git ~/Projects/AIXMOS-AGENTS"
fi

AGENTS_DIR=~/Projects/AIXMOS-AGENTS
[ -d "$AGENTS_DIR" ] || die "AIXMOS-AGENTS not found. Clone it first (see above), then re-run."

# ── 2. DEPS ────────────────────────────────────────────────────────────────

log "Installing npm dependencies..."
cd "$AGENTS_DIR"
npm install --silent
ok "npm deps ready"

# ── 3. GHL CREDENTIALS ────────────────────────────────────────────────────

log "Checking GHL credentials..."
mkdir -p ~/.config/tmmt
GHL_ENV=~/.config/tmmt/ghl.env

if [ -f "$GHL_ENV" ]; then
  source "$GHL_ENV" 2>/dev/null || true
fi

# Try pulling from Vercel if vercel CLI is available and key is missing
if [ -z "$GHL_API_KEY" ] || [ -z "$GHL_LOCATION_ID" ]; then
  if command -v vercel >/dev/null 2>&1; then
    log "Pulling env from Vercel (tmmt-ops project)..."
    cd ~/Projects/TMMT
    vercel env pull /tmp/vercel-pull.env --environment=production --yes 2>/dev/null || true
    if [ -f /tmp/vercel-pull.env ]; then
      GHL_API_KEY=$(grep "^GHL_API_KEY=" /tmp/vercel-pull.env | cut -d= -f2- | tr -d '"')
      GHL_LOCATION_ID=$(grep "^GHL_LOCATION_ID=" /tmp/vercel-pull.env | cut -d= -f2- | tr -d '"')
      rm -f /tmp/vercel-pull.env
      ok "Pulled GHL keys from Vercel"
    fi
  fi
fi

# If still missing — prompt once
if [ -z "$GHL_API_KEY" ]; then
  echo ""
  warn "GHL_API_KEY not found. Paste it now (or press Enter to skip):"
  read -r -s GHL_API_KEY_INPUT
  [ -n "$GHL_API_KEY_INPUT" ] && GHL_API_KEY="$GHL_API_KEY_INPUT"
fi

if [ -z "$GHL_LOCATION_ID" ]; then
  echo ""
  warn "GHL_LOCATION_ID not found. Paste it now (or press Enter to skip):"
  read -r GHL_LOC_INPUT
  [ -n "$GHL_LOC_INPUT" ] && GHL_LOCATION_ID="$GHL_LOC_INPUT"
fi

# Save to secrets file
if [ -n "$GHL_API_KEY" ] && [ -n "$GHL_LOCATION_ID" ]; then
  cat > "$GHL_ENV" <<EOF
GHL_API_KEY=$GHL_API_KEY
GHL_LOCATION_ID=$GHL_LOCATION_ID
EOF
  chmod 600 "$GHL_ENV"
  ok "GHL credentials saved to $GHL_ENV (mode 600)"
else
  warn "GHL keys not set — ProjectX feed will show zeros for deals/collected"
fi

# ── 4. AGENTS ENV ─────────────────────────────────────────────────────────

log "Configuring agents .env..."
cd "$AGENTS_DIR"

AGENTS_ENV="$AGENTS_DIR/.env"

# Set LLM backend to ollama if ollama is running
if $OLLAMA_OK; then
  BEST_MODEL="llama3.2:3b"
  # Prefer a chat-capable model if available
  for m in "qwen2.5:1.5b" "llama3.2:3b" "hermes3:8b" "qwen3:8b"; do
    if curl -s http://localhost:11434/api/tags | grep -q "\"$m\""; then
      BEST_MODEL="$m"
      break
    fi
  done
  ok "Using Ollama model: $BEST_MODEL"
  # Patch .env model line
  if [ -f "$AGENTS_ENV" ]; then
    sed -i '' "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$BEST_MODEL|" "$AGENTS_ENV"
    sed -i '' "s|^AIXMOS_LLM_BACKEND=.*|AIXMOS_LLM_BACKEND=ollama|" "$AGENTS_ENV"
  fi
fi

# Inject GHL keys into agents .env (no-op if already set)
if [ -n "$GHL_API_KEY" ] && [ -f "$AGENTS_ENV" ]; then
  if ! grep -q "^GHL_API_KEY=" "$AGENTS_ENV"; then
    echo "GHL_API_KEY=$GHL_API_KEY" >> "$AGENTS_ENV"
    echo "GHL_LOCATION_ID=$GHL_LOCATION_ID" >> "$AGENTS_ENV"
    ok "GHL keys injected into agents .env"
  else
    sed -i '' "s|^GHL_API_KEY=.*|GHL_API_KEY=$GHL_API_KEY|" "$AGENTS_ENV"
    sed -i '' "s|^GHL_LOCATION_ID=.*|GHL_LOCATION_ID=$GHL_LOCATION_ID|" "$AGENTS_ENV"
    ok "GHL keys updated in agents .env"
  fi
fi

# ── 5. RUN AGENT TESTS ────────────────────────────────────────────────────

log "Running agent health check..."
cd "$AGENTS_DIR"
node test-all-agents.js 2>&1 | tail -4

# ── 6. GHL STAGE CHECK ────────────────────────────────────────────────────

if [ -n "$GHL_API_KEY" ] && [ -n "$GHL_LOCATION_ID" ]; then
  log "Checking GHL pipeline stages..."
  node -e "
    process.env.GHL_API_KEY='$GHL_API_KEY';
    process.env.GHL_LOCATION_ID='$GHL_LOCATION_ID';
    fetch('https://services.leadconnectorhq.com/opportunities/search?location_id=$GHL_LOCATION_ID&limit=10',{
      headers:{Authorization:'Bearer $GHL_API_KEY',Version:'2021-07-28'}
    })
    .then(r=>r.json())
    .then(d=>{
      const opps=d?.opportunities??[];
      console.log('Total opps in GHL:', d?.meta?.total??'?');
      const stages={};
      opps.forEach(o=>{if(o.pipelineStageId)stages[o.status+':'+o.pipelineStageId]=(stages[o.status+':'+o.pipelineStageId]||0)+1;});
      Object.entries(stages).forEach(([k,v])=>console.log(' ',k,'('+v+')'));
    })
    .catch(e=>console.error('GHL error:',e.message));
  " 2>&1
fi

# ── 7. PROJECTX FEED ──────────────────────────────────────────────────────

log "Running ProjectX live feed..."
node "$AGENTS_DIR/projectx-feed.js" 2>&1

# Copy feed next to the RPG game
RPG_DIR=~/Documents/Claude/Projects/TRAP\ MONEY\ MOVES\ TIMELESS\ X\ 4HEPEOPLE
if [ -d "$RPG_DIR" ]; then
  cp "$AGENTS_DIR/projectx-feed.json" "$RPG_DIR/projectx-feed.json"
  ok "Feed copied to RPG folder"
fi

# ── 8. LAUNCHD — NIGHTLY CRON (11pm) ─────────────────────────────────────

log "Installing nightly ProjectX feed cron (11pm)..."

PLIST_LABEL="com.aixmos.projectx-feed"
PLIST_PATH=~/Library/LaunchAgents/$PLIST_LABEL.plist

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(command -v node)</string>
    <string>$HOME/Projects/AIXMOS-AGENTS/projectx-feed.js</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>23</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$HOME/Projects/AIXMOS-AGENTS/logs/projectx-feed-cron.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/Projects/AIXMOS-AGENTS/logs/projectx-feed-cron.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME</string>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
  </dict>
</dict>
</plist>
EOF

# Load (or reload) the plist
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
ok "Nightly cron installed — runs every night at 11:00 PM"

# ── 9. SSH REMOTE LOGIN REMINDER ──────────────────────────────────────────

SSH_STATUS=$(sudo systemsetup -getremotelogin 2>/dev/null || echo "unknown")
if echo "$SSH_STATUS" | grep -qi "off\|unknown"; then
  echo ""
  warn "SSH Remote Login is OFF. To let your carry Mac connect directly:"
  warn "  System Settings → General → Sharing → Remote Login → ON"
  warn "  Or run: sudo systemsetup -setremotelogin on"
fi

# ── DONE ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${C_BOLD}${C_GREEN}╔══════════════════════════════════════════╗${C_RESET}"
echo -e "${C_BOLD}${C_GREEN}║   DONE. M1 Mac is wired and running.     ║${C_RESET}"
echo -e "${C_BOLD}${C_GREEN}╚══════════════════════════════════════════╝${C_RESET}"
echo ""
echo -e "  ${C_CYAN}Run agents anytime:${C_RESET}   cd ~/Projects/AIXMOS-AGENTS && node orchestrator.js"
echo -e "  ${C_CYAN}ProjectX feed:${C_RESET}        npm run projectx"
echo -e "  ${C_CYAN}Agent health:${C_RESET}         node test-all-agents.js"
echo -e "  ${C_CYAN}Nightly feed:${C_RESET}         Auto-runs 11pm via launchd"
echo ""
