"""Load TMMT integration config and build unified snapshots from Airtable, Supabase, and Vercel."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import aix_operator as aix

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "tmmt_integration.json"
EXAMPLE_CONFIG = ROOT / "config" / "tmmt_integration.example.json"


def _config_path() -> Path:
    override = os.environ.get("AIX_INTEGRATION_CONFIG")
    if override:
        return Path(override)
    if DEFAULT_CONFIG.is_file():
        return DEFAULT_CONFIG
    return EXAMPLE_CONFIG


def load_integration_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_airtable_base_id(cfg: dict[str, Any] | None = None) -> str | None:
    env_base = os.environ.get("AIRTABLE_BASE_ID")
    if env_base:
        return env_base
    cfg = cfg if cfg is not None else load_integration_config()
    airtable = cfg.get("airtable") or {}
    return airtable.get("base_id")


def get_supabase_url(cfg: dict[str, Any] | None = None) -> str | None:
    env_url = os.environ.get("SUPABASE_URL")
    if env_url:
        return env_url.rstrip("/")
    cfg = cfg if cfg is not None else load_integration_config()
    supabase = cfg.get("supabase") or {}
    url = supabase.get("url")
    return url.rstrip("/") if url else None


def _csv_env(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def airtable_snapshot_tables(cfg: dict[str, Any]) -> list[str]:
    env_tables = _csv_env("AIRTABLE_SNAPSHOT_TABLES")
    if env_tables:
        return env_tables
    airtable = cfg.get("airtable") or {}
    return list(airtable.get("snapshot_tables") or [])


def supabase_snapshot_tables(cfg: dict[str, Any]) -> list[str]:
    env_tables = _csv_env("SUPABASE_SNAPSHOT_TABLES")
    if env_tables:
        return env_tables
    supabase = cfg.get("supabase") or {}
    return list(supabase.get("snapshot_tables") or [])


def vercel_snapshot_urls(cfg: dict[str, Any]) -> list[str]:
    env_paths = _csv_env("VERCEL_SNAPSHOT_PATHS")
    app_url = (
        os.environ.get("VERCEL_APP_URL")
        or os.environ.get("NEXT_PUBLIC_VERCEL_APP_URL")
        or (cfg.get("vercel") or {}).get("app_url")
        or ""
    ).rstrip("/")

    if env_paths and app_url:
        return [f"{app_url}{path if path.startswith('/') else '/' + path}" for path in env_paths]

    vercel = cfg.get("vercel") or {}
    paths = list(vercel.get("snapshot_paths") or [])
    if app_url and paths:
        return [f"{app_url}{path if path.startswith('/') else '/' + path}" for path in paths]
    return []


def prompt_name(cfg: dict[str, Any], key: str, default: str) -> str:
    prompts = cfg.get("prompts") or {}
    return str(prompts.get(key) or default)


def credentials_status() -> dict[str, Any]:
    cfg = load_integration_config()
    return {
        "airtable": bool(os.environ.get("AIRTABLE_API_KEY") and get_airtable_base_id(cfg)),
        "supabase": bool(get_supabase_url(cfg) and os.environ.get("SUPABASE_KEY")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "vercel_app_url": bool(
            os.environ.get("VERCEL_APP_URL")
            or os.environ.get("NEXT_PUBLIC_VERCEL_APP_URL")
            or load_integration_config().get("vercel", {}).get("app_url")
        ),
    }


def discover_airtable_tables() -> list[dict[str, str]]:
    cfg = load_integration_config()
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = get_airtable_base_id(cfg)
    if not api_key or not base_id:
        raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID (or config airtable.base_id) are required")
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    response = aix.http_request(url, headers={"Authorization": f"Bearer {api_key}"})
    if not isinstance(response, dict):
        return []
    return [
        {"id": table.get("id", ""), "name": table.get("name", "")}
        for table in response.get("tables", [])
        if table.get("name")
    ]


def probe_table(name: str, source: str) -> dict[str, Any]:
    try:
        if source == "airtable":
            api_key = os.environ.get("AIRTABLE_API_KEY")
            base_id = get_airtable_base_id()
            if not api_key or not base_id:
                return {"ok": False, "error": "missing Airtable credentials"}
            rows = aix.fetch_airtable_table_rows(name, base_id, api_key, max_records=3)
            return {"ok": True, "sample_count": len(rows)}
        if source == "supabase":
            url = get_supabase_url()
            key = os.environ.get("SUPABASE_KEY")
            if not url or not key:
                return {"ok": False, "error": "missing Supabase credentials"}
            rows = aix.fetch_supabase_table_rows(url, key, name, limit=3)
            count = len(rows) if isinstance(rows, list) else 0
            return {"ok": True, "sample_count": count}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"unknown source {source}"}


def build_tmmt_snapshot(
    *,
    airtable_tables: list[str] | None = None,
    supabase_tables: list[str] | None = None,
    vercel_urls: list[str] | None = None,
    max_airtable_records: int = 50,
    max_supabase_records: int = 50,
) -> dict[str, Any]:
    cfg = load_integration_config()
    airtable_tables = airtable_tables if airtable_tables is not None else airtable_snapshot_tables(cfg)
    supabase_tables = supabase_tables if supabase_tables is not None else supabase_snapshot_tables(cfg)
    vercel_urls = vercel_urls if vercel_urls is not None else vercel_snapshot_urls(cfg)

    cfg = load_integration_config()
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = get_airtable_base_id(cfg)
    supabase_url = get_supabase_url(cfg)
    supabase_key = os.environ.get("SUPABASE_KEY")

    snapshot: dict[str, Any] = {"sources": {}, "integration": cfg.get("name", "tmmt")}

    errors: list[str] = []
    if airtable_tables:
        if not api_key or not base_id:
            errors.append("Airtable tables requested but AIRTABLE_API_KEY / AIRTABLE_BASE_ID missing")
        else:
            snapshot["sources"]["airtable"] = {}
            for table in airtable_tables:
                try:
                    snapshot["sources"]["airtable"][table] = aix.fetch_airtable_table_rows(
                        table, base_id, api_key, max_records=max_airtable_records
                    )
                except Exception as exc:
                    snapshot["sources"]["airtable"][table] = {"error": str(exc)}
                    errors.append(f"airtable:{table}: {exc}")

    if supabase_tables:
        if not supabase_url or not supabase_key:
            errors.append("Supabase tables requested but SUPABASE_URL / SUPABASE_KEY missing")
        else:
            snapshot["sources"]["supabase"] = {}
            for table in supabase_tables:
                try:
                    rows = aix.fetch_supabase_table_rows(
                        supabase_url, supabase_key, table, limit=max_supabase_records
                    )
                    snapshot["sources"]["supabase"][table] = rows if isinstance(rows, list) else rows
                except Exception as exc:
                    snapshot["sources"]["supabase"][table] = {"error": str(exc)}
                    errors.append(f"supabase:{table}: {exc}")

    if vercel_urls:
        snapshot["sources"]["vercel"] = {}
        for url in vercel_urls:
            try:
                snapshot["sources"]["vercel"][url] = aix.http_request(
                    url, method="GET", headers={"Accept": "application/json"}
                )
            except Exception as exc:
                snapshot["sources"]["vercel"][url] = {"error": str(exc)}
                errors.append(f"vercel:{url}: {exc}")

    if errors:
        snapshot["errors"] = errors
    return snapshot


def summarize_tmmt_snapshot(snapshot: dict[str, Any], prompt_key: str = "tmmt_command_center_snapshot") -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for AI summaries")
    flat = _flatten_snapshot_for_prompt(snapshot)
    return aix.summarize_snapshot(prompt_key, flat, api_key)


def _flatten_snapshot_for_prompt(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Convert nested integration snapshot to keys expected by summarize_snapshot."""
    flat: dict[str, Any] = {}
    sources = snapshot.get("sources") or {}
    for table, rows in (sources.get("airtable") or {}).items():
        flat[f"airtable:{table}"] = rows
    for table, rows in (sources.get("supabase") or {}).items():
        flat[f"supabase:{table}"] = rows
    for url, payload in (sources.get("vercel") or {}).items():
        flat[f"vercel:{url}"] = payload
    return flat


def integration_status(probe: bool = False) -> dict[str, Any]:
    cfg = load_integration_config()
    airtable_meta = cfg.get("airtable") or {}
    status: dict[str, Any] = {
        "config_path": str(_config_path()),
        "airtable_base_id": get_airtable_base_id(cfg),
        "airtable_primary_table_id": airtable_meta.get("primary_table_id"),
        "supabase_url": get_supabase_url(cfg),
        "vercel_app_url": (cfg.get("vercel") or {}).get("app_url") or os.environ.get("VERCEL_APP_URL"),
        "credentials": credentials_status(),
        "airtable_tables": airtable_snapshot_tables(cfg),
        "supabase_tables": supabase_snapshot_tables(cfg),
        "vercel_urls": vercel_snapshot_urls(cfg),
        "prompts": cfg.get("prompts") or {},
    }
    if probe:
        status["probes"] = {
            "airtable": {
                table: probe_table(table, "airtable")
                for table in status["airtable_tables"][:8]
            },
            "supabase": {
                table: probe_table(table, "supabase")
                for table in status["supabase_tables"][:8]
            },
        }
    return status
