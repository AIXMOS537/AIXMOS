#!/usr/bin/env python3
"""Lead Autopilot — turn the 575-lead Notes backlog into a clean, worked pipeline.

Your team logs status in the Notes field, leaving the Status field empty. This reads Incoming Leads,
classifies each Note into your REAL Status + Priority options, and (on APPLY) writes them back —
so the pipeline self-maintains and you can actually filter/report/automate.

SAFE: DRY_RUN by default (writes a proposed-changes report, NO Airtable writes). APPLY=1 to commit.
Texting is NOT automated here — it builds a review queue; sending stays your call (per-recipient).

Setup:  export AIRTABLE_PAT=pat_xxx   (airtable.com/create/tokens, scope: data.records:read+write on TMMT Rentals)
Run:    python3 lead-classifier.py            # dry-run report
        APPLY=1 python3 lead-classifier.py     # write Status/Priority back
        python3 lead-classifier.py --selftest  # demo the logic on sample notes (no PAT needed)
"""
import os, sys, json, urllib.request, urllib.parse

BASE="appcenWUju039rD7b"; TABLE="tbl4gndUYeiOUWYRR"
F_STATUS="Status"; F_PRIORITY="Priority Level"; F_NOTES="fldKd06ZG3iyrhcBb"; F_NAME="fldigw5KNytkgJkA4"
# real Status options in your base
S_NEW,S_CONTACTED,S_FOLLOWUP,S_NOTINT,S_DND,S_DUP,S_CONTRACTING = \
 "New Lead","Contacted","Follow-Up","Not Interested","DND","Duplicate","Contracting"
P_URGENT,P_MOD,P_FU="Urgent","Moderate","Requires Follow Up"

def classify(note):
    n=(note or "").lower().strip()
    if not n: return (S_NEW, P_MOD, "no notes")
    if "duplicate" in n or "repeated form" in n: return (S_DUP, P_MOD, "duplicate")
    if "not eligible" in n or "criminal" in n or "do not rent" in n or "dnr" in n: return (S_DND, P_MOD, "disqualified")
    if "not interested" in n or "no longer" in n or "not anymore" in n: return (S_NOTINT, P_MOD, "declined")
    # HOT: waiting for inventory you now have
    if "follow up once" in n or "waiting on inventory" in n or "when available" in n or "become available" in n or "new availability" in n:
        return (S_FOLLOWUP, P_URGENT, "inventory-waiter (cars now open!)")
    if "waiting list" in n or "waitlist" in n or "on the list" in n: return (S_FOLLOWUP, P_FU, "on waitlist")
    if "contracting" in n: return (S_CONTRACTING, P_URGENT, "contracting")
    if "reached out" in n or "contacted" in n or "called" in n or "texted" in n or "appointment" in n or "came for" in n:
        return (S_CONTACTED, P_FU, "already touched")
    return (S_NEW, P_MOD, "new/unworked")

SAMPLES=["reached out","On waiting list","Not interested, seems expensive","Not eligible, 12 criminal records",
 "Follow up once vehicles become available","Repeated form","On waiting list, wants to start Wednesday",
 "JV Lead","waiting on inventory, not responding","Needs manager review","Reached out, need to update on new availability",""]

def selftest():
    print("CLASSIFIER DEMO (note → Status / Priority / why):")
    for s in SAMPLES:
        st,pr,why=classify(s); print(f"  {repr(s)[:48]:50} → {st:14} | {pr:18} | {why}")

def api(path, method="GET", body=None, pat=None):
    req=urllib.request.Request(f"https://api.airtable.com/v0/{path}", method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization":f"Bearer {pat}","Content-Type":"application/json"})
    import ssl;
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as r: return json.loads(r.read())
    except Exception as e: print("API error:", e); return {}

def main():
    if "--selftest" in sys.argv: return selftest()
    pat=os.environ.get("AIRTABLE_PAT")
    if not pat: print("No AIRTABLE_PAT set. Showing logic demo instead:\n"); return selftest()
    apply = os.environ.get("APPLY")=="1"
    # fetch all leads (paginate)
    recs=[]; offset=None
    while True:
        q=f"{BASE}/{TABLE}?pageSize=100"+(f"&offset={offset}" if offset else "")
        d=api(q, pat=pat); recs+=d.get("records",[]); offset=d.get("offset")
        if not offset: break
    import collections; dist=collections.Counter(); to_text=[]; updates=[]
    for r in recs:
        f=r.get("fields",{})
        if f.get("Status"): continue   # only fill empty Status
        note=f.get("Notes") or (f.get(F_NOTES) or "")
        st,pr,why=classify(note); dist[st]+=1
        updates.append({"id":r["id"],"fields":{F_STATUS:st,F_PRIORITY:pr}})
        if st==S_FOLLOWUP: to_text.append((f.get("Contact Name") or f.get(F_NAME) or "?", f.get("SMS Number (auto)") or "", why))
    priv=os.path.join(os.path.dirname(__file__),"private"); os.makedirs(priv,exist_ok=True)
    with open(os.path.join(priv,"lead-cleanup-proposed.md"),"w") as fh:
        fh.write(f"# Proposed Status cleanup ({'APPLIED' if apply else 'DRY-RUN'})\n\nEmpty-Status leads: {len(updates)}\n\n")
        for k,v in dist.most_common(): fh.write(f"- {k}: {v}\n")
        fh.write(f"\n## Text queue (Follow-Up): {len(to_text)}\n")
        for n,p,w in to_text: fh.write(f"- {n} | {p} | {w}\n")
    print(f"{'APPLIED' if apply else 'DRY-RUN'}: {len(updates)} leads classified. Report → private/lead-cleanup-proposed.md")
    print("distribution:", dict(dist))
    if apply:
        for i in range(0,len(updates),10):
            api(f"{BASE}/{TABLE}", "PATCH", {"records":updates[i:i+10]}, pat=pat)
        print("Status/Priority written to Airtable.")
    else:
        print("Review the report, then re-run with APPLY=1 to write it back.")

if __name__=="__main__": main()
