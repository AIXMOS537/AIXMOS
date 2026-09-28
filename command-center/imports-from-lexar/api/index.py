"""Vercel serverless entrypoint for the AIX Operator API."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api import app  # noqa: F401 — Vercel imports `app`
