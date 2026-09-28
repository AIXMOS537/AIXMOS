#!/usr/bin/env python3
"""AIX AI Command System — local CLI for prompts, Airtable, Supabase, and Vercel."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROMPTS_DIR = ROOT / "prompts"
TEMPLATES_DIR = ROOT / "airtable_templates"
AIRTABLE_API = "https://api.airtable.com/v0"
AIRTABLE_META = "https://api.airtable.com/v0/meta/bases"
OPENAI_API = "https://api.openai.com/v1/chat/completions"


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def env(name: str, required: bool = False) -> str | None:
    value = os.environ.get(name)
    if required and not value:
        eprint(f"Missing required environment variable: {name}")
        sys.exit(1)
    return value


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 120,
) -> tuple[int, Any]:
    req = urllib.request.Request(url, data=body, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {"error": err.reason}
        except json.JSONDecodeError:
            payload = {"error": raw or err.reason}
        return err.code, payload


def load_prompt(name: str) -> dict[str, Any]:
    path = PROMPTS_DIR / f"{name}.json"
    if not path.is_file():
        eprint(f"Prompt not found: {name} (expected {path})")
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("name", name)
    return data


def list_prompts() -> list[str]:
    if not PROMPTS_DIR.is_dir():
        return []
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.json"))


def show_prompt(name: str) -> None:
    prompt = load_prompt(name)
    print(json.dumps(prompt, indent=2))


def run_openai(prompt: dict[str, Any], extra_context: str | None) -> str:
    api_key = env("OPENAI_API_KEY", required=True)
    system = prompt.get("system", "")
    user_template = prompt.get("user", "")
    user = user_template
    if extra_context:
        placeholder = "{{data}}"
        user = user.replace(placeholder, extra_context) if placeholder in user else f"{user}\n\n---\nContext:\n{extra_context}"

    payload = {
        "model": prompt.get("model", os.environ.get("OPENAI_MODEL", "gpt-4o-mini")),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": prompt.get("temperature", 0.4),
    }
    body = json.dumps(payload).encode("utf-8")
    status, data = http_request(
        "POST",
        OPENAI_API,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        body=body,
    )
    if status >= 400 or not isinstance(data, dict):
        eprint("OpenAI request failed:", data)
        sys.exit(1)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        eprint("Unexpected OpenAI response:", json.dumps(data, indent=2))
        sys.exit(1)


def cmd_list(_: argparse.Namespace) -> None:
    for name in list_prompts():
        prompt = load_prompt(name)
        title = prompt.get("title", name)
        print(f"{name}\t{title}")


def cmd_show(args: argparse.Namespace) -> None:
    show_prompt(args.name)


def cmd_run(args: argparse.Namespace) -> None:
    prompt = load_prompt(args.name)
    extra = args.data
    if args.data_file:
        path = Path(args.data_file)
        if not path.is_file():
            eprint(f"Data file not found: {path}")
            sys.exit(1)
        extra = path.read_text(encoding="utf-8")
    result = run_openai(prompt, extra)
    print(result)


def list_csv_templates() -> list[str]:
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.csv"))


def template_path(name: str) -> Path:
    path = TEMPLATES_DIR / f"{name}.csv"
    if not path.is_file():
        eprint(f"Template not found: {name} (expected {path})")
        sys.exit(1)
    return path


def read_csv_template(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            eprint(f"CSV has no headers: {path}")
            sys.exit(1)
        fields = [f.strip() for f in reader.fieldnames if f and f.strip()]
        rows = []
        for row in reader:
            cleaned = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            if any(cleaned.values()):
                rows.append(cleaned)
    return fields, rows


def airtable_headers() -> dict[str, str]:
    key = env("AIRTABLE_API_KEY", required=True)
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def airtable_base_id() -> str:
    base = env("AIRTABLE_BASE_ID", required=True)
    assert base is not None
    return base


def allowed_airtable_tables() -> set[str] | None:
    """Live writes are only allowed against tables named in AIRTABLE_TABLE_ALLOWLIST
    (comma-separated). Unset/empty means no table has been approved for live writes yet —
    fail closed rather than let a typo'd --table silently create/pollute the wrong table."""
    raw = os.environ.get("AIRTABLE_TABLE_ALLOWLIST", "")
    names = {name.strip() for name in raw.split(",") if name.strip()}
    return names or None


def require_table_allowlisted(table_name: str) -> None:
    allowed = allowed_airtable_tables()
    if not allowed:
        eprint(
            "Refusing live Airtable write: AIRTABLE_TABLE_ALLOWLIST is not set. "
            "Set it to a comma-separated list of approved table names to enable --live writes."
        )
        sys.exit(1)
    if table_name not in allowed:
        eprint(
            f"Refusing live Airtable write: table '{table_name}' is not in AIRTABLE_TABLE_ALLOWLIST "
            f"({', '.join(sorted(allowed))})."
        )
        sys.exit(1)


def confirm_live_write(table_name: str, row_count: int, assume_yes: bool) -> None:
    if assume_yes:
        return
    eprint(f"About to WRITE {row_count} row(s) into Airtable table '{table_name}'.")
    reply = input("Type the table name to confirm, or anything else to abort: ").strip()
    if reply != table_name:
        eprint("Confirmation did not match table name — aborting, no records written.")
        sys.exit(1)


def airtable_get_table_id(table_name: str) -> str | None:
    base_id = airtable_base_id()
    url = f"{AIRTABLE_META}/{base_id}/tables"
    status, data = http_request("GET", url, headers=airtable_headers())
    if status >= 400:
        eprint("Failed to list Airtable tables:", data)
        sys.exit(1)
    for table in data.get("tables", []):
        if table.get("name") == table_name:
            return table.get("id")
    return None


def airtable_ensure_table(table_name: str, field_names: list[str], dry_run: bool) -> None:
    if airtable_get_table_id(table_name):
        return
    if dry_run:
        print(f"[DRY RUN] would create table '{table_name}' with fields: {', '.join(field_names)}")
        return
    require_table_allowlisted(table_name)
    base_id = airtable_base_id()
    url = f"{AIRTABLE_META}/{base_id}/tables"
    fields = [{"name": name, "type": "singleLineText"} for name in field_names]
    payload = {"name": table_name, "fields": fields}
    status, data = http_request(
        "POST",
        url,
        headers=airtable_headers(),
        body=json.dumps(payload).encode("utf-8"),
    )
    if status >= 400:
        eprint("Failed to create Airtable table:", data)
        sys.exit(1)
    print(f"Created table: {table_name}")


def airtable_create_records(
    table_name: str, rows: list[dict[str, str]], dry_run: bool, assume_yes: bool = False
) -> int:
    if not rows:
        return 0
    if dry_run:
        print(f"[DRY RUN] would import {len(rows)} row(s) into table '{table_name}' (no write performed)")
        return len(rows)
    require_table_allowlisted(table_name)
    confirm_live_write(table_name, len(rows), assume_yes)
    base_id = airtable_base_id()
    encoded_table = urllib.parse.quote(table_name, safe="")
    url = f"{AIRTABLE_API}/{base_id}/{encoded_table}"
    created = 0
    batch_size = 10
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        records = [{"fields": row} for row in chunk]
        status, data = http_request(
            "POST",
            url,
            headers=airtable_headers(),
            body=json.dumps({"records": records}).encode("utf-8"),
        )
        if status >= 400:
            eprint(f"Failed to import batch {i // batch_size + 1} ({len(chunk)} rows):", data)
            sys.exit(1)
        created += len(data.get("records", chunk))
        print(f"  batch {i // batch_size + 1}: wrote {len(chunk)} row(s), {created}/{len(rows)} total")
    return created


def airtable_fetch_table(table_name: str) -> list[dict[str, Any]]:
    base_id = airtable_base_id()
    encoded_table = urllib.parse.quote(table_name, safe="")
    url = f"{AIRTABLE_API}/{base_id}/{encoded_table}"
    records: list[dict[str, Any]] = []
    offset = None
    while True:
        page_url = url if not offset else f"{url}?offset={urllib.parse.quote(offset)}"
        status, data = http_request("GET", page_url, headers=airtable_headers())
        if status >= 400:
            eprint("Failed to fetch Airtable table:", data)
            sys.exit(1)
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def cmd_airtable_list_templates(_: argparse.Namespace) -> None:
    for name in list_csv_templates():
        print(name)


def cmd_airtable_show_template(args: argparse.Namespace) -> None:
    path = template_path(args.template)
    fields, rows = read_csv_template(path)
    print(f"Template: {args.template}")
    print(f"File: {path}")
    print(f"Fields: {', '.join(fields)}")
    print(f"Sample rows: {min(len(rows), 5)} of {len(rows)}")
    for row in rows[:5]:
        print(json.dumps(row, ensure_ascii=False))


def cmd_airtable_import_template(args: argparse.Namespace) -> None:
    path = template_path(args.template)
    table_name = args.table or args.template
    fields, rows = read_csv_template(path)
    dry_run = not args.live
    airtable_ensure_table(table_name, fields, dry_run=dry_run)
    count = airtable_create_records(table_name, rows, dry_run=dry_run, assume_yes=args.yes)
    verb = "Would import" if dry_run else "Imported"
    print(f"{verb} {count} rows into table '{table_name}' from {path.name}")
    if dry_run:
        print("(dry run — pass --live to actually write; table must be in AIRTABLE_TABLE_ALLOWLIST)")


def cmd_airtable_sync_templates(args: argparse.Namespace) -> None:
    names = list_csv_templates()
    if not names:
        print("No CSV templates found.")
        return
    dry_run = not args.live
    for name in names:
        path = template_path(name)
        fields, rows = read_csv_template(path)
        airtable_ensure_table(name, fields, dry_run=dry_run)
        count = airtable_create_records(name, rows, dry_run=dry_run, assume_yes=args.yes)
        verb = "would import" if dry_run else "imported"
        print(f"{name}: {verb} {count} rows")
    if dry_run:
        print("(dry run — pass --live to actually write; each table must be in AIRTABLE_TABLE_ALLOWLIST)")


def cmd_airtable_get_table(args: argparse.Namespace) -> None:
    records = airtable_fetch_table(args.table)
    print(json.dumps(records, indent=2))


def supabase_fetch_table(table: str) -> list[dict[str, Any]]:
    base_url = env("SUPABASE_URL", required=True)
    key = env("SUPABASE_KEY", required=True)
    assert base_url and key
    url = f"{base_url.rstrip('/')}/rest/v1/{urllib.parse.quote(table, safe='')}?select=*"
    status, data = http_request(
        "GET",
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    if status >= 400:
        eprint("Supabase fetch failed:", data)
        sys.exit(1)
    return data if isinstance(data, list) else []


def cmd_supabase_fetch_table(args: argparse.Namespace) -> None:
    rows = supabase_fetch_table(args.table)
    print(json.dumps(rows, indent=2))


def vercel_call_endpoint(endpoint: str, method: str, body: str | None) -> Any:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = body.encode("utf-8") if body else None
    status, data = http_request(method, endpoint, headers=headers, body=payload)
    if status >= 400:
        eprint(f"Vercel endpoint returned {status}:", data)
        sys.exit(1)
    return data


def cmd_vercel_call_endpoint(args: argparse.Namespace) -> None:
    result = vercel_call_endpoint(args.endpoint, args.http_method, args.body)
    if result is None:
        print("(empty response)")
    else:
        print(json.dumps(result, indent=2) if isinstance(result, (dict, list)) else result)


def parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_snapshot(
    airtable_tables: list[str],
    supabase_tables: list[str],
    vercel_endpoints: list[str],
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "airtable": {},
        "supabase": {},
        "vercel": {},
    }
    if airtable_tables and env("AIRTABLE_API_KEY") and env("AIRTABLE_BASE_ID"):
        for table in airtable_tables:
            snapshot["airtable"][table] = airtable_fetch_table(table)
    if supabase_tables and env("SUPABASE_URL") and env("SUPABASE_KEY"):
        for table in supabase_tables:
            snapshot["supabase"][table] = supabase_fetch_table(table)
    for endpoint in vercel_endpoints:
        snapshot["vercel"][endpoint] = vercel_call_endpoint(endpoint, "GET", None)
    return snapshot


def cmd_snapshot(args: argparse.Namespace) -> None:
    airtable_tables = parse_csv_list(args.airtable_tables)
    supabase_tables = parse_csv_list(args.supabase_tables)
    vercel_endpoints = parse_csv_list(args.vercel_endpoints)
    snapshot = build_snapshot(airtable_tables, supabase_tables, vercel_endpoints)
    snapshot_json = json.dumps(snapshot, indent=2)

    if env("OPENAI_API_KEY"):
        prompt_name = args.prompt_name or "tmmt_command_center_snapshot"
        prompt = load_prompt(prompt_name)
        result = run_openai(prompt, snapshot_json)
        print(result)
    else:
        print(snapshot_json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aix_operator",
        description="AIX AI Command System — prompts, Airtable templates, and live data integrations.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List available prompts").set_defaults(func=cmd_list)

    show_p = sub.add_parser("show", help="Show a prompt template")
    show_p.add_argument("name", help="Prompt name")
    show_p.set_defaults(func=cmd_show)

    run_p = sub.add_parser("run", help="Run a prompt with OpenAI")
    run_p.add_argument("name", help="Prompt name")
    run_p.add_argument("--data", help="Extra context string")
    run_p.add_argument("--data-file", help="Path to extra context file")
    run_p.set_defaults(func=cmd_run)

    airtable = sub.add_parser("airtable", help="Airtable template and data operations")
    airtable_sub = airtable.add_subparsers(dest="airtable_command", required=True)

    airtable_sub.add_parser("list-templates").set_defaults(func=cmd_airtable_list_templates)

    show_t = airtable_sub.add_parser("show-template")
    show_t.add_argument("--template", required=True)
    show_t.set_defaults(func=cmd_airtable_show_template)

    import_t = airtable_sub.add_parser("import-template")
    import_t.add_argument("--template", required=True)
    import_t.add_argument("--table", help="Target Airtable table name (default: template name)")
    import_t.add_argument("--live", action="store_true", help="Actually write records (default: dry run)")
    import_t.add_argument("--yes", action="store_true", help="Skip interactive confirmation for --live writes")
    import_t.set_defaults(func=cmd_airtable_import_template)

    sync_t = airtable_sub.add_parser("sync-templates")
    sync_t.add_argument("--live", action="store_true", help="Actually write records (default: dry run)")
    sync_t.add_argument("--yes", action="store_true", help="Skip interactive confirmation for --live writes")
    sync_t.set_defaults(func=cmd_airtable_sync_templates)

    get_t = airtable_sub.add_parser("get-table")
    get_t.add_argument("--table", required=True)
    get_t.set_defaults(func=cmd_airtable_get_table)

    supabase = sub.add_parser("supabase", help="Supabase operations")
    supabase_sub = supabase.add_subparsers(dest="supabase_command", required=True)
    fetch_t = supabase_sub.add_parser("fetch-table")
    fetch_t.add_argument("--table", required=True)
    fetch_t.set_defaults(func=cmd_supabase_fetch_table)

    vercel = sub.add_parser("vercel", help="Vercel endpoint operations")
    vercel_sub = vercel.add_subparsers(dest="vercel_command", required=True)
    call_p = vercel_sub.add_parser("call-endpoint")
    call_p.add_argument("--endpoint", required=True)
    call_p.add_argument("--http-method", default="GET", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    call_p.add_argument("--body", help="JSON request body")
    call_p.set_defaults(func=cmd_vercel_call_endpoint)

    snap_p = sub.add_parser("snapshot", help="Combined TMMT snapshot from all integrations")
    snap_p.add_argument("--airtable-tables", default="", help="Comma-separated Airtable tables")
    snap_p.add_argument("--supabase-tables", default="", help="Comma-separated Supabase tables")
    snap_p.add_argument("--vercel-endpoints", default="", help="Comma-separated Vercel URLs")
    snap_p.add_argument("--prompt-name", default="tmmt_command_center_snapshot")
    snap_p.set_defaults(func=cmd_snapshot)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    func = getattr(args, "func", None)
    if not func:
        parser.print_help()
        sys.exit(1)
    func(args)


if __name__ == "__main__":
    main()
