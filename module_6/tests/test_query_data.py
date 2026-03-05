"""
test_query_data.py

Unit tests for src/worker/etl/query_data.py.
psycopg is fully mocked — no real database connections are made.
"""

from unittest.mock import MagicMock

import pytest

from query_data import (
    _MAX_QUERY_LIMIT,
    extra_question_1,
    extra_question_2,
    q1_fall_2026_count,
    q2_percent_international,
    q3_avg_scores,
    q4_avg_gpa_us_fall_2026,
    q5_percent_accept_fall_2026,
    q6_avg_gpa_accept_fall_2026,
    q7_jhu_ms_cs_count,
    q8_top_cs_phd_accepts,
    q9_llm_vs_raw_comparison,
    query_all,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mock_conn(fetchone=None, fetchall=None):
    """
    Return (mock_conn, mock_cur) where:
        mock_conn.cursor() is a context manager returning mock_cur
        mock_cur.fetchone() returns fetchone
        mock_cur.fetchall() returns fetchall
    """
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = fetchone
    mock_cur.fetchall.return_value = fetchall if fetchall is not None else []

    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=mock_cur)
    cur_cm.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cur_cm
    return mock_conn, mock_cur


# ---------------------------------------------------------------------------
# q1 — fall 2026 count
# ---------------------------------------------------------------------------

def test_q1_returns_count():
    conn, cur = _mock_conn(fetchone=(42,))
    result = q1_fall_2026_count(conn)
    assert result == 42
    cur.execute.assert_called_once()


# ---------------------------------------------------------------------------
# q2 — percent international
# ---------------------------------------------------------------------------

def test_q2_returns_percentage():
    conn, cur = _mock_conn(fetchone=(75.50,))
    result = q2_percent_international(conn)
    assert result == pytest.approx(75.50)
    cur.execute.assert_called_once()


def test_q2_returns_none_when_no_data():
    conn, cur = _mock_conn(fetchone=(None,))
    assert q2_percent_international(conn) is None


# ---------------------------------------------------------------------------
# q3 — average scores tuple
# ---------------------------------------------------------------------------

def test_q3_returns_tuple():
    expected = (3.50, 315.00, 160.00, 4.00)
    conn, cur = _mock_conn(fetchone=expected)
    result = q3_avg_scores(conn)
    assert result == expected


# ---------------------------------------------------------------------------
# q4 — avg GPA US fall 2026
# ---------------------------------------------------------------------------

def test_q4_returns_avg_gpa():
    conn, cur = _mock_conn(fetchone=(3.75,))
    assert q4_avg_gpa_us_fall_2026(conn) == pytest.approx(3.75)


# ---------------------------------------------------------------------------
# q5 — percent acceptance fall 2026
# ---------------------------------------------------------------------------

def test_q5_returns_acceptance_percent():
    conn, cur = _mock_conn(fetchone=(40.00,))
    assert q5_percent_accept_fall_2026(conn) == pytest.approx(40.00)


# ---------------------------------------------------------------------------
# q6 — avg GPA of accepted fall 2026
# ---------------------------------------------------------------------------

def test_q6_returns_accepted_avg_gpa():
    conn, cur = _mock_conn(fetchone=(3.80,))
    assert q6_avg_gpa_accept_fall_2026(conn) == pytest.approx(3.80)


# ---------------------------------------------------------------------------
# q7 — JHU MS CS count
# ---------------------------------------------------------------------------

def test_q7_returns_jhu_count():
    conn, cur = _mock_conn(fetchone=(5,))
    assert q7_jhu_ms_cs_count(conn) == 5


# ---------------------------------------------------------------------------
# q8 — top CS PhD acceptances
# ---------------------------------------------------------------------------

def test_q8_returns_top_phd_count():
    conn, cur = _mock_conn(fetchone=(10,))
    assert q8_top_cs_phd_accepts(conn) == 10


# ---------------------------------------------------------------------------
# q9 — LLM field comparison
# ---------------------------------------------------------------------------

def test_q9_returns_llm_count():
    conn, cur = _mock_conn(fetchone=(8,))
    assert q9_llm_vs_raw_comparison(conn) == 8


# ---------------------------------------------------------------------------
# extra_question_1 — limit clamping
# ---------------------------------------------------------------------------

def test_extra_question_1_default_limit():
    rows = [("PhD", 3.75), ("Masters", 3.50)]
    conn, cur = _mock_conn(fetchall=rows)
    result = extra_question_1(conn)
    assert result == rows
    # Default limit is 50 — check it was passed to execute
    passed_params = cur.execute.call_args[0][1]
    assert passed_params == (50,)


def test_extra_question_1_clamps_below_one():
    """limit=0 → clamped to 1."""
    conn, cur = _mock_conn(fetchall=[])
    extra_question_1(conn, limit=0)
    passed_params = cur.execute.call_args[0][1]
    assert passed_params == (1,)


def test_extra_question_1_clamps_above_max():
    """limit=999 → clamped to _MAX_QUERY_LIMIT (100)."""
    conn, cur = _mock_conn(fetchall=[])
    extra_question_1(conn, limit=999)
    passed_params = cur.execute.call_args[0][1]
    assert passed_params == (_MAX_QUERY_LIMIT,)


def test_extra_question_1_explicit_valid_limit():
    """A limit within range is used as-is."""
    conn, cur = _mock_conn(fetchall=[])
    extra_question_1(conn, limit=25)
    passed_params = cur.execute.call_args[0][1]
    assert passed_params == (25,)


# ---------------------------------------------------------------------------
# extra_question_2
# ---------------------------------------------------------------------------

def test_extra_question_2_returns_percentage():
    conn, cur = _mock_conn(fetchone=(35.00,))
    assert extra_question_2(conn) == pytest.approx(35.00)


# ---------------------------------------------------------------------------
# query_all — aggregate runner
# ---------------------------------------------------------------------------

def test_query_all_returns_all_expected_keys():
    """query_all must return a dict with all 11 expected keys."""
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = (0,)
    mock_cur.fetchall.return_value = []

    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=mock_cur)
    cur_cm.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cur_cm

    result = query_all(mock_conn)

    expected_keys = {
        "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "extra_1", "extra_2"
    }
    assert set(result.keys()) == expected_keys


def test_query_all_calls_all_query_functions():
    """query_all calls cursor.execute at least 11 times (once per query)."""
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = (0,)
    mock_cur.fetchall.return_value = []

    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=mock_cur)
    cur_cm.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cur_cm

    query_all(mock_conn)

    # 11 queries: q1-q9 (9) + extra_question_1 (1) + extra_question_2 (1)
    assert mock_cur.execute.call_count == 11
