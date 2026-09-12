"""
pathway.py -- the TMMT operator pathway for people who want to become a licensed TMMT operator.

The 15-module certification (Learn / Earn / Churn), the 100-point readiness rubric, the price doors
and the operator fences, plus local progress tracking. Source of truth for the modules is TMMT
`src/lib/operator/academy-modules.ts`; this is the offline copy a candidate can train on.

  modules()          -> the 15 modules
  progress()         -> {"done": [n, ...]}
  mark(n, done)      -> update progress
  command(arg)       -> markdown answer for the /pathway chat command
  status_text()      -> one-paragraph status for the system prompt
  ensure_pack()      -> write the pathway into the vault (memory/kit/tmmt-operator-pathway); True if written
"""
import os, json, threading
from . import settings

FILE = os.path.join(settings.MEMDIR, "pathway.json")
PACK = os.path.join(settings.MEMDIR, "kit", "tmmt-operator-pathway")
VERSION = "2026-09-11"
_LOCK = threading.Lock()

MODULES = [
    (1, "learn", "Welcome to AIXMOS", "Name the product, the empire, and what money never buys.",
     "Write one sentence: AIXMOS is what they buy. HAILMARY is never sold.",
     "Can state the naming law without using a fourth public brand.",
     "AIXMOS is the public operating system. PROJECT X HAILMARY is the owner empire; money never buys it. Clients say AIXMOS."),
    (2, "learn", "The two doors", "Route a buyer to the Dealer flagship or the $97 Operator seat without mixing SKUs.",
     "Qualify a mock buyer: lot owner vs solo entrepreneur.",
     "Picks Dealer Bundle/Ops Kit or $97, never both as one invoice.",
     "Dealer (mom-and-pop lots): Ops Kit $997 + $297/mo or Dealer Bundle $3,497 + $697/mo, dedicated instance. Operator: $97/mo, 500 tokens, this academy. Credit guidance is later and legal-gated."),
    (3, "learn", "Intake that does not die", "Get every lead off texts and clipboards into one form.",
     "Submit the lead-intake form with a test name and confirm it lands.",
     "Can show a lead in the admin pipeline within 5 minutes.",
     "Leads die in DMs and notebooks. Public intake writes to the people spine. Follow-up is the product."),
    (4, "learn", "GHL is the hub, not a second pile", "Explain checkout, tags and webhooks without selling a second CRM.",
     "List the checkout tags a new member gets.",
     "Names member-97 and kit-ordered-dealer-bundle correctly.",
     "GoHighLevel keeps checkout and nurture; the ops app keeps operations. Tags: member-97, kit-ordered-ops-kit, kit-ordered-dealer-bundle."),
    (5, "earn", "TMMT Ops floor desk", "Run a day on the floor: vehicles, tickets, payments.",
     "Add one vehicle and one ticket on the demo ops desk.",
     "Can walk a floor manager through login to first ticket.",
     "The desk is not a DMS. It stacks beside what the lot already has. Daily: fleet, customers, tickets, payments."),
    (6, "earn", "Fleet and lot", "Track units so the owner is not blind.",
     "Map 5 units into statuses the owner can read in 10 seconds.",
     "Owner can answer 'what's on the lot' without a phone call.",
     "If the owner has to text the floor to know what's out, the system is not live."),
    (7, "earn", "Follow-up that closes", "Turn a missed call into a booked return or a deal.",
     "Write a 3-touch follow-up for a no-show (hour 1, day 1, day 3).",
     "No 'just checking in' copy. Every touch has a next step.",
     "If this closes one extra deal a month, it pays for itself. Follow-up is the missing piece, not traffic."),
    (8, "earn", "Owner command center", "Show the owner numbers without another dashboard SaaS.",
     "Open the command view on the demo and name three tiles the owner cares about.",
     "Can demo Command in under 3 minutes.",
     "Dealer Bundle includes Command Center. Ops Kit is floor-only. Command is not a fourth brand."),
    (9, "earn", "Tokens and the $97 seat", "Explain 500 tokens a month without promising income.",
     "Enroll a test contact with tag member-97 (sandbox only).",
     "Never says guaranteed income. Sells the system and the path.",
     "$97/mo grants 500 tokens when checkout fires."),
    (10, "learn", "Credit guidance vs repair", "Keep credit language legal.",
     "Rewrite a banned sentence: 'we will raise your score 47 points'.",
     "Zero 'repair' or score-guarantee language.",
     "We educate. Credit repair is not offered by operators. The dealer pitch today is software-only."),
    (11, "learn", "Compliance posture", "Customer financials stay off operator eyes.",
     "List three things an operator must never see.",
     "Names the customer-financials fence and who approves exceptions (the TMMT lead, nobody else).",
     "Operators do not see customer financials. Only people inside the official TMMT program get access; never route leads outside it."),
    (12, "earn", "Close a mom-and-pop dealer", "Run the 15-minute demo and ask for the Bundle.",
     "Role-play the 30-second pitch.",
     "Qualifies 3 of 5 checks before quoting.",
     "Demo the kits and lead intake. Close the Dealer Bundle."),
    (13, "earn", "Provision and handoff", "Hand a dealer their start-here pack without a placeholder go-live.",
     "Walk through a dry-run provisioning with a demo lot.",
     "Knows a dry run comes first and that cloud projects are created by TMMT, not the operator.",
     "Dry-run first. No placeholder logo on a live dealer."),
    (14, "churn", "Daily churn", "Work the desk every day so the system compounds.",
     "Write a 6-item daily checklist for a floor manager.",
     "Checklist fits on one phone screen.",
     "Learn, Earn, Churn. The $97 seat teaches. The dealer instance runs the lot. Daily use is the product."),
    (15, "churn", "Certify", "Know when someone is ready to operate a city.",
     "Score a mock operator on the 100-point rubric (70+ certified).",
     "Treats operators as licensed partners, not employees.",
     "70+ certified, 75+ senior, 85+ master. A TMMT lead certifies you; this module does not flip the switch."),
]

RUBRIC = [("Consistent results", 20), ("Community leadership", 15), ("Platform engagement", 15), ("Coachability", 15),
          ("Communication skill", 15), ("Network / audience", 10), ("Financial readiness", 10)]
DOORS = [("Operator seat", "$97/mo, 500 tokens"), ("Ops Kit", "$997 + $297/mo"), ("Dealer Bundle", "$3,497 + $697/mo")]
FENCES = [
    "You become a licensed partner, not an employee, and not the founder.",
    "White-label means your brand on TMMT Rentals. The engine stays AIXMOS-owned.",
    "No customer financials on your machine or stick.",
    "No keys, passwords or .env files, ever. TMMT issues access through your login.",
    "Work only through the official TMMT program; never route leads to anyone outside it.",
    "Draft outreach. Never auto-send.",
    "No income claims. You sell the system and the path.",
    "No credit-repair or score-guarantee language.",
]

def modules():
    return [{"n": m[0], "track": m[1], "title": m[2], "objective": m[3], "drill": m[4], "pass": m[5], "content": m[6]} for m in MODULES]

def progress():
    with _LOCK:
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
    done = sorted({int(n) for n in d.get("done", []) if str(n).isdigit() and 1 <= int(n) <= len(MODULES)})
    return {"done": done}

def mark(n, done=True):
    n = int(n)
    if not 1 <= n <= len(MODULES):
        raise ValueError("module must be 1-%d" % len(MODULES))
    cur = set(progress()["done"])
    (cur.add if done else cur.discard)(n)
    os.makedirs(settings.MEMDIR, exist_ok=True)
    with _LOCK:
        tmp = FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"done": sorted(cur)}, f)
        os.replace(tmp, FILE)
    return progress()

def next_module():
    done = set(progress()["done"])
    return next((m for m in modules() if m["n"] not in done), None)

def _card(m):
    return ("### Module %d (%s): %s\n**Goal:** %s\n\n%s\n\n**Drill:** %s\n\n**You pass when:** %s"
            % (m["n"], m["track"], m["title"], m["objective"], m["content"], m["drill"], m["pass"]))

def status_text():
    done, nxt = progress()["done"], next_module()
    s = "TMMT operator pathway: %d of %d modules done." % (len(done), len(MODULES))
    return s + (" Next: module %d, %s." % (nxt["n"], nxt["title"]) if nxt else " All modules done: ready to ask a TMMT lead to certify.")

def command(arg=""):
    a = (arg or "").strip().lower()
    words = a.split()
    if words and words[0] in ("done", "undo") and len(words) > 1 and words[1].isdigit():
        mark(int(words[1]), words[0] == "done")
        nxt = next_module()
        return status_text() + ("\n\n" + _card(nxt) if nxt else "")
    if a.isdigit():
        m = next((x for x in modules() if x["n"] == int(a)), None)
        return _card(m) if m else "There are %d modules; pick 1-%d." % (len(MODULES), len(MODULES))
    if a in ("rubric", "score"):
        return ("## Readiness rubric (100 points)\n" + "\n".join("- %s: %d" % r for r in RUBRIC) +
                "\n\n70+ certified, 75+ senior, 85+ master. A TMMT lead scores and certifies you.")
    if a in ("doors", "price", "prices", "pricing"):
        return "## Price doors (there are only these)\n" + "\n".join("- **%s**: %s" % d for d in DOORS)
    if a in ("fences", "rules"):
        return "## Operator fences\n" + "\n".join("%d. %s" % (i + 1, f) for i, f in enumerate(FENCES))
    if a in ("all", "list", "modules"):
        done = set(progress()["done"])
        return "## The 15 modules\n" + "\n".join("- [%s] %d. %s (%s)" % ("x" if m["n"] in done else " ", m["n"], m["title"], m["track"]) for m in modules())
    nxt = next_module()
    head = "## Your TMMT operator pathway\n" + status_text()
    tips = ("\n\nCommands: `/pathway all`, `/pathway 3` (open a module), `/pathway done 3`, `/pathway rubric`, "
            "`/pathway doors`, `/pathway fences`.")
    return head + ("\n\n" + _card(nxt) if nxt else "") + tips

def ensure_pack():
    """Write the pathway into the vault so /vault and the agent can search it. Idempotent."""
    stamp = os.path.join(PACK, ".version")
    try:
        with open(stamp, "r", encoding="utf-8") as f:
            if f.read().strip() == VERSION:
                return False
    except OSError:
        pass
    os.makedirs(PACK, exist_ok=True)
    files = {
        "00-START-HERE.md": "# TMMT operator pathway\n\n**What this is:** the path from candidate to licensed TMMT operator: "
                            "15 modules (Learn, Earn, Churn), a 100-point readiness rubric, the price doors and the fences.\n\n"
                            "Type `/pathway` in chat to see your progress and the next module.\n",
        "modules.md": "# The 15 certification modules\n\n" + "\n\n".join(_card(m) for m in modules()) + "\n",
        "rubric-and-doors.md": command("rubric") + "\n\n" + command("doors") + "\n",
        "fences.md": command("fences") + "\n",
    }
    for name, text in files.items():
        with open(os.path.join(PACK, name), "w", encoding="utf-8") as f:
            f.write(text)
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(VERSION)
    return True
