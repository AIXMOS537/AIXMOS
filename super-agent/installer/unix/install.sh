#!/usr/bin/env bash
# PROJECT AIXMOS // 4THEPEOPLE -- one-shot installer for macOS and Linux.
#
#   bash install.sh                      # from the folder that holds aixmos-app.zip
#   bash install.sh --role student       # student | employee | tmmt_pathway | tmmt_operator | builder | everything
#   flags: --dir PATH --port N --no-ollama --no-model --no-launch
#
# Installs to ~/AIXMOS, keeps memory/ on re-run (conversation, settings, CRM, media),
# creates a Python venv with requests + pillow, installs Ollama if missing, pulls
# qwen2.5:3b, writes start/stop launchers, starts the server and opens the first-boot intro.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/AIXMOS"; PORT=8770; ROLE=""; OLLAMA=1; MODEL=1; LAUNCH=1
MODEL_NAME="qwen2.5:3b"
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DEST="$2"; shift ;;
    --port) PORT="$2"; shift ;;
    --role) ROLE="$2"; shift ;;
    --no-ollama) OLLAMA=0 ;;
    --no-model) MODEL=0 ;;
    --no-launch) LAUNCH=0 ;;
  esac; shift
done
say(){ printf '\n\033[36m>>> %s\033[0m\n' "$*"; }
warn(){ printf '\033[33m    %s\033[0m\n' "$*"; }
OS="$(uname -s)"

echo "=============================================================="
echo "   PROJECT AIXMOS  //  4THEPEOPLE  //  $OS setup"
echo "=============================================================="

ZIP="$HERE/aixmos-app.zip"
[ -f "$ZIP" ] || { echo "aixmos-app.zip not found next to install.sh"; exit 1; }

if [ -z "$ROLE" ] && [ -t 0 ]; then
  echo; echo "Who is this machine for?"
  echo "  1) Student         (school, a program, or teaching yourself)"
  echo "  2) Employee        (get your job done faster; work data stays here)"
  echo "  3) TMMT pathway    (you want to become a licensed TMMT operator)"
  echo "  4) TMMT operator   (you already run rentals / detailing / dispatch / sales)"
  echo "  5) Entrepreneur    (build your own business, product or project)"
  echo "  6) Everything      (full station: all of the above + TMMT operator tools)"
  printf "Choose 1-6 [5]: "; read -r c
  case "$c" in 1) ROLE=student ;; 2) ROLE=employee ;; 3) ROLE=tmmt_pathway ;; 4) ROLE=tmmt_operator ;; 6) ROLE=everything ;; *) ROLE=aixmos_member ;; esac
fi
ROLE="${ROLE:-aixmos_member}"
[ "$ROLE" = "builder" ] && ROLE=aixmos_member
case "$ROLE" in all|full) ROLE=everything ;; esac

say "[1/6] Python 3"
PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  if [ "$OS" = "Darwin" ]; then warn "Python 3 missing. Installing the Xcode command line tools (a dialog will open)..."; xcode-select --install 2>/dev/null; fi
  if command -v apt-get >/dev/null; then sudo apt-get update -y && sudo apt-get install -y python3 python3-venv python3-pip; fi
  if command -v dnf >/dev/null; then sudo dnf install -y python3 python3-pip; fi
  PY="$(command -v python3 || true)"
  [ -n "$PY" ] || { echo "Install Python 3 (python.org) and re-run."; exit 1; }
fi
echo "    $($PY --version)"

say "[2/6] Unpacking AIXMOS to $DEST"
mkdir -p "$DEST"
TMP="$(mktemp -d)"
"$PY" - "$ZIP" "$TMP" <<'EOF'
import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])
EOF
if [ -d "$DEST/memory" ]; then
  # keep the user's memory; refresh only the kit (app content)
  rm -rf "$DEST/memory/kit"; cp -R "$TMP/memory/kit" "$DEST/memory/kit"
  rm -rf "$TMP/memory"; echo "    existing memory kept"
fi
cp -R "$TMP"/. "$DEST"/; rm -rf "$TMP"

say "[3/6] Python environment (requests, pillow)"
"$PY" -m venv "$DEST/.venv" 2>/dev/null || warn "venv unavailable; using system python"
VPY="$DEST/.venv/bin/python"; [ -x "$VPY" ] || VPY="$PY"
"$VPY" -m pip install --quiet --upgrade pip >/dev/null 2>&1
"$VPY" -m pip install --quiet requests pillow || warn "pip install failed; image rendering may be limited"

say "[4/6] Ollama + local model"
if ! command -v ollama >/dev/null; then
  if [ $OLLAMA -eq 1 ]; then
    if [ "$OS" = "Darwin" ]; then
      if command -v brew >/dev/null; then brew install ollama; else warn "Install Ollama from https://ollama.com/download (drag to Applications), then re-run."; fi
    else
      # download first, then run: a dropped connection can't execute half a script, and the file can be inspected
      OI="$(mktemp)"
      if curl -fsSL --proto '=https' --tlsv1.2 -o "$OI" https://ollama.com/install.sh && [ -s "$OI" ]; then
        sh "$OI" || warn "Ollama install failed; see https://ollama.com"
      else warn "could not download the Ollama installer; see https://ollama.com"; fi
      rm -f "$OI"
    fi
  else warn "skipped (--no-ollama)"; fi
fi
if command -v ollama >/dev/null; then
  curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1 || { (ollama serve >/dev/null 2>&1 &); sleep 4; }
  if [ $MODEL -eq 1 ]; then ollama list 2>/dev/null | grep -q "^$MODEL_NAME" && echo "    $MODEL_NAME present" || ollama pull "$MODEL_NAME"; fi
fi
command -v ffmpeg >/dev/null || warn "ffmpeg not found: video editing is off until you install it (brew install ffmpeg / apt install ffmpeg)"

say "[5/6] Role, launchers"
"$VPY" - "$DEST" "$ROLE" <<'EOF'
import sys, os; sys.path.insert(0, sys.argv[1])
from aixmos import genesis; genesis.seed(sys.argv[2]); print("    role:", sys.argv[2])
EOF
cat > "$DEST/start-aixmos.sh" <<EOF
#!/usr/bin/env bash
cd "$DEST"
curl -s -o /dev/null http://127.0.0.1:$PORT/api/telemetry || { nohup "$VPY" project_aixmos_server.py $PORT >/dev/null 2>&1 & sleep 3; }
( command -v open >/dev/null && open http://localhost:$PORT ) || ( command -v xdg-open >/dev/null && xdg-open http://localhost:$PORT ) || echo "Open http://localhost:$PORT"
EOF
cat > "$DEST/stop-aixmos.sh" <<EOF
#!/usr/bin/env bash
pkill -f "project_aixmos_server.py $PORT" && echo "AIXMOS stopped."
EOF
chmod +x "$DEST/start-aixmos.sh" "$DEST/stop-aixmos.sh"
if [ "$OS" = "Darwin" ]; then
  cp "$DEST/start-aixmos.sh" "$HOME/Desktop/AIXMOS.command" 2>/dev/null && chmod +x "$HOME/Desktop/AIXMOS.command"
elif [ -d "$HOME/.local/share/applications" ] || mkdir -p "$HOME/.local/share/applications"; then
  printf '[Desktop Entry]\nType=Application\nName=AIXMOS\nExec=%s\nTerminal=false\n' "$DEST/start-aixmos.sh" > "$HOME/.local/share/applications/aixmos.desktop"
fi

say "[6/6] Starting AIXMOS on port $PORT"
if [ $LAUNCH -eq 1 ]; then "$DEST/start-aixmos.sh"; else echo "    run $DEST/start-aixmos.sh"; fi
echo
echo "AIXMOS is installed at $DEST. It will introduce itself and learn what you are building."
