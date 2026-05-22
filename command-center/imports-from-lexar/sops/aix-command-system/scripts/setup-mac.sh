#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "AIX setup — Mac"
echo "Project: $ROOT"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found."
  echo "Install: https://www.python.org/downloads/ or run: brew install python"
  exit 1
fi

echo "Python: $(python3 --version)"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit it with your Airtable token and base ID."
else
  echo ".env already exists — leaving it unchanged."
fi

chmod +x scripts/*.sh 2>/dev/null || true

echo ""
echo "Quick test:"
# shellcheck disable=SC1091
source scripts/load-env.sh 2>/dev/null || true
python3 aix_operator.py list || python3 aix_operator.py list

echo ""
echo "Done. Next steps:"
echo "  1. Edit .env (AIRTABLE_API_KEY, AIRTABLE_BASE_ID)"
echo "  2. ./scripts/aix airtable list-templates"
echo "  3. Open this folder in Cursor"
