"""
test_buttons.py

Button & Busy-State behavior tests.

Verifies:
- POST /pull-data returns 200, triggers loader using mocked scraper output
- POST /update-analysis returns 200 when not busy
- Busy gating:
    - when pull in progress, POST /update-analysis returns 409 {"busy": true}
    - when busy, POST /pull-data returns 409

All tests are marked ``buttons``.
"""

import os
import pytest
from src.app import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_busy_app(busy_state=None):
    """
    Create an app whose busy state is injectable via a mutable list.

    busy_state[0] is the current flag value.
    """
    if busy_state is None:
        busy_state = [False]

    captured_loads = []

    def fake_scraper():
        return [{"notes": "Test | Prog | Fall 2026 | American | Masters | accepted",
                 "program": "Test", "decision": "Accepted",
                 "gpa": "3.5", "decision_date": None,
                 "llm-generated-program": None,
                 "llm-generated-university": None}]

    def fake_loader(rows, conn):
        captured_loads.append(rows)

    def fake_query(conn):
        return {
            "q1": 0, "q2": None, "q3": (None, None, None, None),
            "q4": None, "q5": None, "q6": None,
            "q7": 0, "q8": 0, "q9": 0,
            "extra_1": [], "extra_2": None,
        }

    app = create_app({
        "TESTING": True,
        "DATABASE_URL": os.environ.get("DATABASE_URL", "postgresql://localhost/test"),
        "SCRAPER_FN": fake_scraper,
        "LOADER_FN": fake_loader,
        "QUERY_FN": fake_query,
        "BUSY_GETTER": lambda: busy_state[0],
        "BUSY_SETTER": lambda v: busy_state.__setitem__(0, v),
    })
    return app, captured_loads, busy_state


# ---------------------------------------------------------------------------
# B) Buttons & Busy-State
# ---------------------------------------------------------------------------

@pytest.mark.buttons
def test_post_pull_returns_200_when_not_busy():
    """POST /pull-data when not busy must return 200 with {"ok": true}."""
    app, loads, _ = _make_busy_app()
    client = app.test_client()
    resp = client.post("/pull-data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"ok": True}


@pytest.mark.buttons
def test_post_pull_triggers_loader():
    """POST /pull-data must call the loader with scraped rows."""
    app, loads, _ = _make_busy_app()
    client = app.test_client()
    client.post("/pull-data")
    assert len(loads) == 1, "Loader was not called"
    assert len(loads[0]) >= 1, "Loader was called with empty rows"


@pytest.mark.buttons
def test_post_update_returns_200_when_not_busy():
    """POST /update-analysis when not busy must return 200 with {"ok": true}."""
    app, _, _ = _make_busy_app()
    client = app.test_client()
    resp = client.post("/update-analysis")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"ok": True}


@pytest.mark.buttons
def test_post_update_returns_409_when_busy():
    """POST /update-analysis while busy must return 409 {"busy": true}."""
    app, loads, busy = _make_busy_app(busy_state=[True])
    client = app.test_client()
    resp = client.post("/update-analysis")
    assert resp.status_code == 409
    data = resp.get_json()
    assert data.get("busy") is True


@pytest.mark.buttons
def test_post_update_does_not_trigger_loader_when_busy():
    """POST /update-analysis while busy must not call the loader."""
    app, loads, busy = _make_busy_app(busy_state=[True])
    client = app.test_client()
    client.post("/update-analysis")
    assert loads == [], "Loader should NOT be called when busy"


@pytest.mark.buttons
def test_post_pull_returns_409_when_busy():
    """POST /pull-data while busy must return 409 {"busy": true}."""
    app, loads, busy = _make_busy_app(busy_state=[True])
    client = app.test_client()
    resp = client.post("/pull-data")
    assert resp.status_code == 409
    data = resp.get_json()
    assert data.get("busy") is True


@pytest.mark.buttons
def test_post_pull_does_not_write_when_busy():
    """POST /pull-data while busy must not call the loader."""
    app, loads, busy = _make_busy_app(busy_state=[True])
    client = app.test_client()
    client.post("/pull-data")
    assert loads == [], "Loader should NOT be called when pull is already busy"


@pytest.mark.buttons
def test_busy_state_resets_after_pull():
    """Busy flag must be False again after a successful pull."""
    app, loads, busy = _make_busy_app()
    client = app.test_client()
    resp = client.post("/pull-data")
    assert resp.status_code == 200
    # After pull completes, busy should be False again
    assert busy[0] is False


@pytest.mark.buttons
def test_pull_response_is_json():
    """POST /pull-data response must be JSON."""
    app, _, _ = _make_busy_app()
    client = app.test_client()
    resp = client.post("/pull-data")
    assert resp.content_type.startswith("application/json")


@pytest.mark.buttons
def test_update_response_is_json():
    """POST /update-analysis response must be JSON."""
    app, _, _ = _make_busy_app()
    client = app.test_client()
    resp = client.post("/update-analysis")
    assert resp.content_type.startswith("application/json")
