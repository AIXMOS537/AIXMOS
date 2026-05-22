# Portable AI Fleet Flash Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safe cross-platform `AIXMOS-PORTABLE-KIT` on the MASTER, WORK, and FIELD flash drives so they can be plugged into a Mac or Windows computer and used to start work.

**Architecture:** Add one portable-kit builder script with role-aware sync profiles and one shell test harness. The builder creates root entrypoints, role markers, Mac and Windows launcher scripts, clean source snapshots, docs, manifests, and verification reports inside `AIXMOS-PORTABLE-KIT` on each mounted drive. The first pass is non-destructive outside the clean kit folder.

**Tech Stack:** Bash, rsync, PowerShell launcher text, Windows batch launcher text, existing local repos under `~`.

---

## File Structure

- Create: `docs/superpowers/plans/2026-05-22-portable-ai-fleet-flash.md`
  - This implementation plan.
- Create: `scripts/portable-kit/build-portable-kit.sh`
  - Role-aware builder that creates and verifies kits on `/Volumes/AIXMOS02`, `/Volumes/CYBORG`, and `/Volumes/LEXAR`.
- Create: `scripts/portable-kit/tests/test-build-portable-kit.sh`
  - Bash integration test using temporary fake source folders and fake mounted drives.
- Generated on drives by the builder:
  - `/Volumes/<drive>/START-HERE.md`
  - `/Volumes/<drive>/README_LOAD_FIRST.txt`
  - `/Volumes/<drive>/START_MAC.command`
  - `/Volumes/<drive>/START_WINDOWS.bat`
  - `/Volumes/<drive>/AIXMOS-PORTABLE-KIT/START-HERE.md`
  - `/Volumes/<drive>/AIXMOS-PORTABLE-KIT/ROLE-<role>.md`
  - `/Volumes/<drive>/AIXMOS-PORTABLE-KIT/MANIFEST.txt`
  - `/Volumes/<drive>/AIXMOS-PORTABLE-KIT/checksums/SHA256SUMS.txt`
  - `/Volumes/<drive>/AIXMOS-PORTABLE-KIT/reports/verification.txt`

## Task 1: Add Failing Integration Test

**Files:**
- Create: `scripts/portable-kit/tests/test-build-portable-kit.sh`
- Test: `scripts/portable-kit/tests/test-build-portable-kit.sh`

- [ ] **Step 1: Create the test harness**

```bash
mkdir -p scripts/portable-kit/tests
cat > scripts/portable-kit/tests/test-build-portable-kit.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILDER="$REPO_ROOT/scripts/portable-kit/build-portable-kit.sh"
TMP_ROOT="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "expected file: $path"
}

assert_dir() {
  local path="$1"
  [[ -d "$path" ]] || fail "expected directory: $path"
}

assert_not_exists() {
  local path="$1"
  [[ ! -e "$path" ]] || fail "expected absent: $path"
}

assert_contains() {
  local path="$1"
  local text="$2"
  grep -Fq "$text" "$path" || fail "expected '$text' in $path"
}

make_source() {
  local base="$1"
  mkdir -p "$base/AI-OPS-STARTER/docs" \
    "$base/AIXMOS-AGENTS/lib" \
    "$base/AIX-Command-Center/guides" \
    "$base/AIX-Command-Center/docs" \
    "$base/portable-setup" \
    "$base/TMMT/src" \
    "$base/TMMT/node_modules/example" \
    "$base/TMMT/.next/cache" \
    "$base/Desktop"

  printf '# AI OPS\n' > "$base/AI-OPS-STARTER/README.md"
  printf '# AIXMOS\n' > "$base/AIXMOS-AGENTS/README.md"
  printf 'module.exports = {}\n' > "$base/AIXMOS-AGENTS/lib/llm.js"
  printf '# Command\n' > "$base/AIX-Command-Center/README.md"
  printf '# Guide\n' > "$base/AIX-Command-Center/guides/SPEAK_AND_VIBE_CODE_GUIDE.md"
  printf '# Portable\n' > "$base/portable-setup/README.md"
  printf '{"scripts":{"dev":"next dev"}}\n' > "$base/TMMT/package.json"
  printf 'console.log("app")\n' > "$base/TMMT/src/app.js"
  printf 'SECRET=do-not-copy\n' > "$base/TMMT/.env"
  printf 'cached\n' > "$base/TMMT/.next/cache/blob"
  printf 'dependency\n' > "$base/TMMT/node_modules/example/file"
  printf 'team guide\n' > "$base/Desktop/TEAM_SIMPLE_SETUP_GUIDE.txt"
}

make_volumes() {
  local root="$1"
  mkdir -p "$root/AIXMOS02" "$root/CYBORG" "$root/LEXAR"
}

SOURCE_ROOT="$TMP_ROOT/source"
VOLUMES_ROOT="$TMP_ROOT/volumes"
make_source "$SOURCE_ROOT"
make_volumes "$VOLUMES_ROOT"

[[ -x "$BUILDER" ]] || fail "builder is missing or not executable: $BUILDER"

PORTABLE_KIT_HOME="$SOURCE_ROOT" \
PORTABLE_KIT_VOLUMES_ROOT="$VOLUMES_ROOT" \
"$BUILDER" --apply

for drive in AIXMOS02 CYBORG LEXAR; do
  kit="$VOLUMES_ROOT/$drive/AIXMOS-PORTABLE-KIT"
  assert_dir "$kit"
  assert_file "$VOLUMES_ROOT/$drive/START-HERE.md"
  assert_file "$VOLUMES_ROOT/$drive/README_LOAD_FIRST.txt"
  assert_file "$VOLUMES_ROOT/$drive/START_MAC.command"
  assert_file "$VOLUMES_ROOT/$drive/START_WINDOWS.bat"
  assert_file "$kit/START-HERE.md"
  assert_file "$kit/MANIFEST.txt"
  assert_file "$kit/checksums/SHA256SUMS.txt"
  assert_file "$kit/reports/verification.txt"
  assert_contains "$kit/reports/verification.txt" "PASS"
  assert_not_exists "$kit/work/TMMT/.env"
  assert_not_exists "$kit/work/TMMT/node_modules"
  assert_not_exists "$kit/work/TMMT/.next"
done

assert_file "$VOLUMES_ROOT/AIXMOS02/AIXMOS-PORTABLE-KIT/ROLE-MASTER.md"
assert_file "$VOLUMES_ROOT/CYBORG/AIXMOS-PORTABLE-KIT/ROLE-WORK.md"
assert_file "$VOLUMES_ROOT/LEXAR/AIXMOS-PORTABLE-KIT/ROLE-FIELD.md"

assert_file "$VOLUMES_ROOT/AIXMOS02/AIXMOS-PORTABLE-KIT/work/TMMT/package.json"
assert_file "$VOLUMES_ROOT/CYBORG/AIXMOS-PORTABLE-KIT/work/TMMT/package.json"
assert_not_exists "$VOLUMES_ROOT/LEXAR/AIXMOS-PORTABLE-KIT/work/TMMT/package.json"
assert_file "$VOLUMES_ROOT/LEXAR/AIXMOS-PORTABLE-KIT/docs/team/TEAM_SIMPLE_SETUP_GUIDE.txt"

echo "portable kit builder test passed"
EOF
chmod +x scripts/portable-kit/tests/test-build-portable-kit.sh
```

- [ ] **Step 2: Run the test and confirm it fails because the builder does not exist**

Run:

```bash
scripts/portable-kit/tests/test-build-portable-kit.sh
```

Expected: `FAIL: builder is missing or not executable`.

- [ ] **Step 3: Commit the failing test**

```bash
git add scripts/portable-kit/tests/test-build-portable-kit.sh
git commit -m "test: add portable kit builder coverage"
```

## Task 2: Add Portable Kit Builder

**Files:**
- Create: `scripts/portable-kit/build-portable-kit.sh`
- Test: `scripts/portable-kit/tests/test-build-portable-kit.sh`

- [ ] **Step 1: Create the builder script**

```bash
mkdir -p scripts/portable-kit
cat > scripts/portable-kit/build-portable-kit.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"
if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" && "$MODE" != "--verify-only" ]]; then
  echo "Usage: $0 [--dry-run|--apply|--verify-only]" >&2
  exit 2
fi

HOME_ROOT="${PORTABLE_KIT_HOME:-$HOME}"
VOLUMES_ROOT="${PORTABLE_KIT_VOLUMES_ROOT:-/Volumes}"
KIT_NAME="AIXMOS-PORTABLE-KIT"
DATE_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

DRIVE_NAMES=("AIXMOS02" "CYBORG" "LEXAR")
DRIVE_ROLES=("MASTER" "WORK" "FIELD")

COMMON_EXCLUDES=(
  "--exclude=.git/"
  "--exclude=.env"
  "--exclude=.env.*"
  "--exclude=secrets/"
  "--exclude=SECRETS/"
  "--exclude=*secret*"
  "--exclude=*Secret*"
  "--exclude=*token*"
  "--exclude=*Token*"
  "--exclude=*.key"
  "--exclude=*.pem"
  "--exclude=id_rsa"
  "--exclude=id_ed25519"
  "--exclude=node_modules/"
  "--exclude=.next/"
  "--exclude=.vercel/"
  "--exclude=.venv/"
  "--exclude=venv/"
  "--exclude=__pycache__/"
  "--exclude=.pytest_cache/"
  "--exclude=test-results/"
  "--exclude=*.tsbuildinfo"
  "--exclude=.DS_Store"
  "--exclude=._*"
)

log() {
  printf '%s\n' "$*"
}

run() {
  if [[ "$MODE" == "--dry-run" ]]; then
    printf '[dry-run] %q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

role_for_drive() {
  local drive="$1"
  local i
  for i in "${!DRIVE_NAMES[@]}"; do
    if [[ "${DRIVE_NAMES[$i]}" == "$drive" ]]; then
      printf '%s\n' "${DRIVE_ROLES[$i]}"
      return 0
    fi
  done
  return 1
}

drive_path() {
  printf '%s/%s\n' "$VOLUMES_ROOT" "$1"
}

kit_path() {
  printf '%s/%s/%s\n' "$VOLUMES_ROOT" "$1" "$KIT_NAME"
}

ensure_drive() {
  local drive="$1"
  local path
  path="$(drive_path "$drive")"
  [[ -d "$path" ]] || {
    echo "Missing drive: $path" >&2
    exit 1
  }
}

mkdirs_for_drive() {
  local drive="$1"
  local kit
  kit="$(kit_path "$drive")"
  run mkdir -p "$kit"/{AI-OPS-STARTER,AIXMOS-AGENTS,AIX-Command-Center,portable-setup,docs/team,docs/fleet,installers,scripts/mac,scripts/windows,scripts/common,checksums,reports,work}
}

write_file() {
  local path="$1"
  shift
  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] write $path"
  else
    mkdir -p "$(dirname "$path")"
    cat > "$path" "$@"
  fi
}

write_root_entrypoints() {
  local drive="$1"
  local role="$2"
  local root
  root="$(drive_path "$drive")"

  write_file "$root/START-HERE.md" <<EOF_ROOT
# AIXMOS Portable Kit - $role

Plug this drive into a Mac or Windows computer, then open:

- Mac: \`START_MAC.command\`
- Windows: \`START_WINDOWS.bat\`
- Manual docs: \`$KIT_NAME/START-HERE.md\`

Role: $role
Generated: $DATE_UTC

No setup script should ask you to paste secrets into chat. Keep API keys in a password manager or local machine env files.
EOF_ROOT

  write_file "$root/README_LOAD_FIRST.txt" <<EOF_README
AIXMOS PORTABLE KIT - $role

1. Open START-HERE.md first.
2. Mac users run START_MAC.command.
3. Windows users run START_WINDOWS.bat.
4. Keep secrets out of the FIELD drive.
5. Use Tailscale for private remote access.
EOF_README

  write_file "$root/START_MAC.command" <<'EOF_MAC'
#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/AIXMOS-PORTABLE-KIT"
echo "AIXMOS Portable Kit"
echo "Drive: $DIR"
echo
if command -v open >/dev/null 2>&1; then
  open START-HERE.md || true
fi
bash scripts/mac/bootstrap-mac.sh
EOF_MAC

  write_file "$root/START_WINDOWS.bat" <<'EOF_BAT'
@echo off
setlocal
cd /d "%~dp0AIXMOS-PORTABLE-KIT"
echo AIXMOS Portable Kit
echo Drive: %~dp0
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\bootstrap-windows.ps1
pause
EOF_BAT

  if [[ "$MODE" != "--dry-run" ]]; then
    chmod +x "$root/START_MAC.command"
  fi
}

write_kit_docs() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"

  write_file "$kit/START-HERE.md" <<EOF_START
# AIXMOS Portable Kit

Role: $role
Drive: $drive
Generated: $DATE_UTC

## What this kit is for

- Start work from a Mac or Windows computer.
- Reach Brainiac 7, the home PC AI brain, through Tailscale.
- Use the work Mac as the coding brain when it is online.
- Keep production hosting on GitHub, Vercel, and Supabase.

## Quick start

### Mac

Run from the drive root:

\`\`\`bash
./START_MAC.command
\`\`\`

### Windows

Double-click:

\`\`\`text
START_WINDOWS.bat
\`\`\`

## Machine map

- Home PC: Brainiac 7, local AI, Open WebUI, n8n, Qdrant.
- Work Mac: coding brain, TMMT development, tests, deploy tooling.
- Personal Mac: mobile control and flash-drive refresh.

## Safety

- Do not expose Ollama, Open WebUI, n8n, Qdrant, SSH, or local dev servers to the public internet.
- Use Tailscale or LAN only.
- Do not put real API keys, service-role keys, private keys, or production env files on FIELD.
- Customer-facing and money-facing actions require human approval.
EOF_START

  write_file "$kit/ROLE-$role.md" <<EOF_ROLE
# Role: $role

Generated: $DATE_UTC

MASTER is the owner-only gold source.
WORK is the daily developer transport.
FIELD is the simplified team/recovery kit with no real secrets.
EOF_ROLE

  write_file "$kit/scripts/mac/bootstrap-mac.sh" <<'EOF_BOOT_MAC'
#!/usr/bin/env bash
set -euo pipefail

echo "Mac bootstrap check"
echo

check() {
  local name="$1"
  local cmd="$2"
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "[OK] $name"
  else
    echo "[MISSING] $name"
  fi
}

check "git" git
check "node" node
check "npm" npm
check "ollama" ollama
check "tailscale" tailscale

echo
echo "Recommended work paths:"
echo "- Code on Mac: ~/dev/TMMT or ~/Documents/TMMT"
echo "- Brainiac 7 WebUI: http://brainiac-7:3000"
echo "- Brainiac 7 Ollama: http://brainiac-7:11434"
echo
echo "If this is a new Mac, install missing tools first. Keep secrets in your password manager, not on the flash drive."
EOF_BOOT_MAC

  write_file "$kit/scripts/windows/bootstrap-windows.ps1" <<'EOF_BOOT_WIN'
$ErrorActionPreference = "Stop"

Write-Host "Windows bootstrap check"
Write-Host ""

function Test-Command($Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if ($cmd) {
    Write-Host "[OK] $Name"
  } else {
    Write-Host "[MISSING] $Name"
  }
}

Test-Command git
Test-Command node
Test-Command npm
Test-Command ollama
Test-Command tailscale

Write-Host ""
Write-Host "Recommended work paths:"
Write-Host "- Code on Windows: C:\dev\TMMT"
Write-Host "- Brainiac 7 WebUI: http://brainiac-7:3000"
Write-Host "- Brainiac 7 Ollama: http://brainiac-7:11434"
Write-Host ""
Write-Host "If this is a new Windows computer, install missing tools first. Keep secrets in your password manager, not on the flash drive."
EOF_BOOT_WIN

  if [[ "$MODE" != "--dry-run" ]]; then
    chmod +x "$kit/scripts/mac/bootstrap-mac.sh"
  fi
}

sync_dir() {
  local src="$1"
  local dst="$2"
  [[ -d "$src" ]] || {
    log "skip missing source: $src"
    return 0
  }
  run mkdir -p "$dst"
  run rsync -a --delete "${COMMON_EXCLUDES[@]}" "$src/" "$dst/"
}

sync_common_sources() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"

  sync_dir "$HOME_ROOT/AI-OPS-STARTER" "$kit/AI-OPS-STARTER"
  sync_dir "$HOME_ROOT/AIXMOS-AGENTS" "$kit/AIXMOS-AGENTS"
  sync_dir "$HOME_ROOT/portable-setup" "$kit/portable-setup"

  if [[ "$role" == "FIELD" ]]; then
    sync_dir "$HOME_ROOT/AIX-Command-Center/guides" "$kit/AIX-Command-Center/guides"
    sync_dir "$HOME_ROOT/AIX-Command-Center/docs" "$kit/AIX-Command-Center/docs"
    sync_dir "$HOME_ROOT/AIX-Command-Center/agents" "$kit/AIX-Command-Center/agents"
    [[ -f "$HOME_ROOT/AIX-Command-Center/README.md" ]] && run rsync -a "${COMMON_EXCLUDES[@]}" "$HOME_ROOT/AIX-Command-Center/README.md" "$kit/AIX-Command-Center/README.md"
  else
    sync_dir "$HOME_ROOT/AIX-Command-Center" "$kit/AIX-Command-Center"
    sync_dir "$HOME_ROOT/TMMT" "$kit/work/TMMT"
  fi

  if [[ -d "$HOME_ROOT/Desktop" ]]; then
    run mkdir -p "$kit/docs/team"
    find "$HOME_ROOT/Desktop" -maxdepth 1 -type f \( -name 'TEAM_*' -o -name '*GUIDE*' -o -name '*AIXMOS*' \) -print0 2>/dev/null |
      while IFS= read -r -d '' file; do
        run rsync -a "${COMMON_EXCLUDES[@]}" "$file" "$kit/docs/team/"
      done
  fi
}

write_manifest() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"
  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] write $kit/MANIFEST.txt"
    return 0
  fi
  {
    echo "AIXMOS Portable Kit Manifest"
    echo "Drive: $drive"
    echo "Role: $role"
    echo "Generated: $DATE_UTC"
    echo
    find "$kit" -maxdepth 3 -mindepth 1 | sed "s#^$kit/##" | sort
  } > "$kit/MANIFEST.txt"
}

write_checksums() {
  local drive="$1"
  local kit
  kit="$(kit_path "$drive")"
  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] write $kit/checksums/SHA256SUMS.txt"
    return 0
  fi
  (
    cd "$kit"
    find . -type f \
      ! -path './checksums/SHA256SUMS.txt' \
      ! -path './reports/verification.txt' \
      ! -name '.DS_Store' \
      -print0 | sort -z | xargs -0 shasum -a 256
  ) > "$kit/checksums/SHA256SUMS.txt"
}

verify_kit() {
  local drive="$1"
  local role="$2"
  local kit
  kit="$(kit_path "$drive")"
  local report="$kit/reports/verification.txt"
  local bad

  if [[ "$MODE" == "--dry-run" ]]; then
    log "[dry-run] verify $kit"
    return 0
  fi

  bad="$(find "$kit" \( \
    -name '.env' -o \
    -name '.env.*' -o \
    -iname '*secret*' -o \
    -iname '*token*' -o \
    -name '*.key' -o \
    -name '*.pem' -o \
    -name 'id_rsa' -o \
    -name 'id_ed25519' -o \
    -name 'node_modules' -o \
    -name '.next' -o \
    -name '.venv' -o \
    -name '__pycache__' -o \
    -name '.pytest_cache' -o \
    -name 'test-results' \
  \) -print 2>/dev/null || true)"

  {
    echo "Verification report"
    echo "Drive: $drive"
    echo "Role: $role"
    echo "Generated: $DATE_UTC"
    echo
    if [[ -n "$bad" ]]; then
      echo "FAIL"
      echo "$bad"
    else
      echo "PASS"
    fi
  } > "$report"

  [[ -z "$bad" ]] || {
    echo "Verification failed for $drive. See $report" >&2
    return 1
  }
}

build_drive() {
  local drive="$1"
  local role="$2"
  ensure_drive "$drive"
  mkdirs_for_drive "$drive"
  write_root_entrypoints "$drive" "$role"
  write_kit_docs "$drive" "$role"
  if [[ "$MODE" != "--verify-only" ]]; then
    sync_common_sources "$drive" "$role"
    write_manifest "$drive" "$role"
    write_checksums "$drive"
  fi
  verify_kit "$drive" "$role"
  log "done: $drive ($role)"
}

for i in "${!DRIVE_NAMES[@]}"; do
  build_drive "${DRIVE_NAMES[$i]}" "${DRIVE_ROLES[$i]}"
done
EOF
chmod +x scripts/portable-kit/build-portable-kit.sh
```

- [ ] **Step 2: Run the test and confirm it passes**

Run:

```bash
scripts/portable-kit/tests/test-build-portable-kit.sh
```

Expected: `portable kit builder test passed`.

- [ ] **Step 3: Commit the builder**

```bash
git add scripts/portable-kit/build-portable-kit.sh
git commit -m "feat: add portable flash kit builder"
```

## Task 3: Dry Run Against Real Drives

**Files:**
- Use: `scripts/portable-kit/build-portable-kit.sh`
- Generated: no drive writes in dry-run mode

- [ ] **Step 1: Confirm the drives are mounted**

Run:

```bash
ls -d /Volumes/AIXMOS02 /Volumes/CYBORG /Volumes/LEXAR
```

Expected:

```text
/Volumes/AIXMOS02
/Volumes/CYBORG
/Volumes/LEXAR
```

- [ ] **Step 2: Run the dry-run builder**

Run:

```bash
scripts/portable-kit/build-portable-kit.sh --dry-run
```

Expected: printed `[dry-run]` commands for all three drives and no modified files on the drives.

- [ ] **Step 3: Inspect dry-run output**

Confirm the output mentions:

```text
/Volumes/AIXMOS02
/Volumes/CYBORG
/Volumes/LEXAR
AIXMOS-PORTABLE-KIT
```

## Task 4: Apply Clean Kits To Drives

**Files:**
- Use: `scripts/portable-kit/build-portable-kit.sh`
- Generated on drives:
  - `/Volumes/AIXMOS02/AIXMOS-PORTABLE-KIT`
  - `/Volumes/CYBORG/AIXMOS-PORTABLE-KIT`
  - `/Volumes/LEXAR/AIXMOS-PORTABLE-KIT`

- [ ] **Step 1: Apply the builder**

Run:

```bash
scripts/portable-kit/build-portable-kit.sh --apply
```

Expected:

```text
done: AIXMOS02 (MASTER)
done: CYBORG (WORK)
done: LEXAR (FIELD)
```

- [ ] **Step 2: Verify role markers**

Run:

```bash
ls /Volumes/AIXMOS02/AIXMOS-PORTABLE-KIT/ROLE-MASTER.md
ls /Volumes/CYBORG/AIXMOS-PORTABLE-KIT/ROLE-WORK.md
ls /Volumes/LEXAR/AIXMOS-PORTABLE-KIT/ROLE-FIELD.md
```

Expected: each path prints once with no error.

- [ ] **Step 3: Verify Windows and Mac launchers**

Run:

```bash
ls /Volumes/AIXMOS02/START_MAC.command /Volumes/AIXMOS02/START_WINDOWS.bat
ls /Volumes/CYBORG/START_MAC.command /Volumes/CYBORG/START_WINDOWS.bat
ls /Volumes/LEXAR/START_MAC.command /Volumes/LEXAR/START_WINDOWS.bat
```

Expected: all six launcher paths print with no error.

## Task 5: Security And Junk Verification

**Files:**
- Use: generated verification reports
- Use: `scripts/portable-kit/build-portable-kit.sh`

- [ ] **Step 1: Run verify-only mode**

Run:

```bash
scripts/portable-kit/build-portable-kit.sh --verify-only
```

Expected:

```text
done: AIXMOS02 (MASTER)
done: CYBORG (WORK)
done: LEXAR (FIELD)
```

- [ ] **Step 2: Confirm verification reports pass**

Run:

```bash
grep -H "PASS" /Volumes/AIXMOS02/AIXMOS-PORTABLE-KIT/reports/verification.txt /Volumes/CYBORG/AIXMOS-PORTABLE-KIT/reports/verification.txt /Volumes/LEXAR/AIXMOS-PORTABLE-KIT/reports/verification.txt
```

Expected: each of the three reports contains `PASS`.

- [ ] **Step 3: Confirm FIELD clean kit has no secret-like paths**

Run:

```bash
find /Volumes/LEXAR/AIXMOS-PORTABLE-KIT \( -name '.env' -o -name '.env.*' -o -iname '*secret*' -o -iname '*token*' -o -name '*.key' -o -name '*.pem' -o -name 'node_modules' -o -name '.next' -o -name '.venv' \) -print
```

Expected: no output.

## Task 6: Final Commit And Handoff

**Files:**
- Commit:
  - `scripts/portable-kit/build-portable-kit.sh`
  - `scripts/portable-kit/tests/test-build-portable-kit.sh`
  - `docs/superpowers/plans/2026-05-22-portable-ai-fleet-flash.md`

- [ ] **Step 1: Check repo status**

Run:

```bash
git status --short
```

Expected: only the portable-kit plan and scripts are staged or unstaged for this implementation, plus any pre-existing unrelated files remain untouched.

- [ ] **Step 2: Commit the implementation plan if it is not already committed**

Run:

```bash
git add docs/superpowers/plans/2026-05-22-portable-ai-fleet-flash.md
git commit -m "plan: add portable flash kit implementation"
```

Expected: a commit containing the plan.

- [ ] **Step 3: Final status report**

Report:

```text
MASTER: /Volumes/AIXMOS02/AIXMOS-PORTABLE-KIT
WORK: /Volumes/CYBORG/AIXMOS-PORTABLE-KIT
FIELD: /Volumes/LEXAR/AIXMOS-PORTABLE-KIT
Verification: PASS for all three clean kits
Notes: existing old drive contents were left in place
```

## Self-Review

Spec coverage:

- Machine roles are represented in generated `START-HERE.md`.
- Hosting boundary and Tailscale-only rule are represented in generated docs.
- MASTER, WORK, and FIELD roles are represented by drive mapping and role marker files.
- Standard layout is represented inside `AIXMOS-PORTABLE-KIT`.
- Sync exclusions are implemented in `COMMON_EXCLUDES`.
- First pass is non-destructive outside `AIXMOS-PORTABLE-KIT`.
- Verification checks for secrets and generated junk.

Placeholder scan:

- No placeholder labels or blank implementation sections are used.

Type and name consistency:

- The kit folder is consistently named `AIXMOS-PORTABLE-KIT`.
- Drive names are consistently `AIXMOS02`, `CYBORG`, and `LEXAR`.
- Roles are consistently `MASTER`, `WORK`, and `FIELD`.
