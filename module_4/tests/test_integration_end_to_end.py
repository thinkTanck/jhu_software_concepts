"""
test_integration_end_to_end.py

End-to-end integration tests.

Verifies:
- Inject fake scraper returning multiple records
- POST /pull-data succeeds and rows are in DB
- POST /update-analysis succeeds when not busy
- GET /analysis shows updated analysis with correct formatting
- Multiple pulls with overlapping data remain consistent (uniqueness policy)

All tests are marked ``integration``.
"""

import re
import pytest
from bs4 import BeautifulSoup

from src import load_data as ld
from src import query_data as qd
from tests.conftest import FAKE_ROWS, DATABASE_URL


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

def _count_rows(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applicants")
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# E) Integration
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_pull_succeeds_end_to_end(db_client, db_transaction):
    """POST /pull-data must succeed and insert rows into the DB."""
    resp = db_client.post("/pull-data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True
    # Rows must now exist in the DB
    count = _count_rows(db_transaction)
    assert count > 0, "Expected rows in DB after pull"


@pytest.mark.integration
def test_pull_inserts_correct_row_count(db_client, db_transaction):
    """POST /pull-data must insert exactly len(FAKE_ROWS) rows."""
    db_client.post("/pull-data")
    count = _count_rows(db_transaction)
    assert count == len(FAKE_ROWS), (
        f"Expected {len(FAKE_ROWS)} rows after pull, found {count}"
    )


@pytest.mark.integration
def test_update_succeeds_when_not_busy(db_client):
    """POST /update-analysis must return 200 {"ok": true} when not busy."""
    resp = db_client.post("/update-analysis")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


@pytest.mark.integration
def test_analysis_page_renders_after_pull(db_client):
    """GET /analysis must return 200 after a pull."""
    db_client.post("/pull-data")
    resp = db_client.get("/analysis")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Analysis" in text
    assert "Answer:" in text


@pytest.mark.integration
def test_analysis_page_contains_buttons_after_pull(db_client):
    """After a pull, both buttons must still be present."""
    db_client.post("/pull-data")
    resp = db_client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    pull_btn = soup.find("button", attrs={"data-testid": "pull-data-btn"})
    update_btn = soup.find("button", attrs={"data-testid": "update-analysis-btn"})
    assert pull_btn is not None
    assert update_btn is not None


@pytest.mark.integration
def test_overlapping_pull_no_duplicates(db_client, db_transaction):
    """Two pulls with the same data must not create duplicates."""
    db_client.post("/pull-data")
    db_client.post("/pull-data")
    count = _count_rows(db_transaction)
    assert count == len(FAKE_ROWS), (
        f"Duplicate rows found: expected {len(FAKE_ROWS)}, got {count}"
    )


@pytest.mark.integration
def test_pull_then_update_full_flow(db_client):
    """Complete flow: pull → update → GET analysis must all succeed."""
    r1 = db_client.post("/pull-data")
    assert r1.status_code == 200

    r2 = db_client.post("/update-analysis")
    assert r2.status_code == 200

    r3 = db_client.get("/analysis")
    assert r3.status_code == 200
    assert "Analysis" in r3.data.decode()


@pytest.mark.integration
def test_analysis_percentages_two_decimals_integration(db_client):
    """After full pull, rendered percentages must use two decimal places."""
    db_client.post("/pull-data")
    resp = db_client.get("/analysis")
    text = resp.data.decode()
    # Find all percentage patterns
    pcts = re.findall(r"\d+\.\d+%", text)
    for p in pcts:
        assert re.fullmatch(r"\d+\.\d{2}%", p), (
            f"Percentage '{p}' does not have exactly 2 decimal places"
        )


@pytest.mark.integration
def test_query_results_keys_present_after_pull(db_client, db_transaction):
    """After pull, query_all() must return all required keys."""
    db_client.post("/pull-data")
    results = qd.query_all(db_transaction)
    for key in ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "extra_1", "extra_2"]:
        assert key in results, f"Key '{key}' missing from query_all() result"


@pytest.mark.integration
def test_additional_rows_incremental_pull(db_client, db_transaction):
    """A second pull with additional unique rows must add them."""
    from src import load_data as _ld

    extra_rows = [
        {
            "notes": "Carnegie Mellon | Computer Science | Fall 2026 | International | PhD | accepted",
            "program": "Computer Science",
            "decision": "Accepted",
            "gpa": "3.95",
            "decision_date": "January 20, 2026",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Carnegie Mellon",
        }
    ]

    db_client.post("/pull-data")  # inserts FAKE_ROWS
    count_after_first = _count_rows(db_transaction)

    # Load the extra rows directly (simulating a second pull with new data)
    _ld.load_rows(extra_rows, db_transaction)
    count_after_second = _count_rows(db_transaction)

    assert count_after_second == count_after_first + 1, (
        f"Expected {count_after_first + 1} rows after second load, got {count_after_second}"
    )
