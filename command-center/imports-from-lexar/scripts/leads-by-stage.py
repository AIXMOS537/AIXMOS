"""Sort all leads by follow-up stage so the team knows exactly who to contact today."""
import json, os, sys, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_KEY = os.environ.get("AIRTABLE_API_KEY", "")
BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appXXXXXXXXXXXXXX")

STAGES = {
    "waitlist":      ["wait list", "waitlist", "waiting list"],
    "form_sent":     ["form sent", "form filled", "form sent!"],
    "no_response":   ["no response", "no resp", "3 days", "reached multiple", "unavailable", "unsuccessful", "call declined", "delivery was unsuccessful"],
    "not_eligible":  ["not eligible", "criminal", "not eligible --ss"],
    "not_interested":["not interested", "dnd", "don't call", "dont call", "not nterested"],
    "cold":          ["number has been changed", "out of radius", "number changed", "wrong number"],
    "current":       ["current customer", "repeat"],
    "fresh":         [],  # catch-all — no notes or unrecognized
}


def classify(notes: str) -> str:
    n = notes.lower()
    for stage, keywords in STAGES.items():
        if any(k in n for k in keywords):
            return stage
    return "fresh"


def fetch(table):
    records, offset = [], None
    while True:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{urllib.parse.quote(table)}?pageSize=100"
        if offset:
            url += f"&offset={offset}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read())
                records += [dict(r["fields"], _id=r["id"]) for r in resp["records"]]
                offset = resp.get("offset")
                if not offset:
                    break
        except urllib.error.HTTPError as e:
            print(f"ERROR: {e.code} {e.reason}")
            break
    return records


def fmt_phone(p):
    p = str(p).strip()
    if p.startswith("1") and len(p) == 11:
        return f"({p[1:4]}) {p[4:7]}-{p[7:]}"
    return p


def main():
    if not API_KEY:
        print("ERROR: AIRTABLE_API_KEY not set in .env")
        sys.exit(1)

    leads = fetch("Incoming Leads")
    buckets = {s: [] for s in STAGES}

    for l in leads:
        notes = str(l.get("Notes", "")).strip()
        stage = classify(notes)
        buckets[stage].append(l)

    print(f"\n{'='*58}")
    print(f"  LEADS BY STAGE — {len(leads)} total")
    print(f"{'='*58}\n")

    priority_order = ["waitlist", "fresh", "form_sent", "no_response",
                      "not_eligible", "cold", "current", "not_interested"]

    labels = {
        "waitlist":       "WAITLIST — offer a spot NOW",
        "fresh":          "FRESH / NEW — contact today",
        "form_sent":      "FORM SENT — follow up",
        "no_response":    "NO RESPONSE — final push",
        "not_eligible":   "NOT ELIGIBLE — soft close",
        "cold":           "COLD — bad number / out of area",
        "current":        "CURRENT CUSTOMERS",
        "not_interested": "NOT INTERESTED — DO NOT CONTACT",
    }

    action = {
        "waitlist":       "Send Stage 5 text — spot available",
        "fresh":          "Send Stage 1 text — first contact",
        "form_sent":      "Send Stage 2 text — check on form",
        "no_response":    "Send Stage 3 text — final follow-up",
        "not_eligible":   "Send Stage 6 text — soft close",
        "cold":           "Verify number — update Airtable",
        "current":        "Already a customer — no action",
        "not_interested": "CLOSED — do not text",
    }

    for stage in priority_order:
        group = buckets[stage]
        if not group:
            continue
        print(f"--- {labels[stage]} ({len(group)}) ---")
        print(f"    ACTION: {action[stage]}")
        print()
        for l in group[:20]:
            name  = l.get("Contact Name", "Unknown")
            phone = fmt_phone(l.get("phone", "—"))
            opp   = l.get("Opportunity Name", "—")
            notes = str(l.get("Notes", "")).strip().replace("\n", " | ")[:60]
            print(f"    {name:<28} {phone:<18} {opp[:25]}")
            if notes:
                print(f"    {'':28} Notes: {notes}")
        if len(group) > 20:
            print(f"    ... and {len(group) - 20} more")
        print()

    print(f"{'='*58}")
    actionable = len(buckets["waitlist"]) + len(buckets["fresh"]) + len(buckets["form_sent"]) + len(buckets["no_response"])
    print(f"  LEADS TO CONTACT TODAY: {actionable}")
    print(f"  Waitlist (highest priority): {len(buckets['waitlist'])}")
    print(f"  Fresh leads:                 {len(buckets['fresh'])}")
    print(f"  Form sent — follow up:       {len(buckets['form_sent'])}")
    print(f"  No response — final push:    {len(buckets['no_response'])}")
    print(f"{'='*58}\n")


if __name__ == "__main__":
    main()
