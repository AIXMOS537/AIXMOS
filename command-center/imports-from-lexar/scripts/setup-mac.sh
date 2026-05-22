#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "AIX AI Command System — setup"
echo "Project: $ROOT"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install from https://www.python.org/downloads/ or: brew install python"
  exit 1
fi

echo "Python: $(python3 --version)"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  echo "Created virtual environment at .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
echo "Installed Python dependencies"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your Airtable token and base ID."
else
  echo ".env already exists — leaving it unchanged."
fi

if [[ ! -f config/tmmt_integration.json ]]; then
  cp config/tmmt_integration.example.json config/tmmt_integration.json
  echo "Created config/tmmt_integration.json — edit table names to match your TMMT base."
fi

chmod +x scripts/*.sh scripts/aix 2>/dev/null || true

echo ""
echo "Quick test:"
./scripts/aix list | head -15

echo ""
echo "Done. Next steps:"
echo "  1. Edit .env (AIRTABLE_API_KEY, AIRTABLE_BASE_ID)"
echo "  2. ./scripts/aix airtable list-templates"
echo "  3. ./scripts/aix airtable sync-templates   # after keys are set"
echo "  4. See TEAM_DEPLOY.md for rolling out to your team"
