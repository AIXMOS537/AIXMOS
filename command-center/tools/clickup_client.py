"""Pure logic for the brain-dump → ClickUp tool. Open WebUI imports from this."""
import json
from pathlib import Path

import requests

CLICKUP_API_BASE = "https://api.clickup.com/api/v2"


def load_ventures(ventures_path: Path) -> list[dict]:
    """Read ventures.json and return only ventures with status == 'active'."""
    with open(ventures_path) as f:
        data = json.load(f)
    return [v for v in data["ventures"] if v.get("status") == "active"]


def create_task_for_venture(
    token: str,
    ventures_path: Path,
    venture_slug: str,
    title: str,
    description: str,
    assignee_id: int,
    due_date_ms: int | None = None,
    priority: int | None = None,
) -> dict:
    """Create a ClickUp task in the list registered for venture_slug.

    Returns: {"task_id": str, "url": str, "title": str}
    Raises:  ValueError if venture not registered
             RuntimeError if ClickUp API call fails
    """
    venture = _lookup_venture(ventures_path, venture_slug)
    list_id = venture["clickup_list_id"]
    tag = venture["default_tag"]

    body = {
        "name": title,
        "description": description,
        "assignees": [assignee_id],
        "tags": [tag],
    }
    if due_date_ms is not None:
        body["due_date"] = due_date_ms
    if priority is not None:
        body["priority"] = priority

    response = requests.post(
        f"{CLICKUP_API_BASE}/list/{list_id}/task",
        headers={"Authorization": token, "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    if response.status_code >= 300:
        raise RuntimeError(
            f"ClickUp API returned {response.status_code}: {response.text[:200]}"
        )

    payload = response.json()
    return {
        "task_id": payload["id"],
        "url": payload["url"],
        "title": title,
    }


def _lookup_venture(ventures_path: Path, slug: str) -> dict:
    for v in load_ventures(ventures_path):
        if v["slug"] == slug:
            return v
    raise ValueError(f"Unknown venture slug: {slug!r}")
