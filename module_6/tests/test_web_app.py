# module_6/tests/test_web_app.py
from __future__ import annotations

import json
import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg


def _mock_conn(fetchone_result):
    """
    Build a mock psycopg connection/cursor pair supporting the context-manager usage:
      with _db_conn() as conn:
          with conn.cursor() as cur:
              cur.execute(...)
              row = cur.fetchone()
    """
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_result

    cur_cm = MagicMock()
    cur_cm.__enter__.return_value = cur
    cur_cm.__exit__.return_value = False

    conn = MagicMock()
    conn.cursor.return_value = cur_cm

    conn_cm = MagicMock()
    conn_cm.__enter__.return_value = conn
    conn_cm.__exit__.return_value = False
    return conn_cm


def test_get_analysis_returns_200(client):
    resp = client.get("/analysis")
    assert resp.status_code == 200


def test_post_analyze_recompute_returns_202_and_queues(client):
    with patch("app.publish_task") as mock_publish:
        resp = client.post("/analyze", data={"action": "recompute_analytics"})
        assert resp.status_code == 202
        mock_publish.assert_called_once()
        assert b"Request queued" in resp.data


def test_post_analyze_scrape_returns_202_and_queues(client):
    with patch("app.publish_task") as mock_publish:
        resp = client.post("/analyze", data={"action": "scrape_new_data"})
        assert resp.status_code == 202
        mock_publish.assert_called_once()
        assert b"Request queued" in resp.data


def test_fetch_cached_results_no_row_branch(client):
    # fetchone() -> None triggers early return of defaults
    with patch("app._db_conn", return_value=_mock_conn(None)):
        resp = client.get("/analysis")
        assert resp.status_code == 200
        # Default q1 is 0 in the app defaults
        assert b"Applicant count" in resp.data
        assert b"[0]" in resp.data


def test_fetch_cached_results_dict_payload_branch(client):
    payload = {"q7": 7}
    with patch("app._db_conn", return_value=_mock_conn((payload,))):
        resp = client.get("/analysis")
        assert resp.status_code == 200
        # Template prints: Answer: [7]
        assert b"Answer:" in resp.data
        assert b"[7]" in resp.data


def test_fetch_cached_results_json_string_payload_branch(client):
    payload = json.dumps({"q1": 42})
    with patch("app._db_conn", return_value=_mock_conn((payload,))):
        resp = client.get("/analysis")
        assert resp.status_code == 200
        assert b"Applicant count" in resp.data
        assert b"[42]" in resp.data


def test_fetch_cached_results_invalid_json_payload_branch(client):
    payload = "not-valid-json"
    with patch("app._db_conn", return_value=_mock_conn((payload,))):
        resp = client.get("/analysis")
        assert resp.status_code == 200
        # Should fall back to defaults without crashing
        assert b"Applicant count" in resp.data
        assert b"[0]" in resp.data


def test_fetch_cached_results_outer_exception_branch(client):
    # Use RuntimeError rather than generic Exception for clearer intent
    with patch("app._db_conn", side_effect=RuntimeError("no db")):
        resp = client.get("/analysis")
        assert resp.status_code == 200
        assert b"Applicant count" in resp.data
        assert b"[0]" in resp.data


def test_db_conn_body_covered_executes_psycopg_connect():
    # Patch psycopg.connect so _db_conn() body line executes
    with patch("psycopg.connect") as mock_connect:
        from app import _db_conn  # imported after conftest sys.path setup

        _ = _db_conn()
        mock_connect.assert_called_once()


def test_app_py_main_guard_covered_without_starting_server():
    app_path = Path(__file__).resolve().parents[1] / "src" / "web" / "app.py"
    # Patch the canonical Flask.run location
    with patch("flask.app.Flask.run") as mock_run:
        runpy.run_path(str(app_path), run_name="__main__")
        mock_run.assert_called_once()


def test_run_py_main_guard_covered_without_starting_server():
    run_path = Path(__file__).resolve().parents[1] / "src" / "web" / "run.py"
    with patch("flask.app.Flask.run") as mock_run:
        runpy.run_path(str(run_path), run_name="__main__")
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# Missing route coverage (lines 72-73, 91, 108-110, 122-124, 136 in app.py)
# ---------------------------------------------------------------------------

def test_get_index_returns_200(client):
    """GET / (index route) — covers lines 72-73 in app.py."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_post_analyze_unknown_action_returns_202(client):
    """Unknown action → 'Unknown action' branch (line 91), no publish call."""
    with patch("app.publish_task") as mock_pub:
        resp = client.post("/analyze", data={"action": "bogus_unknown"})
    assert resp.status_code == 202
    assert b"Unknown action" in resp.data
    mock_pub.assert_not_called()


def test_post_pull_data_alias_returns_202(client):
    """POST /pull-data alias — covers lines 108-110 in app.py."""
    with patch("app.publish_task") as mock_pub:
        resp = client.post("/pull-data")
    assert resp.status_code == 202
    assert b"Request queued" in resp.data
    mock_pub.assert_called_once_with("scrape_new_data", payload={"source": "web"})


def test_post_update_analysis_alias_returns_202(client):
    """POST /update-analysis alias — covers lines 122-124 in app.py."""
    with patch("app.publish_task") as mock_pub:
        resp = client.post("/update-analysis")
    assert resp.status_code == 202
    assert b"Request queued" in resp.data
    mock_pub.assert_called_once_with("recompute_analytics", payload={"source": "web"})


def test_get_healthz_returns_200(client):
    """GET /healthz — covers line 136 in app.py."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_scrape_status_module_initial_state():
    """Import scrape_status — covers scrape_status.py line 3 (SCRAPE_RUNNING = False)."""
    import scrape_status  # noqa: PLC0415
    assert scrape_status.SCRAPE_RUNNING is False