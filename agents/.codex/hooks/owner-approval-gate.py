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
"""
import json
import os
import re
import sys

# (label, regex) — matches only REAL outbound/financial/production actions:
# a call to a send/pay API host, an SDK send/charge call, a CLI invoked with a
# real subcommand, or a prod deploy. Deliberately precise so it does NOT trip on
# the mere WORD appearing in a commit message, file path (e.g. twilio-send.ts),
# test name, or grep — only ordinary dev, which must always pass untouched.
RISK = [
    ("send SMS (Twilio)",     r"api\.twilio\.com|/Messages\.json\b|\bmessages\.create\s*\(|(?<![\w-])twilio\s+(?:api|messages|phone-numbers)\b"),
    ("charge/pay (Stripe)",   r"api\.stripe\.com|(?<![\w-])stripe\s+(?:charges|payouts|transfers|payment_intents|refunds)\b|\b(?:charges|payouts|paymentIntents|transfers|refunds)\.create\s*\("),
    ("send (GoHighLevel)",    r"services\.leadconnectorhq\.com|rest\.gohighlevel\.com"),
    ("send email (ESP)",      r"api\.sendgrid\.com|api\.mailgun\.net|email\.[a-z0-9.\-]*amazonaws\.com|(?<![\w-])aws\s+ses\s+send-email\b"),
    ("e-sign",                r"\.docusign\.(?:net|com)|api\.hellosign\.com|api\.eversign\.com"),
    ("deploy to production",  r"(?<![\w-])vercel\s+(?:deploy\s+)?[^\n]*--prod\b|(?<![\w-])netlify\s+deploy\s+[^\n]*--prod\b"),
    ("credit-bureau submit",  r"(?:api|secure)\.(?:experian|equifax|transunion)\.com"),
]


def main() -> int:
    if os.environ.get("AIXMOS_OWNER_APPROVED") == "1":
        return 0  # owner approved this session explicitly
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # fail-open: never brick the agent on bad input
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = str(payload.get("tool_input", {}).get("command", ""))
    for label, pattern in RISK:
        if re.search(pattern, cmd, re.IGNORECASE):
            sys.stderr.write(
                "OWNER-APPROVAL GATE (blocked): this command looks like a "
                f"'{label}' action — a customer-facing / financial / production "
                "step that must NOT auto-execute (CLAUDE.md NON-NEGOTIABLE RULES).\n"
                "If the owner has approved, re-run with AIXMOS_OWNER_APPROVED=1 set "
                "in the environment, or route it through shared/owner-approval-gate/.\n"
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
