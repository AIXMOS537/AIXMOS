"""
title: TMMT Command Center
author: aix
version: 0.1.0
description: Brain-dump → ClickUp task creation across registered ventures.
"""
import os
from pathlib import Path
from typing import Optional

import requests
from pydantic import BaseModel, Field

# When installed in Open WebUI's tools dir, clickup_client must be importable.
# In dev, set PYTHONPATH to the tools/ folder.
from clickup_client import create_task_for_venture, load_ventures


class Tools:
    class Valves(BaseModel):
        CLICKUP_API_TOKEN: str = Field(
            default="",
            description="ClickUp personal API token (pk_...). Required.",
        )
        CLICKUP_DEFAULT_ASSIGNEE_ID: int = Field(
            default=0,
            description="Numeric ClickUp user id to assign tasks to. Required.",
        )
        VENTURES_PATH: str = Field(
            default=os.path.expanduser("~/AIX-Command-Center/config/ventures.json"),
            description="Absolute path to ventures.json. Override when running in Docker if the mount differs from the host path.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def list_ventures(self) -> list[dict]:
        """List active ventures the agent can create tasks in.

        :return: list of {slug, name, default_tag} for each active venture
        """
        ventures = load_ventures(Path(self.valves.VENTURES_PATH))
        return [
            {"slug": v["slug"], "name": v["name"], "default_tag": v["default_tag"]}
            for v in ventures
        ]

    def clickup_create_task(
        self,
        title: str,
        description: str,
        venture_slug: str,
        due_date_ms: Optional[int] = None,
        priority: Optional[int] = None,
    ) -> dict:
        """Create a ClickUp task in the registered list for the given venture.

        :param title: Short imperative task title (e.g. "Call Maria Rodriguez")
        :param description: Original phrasing from the brain-dump, preserved
        :param venture_slug: Must be a slug returned by list_ventures()
        :param due_date_ms: Epoch ms for the due date, or None
        :param priority: 1 (urgent) to 4 (low), or None
        :return: {task_id, url, title} or {error: "..."} on failure
        """
        if not self.valves.CLICKUP_API_TOKEN:
            return {"error": "CLICKUP_API_TOKEN not configured in tool valves"}
        if self.valves.CLICKUP_DEFAULT_ASSIGNEE_ID == 0:
            return {"error": "CLICKUP_DEFAULT_ASSIGNEE_ID not configured in tool valves"}

        try:
            return create_task_for_venture(
                token=self.valves.CLICKUP_API_TOKEN,
                ventures_path=Path(self.valves.VENTURES_PATH),
                venture_slug=venture_slug,
                title=title,
                description=description,
                assignee_id=self.valves.CLICKUP_DEFAULT_ASSIGNEE_ID,
                due_date_ms=due_date_ms,
                priority=priority,
            )
        except ValueError as e:
            return {"error": str(e)}
        except RuntimeError as e:
            return {"error": str(e)}
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {e}"}
