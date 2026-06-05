import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROMPTS_DIR = ROOT / "prompts"
AIRTABLE_TEMPLATES_DIR = ROOT / "airtable_templates"

CODE_BLOCK_RE = re.compile(r"```(?:text)?\n(.*?)\n```", re.DOTALL)
SECTION_HEADING_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)
NAME_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

PROMPT_ALIASES = {
    "morning_command": ["morning"],
    "midday_rescue": ["midday"],
    "end_of_day_closeout": ["end_of_day"],
    "daily_money_check": ["money_check"],
    "credit_card_paydown": ["credit_paydown"],
    "expense_cut_list": ["expense_cut"],
    "missed_money_review": ["missed_review"],
    "dealership_daily_snapshot": ["dealership_daily", "dealership_snapshot"],
    "network_coordination": ["network"],
    "dynamic_pricing": ["pricing", "price_optimize"],
    "partner_performance_scorecard": ["scorecard"],
    "revenue_split_calculator": ["revenue_split"],
}


def normalize_prompt_name(name):
    key = name.strip().lower()
    key = NAME_NORMALIZE_RE.sub("_", key)
    key = key.strip("_")
    if key == "master_operator_prompt":
        return "master"
    return key


def load_prompt_templates():
    templates = {}
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        if path.name.startswith("._"):
            continue
        text = path.read_text(encoding="utf-8")
        sections = parse_markdown_prompts(text, path.stem)
        templates.update(sections)

    aliases = {}
    for key, value in templates.items():
        alias_values = PROMPT_ALIASES.get(key)
        if not alias_values:
            continue
        if isinstance(alias_values, str):
            alias_values = [alias_values]
        for alias in alias_values:
            if alias not in templates:
                aliases[alias] = value
    templates.update(aliases)
    return templates


def parse_markdown_prompts(text, default_name="prompt"):
    sections = {}
    headings = list(SECTION_HEADING_RE.finditer(text))

    if headings:
        for index, heading in enumerate(headings):
            start = heading.end()
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            block = CODE_BLOCK_RE.search(text[start:end])
            if not block:
                continue
            key = normalize_prompt_name(heading.group(1))
            sections[key] = block.group(1).strip()
    else:
        block = CODE_BLOCK_RE.search(text)
        if block:
            key = normalize_prompt_name(default_name)
            sections[key] = block.group(1).strip()
    return sections


def list_prompts():
    return sorted(load_prompt_templates().keys())


def load_prompt_text(key):
    prompts = load_prompt_templates()
    normalized = normalize_prompt_name(key)
    if normalized not in prompts:
        raise KeyError(f"Unknown prompt '{key}'. Available: {', '.join(sorted(prompts.keys()))}")
    return prompts[normalized]


def run_openai(prompt, model="gpt-4o-mini", api_key=None):
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key is required via --api-key or OPENAI_API_KEY")

    url = "https://api.openai.com/v1/chat/completions"
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800,
    }).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            choices = result.get("choices")
            if not choices:
                raise RuntimeError("OpenAI response has no choices")
            return choices[0]["message"]["content"].strip()
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        raise RuntimeError(f"OpenAI HTTP error: {exc.code} {exc.reason}\n{payload}")


def list_airtable_templates():
    return sorted(path for path in AIRTABLE_TEMPLATES_DIR.glob("*.csv") if not path.name.startswith("._"))


def find_airtable_template(name):
    candidate = name if name.lower().endswith(".csv") else f"{name}.csv"
    candidate_lower = candidate.lower()
    for path in list_airtable_templates():
        if path.name.lower() == candidate_lower:
            return path
    raise FileNotFoundError(f"Airtable template not found: {name}")


def read_csv_template(path):
    with open(path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = []
        for row in reader:
            fields = {k: v for k, v in row.items() if v is not None and str(v).strip() != ""}
            if fields:
                rows.append(fields)
        return rows


def airtable_request(url, body, api_key):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        raise RuntimeError(f"Airtable HTTP error: {exc.code} {exc.reason}\n{payload}")


def create_airtable_records(base_id, table_name, rows, api_key, dry_run=False):
    if not rows:
        print(f"No rows found for table '{table_name}'.")
        return
    quoted_table = urllib.parse.quote(table_name, safe="")
    url = f"https://api.airtable.com/v0/{base_id}/{quoted_table}"
    for index in range(0, len(rows), 10):
        batch = rows[index:index + 10]
        body = {"records": [{"fields": record} for record in batch], "typecast": True}
        if dry_run:
            print(f"Dry run: would send {len(batch)} records to {table_name}.")
            continue
        response = airtable_request(url, body, api_key)
        created = response.get("records", [])
        print(f"Imported {len(created)} records into '{table_name}'.")


def import_airtable_template(template_name, base_id, api_key, table_name=None, dry_run=False):
    path = find_airtable_template(template_name)
    rows = read_csv_template(path)
    actual_table = table_name or path.stem.replace("_", " ")
    print(f"Importing '{path.name}' into Airtable table '{actual_table}'.")
    if dry_run:
        print(f"Found {len(rows)} rows. Sample record:\n{json.dumps(rows[0], indent=2) if rows else '{}'}")
    create_airtable_records(base_id, actual_table, rows, api_key, dry_run=dry_run)


def sync_airtable_templates(base_id, api_key, dry_run=False):
    templates = list_airtable_templates()
    if not templates:
        print("No Airtable CSV templates found.")
        return
    for path in templates:
        rows = read_csv_template(path)
        table_name = path.stem.replace("_", " ")
        print(f"Syncing {path.name} -> {table_name} ({len(rows)} rows)")
        create_airtable_records(base_id, table_name, rows, api_key, dry_run=dry_run)


def http_request(url, method="GET", body=None, headers=None):
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = body
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return json.loads(text)
            return text
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP error: {exc.code} {exc.reason}\n{payload}")


def fetch_airtable_table_rows(table_name, base_id, api_key, max_records=20):
    quoted_table = urllib.parse.quote(table_name, safe="")
    query = urllib.parse.urlencode({"pageSize": max_records, "maxRecords": max_records})
    url = f"https://api.airtable.com/v0/{base_id}/{quoted_table}?{query}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = http_request(url, headers=headers)
    records = response.get("records", []) if isinstance(response, dict) else []
    return [record.get("fields", {}) for record in records]


def fetch_supabase_table_rows(supabase_url, api_key, table_name, select="*", limit=20):
    if supabase_url.endswith("/"):
        supabase_url = supabase_url[:-1]
    quoted_table = urllib.parse.quote(table_name, safe="")
    query = urllib.parse.urlencode({"select": select, "limit": limit})
    url = f"{supabase_url}/rest/v1/{quoted_table}?{query}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    return http_request(url, headers=headers)


def parse_list_arg(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def resolve_airtable_base_id(base_id=None):
    if base_id:
        return base_id
    env_base = os.environ.get("AIRTABLE_BASE_ID")
    if env_base:
        return env_base
    try:
        from backend.integration import get_airtable_base_id

        return get_airtable_base_id()
    except ImportError:
        return None


def list_airtable_base_tables(base_id=None, api_key=None):
    base_id = resolve_airtable_base_id(base_id)
    api_key = api_key or os.environ.get("AIRTABLE_API_KEY")
    if not base_id or not api_key:
        raise ValueError(
            "AIRTABLE_API_KEY and AIRTABLE_BASE_ID (or config airtable.base_id) are required"
        )
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    response = http_request(url, headers={"Authorization": f"Bearer {api_key}"})
    if not isinstance(response, dict):
        return []
    return [
        {"id": table.get("id", ""), "name": table.get("name", "")}
        for table in response.get("tables", [])
        if table.get("name")
    ]


def build_snapshot_from_sources(airtable_tables, base_id, airtable_api_key, supabase_tables=None, supabase_url=None, supabase_key=None, vercel_endpoints=None):
    snapshot = {}

    if airtable_tables:
        for table_name in parse_list_arg(airtable_tables):
            snapshot[f"airtable:{table_name}"] = fetch_airtable_table_rows(table_name, base_id, airtable_api_key, max_records=50)

    if supabase_tables:
        if supabase_url and supabase_key:
            for table_name in parse_list_arg(supabase_tables):
                snapshot[f"supabase:{table_name}"] = fetch_supabase_table_rows(supabase_url, supabase_key, table_name, limit=50)
        else:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required to fetch Supabase tables")

    if vercel_endpoints:
        for endpoint in parse_list_arg(vercel_endpoints):
            snapshot[f"vercel:{endpoint}"] = http_request(endpoint, method="GET", headers={"Accept": "application/json"})

    return snapshot


def summarize_snapshot(prompt_key, snapshot, api_key, model="gpt-4o-mini"):
    prompt_text = load_prompt_text(prompt_key)
    snapshot_text = json.dumps(snapshot, indent=2)
    if len(snapshot_text) > 16000:
        snapshot_text = snapshot_text[:16000] + "\n...TRUNCATED..."
    prompt = (
        prompt_text
        + "\n\nUse the data below to summarize the current business snapshot, focusing on revenue, money at risk, customer issues, team blockers, and automation opportunities."
        + "\n\nCurrent system snapshot:\n"
        + snapshot_text
    )
    return run_openai(prompt, model=model, api_key=api_key)


def main():
    parser = argparse.ArgumentParser(
        description="AIX AI Command System helper for prompt templates, Airtable, Supabase, Vercel, and snapshot integration."
    )
    parser.add_argument(
        "action",
        choices=["list", "show", "run", "airtable", "supabase", "vercel", "snapshot", "dealership", "integrate"],
        help="Action to perform",
    )
    parser.add_argument("target", nargs="?", default="master", help="Prompt key, service subcommand, or endpoint identifier")
    parser.add_argument("--api-key", help="OpenAI API key, Airtable API key, or Supabase API key depending on the action")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use")
    parser.add_argument("--data", help="Additional context or data to append to the prompt")
    parser.add_argument("--dealership-id", help="Dealership ID for dealership-specific actions")
    parser.add_argument("--data-file", help="Read additional prompt context from a file")
    parser.add_argument("--base-id", help="Airtable base ID")
    parser.add_argument("--table", help="Airtable or Supabase table name")
    parser.add_argument("--template", help="Airtable CSV template name for import or preview")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--airtable-tables", help="Comma-separated Airtable table names for snapshot or fetch")
    parser.add_argument("--supabase-tables", help="Comma-separated Supabase table names for snapshot or fetch")
    parser.add_argument("--vercel-endpoints", help="Comma-separated Vercel endpoint URLs for snapshot or call")
    parser.add_argument("--endpoint", help="HTTP endpoint URL for Vercel or generic calls")
    parser.add_argument("--http-method", default="GET", help="HTTP method to use for Vercel endpoint calls")
    parser.add_argument("--prompt-name", default="master", help="Prompt key to use for snapshot summarization")
    parser.add_argument("--body", help="JSON body for Vercel endpoint calls")
    parser.add_argument("--probe", action="store_true", help="Probe configured tables (integrate status)")

    args = parser.parse_args()

    if args.action == "list":
        print("Available prompts:")
        for key in list_prompts():
            print(f"- {key}")
        return

    if args.action == "show":
        try:
            prompt_text = load_prompt_text(args.target)
            print(prompt_text)
        except KeyError as exc:
            print(exc)
            sys.exit(1)
        return

    if args.action == "run":
        try:
            prompt_text = load_prompt_text(args.target)
        except KeyError as exc:
            print(exc)
            sys.exit(1)

        extra = []
        if args.data:
            extra.append(args.data.strip())
        if args.data_file:
            extra.append(Path(args.data_file).read_text(encoding="utf-8").strip())
        if extra:
            prompt_text = prompt_text + "\n\n" + "\n\n".join(extra)
        response = run_openai(prompt_text, model=args.model, api_key=args.api_key)
        print(response)
        return

    if args.action == "airtable":
        airtable_api_key = args.api_key or os.environ.get("AIRTABLE_API_KEY")
        base_id = resolve_airtable_base_id(args.base_id)
        if args.target == "list-templates":
            templates = list_airtable_templates()
            for path in templates:
                print(f"- {path.name}")
            return
        if args.target == "show-template":
            if not args.template:
                print("--template is required for show-template")
                sys.exit(1)
            path = find_airtable_template(args.template)
            rows = read_csv_template(path)
            print(f"Template: {path.name}")
            print(f"Rows: {len(rows)}")
            print("First row sample:")
            print(json.dumps(rows[0] if rows else {}, indent=2))
            return
        if args.target == "import-template":
            if not args.template:
                print("--template is required for import-template")
                sys.exit(1)
            if not airtable_api_key or not base_id:
                print("Airtable API key and base ID are required for import-template")
                sys.exit(1)
            import_airtable_template(args.template, base_id, airtable_api_key, table_name=args.table, dry_run=args.dry_run)
            return
        if args.target == "sync-templates":
            if not airtable_api_key or not base_id:
                print("Airtable API key and base ID are required for sync-templates")
                sys.exit(1)
            sync_airtable_templates(base_id, airtable_api_key, dry_run=args.dry_run)
            return
        if args.target == "get-table":
            if not args.table:
                print("--table is required for get-table")
                sys.exit(1)
            if not airtable_api_key or not base_id:
                print("Airtable API key and base ID are required for get-table")
                sys.exit(1)
            rows = fetch_airtable_table_rows(args.table, base_id, airtable_api_key, max_records=50)
            print(json.dumps(rows, indent=2))
            return

        print("Unknown airtable subcommand. Use one of: list-templates, show-template, import-template, sync-templates, get-table")
        sys.exit(1)

    if args.action == "supabase":
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = args.api_key or os.environ.get("SUPABASE_KEY")
        if args.target == "fetch-table":
            if not args.table:
                print("--table is required for fetch-table")
                sys.exit(1)
            if not supabase_url or not supabase_key:
                print("SUPABASE_URL and SUPABASE_KEY are required for fetch-table")
                sys.exit(1)
            rows = fetch_supabase_table_rows(supabase_url, supabase_key, args.table, limit=50)
            print(json.dumps(rows, indent=2))
            return

        print("Unknown supabase subcommand. Use: fetch-table")
        sys.exit(1)

    if args.action == "vercel":
        if args.target == "call-endpoint":
            endpoint = args.endpoint
            if not endpoint:
                print("--endpoint is required for call-endpoint")
                sys.exit(1)
            headers = {"Accept": "application/json"}
            body = None
            if args.body:
                try:
                    body = json.loads(args.body)
                    headers["Content-Type"] = "application/json"
                except json.JSONDecodeError:
                    body = args.body
            response = http_request(endpoint, method=args.http_method.upper(), body=body, headers=headers)
            if isinstance(response, (dict, list)):
                print(json.dumps(response, indent=2))
            else:
                print(response)
            return

        print("Unknown vercel subcommand. Use: call-endpoint")
        sys.exit(1)

    if args.action == "dealership":
        airtable_api_key = args.api_key or os.environ.get("AIRTABLE_API_KEY")
        base_id = resolve_airtable_base_id(args.base_id)
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = args.api_key or os.environ.get("SUPABASE_KEY")

        if args.target == "get-partners":
            if not airtable_api_key or not base_id:
                print("Airtable API key and base ID are required to fetch partners")
                sys.exit(1)
            rows = fetch_airtable_table_rows("Dealership Partners", base_id, airtable_api_key, max_records=100)
            print(json.dumps(rows, indent=2))
            return

        if args.target == "get-shared-lot":
            if not airtable_api_key or not base_id:
                print("Airtable API key and base ID are required to fetch the shared lot")
                sys.exit(1)
            rows = fetch_airtable_table_rows("Shared Lot Inventory", base_id, airtable_api_key, max_records=100)
            print(json.dumps(rows, indent=2))
            return

        if args.target == "get-fleet":
            if not args.table:
                print("--table is required for get-fleet")
                sys.exit(1)
            if not airtable_api_key or not base_id:
                print("Airtable API key and base ID are required to fetch fleet data")
                sys.exit(1)
            rows = fetch_airtable_table_rows(args.table, base_id, airtable_api_key, max_records=100)
            print(json.dumps(rows, indent=2))
            return

        if args.target == "snapshot":
            if not args.airtable_tables and not args.supabase_tables and not args.vercel_endpoints:
                print("No snapshot sources provided. Use --airtable-tables, --supabase-tables, or --vercel-endpoints.")
                sys.exit(1)
            if not airtable_api_key or not base_id:
                print("Airtable API key and base ID are required for dealership snapshot")
                sys.exit(1)
            try:
                snapshot = build_snapshot_from_sources(args.airtable_tables, base_id, airtable_api_key, args.supabase_tables, supabase_url, supabase_key, args.vercel_endpoints)
            except Exception as exc:
                print(f"Failed to build dealership snapshot: {exc}")
                sys.exit(1)
            prompt_name = args.prompt_name or "dealership_daily_snapshot"
            if args.api_key or os.environ.get("OPENAI_API_KEY"):
                openai_key = args.api_key or os.environ.get("OPENAI_API_KEY")
                try:
                    summary = summarize_snapshot(prompt_name, snapshot, openai_key, model=args.model)
                    print(summary)
                    return
                except Exception as exc:
                    print(f"Snapshot summary failed: {exc}")
            print(json.dumps(snapshot, indent=2))
            return

        print("Unknown dealership subcommand. Use one of: get-partners, get-shared-lot, get-fleet, snapshot")
        sys.exit(1)

    if args.action == "snapshot":
        airtable_api_key = os.environ.get("AIRTABLE_API_KEY")
        base_id = resolve_airtable_base_id()
        try:
            from backend.integration import get_supabase_url

            supabase_url = get_supabase_url()
        except ImportError:
            supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        snapshot = {}

        if args.airtable_tables:
            if not airtable_api_key or not base_id:
                print("AIRTABLE_API_KEY and AIRTABLE_BASE_ID are required to fetch Airtable tables")
                sys.exit(1)
            for table_name in parse_list_arg(args.airtable_tables):
                snapshot[f"airtable:{table_name}"] = fetch_airtable_table_rows(table_name, base_id, airtable_api_key, max_records=20)

        if args.supabase_tables:
            if not supabase_url or not supabase_key:
                print("SUPABASE_URL and SUPABASE_KEY are required to fetch Supabase tables")
                sys.exit(1)
            for table_name in parse_list_arg(args.supabase_tables):
                snapshot[f"supabase:{table_name}"] = fetch_supabase_table_rows(supabase_url, supabase_key, table_name, limit=20)

        if args.vercel_endpoints:
            for endpoint in parse_list_arg(args.vercel_endpoints):
                snapshot[f"vercel:{endpoint}"] = http_request(endpoint, method="GET", headers={"Accept": "application/json"})

        if not snapshot:
            print("No snapshot sources provided. Use --airtable-tables, --supabase-tables, or --vercel-endpoints.")
            sys.exit(1)

        if args.api_key or os.environ.get("OPENAI_API_KEY"):
            openai_key = args.api_key or os.environ.get("OPENAI_API_KEY")
            try:
                summary = summarize_snapshot(args.prompt_name, snapshot, openai_key, model=args.model)
                print(summary)
                return
            except Exception as exc:
                print(f"Snapshot summary failed: {exc}")

        print(json.dumps(snapshot, indent=2))
        return

    if args.action == "integrate":
        from backend import integration as integ

        if args.target == "discover-airtable":
            base_id = integ.get_airtable_base_id()
            tables = list_airtable_base_tables(base_id=base_id)
            print(json.dumps(tables, indent=2))
            return
        if args.target == "status":
            status = integ.integration_status(probe=args.probe)
            print(json.dumps(status, indent=2))
            return
        if args.target == "tmmt-snapshot":
            snapshot = integ.build_tmmt_snapshot()
            prompt_name = args.prompt_name or integ.prompt_name(
                integ.load_integration_config(), "command_center_snapshot", "tmmt_command_center_snapshot"
            )
            if args.api_key or os.environ.get("OPENAI_API_KEY"):
                openai_key = args.api_key or os.environ.get("OPENAI_API_KEY")
                try:
                    summary = integ.summarize_tmmt_snapshot(snapshot, prompt_name)
                    print(summary)
                    return
                except Exception as exc:
                    print(f"Summary failed: {exc}")
            print(json.dumps(snapshot, indent=2))
            return

        print("Unknown integrate subcommand. Use: status, discover-airtable, tmmt-snapshot")
        sys.exit(1)


if __name__ == "__main__":
    main()
