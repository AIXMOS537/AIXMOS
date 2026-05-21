"""Pure logic for the brain-dump → ClickUp tool. Open WebUI imports from this."""
import json
from pathlib import Path


def load_ventures(ventures_path: Path) -> list[dict]:
    """Read ventures.json and return only ventures with status == 'active'."""
    with open(ventures_path) as f:
        data = json.load(f)
    return [v for v in data["ventures"] if v.get("status") == "active"]
