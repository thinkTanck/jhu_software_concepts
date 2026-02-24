"""
conftest.py

Shared pytest fixtures for the Module 4 test suite.

Database isolation strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests that touch the database use a SEPARATE schema (``test_module4``) with
its own ``applicants`` table.  This keeps the real production data untouched.

The test schema is created once per session (``_schema_setup`` fixture).
Each test gets a fresh connection via ``db_transaction``; after the test
the table is TRUNCATED to ensure isolation for the next test.

This approach is robust against load_rows' internal commit calls.

Dependency-injection strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The Flask app accepts ``SCRAPER_FN``, ``LOADER_FN``, and ``QUERY_FN``
config keys.  Tests supply fake callables instead of hitting the network
or the real loader.  ``QUERY_FN`` may be a 0-arg callable (skips DB
connection) or a 1-arg callable that receives the psycopg conn.
"""

import os
import pytest
import psycopg

from src.app import create_app


# ---------------------------------------------------------------------------
# Helpers / fake data
# ---------------------------------------------------------------------------

FAKE_ROWS = [
    {
        "notes": "Johns Hopkins University | Computer Science | Fall 2026 | American | Masters | accepted | GPA 3.8",
        "program": "Computer Science",
        "decision": "Accepted",
        "gpa": "3.8",
        "decision_date": "January 15, 2026",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Johns Hopkins University",
    },
    {
        "notes": "MIT | Computer Science | Fall 2026 | International | PhD | accepted | GPA 3.9",
        "program": "Computer Science",
        "decision": "Accepted",
        "gpa": "3.9",
        "decision_date": "February 01, 2026",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "MIT",
    },
    {
        "notes": "Stanford | Computer Science | Fall 2026 | American | PhD | rejected | GPA 3.5",
        "program": "Computer Science",
        "decision": "Rejected",
        "gpa": "3.5",
        "decision_date": "March 10, 2026",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Stanford",
    },
]

# Test schema name — isolates from the real 'applicants' table
TEST_SCHEMA = "test_module4"

# DDL for the test schema applicants table (with UNIQUE constraint for idempotency)
CREATE_TEST_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TEST_SCHEMA}.applicants (
    id                       SERIAL PRIMARY KEY,
    program                  TEXT,
    comments                 TEXT,
    date_added               DATE,
    url                      TEXT,
    status                   TEXT,
    term                     TEXT,
    us_or_international      TEXT,
    gpa                      NUMERIC(10,2),
    gre                      NUMERIC(10,2),
    gre_v                    NUMERIC(10,2),
    gre_aw                   NUMERIC(10,2),
    degree                   TEXT,
    llm_generated_program    TEXT,
    llm_generated_university TEXT,
    UNIQUE (comments, date_added, url)
);
"""


def _fake_query_fn():
    """Return a minimal results dict without hitting the real DB."""
    return {
        "q1": 42,
        "q2": 39.28,
        "q3": (3.75, 320.00, 160.00, 4.50),
        "q4": 3.80,
        "q5": 55.00,
        "q6": 3.85,
        "q7": 5,
        "q8": 3,
        "q9": 2,
        "extra_1": [("Masters", 3.75), ("PhD", 3.85)],
        "extra_2": 39.28,
    }


# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Export it before running the test suite, e.g.:\n"
        "  export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres"
    )


# ---------------------------------------------------------------------------
# Schema setup fixture (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _schema_setup():
    """
    Create the test schema and table once per session.
    Drop them at session end.
    """
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}")
    conn.execute(CREATE_TEST_TABLE_SQL)
    yield
    conn.execute(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE")
    conn.close()


# ---------------------------------------------------------------------------
# Per-test DB fixture (fresh connection + truncate for isolation)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_transaction():
    """
    Provide a fresh psycopg connection with search_path set to the test schema.

    The ``applicants`` table is TRUNCATED before each test (clean slate).
    The connection is closed after the test.

    This approach works correctly even when ``load_rows`` issues its own
    ``conn.commit()`` calls.
    """
    conn = psycopg.connect(DATABASE_URL)
    conn.execute(f"SET search_path TO {TEST_SCHEMA}")
    conn.execute(f"TRUNCATE {TEST_SCHEMA}.applicants RESTART IDENTITY")
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Flask app fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    """Flask app with fake QUERY_FN (no real DB queries on GET /analysis)."""
    return create_app({
        "TESTING": True,
        "DATABASE_URL": DATABASE_URL,
        "QUERY_FN": _fake_query_fn,
    })


@pytest.fixture()
def client(app):
    """Test client for the default app fixture."""
    return app.test_client()


@pytest.fixture()
def db_app(db_transaction):
    """
    Flask app wired to the real test schema.

    SCRAPER_FN returns FAKE_ROWS; LOADER_FN and QUERY_FN operate on
    the test schema connection (db_transaction).
    """
    from src import load_data as _ld
    from src import query_data as _qd

    _conn = db_transaction  # capture for closures

    def _fake_scraper():
        return FAKE_ROWS

    def _real_loader(rows, conn):
        # Ignore app's conn; use the test schema connection
        _ld.load_rows(rows, _conn)

    def _real_query(conn):
        # Ignore app's conn; use the test schema connection
        return _qd.query_all(_conn)

    cfg = {
        "TESTING": True,
        "DATABASE_URL": DATABASE_URL,
        "SCRAPER_FN": _fake_scraper,
        "LOADER_FN": _real_loader,
        "QUERY_FN": _real_query,
    }
    return create_app(cfg)


@pytest.fixture()
def db_client(db_app):
    """Test client wired to the real test schema."""
    return db_app.test_client()
