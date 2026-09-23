#!/usr/bin/env python3
"""
Owner-Approval Gate — Claude Code PreToolUse hook.

CLAUDE.md's core rule: "Never auto-execute send/pay/sign/ship." This is the code
enforcement of that rule for agent-run shell commands. It inspects each Bash
command BEFORE it runs and BLOCKS the ones that would push a customer-facing
message, move money, sign/ship, or deploy to production — unless the owner has
explicitly approved this session by setting  AIXMOS_OWNER_APPROVED=1  in the env.

Protocol: PreToolUse hooks receive a JSON blob on stdin. Exit 0 = allow; exit 2 =
block (stderr is shown back to the model). Fail-open on unexpected input so a
malformed payload never bricks the agent — this gate supports the owner rule, it
is not the sole control (approval primitives live in shared/owner-approval-gate/).

Tune the RISK patterns to your stack; keep this file installed (CLAUDE.md §NON-NEGOTIABLE).

INSTALL NOTE (2026-07-16): this is the home-directory copy. The TMMT repo registers
this hook as "$CLAUDE_PROJECT_DIR/.claude/hooks/owner-approval-gate.py". When a
session starts from ~ (the documented way to run Rick), CLAUDE_PROJECT_DIR is ~,
so the gate resolves here. Keep both copies in sync.

FALSE-ALARM FIX (2026-09-23): the gate used to block on the mere TEXT of a risky
command appearing anywhere in the line — so writing a deny rule, a doc, or a memory
note that merely QUOTED "vercel --prod" was refused. Two scoping rules now apply
before the CLI patterns are tested:
  1. heredoc bodies are stripped (that is file CONTENT being written, not commands);
  2. CLI risks must sit in COMMAND POSITION — start of the line or right after a
     shell separator (; && || | newline $( `), optionally behind env assignments
     or a runner (npx/pnpm/yarn/bunx/sudo/env/time).
Network/SDK risks (an API host, or an SDK .create() call) still match anywhere,
because piping a curl at api.stripe.com is a real charge wherever it appears.
Runs on Bash and PowerShell tools (BRAINIAC uses PowerShell).
Self-test:  python3 owner-approval-gate.py --selftest
"""
import json
import os
import re
import sys

# --- risks that are real wherever they appear (API hosts, SDK calls) ---------
RISK_ANYWHERE = [
    ("send SMS (Twilio)",     r"api\.twilio\.com|/Messages\.json\b|\bmessages\.create\s*\("),
    ("charge/pay (Stripe)",   r"api\.stripe\.com|\b(?:charges|payouts|paymentIntents|transfers|refunds)\.create\s*\("),
    ("send (GoHighLevel)",    r"services\.leadconnectorhq\.com|rest\.gohighlevel\.com"),
    ("send email (ESP)",      r"api\.sendgrid\.com|api\.mailgun\.net|email\.[a-z0-9.\-]*amazonaws\.com"),
    ("e-sign",                r"\.docusign\.(?:net|com)|api\.hellosign\.com|api\.eversign\.com"),
    ("credit-bureau submit",  r"(?:api|secure)\.(?:experian|equifax|transunion)\.com"),
]

# --- risks that only count when actually INVOKED as a command ---------------
RISK_COMMAND = [
    ("send SMS (Twilio)",     r"twilio\s+(?:api|messages|phone-numbers)\b"),
    ("charge/pay (Stripe)",   r"stripe\s+(?:charges|payouts|transfers|payment_intents|refunds)\b"),
    ("send email (ESP)",      r"aws\s+ses\s+send-email\b"),
    ("deploy to production",  r"vercel\s+(?:deploy\s+)?[^\n]*--prod\b"),
    ("deploy to production",  r"netlify\s+deploy\s+[^\n]*--prod\b"),
]

# env assignments (FOO=bar) or a runner that just fronts the real command
_PREFIX = re.compile(r"^(?:\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*|npx|pnpm|yarn|bunx|sudo|env|time|command|exec)\s+)*")
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# shell separators that start a new command position
_SPLIT = re.compile(r"\n|;|\|\||&&|\||\$\(|`")
# a segment may open with subshell/group punctuation before the real command
_OPENER = re.compile(r"^[\(\{\s]+")


def strip_heredocs(cmd: str) -> str:
    """Drop heredoc BODIES — they are file content being written, not commands."""
    out, lines, i = [], cmd.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = _HEREDOC.search(line)
        if m:
            terminator = m.group(2)
            i += 1
            while i < len(lines) and lines[i].strip() != terminator:
                i += 1  # skip the body
        i += 1
    return "\n".join(out)


def command_segments(cmd: str):
    """Yield each stretch of text that begins at a command position."""
    for seg in _SPLIT.split(cmd):
        seg = _OPENER.sub("", seg)
        if seg:
            yield _PREFIX.sub("", seg, count=1)


def find_risk(cmd: str):
    # Heredoc bodies are file CONTENT being written, never executed — a doc or a
    # memory note that names an API host is not a charge or a send.
    scoped = strip_heredocs(cmd)
    for label, pattern in RISK_ANYWHERE:
        if re.search(pattern, scoped, re.IGNORECASE):
            return label
    for seg in command_segments(scoped):
        for label, pattern in RISK_COMMAND:
            if re.match(pattern, seg, re.IGNORECASE):
                return label
    return None


def main() -> int:
    if os.environ.get("AIXMOS_OWNER_APPROVED") == "1":
        return 0  # owner approved this session explicitly
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # fail-open: never brick the agent on bad input
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return 0  # only shell tools carry these actions
    cmd = str(payload.get("tool_input", {}).get("command", ""))
    label = find_risk(cmd)
    if label:
        sys.stderr.write(
            "OWNER-APPROVAL GATE (blocked): this command looks like a "
            f"'{label}' action — a customer-facing / financial / production "
            "step that must NOT auto-execute (CLAUDE.md NON-NEGOTIABLE RULES).\n"
            "If the owner has approved, re-run with AIXMOS_OWNER_APPROVED=1 set "
            "in the environment, or route it through shared/owner-approval-gate/.\n"
        )
        return 2
    return 0


MUST_BLOCK = [
    "npx vercel deploy --prod",
    "(cd ~/Projects/TMMT && vercel --prod)",
    "vercel --prod",
    "cd ~/Projects/TMMT && npx vercel --prod --yes",
    "echo start; netlify deploy --dir=out --prod",
    "curl -X POST https://api.stripe.com/v1/charges -d amount=5000",
    "curl https://services.leadconnectorhq.com/conversations/messages -d @msg.json",
    "twilio api:core:messages:create --to +15715551234 --body hi",
    "aws ses send-email --to a@b.com --subject hi --text yo",
    "node -e \"stripe.charges.create({amount: 100})\"",
    "AIXMOS=1 npx vercel deploy --prod",
]
MUST_PASS = [
    "python3 -c 'print(\"vercel --prod\")'",
    "rick-attention.sh  # mentions vercel --prod in its help text",
    'python3 -c \'d["deny"].append("Bash(npx vercel --prod*)")\'',
    "grep -rn 'vercel --prod' ~/.claude/settings.json",
    "cat > memory/note.md <<'EOF'\nthe gate blocks a curl at api." + "stripe.com\nEOF",
    "cat > doc.md <<'EOF'\nservices." + "leadconnectorhq.com is the GHL send host\nEOF",
    "cat > note.md <<'EOF'\ndeny rule: vercel --prod is blocked\nEOF",
    "echo 'docs: never run vercel --prod by hand' >> README.md",
    "vercel whoami",
    "npx vercel deploy",  # preview deploy, not prod
    "git commit -m 'block vercel --prod in deny list'",
    "ls ~/Projects/TMMT/scripts/ship",
    "rg 'twilio messages' src/",
    "sed -i '' 's/vercel --prod//' notes.md",
]


def selftest() -> int:
    bad = 0
    for c in MUST_BLOCK:
        if not find_risk(c):
            print("FAIL (should block):", c); bad += 1
    for c in MUST_PASS:
        got = find_risk(c)
        if got:
            print(f"FAIL (should pass, blocked as {got}):", c); bad += 1
    print(f"selftest: {len(MUST_BLOCK)} block-cases, {len(MUST_PASS)} pass-cases, {bad} failures")
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
