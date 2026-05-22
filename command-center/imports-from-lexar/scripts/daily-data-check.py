"""Daily Airtable data quality check — flags missing fields across key tables."""
import json, os, sys, urllib.request, urllib.error
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_KEY  = os.environ.get("AIRTABLE_API_KEY", "")
BASE_ID  = os.environ.get("AIRTABLE_BASE_ID", "appXXXXXXXXXXXXXX")

TABLES = {
    "Active Customers": {
        "name":    "Customer Name",
        "phone":   "Contact Phone",
        "plate":   "Vehicle Plate #",
        "status":  "Status",
        "start":   "Rental Start Date",
        "payment": "Payment Amount ",
    },
    "Customer Payments": {
        "name":    "Customer",
        "phone":   "Customer Phone Number",
        "amount":  "Amount",
        "last":    "Last Payment Date",
        "next":    "Next Payment Due Date",
        "status":  "Payment Status",
    },
    "Fleet": {
        "name":    "Vehicle Name",
        "status":  "Vehicle Status",
        "partner": "Partner Name",
        "price":   "Weekly Prices",
    },
}


def fetch(table):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{urllib.parse.quote(table)}?pageSize=100"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["records"]
    except urllib.error.HTTPError as e:
        print(f"  ERROR fetching {table}: {e.code} {e.reason}")
        return []


import urllib.parse

def check(records, fields, table):
    issues = []
    for r in records:
        f = r.get("fields", {})
        name_val = f.get(fields["name"], "")
        if isinstance(name_val, list):
            name_val = name_val[0] if name_val else ""
        display = str(name_val).strip() or f"[Record {r['id']}]"

        missing = []
        for label, field in fields.items():
            val = f.get(field)
            if val is None or val == "" or val == [] or (isinstance(val, list) and not val):
                missing.append(field)

        if missing:
            issues.append((display, missing))
    return issues


def main():
    if not API_KEY:
        print("ERROR: AIRTABLE_API_KEY not set in .env")
        sys.exit(1)

    today = date.today().strftime("%A, %B %d %Y").replace(" 0", " ")
    print(f"\n{'='*55}")
    print(f"  DAILY DATA CHECK — {today}")
    print(f"{'='*55}\n")

    total_issues = 0

    for table, fields in TABLES.items():
        print(f"--- {table} ---")
        records = fetch(table)
        if not records:
            print("  (no records or fetch failed)\n")
            continue

        issues = check(records, fields, table)
        clean = len(records) - len(issues)

        print(f"  Total: {len(records)}  |  Clean: {clean}  |  Needs update: {len(issues)}")

        if issues:
            print()
            for name, missing in issues[:20]:  # cap at 20 per table
                print(f"  !! {name}")
                print(f"     Missing: {', '.join(missing)}")
            if len(issues) > 20:
                print(f"  ... and {len(issues) - 20} more")

        total_issues += len(issues)
        print()

    print(f"{'='*55}")
    if total_issues == 0:
        print("  ALL RECORDS CLEAN -- great work team!")
    else:
        print(f"  TOTAL RECORDS NEEDING UPDATES: {total_issues}")
        print()
        print("  ACTION: Open Airtable and update all flagged records.")
        print("  airtable.com/appcenWUju039rD7b")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
