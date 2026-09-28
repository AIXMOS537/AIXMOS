from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import aix_operator as aix
from backend import integration

app = FastAPI(title="AIX Operator API", version="0.2.0")


def require_command_secret(x_command_secret: str | None = Header(None, alias="X-Command-Secret")) -> None:
    expected = os.environ.get("COMMAND_API_SECRET")
    if not expected:
        return
    if x_command_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Command-Secret")


class SnapshotRequest(BaseModel):
    airtable_tables: str | None = None
    supabase_tables: str | None = None
    vercel_endpoints: str | None = None
    prompt_name: str = "tmmt_command_center_snapshot"
    summarize: bool = True


class TmmtSnapshotRequest(BaseModel):
    airtable_tables: list[str] | None = None
    supabase_tables: list[str] | None = None
    vercel_urls: list[str] | None = None
    prompt_name: str | None = None
    summarize: bool = True
    probe: bool = False


class RunPromptRequest(BaseModel):
    prompt_name: str = "morning_command"
    extra_context: str | None = None
    include_snapshot: bool = True
    summarize: bool = True


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "AIX Operator API",
        "integrations": "/integrations/status",
        "command_center": "/command/tmmt-snapshot",
    }


@app.get("/prompts")
def list_prompts():
    return {"prompts": aix.list_prompts()}


@app.get("/prompts/{prompt_name}")
def get_prompt(prompt_name: str):
    try:
        return {"prompt_name": prompt_name, "prompt": aix.load_prompt_text(prompt_name)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/integrations/status", dependencies=[Depends(require_command_secret)])
def integrations_status(probe: bool = Query(False)):
    return integration.integration_status(probe=probe)


@app.get("/integrations/discover/airtable", dependencies=[Depends(require_command_secret)])
def discover_airtable():
    try:
        tables = integration.discover_airtable_tables()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"tables": tables}


@app.get("/airtable/{table_name}", dependencies=[Depends(require_command_secret)])
def get_airtable_table(table_name: str, max_records: int = Query(50, ge=1, le=100)):
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = integration.get_airtable_base_id()
    if not api_key or not base_id:
        raise HTTPException(
            status_code=400,
            detail="AIRTABLE_API_KEY and AIRTABLE_BASE_ID (or config airtable.base_id) are required",
        )
    try:
        rows = aix.fetch_airtable_table_rows(table_name, base_id, api_key, max_records=max_records)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"table": table_name, "rows": rows}


@app.get("/supabase/{table_name}", dependencies=[Depends(require_command_secret)])
def get_supabase_table(table_name: str, limit: int = Query(50, ge=1, le=100)):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=400, detail="SUPABASE_URL and SUPABASE_KEY are required")
    try:
        rows = aix.fetch_supabase_table_rows(url, key, table_name, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"table": table_name, "rows": rows}


@app.post("/command/tmmt-snapshot", dependencies=[Depends(require_command_secret)])
def command_tmmt_snapshot(request: TmmtSnapshotRequest):
    cfg = integration.load_integration_config()
    prompt_name = request.prompt_name or integration.prompt_name(
        cfg, "command_center_snapshot", "tmmt_command_center_snapshot"
    )
    snapshot = integration.build_tmmt_snapshot(
        airtable_tables=request.airtable_tables,
        supabase_tables=request.supabase_tables,
        vercel_urls=request.vercel_urls,
    )
    if request.probe:
        snapshot["status"] = integration.integration_status(probe=True)

    if request.summarize and os.environ.get("OPENAI_API_KEY"):
        try:
            summary = integration.summarize_tmmt_snapshot(snapshot, prompt_name)
            return {"summary": summary, "snapshot": snapshot, "prompt_name": prompt_name}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    return {"snapshot": snapshot, "prompt_name": prompt_name}


@app.post("/command/run", dependencies=[Depends(require_command_secret)])
def command_run(request: RunPromptRequest):
    try:
        prompt_text = aix.load_prompt_text(request.prompt_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if request.include_snapshot:
        snapshot = integration.build_tmmt_snapshot()
        flat = integration._flatten_snapshot_for_prompt(snapshot)
        snapshot_text = json.dumps(flat, indent=2)
        if len(snapshot_text) > 12000:
            snapshot_text = snapshot_text[:12000] + "\n...TRUNCATED..."
        prompt_text = (
            prompt_text
            + "\n\nLive data from TMMT (Airtable, Supabase, Vercel):\n"
            + snapshot_text
        )

    if request.extra_context:
        prompt_text = prompt_text + "\n\n" + request.extra_context.strip()

    if not request.summarize:
        return {"prompt": prompt_text}

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required when summarize=true")
    try:
        result = aix.run_openai(prompt_text, api_key=openai_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"result": result, "prompt_name": request.prompt_name}


@app.post("/snapshot", dependencies=[Depends(require_command_secret)])
def snapshot(request: SnapshotRequest):
    airtable_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = integration.get_airtable_base_id() or ""
    supabase_url = integration.get_supabase_url()
    supabase_key = os.environ.get("SUPABASE_KEY")
    try:
        snapshot_data = aix.build_snapshot_from_sources(
            request.airtable_tables,
            base_id,
            airtable_key,
            request.supabase_tables,
            supabase_url,
            supabase_key,
            request.vercel_endpoints,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not snapshot_data:
        raise HTTPException(status_code=400, detail="No snapshot data sources provided")

    if request.summarize and os.environ.get("OPENAI_API_KEY"):
        try:
            result = aix.summarize_snapshot(
                request.prompt_name, snapshot_data, os.environ.get("OPENAI_API_KEY")
            )
            return {"summary": result, "snapshot": snapshot_data}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    return {"snapshot": snapshot_data}


@app.get("/dealership/partners", dependencies=[Depends(require_command_secret)])
def get_partners():
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = integration.get_airtable_base_id()
    if not api_key or not base_id:
        raise HTTPException(status_code=400, detail="AIRTABLE_API_KEY and AIRTABLE_BASE_ID are required")
    rows = aix.fetch_airtable_table_rows("Dealership Partners", base_id, api_key, max_records=100)
    return {"partners": rows}


@app.get("/dealership/shared-lot", dependencies=[Depends(require_command_secret)])
def get_shared_lot():
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = integration.get_airtable_base_id()
    if not api_key or not base_id:
        raise HTTPException(status_code=400, detail="AIRTABLE_API_KEY and AIRTABLE_BASE_ID are required")
    rows = aix.fetch_airtable_table_rows("Shared Lot Inventory", base_id, api_key, max_records=100)
    return {"shared_lot": rows}


@app.get("/dealership/fleet", dependencies=[Depends(require_command_secret)])
def get_fleet(table: str = Query(...)):
    api_key = os.environ.get("AIRTABLE_API_KEY")
    base_id = integration.get_airtable_base_id()
    if not api_key or not base_id:
        raise HTTPException(status_code=400, detail="AIRTABLE_API_KEY and AIRTABLE_BASE_ID are required")
    rows = aix.fetch_airtable_table_rows(table, base_id, api_key, max_records=100)
    return {"table": table, "rows": rows}
