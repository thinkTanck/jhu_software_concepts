"""
test_load_data.py

Unit tests for src/db/load_data.py.
psycopg is fully mocked — no real database connections are made.
"""

import json
import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import load_data
from load_data import (
    BASE_URL,
    _build_row_params,
    extract_degree,
    extract_gre_parts,
    extract_nationality,
    extract_program_from_notes,
    extract_status_from_notes,
    extract_term,
    load_rows,
    main,
    parse_date,
    parse_float,
    split_notes,
)

_DB_SRC = Path(__file__).resolve().parents[1] / "src" / "db"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _cur_conn_mock(rowcount=1):
    """Return (mock_conn, mock_cur) for functions that use `with conn.cursor() as cur:`."""
    mock_cur = MagicMock()
    mock_cur.rowcount = rowcount

    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=mock_cur)
    cur_cm.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cur_cm
    return mock_conn, mock_cur


def _psycopg_conn_mock(rowcount=0):
    """Full psycopg.connect mock: supports `with psycopg.connect(...) as conn:`."""
    mock_conn, mock_cur = _cur_conn_mock(rowcount=rowcount)
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cur


# ---------------------------------------------------------------------------
# parse_float
# ---------------------------------------------------------------------------

def test_parse_float_valid():
    assert parse_float("3.14") == pytest.approx(3.14)


def test_parse_float_integer_string():
    assert parse_float("42") == pytest.approx(42.0)


def test_parse_float_none_returns_none():
    assert parse_float(None) is None


def test_parse_float_invalid_str_returns_none():
    assert parse_float("not-a-number") is None


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------

def test_parse_date_long_month_format():
    """'%B %d, %Y' — e.g. 'March 04, 2026'."""
    result = parse_date("March 04, 2026")
    assert result is not None
    assert result.year == 2026


def test_parse_date_short_month_format():
    """'%b %d, %Y' — e.g. 'Mar 04, 2026'; first format fails → continue."""
    result = parse_date("Mar 04, 2026")
    assert result is not None


def test_parse_date_slash_format():
    """'%m/%d/%y' — first two formats fail, third matches."""
    result = parse_date("03/04/26")
    assert result is not None


def test_parse_date_none_returns_none():
    assert parse_date(None) is None


def test_parse_date_empty_returns_none():
    assert parse_date("") is None


def test_parse_date_unparseable_returns_none():
    """All three formats fail → return None."""
    assert parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# extract_term
# ---------------------------------------------------------------------------

def test_extract_term_found():
    assert extract_term("Applied for Fall 2026 term") == "Fall 2026"


def test_extract_term_spring():
    assert extract_term("Spring 2025 admission") == "Spring 2025"


def test_extract_term_not_found():
    assert extract_term("No term mentioned here") is None


def test_extract_term_none_input():
    assert extract_term(None) is None


# ---------------------------------------------------------------------------
# extract_nationality
# ---------------------------------------------------------------------------

def test_extract_nationality_international():
    assert extract_nationality("I am an international student") == "International"


def test_extract_nationality_american():
    assert extract_nationality("I am an american citizen") == "American"


def test_extract_nationality_us_citizen():
    assert extract_nationality("US citizen applying here") == "American"


def test_extract_nationality_not_found():
    assert extract_nationality("Some text without nationality info") is None


def test_extract_nationality_none_input():
    assert extract_nationality(None) is None


# ---------------------------------------------------------------------------
# extract_degree
# ---------------------------------------------------------------------------

def test_extract_degree_phd():
    assert extract_degree("Applying for a PhD program") == "PhD"


def test_extract_degree_masters():
    assert extract_degree("Looking at Masters programs") == "Masters"


def test_extract_degree_not_found():
    assert extract_degree("Some other program type") is None


def test_extract_degree_none_input():
    assert extract_degree(None) is None


# ---------------------------------------------------------------------------
# extract_gre_parts
# ---------------------------------------------------------------------------

def test_extract_gre_parts_all_found():
    text = "GRE 320, GRE V 165, GRE AW 4.5"
    gre, gre_v, gre_aw = extract_gre_parts(text)
    assert gre == pytest.approx(320.0)
    assert gre_v == pytest.approx(165.0)
    assert gre_aw == pytest.approx(4.5)


def test_extract_gre_parts_none_found():
    gre, gre_v, gre_aw = extract_gre_parts("No scores here")
    assert gre is None
    assert gre_v is None
    assert gre_aw is None


def test_extract_gre_parts_none_input():
    gre, gre_v, gre_aw = extract_gre_parts(None)
    assert gre is None
    assert gre_v is None
    assert gre_aw is None


# ---------------------------------------------------------------------------
# split_notes
# ---------------------------------------------------------------------------

def test_split_notes_with_pipe():
    assert split_notes("a | b | c") == ["a", "b", "c"]


def test_split_notes_empty():
    assert split_notes("") == []


def test_split_notes_none():
    assert split_notes(None) == []


# ---------------------------------------------------------------------------
# extract_program_from_notes
# ---------------------------------------------------------------------------

def test_extract_program_from_notes_with_two_plus_parts():
    result = extract_program_from_notes("University Name | Computer Science | PhD")
    assert result == "Computer Science"


def test_extract_program_from_notes_fewer_than_two_parts():
    assert extract_program_from_notes("only one part") is None


# ---------------------------------------------------------------------------
# extract_status_from_notes
# ---------------------------------------------------------------------------

def test_extract_status_accepted():
    assert extract_status_from_notes("Applicant was Accepted to the program") == "Accepted"


def test_extract_status_rejected():
    assert extract_status_from_notes("Unfortunately Rejected from program") == "Rejected"


def test_extract_status_waitlisted_space():
    assert extract_status_from_notes("Currently wait listed pending decision") == "Waitlisted"


def test_extract_status_waitlisted_no_space():
    assert extract_status_from_notes("Status: waitlisted for spring") == "Waitlisted"


def test_extract_status_not_found():
    assert extract_status_from_notes("Interview scheduled, no decision yet") is None


def test_extract_status_none_input():
    assert extract_status_from_notes(None) is None


# ---------------------------------------------------------------------------
# _build_row_params
# ---------------------------------------------------------------------------

def test_build_row_params_uses_notes_field():
    row = {
        "notes": "Johns Hopkins | Computer Science | PhD | American | Fall 2026",
        "gpa": "3.9",
        "decision": None,
        "decision_date": "March 04, 2026",
    }
    params = _build_row_params(row)
    assert params["url"] == BASE_URL
    assert params["gpa"] == pytest.approx(3.9)
    assert params["date_added"] is not None


def test_build_row_params_uses_comments_fallback():
    """When 'notes' absent, 'comments' field is used."""
    row = {
        "comments": "MIT | Computer Science | PhD | Accepted",
        "gpa": "4.0",
        "decision": "Accepted",
        "decision_date": None,
    }
    params = _build_row_params(row)
    assert params["status"] == "Accepted"


def test_build_row_params_explicit_program_wins():
    """Explicit 'program' key takes priority over extraction from notes."""
    row = {
        "notes": "",
        "program": "CS PhD",
        "gpa": None,
        "decision": None,
        "decision_date": None,
    }
    params = _build_row_params(row)
    assert params["program"] == "CS PhD"


def test_build_row_params_llm_fields_forwarded():
    """llm-generated-program and llm-generated-university are mapped."""
    row = {
        "notes": "",
        "gpa": None,
        "decision": None,
        "decision_date": None,
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "MIT",
    }
    params = _build_row_params(row)
    assert params["llm_generated_program"] == "Computer Science"
    assert params["llm_generated_university"] == "MIT"


# ---------------------------------------------------------------------------
# load_rows
# ---------------------------------------------------------------------------

def test_load_rows_increments_on_rowcount():
    conn, cur = _cur_conn_mock(rowcount=1)
    row = {"notes": "", "gpa": None, "decision": None, "decision_date": None}
    result = load_rows([row], conn)
    assert result == 1
    conn.commit.assert_called_once()


def test_load_rows_no_increment_when_rowcount_zero():
    conn, cur = _cur_conn_mock(rowcount=0)
    row = {"notes": "", "gpa": None, "decision": None, "decision_date": None}
    result = load_rows([row], conn)
    assert result == 0
    conn.commit.assert_called_once()


def test_load_rows_multiple_rows():
    conn, cur = _cur_conn_mock(rowcount=1)
    rows = [
        {"notes": "a", "gpa": "3.5", "decision": None, "decision_date": None},
        {"notes": "b", "gpa": "3.8", "decision": None, "decision_date": None},
    ]
    result = load_rows(rows, conn)
    assert result == 2


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def test_main_raises_when_database_url_empty():
    """database_url='' is falsy → RuntimeError (line 238 in load_data.py)."""
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        main(input_json="/fake/path.json", database_url="")


def test_main_reads_database_url_from_env(tmp_path):
    """database_url=None reads DATABASE_URL from the environment (line 235)."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps([]), encoding="utf-8")

    mock_conn, _ = _psycopg_conn_mock(rowcount=0)

    # DATABASE_URL is set by conftest; database_url=None → reads from env
    with patch("psycopg.connect", return_value=mock_conn):
        main(input_json=str(data_file), database_url=None)


def test_main_uses_default_input_json(tmp_path):
    """input_json=None uses _DEFAULT_INPUT_JSON (line 232)."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps([]), encoding="utf-8")

    mock_conn, _ = _psycopg_conn_mock(rowcount=0)

    with patch.object(load_data, "_DEFAULT_INPUT_JSON", str(data_file)), \
            patch("psycopg.connect", return_value=mock_conn):
        main(input_json=None, database_url="postgresql://fake/db")


def test_main_happy_path_inserts_rows(tmp_path):
    """main() creates tables, loads rows, prints summary."""
    row = {"notes": "Test | CS | PhD | Accepted", "gpa": "3.5",
           "decision": None, "decision_date": None}
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps([row]), encoding="utf-8")

    mock_conn, mock_cur = _psycopg_conn_mock(rowcount=1)

    with patch("psycopg.connect", return_value=mock_conn):
        main(input_json=str(data_file), database_url="postgresql://fake/db")

    # Three DDL statements + one INSERT
    assert mock_cur.execute.call_count >= 4


# ---------------------------------------------------------------------------
# if __name__ == "__main__" — covers the guard body line
# ---------------------------------------------------------------------------

def test_load_data_main_guard_covered(tmp_path, monkeypatch):
    """runpy executes load_data.py as __main__, covering the guard body line."""
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps([]), encoding="utf-8")

    # DATA_PATH → used by _DEFAULT_INPUT_JSON when module re-runs under runpy
    monkeypatch.setenv("DATA_PATH", str(data_file))

    mock_conn, _ = _psycopg_conn_mock(rowcount=0)

    with patch("psycopg.connect", return_value=mock_conn):
        runpy.run_path(str(_DB_SRC / "load_data.py"), run_name="__main__")
