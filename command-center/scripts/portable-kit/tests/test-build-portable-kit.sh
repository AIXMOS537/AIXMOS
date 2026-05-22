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
