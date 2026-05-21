import json
from pathlib import Path

from clickup_client import load_ventures

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ventures.test.json"


def test_load_ventures_returns_only_active():
    result = load_ventures(FIXTURE_PATH)
    assert len(result) == 1
    assert result[0]["slug"] == "tmmt-rentals"


def test_load_ventures_preserves_required_fields():
    result = load_ventures(FIXTURE_PATH)
    v = result[0]
    assert v["clickup_list_id"] == "111"
    assert v["name"] == "TMMT Rentals"
    assert v["default_tag"] == "tmmt-rentals"
