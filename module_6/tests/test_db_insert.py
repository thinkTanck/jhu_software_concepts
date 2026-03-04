"""
test_db_insert.py

Database write, schema, and idempotency tests, plus unit tests for the
load_data parsing helper functions.

Verifies:
- Before pull: target table is empty (in the isolated transaction)
- After POST pull: new rows exist and required non-null fields are present
- Idempotency: duplicate rows do not create duplicates
- query_all() returns a dict with the expected keys used by the template
- All parsing helpers handle edge cases correctly

All tests are marked ``db``.
"""

import pytest
import psycopg

from src import load_data as ld
from src import query_data as qd
from tests.conftest import FAKE_ROWS, DATABASE_URL


# ---------------------------------------------------------------------------
# Required schema fields (non-null)
# ---------------------------------------------------------------------------

REQUIRED_NON_NULL_FIELDS = ["comments", "url"]

# Keys that query_all must return
REQUIRED_QUERY_KEYS = [
    "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9",
    "extra_1", "extra_2",
]


# ---------------------------------------------------------------------------
# D) Database Writes
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_table_empty_before_insert(db_transaction):
    """Applicants table must be empty before the test inserts anything."""
    with db_transaction.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applicants")
        count = cur.fetchone()[0]
    assert count == 0, f"Expected 0 rows before insert, found {count}"


@pytest.mark.db
def test_load_rows_inserts_new_rows(db_transaction):
    """load_rows must insert the fake rows into the DB."""
    n = ld.load_rows(FAKE_ROWS, db_transaction)
    assert n == len(FAKE_ROWS), f"Expected {len(FAKE_ROWS)} inserts, got {n}"

    with db_transaction.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applicants")
        count = cur.fetchone()[0]
    assert count == len(FAKE_ROWS)


@pytest.mark.db
def test_required_fields_not_null(db_transaction):
    """Required non-null fields (comments, url) must be populated after insert."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    with db_transaction.cursor() as cur:
        for field in REQUIRED_NON_NULL_FIELDS:
            cur.execute(f"SELECT COUNT(*) FROM applicants WHERE {field} IS NULL")
            null_count = cur.fetchone()[0]
            assert null_count == 0, (
                f"Field '{field}' is NULL in {null_count} rows after insert"
            )


@pytest.mark.db
def test_status_field_populated(db_transaction):
    """The 'status' field must be non-null and meaningful for inserted rows."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    with db_transaction.cursor() as cur:
        cur.execute("SELECT DISTINCT status FROM applicants WHERE status IS NOT NULL")
        statuses = {row[0] for row in cur.fetchall()}
    assert len(statuses) > 0, "No non-null status values found"


@pytest.mark.db
def test_idempotency_no_duplicates(db_transaction):
    """Inserting the same rows twice must not create duplicates."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    ld.load_rows(FAKE_ROWS, db_transaction)

    with db_transaction.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applicants")
        count = cur.fetchone()[0]
    assert count == len(FAKE_ROWS), (
        f"Idempotency failed: expected {len(FAKE_ROWS)} rows, found {count}"
    )


@pytest.mark.db
def test_second_load_returns_zero_inserted(db_transaction):
    """The second load_rows call must report 0 newly inserted rows."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    n2 = ld.load_rows(FAKE_ROWS, db_transaction)
    assert n2 == 0, f"Expected 0 new inserts on second load, got {n2}"


@pytest.mark.db
def test_query_all_returns_dict(db_transaction):
    """query_all() must return a dict."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    results = qd.query_all(db_transaction)
    assert isinstance(results, dict)


@pytest.mark.db
def test_query_all_has_required_keys(db_transaction):
    """query_all() dict must contain all required keys."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    results = qd.query_all(db_transaction)
    for key in REQUIRED_QUERY_KEYS:
        assert key in results, f"Missing key '{key}' in query_all() result"


@pytest.mark.db
def test_query_q1_is_integer(db_transaction):
    """q1 (Fall 2026 count) must be an integer."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    results = qd.query_all(db_transaction)
    assert isinstance(results["q1"], int)


@pytest.mark.db
def test_query_q3_is_tuple(db_transaction):
    """q3 (avg scores) must be a 4-element tuple."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    results = qd.query_all(db_transaction)
    assert isinstance(results["q3"], tuple)
    assert len(results["q3"]) == 4


@pytest.mark.db
def test_query_extra_1_is_list(db_transaction):
    """extra_1 (avg GPA by degree) must be a list."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    results = qd.query_all(db_transaction)
    assert isinstance(results["extra_1"], list)


@pytest.mark.db
def test_new_rows_appear_after_load(db_transaction):
    """After loading FAKE_ROWS, DB row count must match len(FAKE_ROWS)."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    with db_transaction.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applicants")
        count = cur.fetchone()[0]
    assert count == len(FAKE_ROWS)


@pytest.mark.db
def test_load_rows_with_partial_data(db_transaction):
    """load_rows must handle rows with missing optional fields gracefully."""
    sparse_rows = [
        {
            "notes": "Some university | Some program | Fall 2026",
            "program": None,
            "decision": None,
            "gpa": None,
            "decision_date": None,
            "llm-generated-program": None,
            "llm-generated-university": None,
        }
    ]
    n = ld.load_rows(sparse_rows, db_transaction)
    assert n == 1


@pytest.mark.db
def test_url_field_set_to_base_url(db_transaction):
    """The url field must be set to the BASE_URL constant."""
    ld.load_rows(FAKE_ROWS, db_transaction)
    with db_transaction.cursor() as cur:
        cur.execute("SELECT DISTINCT url FROM applicants")
        urls = {row[0] for row in cur.fetchall()}
    assert ld.BASE_URL in urls


# ---------------------------------------------------------------------------
# Parsing helper unit tests (covers uncovered branches in load_data.py)
# ---------------------------------------------------------------------------

@pytest.mark.db
def test_parse_float_valid():
    """parse_float returns a float for valid numeric strings."""
    assert ld.parse_float("3.8") == 3.8
    assert ld.parse_float(3) == 3.0


@pytest.mark.db
def test_parse_float_invalid():
    """parse_float returns None for invalid / None input."""
    assert ld.parse_float(None) is None
    assert ld.parse_float("not-a-number") is None


@pytest.mark.db
def test_parse_date_abbreviated_month():
    """parse_date handles abbreviated month format like 'Jan 15, 2026'."""
    from datetime import date
    result = ld.parse_date("Jan 15, 2026")
    assert result == date(2026, 1, 15)


@pytest.mark.db
def test_parse_date_slash_format():
    """parse_date handles mm/dd/yy format."""
    from datetime import date
    result = ld.parse_date("01/15/26")
    assert result == date(2026, 1, 15)


@pytest.mark.db
def test_parse_date_unrecognized():
    """parse_date returns None for unrecognized format."""
    assert ld.parse_date("not a date") is None


@pytest.mark.db
def test_parse_date_empty():
    """parse_date returns None for empty/None input."""
    assert ld.parse_date(None) is None
    assert ld.parse_date("") is None


@pytest.mark.db
def test_extract_term_no_match():
    """extract_term returns None when no term pattern exists."""
    assert ld.extract_term("no term here") is None


@pytest.mark.db
def test_extract_term_empty():
    """extract_term returns None for empty/None input."""
    assert ld.extract_term(None) is None
    assert ld.extract_term("") is None


@pytest.mark.db
def test_extract_nationality_empty():
    """extract_nationality returns None for empty/None input."""
    assert ld.extract_nationality(None) is None
    assert ld.extract_nationality("") is None


@pytest.mark.db
def test_extract_nationality_american():
    """extract_nationality detects 'american' keyword."""
    assert ld.extract_nationality("I am an american applicant") == "American"


@pytest.mark.db
def test_extract_nationality_us_citizen():
    """extract_nationality detects 'us citizen' keyword."""
    assert ld.extract_nationality("US citizen applying") == "American"


@pytest.mark.db
def test_extract_nationality_no_match():
    """extract_nationality returns None when no keyword matches."""
    assert ld.extract_nationality("domestic applicant") is None


@pytest.mark.db
def test_extract_degree_empty():
    """extract_degree returns None for empty/None input."""
    assert ld.extract_degree(None) is None
    assert ld.extract_degree("") is None


@pytest.mark.db
def test_extract_degree_masters():
    """extract_degree detects 'masters' keyword."""
    assert ld.extract_degree("Masters in CS") == "Masters"


@pytest.mark.db
def test_extract_degree_no_match():
    """extract_degree returns None when no keyword matches."""
    assert ld.extract_degree("Bachelor's applicant") is None


@pytest.mark.db
def test_extract_gre_parts_empty():
    """extract_gre_parts returns all None for empty/None input."""
    assert ld.extract_gre_parts(None) == (None, None, None)
    assert ld.extract_gre_parts("") == (None, None, None)


@pytest.mark.db
def test_extract_gre_parts_with_all_scores():
    """extract_gre_parts extracts GRE total, V, and AW."""
    gre, gre_v, gre_aw = ld.extract_gre_parts("GRE 320 GRE V 160 GRE AW 4.5")
    assert gre == 320.0
    assert gre_v == 160.0
    assert gre_aw == 4.5


@pytest.mark.db
def test_extract_gre_parts_no_scores():
    """extract_gre_parts returns all None when no scores present."""
    assert ld.extract_gre_parts("no scores here") == (None, None, None)


@pytest.mark.db
def test_split_notes_empty():
    """split_notes returns [] for empty/None input."""
    assert ld.split_notes(None) == []
    assert ld.split_notes("") == []


@pytest.mark.db
def test_extract_university_from_notes_empty():
    """extract_university_from_notes returns None for text without pipes."""
    assert ld.extract_university_from_notes(None) is None
    assert ld.extract_university_from_notes("") is None
    assert ld.extract_university_from_notes("nopipes") == "nopipes"


@pytest.mark.db
def test_extract_program_from_notes_single_segment():
    """extract_program_from_notes returns None with only one segment."""
    assert ld.extract_program_from_notes("OnlyOneSegment") is None


@pytest.mark.db
def test_extract_status_from_notes_empty():
    """extract_status_from_notes returns None for empty/None input."""
    assert ld.extract_status_from_notes(None) is None
    assert ld.extract_status_from_notes("") is None


@pytest.mark.db
def test_extract_status_from_notes_waitlisted():
    """extract_status_from_notes detects 'waitlisted' keyword."""
    assert ld.extract_status_from_notes("I was waitlisted") == "Waitlisted"
    assert ld.extract_status_from_notes("wait listed for the program") == "Waitlisted"


@pytest.mark.db
def test_extract_status_from_notes_no_match():
    """extract_status_from_notes returns None when no keyword matches."""
    assert ld.extract_status_from_notes("pending review") is None


@pytest.mark.db
def test_extract_status_from_notes_accepted():
    """extract_status_from_notes detects 'accepted' keyword."""
    assert ld.extract_status_from_notes("I was accepted to the program") == "Accepted"


@pytest.mark.db
def test_extract_status_from_notes_rejected():
    """extract_status_from_notes detects 'rejected' keyword."""
    assert ld.extract_status_from_notes("Application rejected by committee") == "Rejected"


@pytest.mark.db
def test_load_rows_uses_extract_status_from_notes(db_transaction):
    """load_rows uses extract_status_from_notes when decision field is absent."""
    rows_no_decision = [
        {
            "notes": "TestU | CS | Fall 2026 | American | Masters | accepted",
            "program": "CS",
            "decision": None,
            "gpa": "3.6",
            "decision_date": None,
            "llm-generated-program": None,
            "llm-generated-university": None,
        },
        {
            "notes": "TestU | CS | Fall 2026 | American | Masters | rejected from program",
            "program": "CS",
            "decision": "",
            "gpa": "3.5",
            "decision_date": None,
            "llm-generated-program": None,
            "llm-generated-university": None,
        },
    ]
    n = ld.load_rows(rows_no_decision, db_transaction)
    assert n == 2
    with db_transaction.cursor() as cur:
        cur.execute("SELECT status FROM applicants ORDER BY id")
        statuses = [row[0] for row in cur.fetchall()]
    assert "Accepted" in statuses
    assert "Rejected" in statuses


@pytest.mark.db
def test_load_data_main_cli(tmp_path, monkeypatch):
    """load_data.main() CLI function loads rows from a JSON file."""
    import json
    # Write a minimal JSON input file
    test_rows = [
        {
            "notes": "Test U | TestProg | Fall 2026 | American | Masters | accepted",
            "program": "TestProg",
            "decision": "Accepted",
            "gpa": "3.7",
            "decision_date": "January 01, 2026",
            "llm-generated-program": "TestProg",
            "llm-generated-university": "Test U",
        }
    ]
    json_file = tmp_path / "test_input.json"
    json_file.write_text(json.dumps(test_rows))

    # Override DATABASE_URL to use test schema
    test_db_url = DATABASE_URL + "?options=-csearch_path%3Dtest_module4"
    monkeypatch.setenv("DATABASE_URL", test_db_url)

    # Truncate before test
    import psycopg as _psycopg
    conn = _psycopg.connect(DATABASE_URL)
    conn.execute("TRUNCATE test_module4.applicants RESTART IDENTITY")
    conn.commit()
    conn.close()

    ld.main(input_json=str(json_file), database_url=test_db_url)

    # Verify row was inserted
    conn = _psycopg.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM test_module4.applicants")
        count = cur.fetchone()[0]
    conn.close()
    assert count == 1


@pytest.mark.db
def test_load_data_main_uses_env_url(tmp_path, monkeypatch):
    """main() uses DATABASE_URL env var when database_url arg is None."""
    import json
    test_rows = [
        {
            "notes": "EnvU | EnvProg | Fall 2026 | American | Masters | accepted",
            "program": "EnvProg",
            "decision": "Accepted",
            "gpa": "3.5",
            "decision_date": None,
            "llm-generated-program": None,
            "llm-generated-university": None,
        }
    ]
    json_file = tmp_path / "env_test.json"
    json_file.write_text(json.dumps(test_rows))

    test_db_url = DATABASE_URL + "?options=-csearch_path%3Dtest_module4"
    monkeypatch.setenv("DATABASE_URL", test_db_url)

    import psycopg as _psycopg
    conn = _psycopg.connect(DATABASE_URL)
    conn.execute("TRUNCATE test_module4.applicants RESTART IDENTITY")
    conn.commit()
    conn.close()

    # Call main with database_url=None so it reads from env
    ld.main(input_json=str(json_file), database_url=None)

    conn = _psycopg.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM test_module4.applicants")
        count = cur.fetchone()[0]
    conn.close()
    assert count == 1


@pytest.mark.db
def test_load_data_main_default_input_json(tmp_path, monkeypatch):
    """main() uses _DEFAULT_INPUT_JSON when input_json arg is None."""
    import json
    import src.load_data as _ld_mod

    test_rows = [
        {
            "notes": "DefaultU | DefProg | Fall 2026 | International | PhD | accepted",
            "program": "DefProg",
            "decision": "Accepted",
            "gpa": "3.9",
            "decision_date": None,
            "llm-generated-program": None,
            "llm-generated-university": None,
        }
    ]
    json_file = tmp_path / "default_input.json"
    json_file.write_text(json.dumps(test_rows))

    # Patch _DEFAULT_INPUT_JSON to point to our test file
    monkeypatch.setattr(_ld_mod, "_DEFAULT_INPUT_JSON", str(json_file))

    test_db_url = DATABASE_URL + "?options=-csearch_path%3Dtest_module4"

    import psycopg as _psycopg
    conn = _psycopg.connect(DATABASE_URL)
    conn.execute("TRUNCATE test_module4.applicants RESTART IDENTITY")
    conn.commit()
    conn.close()

    # Call main with input_json=None — must read from _DEFAULT_INPUT_JSON
    _ld_mod.main(input_json=None, database_url=test_db_url)

    conn = _psycopg.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM test_module4.applicants")
        count = cur.fetchone()[0]
    conn.close()
    assert count == 1
