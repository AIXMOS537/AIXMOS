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


from clickup_client import create_task_for_venture


def test_create_task_for_venture_posts_to_correct_list(mocker):
    mock_post = mocker.patch("clickup_client.requests.post")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "id": "abc123",
        "url": "https://app.clickup.com/t/abc123",
    }

    result = create_task_for_venture(
        token="pk_test",
        ventures_path=FIXTURE_PATH,
        venture_slug="tmmt-rentals",
        title="Call Maria",
        description="Customer Maria Rodriguez needs a follow-up call Tuesday",
        assignee_id=12345678,
    )

    assert result["task_id"] == "abc123"
    assert result["url"] == "https://app.clickup.com/t/abc123"
    assert result["title"] == "Call Maria"

    # Verify it hit the right URL
    call_args = mock_post.call_args
    assert call_args.args[0] == "https://api.clickup.com/api/v2/list/111/task"

    # Verify the body
    body = call_args.kwargs["json"]
    assert body["name"] == "Call Maria"
    assert body["description"] == "Customer Maria Rodriguez needs a follow-up call Tuesday"
    assert body["assignees"] == [12345678]
    assert body["tags"] == ["tmmt-rentals"]

    # Verify auth header
    headers = call_args.kwargs["headers"]
    assert headers["Authorization"] == "pk_test"


def test_create_task_for_venture_includes_due_date_when_provided(mocker):
    mock_post = mocker.patch("clickup_client.requests.post")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id": "xyz", "url": "https://app.clickup.com/t/xyz"}

    create_task_for_venture(
        token="pk_test",
        ventures_path=FIXTURE_PATH,
        venture_slug="tmmt-rentals",
        title="Oil change",
        description="Mustang VIN 8847",
        assignee_id=12345678,
        due_date_ms=1748390400000,
    )

    body = mock_post.call_args.kwargs["json"]
    assert body["due_date"] == 1748390400000


def test_create_task_for_venture_omits_due_date_when_not_provided(mocker):
    mock_post = mocker.patch("clickup_client.requests.post")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id": "xyz", "url": "https://app.clickup.com/t/xyz"}

    create_task_for_venture(
        token="pk_test",
        ventures_path=FIXTURE_PATH,
        venture_slug="tmmt-rentals",
        title="No due date",
        description="task",
        assignee_id=12345678,
    )

    body = mock_post.call_args.kwargs["json"]
    assert "due_date" not in body


import pytest


def test_create_task_raises_on_unknown_venture(mocker):
    mock_post = mocker.patch("clickup_client.requests.post")
    with pytest.raises(ValueError, match="Unknown venture slug"):
        create_task_for_venture(
            token="pk_test",
            ventures_path=FIXTURE_PATH,
            venture_slug="does-not-exist",
            title="t",
            description="d",
            assignee_id=1,
        )
    mock_post.assert_not_called()


def test_create_task_raises_on_clickup_api_error(mocker):
    mock_post = mocker.patch("clickup_client.requests.post")
    mock_post.return_value.status_code = 401
    mock_post.return_value.text = "Unauthorized"

    with pytest.raises(RuntimeError, match="ClickUp API returned 401"):
        create_task_for_venture(
            token="pk_bad",
            ventures_path=FIXTURE_PATH,
            venture_slug="tmmt-rentals",
            title="t",
            description="d",
            assignee_id=1,
        )


def test_create_task_raises_on_archived_venture(mocker):
    """Archived ventures are filtered out by load_ventures, so lookup should fail."""
    mock_post = mocker.patch("clickup_client.requests.post")
    with pytest.raises(ValueError, match="Unknown venture slug: 'archived-thing'"):
        create_task_for_venture(
            token="pk_test",
            ventures_path=FIXTURE_PATH,
            venture_slug="archived-thing",
            title="t",
            description="d",
            assignee_id=1,
        )
    mock_post.assert_not_called()
