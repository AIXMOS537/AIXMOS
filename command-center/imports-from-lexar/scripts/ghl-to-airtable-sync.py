"""
GHL → Airtable Sync
Pulls contacts + opportunities from GHL and creates/updates records in Airtable Incoming Leads.
Run manually or on a schedule. Safe to re-run — checks for existing records before creating.
"""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GHL_API_KEY     = os.environ.get("GHL_API_KEY", "")
GHL_LOCATION_ID = os.environ.get("GHL_LOCATION_ID", "")
AT_API_KEY      = os.environ.get("AIRTABLE_API_KEY", "")
AT_BASE_ID      = os.environ.get("AIRTABLE_BASE_ID", "appXXXXXXXXXXXXXX")
AT_TABLE        = "Incoming Leads"

# Pipeline stage → Airtable note label
STAGE_LABELS = {
    "New Lead":                  "GHL: New Lead",
    "Verification Form Sent":    "GHL: Form Sent",
    "Verification Form Received":"GHL: Form Received",
    "Qualified":                 "GHL: Qualified",
    "Proposal Sent":             "GHL: Proposal Sent",
    "On the Road":               "GHL: On the Road - CURRENT CUSTOMER",
    "Closed":                    "GHL: Closed",
    "Waitlisted":                "GHL: On wait list",
    "Approved":                  "GHL: Approved",
    "Disqualified - Do not Reapply": "GHL: Not eligible",
}


def ghl_get(path):
    url = f"https://services.leadconnectorhq.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GHL_API_KEY}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "curl/7.88.1",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  GHL ERROR {e.code}: {path}")
        return {}


def at_request(method, path, body=None, params=None):
    table, _, qs = path.partition("?")
    url = f"https://api.airtable.com/v0/{AT_BASE_ID}/{urllib.parse.quote(table)}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    elif qs:
        url += "?" + qs
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {AT_API_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  AIRTABLE ERROR {e.code}: {method} {path} — {e.read().decode()[:200]}")
        return {}


def get_ghl_contacts(limit=100):
    """Fetch all contacts from GHL with pagination."""
    contacts, page = [], 1
    while True:
        data = ghl_get(f"/contacts/?locationId={GHL_LOCATION_ID}&limit={limit}&page={page}")
        batch = data.get("contacts", [])
        if not batch:
            break
        contacts.extend(batch)
        total = data.get("total", 0)
        print(f"  Fetched {len(contacts)}/{total} GHL contacts...")
        if len(contacts) >= total:
            break
        page += 1
        time.sleep(0.3)
    return contacts


def get_ghl_opportunities():
    """Fetch all opportunities with stage info."""
    opps, start_after, start_after_id = [], None, None
    while True:
        path = f"/opportunities/search?location_id={GHL_LOCATION_ID}&limit=100"
        if start_after:
            path += f"&startAfter={start_after}&startAfterId={start_after_id}"
        data = ghl_get(path)
        batch = data.get("opportunities", [])
        if not batch:
            break
        opps.extend(batch)
        meta = data.get("meta", {})
        total = meta.get("total", 0)
        print(f"  Fetched {len(opps)}/{total} GHL opportunities...")
        # Extract cursor from nextPageUrl
        next_url = meta.get("nextPageUrl", "")
        if next_url and len(opps) < total:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(next_url).query)
            start_after    = parsed.get("startAfter", [None])[0]
            start_after_id = parsed.get("startAfterId", [None])[0]
            if not start_after:
                break
        else:
            break
        time.sleep(0.3)
    return opps


def get_existing_airtable_leads():
    """Load existing Airtable leads keyed by phone."""
    existing, offset = {}, None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        data = at_request("GET", AT_TABLE, params=params)
        for rec in data.get("records", []):
            f = rec.get("fields", {})
            phone = str(f.get("phone", "")).strip()
            name  = str(f.get("Contact Name", "")).strip()
            if phone:
                existing[phone] = rec["id"]
            elif name:
                existing[name.lower()] = rec["id"]
        offset = data.get("offset")
        if not offset:
            break
        time.sleep(0.2)
    return existing


def get_pipeline_stages():
    """Map stage IDs to stage names."""
    data = ghl_get(f"/opportunities/pipelines/?locationId={GHL_LOCATION_ID}")
    stage_map = {}
    for pipe in data.get("pipelines", []):
        for stage in pipe.get("stages", []):
            stage_map[stage["id"]] = stage["name"]
    return stage_map


def fmt_phone(p):
    if not p:
        return ""
    p = str(p).strip().replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    try:
        return int(p)
    except ValueError:
        return None


def main():
    if not GHL_API_KEY or not GHL_LOCATION_ID or not AT_API_KEY:
        print("ERROR: Missing GHL_API_KEY, GHL_LOCATION_ID, or AIRTABLE_API_KEY in .env")
        sys.exit(1)

    print("\n" + "="*55)
    print("  GHL → AIRTABLE SYNC")
    print("="*55 + "\n")

    print("Loading GHL pipeline stages...")
    stage_map = get_pipeline_stages()

    print("Loading GHL contacts...")
    contacts = get_ghl_contacts()
    contact_map = {c["id"]: c for c in contacts}

    print("\nLoading GHL opportunities...")
    opportunities = get_ghl_opportunities()

    print("\nLoading existing Airtable leads...")
    existing = get_existing_airtable_leads()
    print(f"  {len(existing)} existing records in Airtable")

    created, updated, skipped = 0, 0, 0

    print(f"\nSyncing {len(contacts)} contacts...")
    for contact in contacts:
        cid    = contact.get("id", "")
        fname  = contact.get("firstName", "") or ""
        lname  = contact.get("lastName", "") or ""
        name   = f"{fname} {lname}".strip() or contact.get("name", "") or "Unknown"
        phone  = fmt_phone(contact.get("phone", ""))
        email  = contact.get("email", "") or ""
        source = contact.get("source", "") or ""
        tags   = ", ".join(contact.get("tags", []) or [])

        # Find opportunity for this contact to get stage
        opp = next((o for o in opportunities if o.get("contactId") == cid), None)
        stage_id   = opp.get("pipelineStageId", "") if opp else ""
        stage_name = stage_map.get(stage_id, "")
        note_label = STAGE_LABELS.get(stage_name, f"GHL: {stage_name}" if stage_name else "GHL: Imported")

        fields = {
            "Contact Name":       name,
            "Opportunity Name":   source or "UBER/LYFT LEAD",
            "Notes":              note_label,
        }
        if phone:
            fields["phone"] = phone
        if email:
            fields["email"] = email

        # Check if already in Airtable
        key = phone if phone else name.lower()
        if key in existing:
            skipped += 1
            continue

        # Create new record
        result = at_request("POST", AT_TABLE, {"fields": fields})
        if result.get("id"):
            created += 1
            if phone:
                existing[phone] = result["id"]
        time.sleep(0.15)

    print(f"\n{'='*55}")
    print(f"  SYNC COMPLETE")
    print(f"  Created:  {created} new records in Airtable")
    print(f"  Skipped:  {skipped} already existed")
    print(f"  Total GHL contacts processed: {len(contacts)}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
