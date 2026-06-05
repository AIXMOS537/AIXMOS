"""
Airtable -> Supabase Sync
Pulls all tables from Airtable and upserts into Supabase.
Safe to re-run — uses airtable_id as the upsert key.
"""
import json, os, sys, time, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AT_API_KEY = os.environ.get("AIRTABLE_API_KEY", "")
AT_BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appXXXXXXXXXXXXXX")
SB_URL     = os.environ.get("SUPABASE_URL", "").rstrip("/")
SB_KEY     = os.environ.get("SUPABASE_KEY", "")

# Airtable table -> Supabase table + field mapping (AT field -> SB column)
TABLES = {
    "Incoming Leads": {
        "sb": "incoming_leads",
        "fields": {
            "Contact Name":     "contact_name",
            "phone":            "phone",
            "email":            "email",
            "Notes":            "notes",
            "Opportunity Name": "opportunity_name",
        },
    },
    "Active Customers": {
        "sb": "active_customers",
        "fields": {
            "Customer Name":    "customer_name",
            "Phone Number":     "contact_phone",
            "Email":            "contact_email",
            "Vehicle Assigned": "vehicle_rented",
            "Weekly Payment":   "payment_amount",
            "Start Date":       "rental_start_date",
            "Status":           "status",
            "Notes":            "service_notes",
        },
    },
    "Customer Payments": {
        "sb": "customer_payments",
        "fields": {
            "Customer":               "customer",
            "Customer Phone Number":  "customer_phone_number",
            "Amount":                 "amount",
            "Payment Status":         "payment_status",
            "Last Payment Date":      "last_payment_date",
            "Next Payment Due Date":  "next_payment_due_date",
            "Amout Past Due":         "amout_past_due",
            "Payment Method":         "payment_method",
            "Notes":                  "notes",
        },
    },
    "Fleet": {
        "sb": "fleet",
        "fields": {
            "Vehicle Name":   "vehicle_name",
            "Year":           "year",
            "License Plate":  "license_plate",
            "Status":         "vehicle_status",
            "Partner":        "partner_name",
            "Weekly Price":   "weekly_prices",
            "Notes":          "notes",
            "VIN":            "vin",
            "Color":          "color",
            "Mileage":        "mileage",
        },
    },
}


def at_fetch(table_name):
    records, offset = [], None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        url = (f"https://api.airtable.com/v0/{AT_BASE_ID}/"
               f"{urllib.parse.quote(table_name)}?"
               + urllib.parse.urlencode(params))
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {AT_API_KEY}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read())
        except urllib.error.HTTPError as e:
            print(f"  AT ERROR {e.code}: {table_name}")
            break
        records.extend(resp.get("records", []))
        offset = resp.get("offset")
        if not offset:
            break
        time.sleep(0.2)
    return records


def sb_upsert(sb_table, rows):
    if not rows:
        return 0
    url = f"{SB_URL}/rest/v1/{sb_table}?on_conflict=airtable_id"
    data = json.dumps(rows).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "apikey":        SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates,return=minimal",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return len(rows)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"  SB ERROR {e.code}: {sb_table} -- {body}")
        return 0


def map_row(at_id, fields, field_map):
    row = {"airtable_id": at_id}
    for at_field, sb_col in field_map.items():
        val = fields.get(at_field)
        if val is None:
            continue
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val)
        row[sb_col] = val
    return row


def main():
    if not AT_API_KEY or not SB_URL or not SB_KEY:
        print("ERROR: Missing AIRTABLE_API_KEY, SUPABASE_URL, or SUPABASE_KEY in .env")
        sys.exit(1)

    print("\n" + "="*55)
    print("  AIRTABLE -> SUPABASE SYNC")
    print("="*55 + "\n")

    total = 0
    for at_table, config in TABLES.items():
        sb_table  = config["sb"]
        field_map = config["fields"]
        print(f"Syncing '{at_table}' -> '{sb_table}'...")
        records = at_fetch(at_table)
        if not records:
            print(f"  No records in Airtable")
            continue

        rows = [map_row(rec["id"], rec.get("fields", {}), field_map) for rec in records]

        # Normalize: all rows must have identical keys for Supabase batch upsert
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())
        rows = [{k: row.get(k) for k in all_keys} for row in rows]

        synced = 0
        for i in range(0, len(rows), 100):
            synced += sb_upsert(sb_table, rows[i:i+100])
            time.sleep(0.1)

        print(f"  {synced}/{len(records)} synced\n")
        total += synced

    print(f"{'='*55}")
    print(f"  DONE — {total} total records pushed to Supabase")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
