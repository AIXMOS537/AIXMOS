#!/usr/bin/env bash
# Fix aix-biz on this Mac: strip CRLF from ~/.zshrc, install ~/bin/aix-biz, reload shell config.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZSHRC="${HOME}/.zshrc"
BIN="${HOME}/bin"

echo "=== AIX Business Ops installer ==="

# Strip Windows ^M from zshrc if present
if [[ -f "$ZSHRC" ]]; then
  if grep -q $'\r' "$ZSHRC" 2>/dev/null; then
    echo "Fixing CRLF in $ZSHRC …"
    perl -pi -e 's/\r\n/\n/g; s/\r/\n/g' "$ZSHRC"
  fi
fi

mkdir -p "$BIN"
ln -sf "${ROOT}/scripts/aix-biz" "${BIN}/aix-biz"
chmod +x "${ROOT}/scripts/aix-biz"
echo "Linked: ${BIN}/aix-biz → ${ROOT}/scripts/aix-biz"

# Ensure zshrc has function (append block only if missing)
if [[ -f "$ZSHRC" ]] && ! grep -q 'AIX_COMMAND_CENTER' "$ZSHRC" 2>/dev/null; then
  cat >>"$ZSHRC" <<'EOF'

# AIX Business Ops
export AIX_COMMAND_CENTER="${HOME}/dev/AIX_Command_Center"
unalias aix-biz 2>/dev/null || true
aix-biz() {
  "${AIX_COMMAND_CENTER}/scripts/aix-biz" "$@"
}
[[ -d "${HOME}/bin" ]] && export PATH="${HOME}/bin:${PATH}"
EOF
  echo "Appended aix-biz block to $ZSHRC"
else
  echo "zshrc already has AIX_COMMAND_CENTER — run: source ~/.zshrc"
fi

echo ""
echo "Done. In THIS terminal run:"
echo "  unalias aix-biz 2>/dev/null; source ~/.zshrc"
echo "  type aix-biz"
echo "  aix-biz channels"
echo ""
echo "Or without zshrc:"
echo "  ${BIN}/aix-biz channels"
