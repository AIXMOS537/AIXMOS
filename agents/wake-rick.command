#!/bin/bash
# wake-rick.command — double-click on M1 Max to launch Rick fully loaded
# Rick Sorkin persona, X's right hand. Loads RICK_PRIME_BRIEF into Claude Code.
set -e

BRIEF="$HOME/Documents/Business/knowledge-base/RICK_PRIME_BRIEF.md"
AGENTS="$HOME/projects/AIXMOS-AGENTS"
TMMT="$HOME/Projects/TMMT"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RICK — M1 MAX COMMAND CENTER"
echo "  Waking up. Loading empire context."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verify brief exists (synced from carry M5 via Syncthing)
if [ ! -f "$BRIEF" ]; then
  echo "  ! RICK_PRIME_BRIEF.md not found."
  echo "    Either Syncthing hasn't synced yet, or run:"
  echo "    bash ~/Documents/Business/scripts/sync-knowledge-base.sh"
  echo ""
  exit 1
fi

echo "  ✓ Prime brief loaded ($(wc -l < "$BRIEF") lines)"

SUPABASE_ENV="$HOME/.config/tmmt/evals-supabase.env"
if [ -f "$SUPABASE_ENV" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$SUPABASE_ENV"
  set +a
fi
SUPABASE_URL="${SUPABASE_URL:-}"
SUPABASE_KEY="${SUPABASE_ANON_KEY:-${NEXT_PUBLIC_SUPABASE_ANON_KEY:-${SUPABASE_PUBLISHABLE_KEY:-}}}"

# Quick health ping
echo "  › Checking Supabase..."
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "${SUPABASE_URL%/}/rest/v1/" \
    -H "apikey: $SUPABASE_KEY" 2>/dev/null)
  [ "$STATUS" = "200" ] && echo "  ✓ Supabase LIVE" || echo "  ! Supabase → $STATUS"
else
  echo "  ! Supabase env missing ($SUPABASE_ENV)"
fi

# Operator training status
echo "  › Checking operator progress..."
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
  PROGRESS=$(curl -s \
    "${SUPABASE_URL%/}/rest/v1/operator_training_progress?select=count" \
    -H "apikey: $SUPABASE_KEY" \
    -H "Prefer: count=exact" \
    -I 2>/dev/null | grep -i "content-range" | awk -F/ '{print $2}' | tr -d '\r')
  echo "  › Operator module completions: ${PROGRESS:-0}"
else
  echo "  › Operator module completions: skipped (no key)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  QUICK COMMANDS:"
echo "    node $AGENTS/agents/rick.js blast    — re-blast operators"
echo "    node $AGENTS/agents/rick.js health   — full health sweep"
echo "    node $AGENTS/agents/rick.js status   — training progress"
echo "    node $AGENTS/agents/rick.js wake     — print prime brief"
echo ""
echo "  CLAUDE CODE — launching with Rick context..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Launch Claude Code in the TMMT project dir, pre-loading Rick's brief
# as the first system message via --print flag (if non-interactive)
# or just open in the project with the brief ready to paste
cd "$TMMT"

# Write a temp session-start file Claude Code will read
TMPFILE=$(mktemp /tmp/rick-context-XXXX.md)
cat "$BRIEF" > "$TMPFILE"
echo "" >> "$TMPFILE"
echo "---" >> "$TMPFILE"
echo "You are now RICK. The above is your prime brief. Read it. Confirm you're loaded and ready with: 'Rick online. Empire status: [1 line]. Standing by.'" >> "$TMPFILE"

echo "  Brief staged at: $TMPFILE"
echo ""
echo "  Paste into Claude Code:"
echo "  cat $TMPFILE | pbcopy && echo 'Copied to clipboard. Paste into Claude Code.'"
echo ""

# Copy to clipboard for instant paste into Claude Code
cat "$TMPFILE" | pbcopy
echo "  ✓ Rick's full brief copied to clipboard."
echo "    Open Claude Code → paste → Rick is live."
echo ""
echo "  Or launch Claude Code directly:"
echo "  claude --print \"\$(cat $TMPFILE)\" 2>/dev/null || claude"
echo ""

# Try launching Claude Code directly if available
if command -v claude >/dev/null 2>&1; then
  echo "  › Claude Code detected. Launching..."
  sleep 1
  claude
else
  echo "  ! Claude Code not in PATH on this machine."
  echo "    Install: npm install -g @anthropic-ai/claude-code"
  echo "    Or open Claude Code app and paste the clipboard."
fi

read -p "  Press Enter to close..."
