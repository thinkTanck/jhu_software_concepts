"""
load_data.py

Loads cleaned and LLM-extended applicant data into the PostgreSQL
``applicants`` table.

Public API (used by app.py and tests)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
load_rows(rows, conn)
    Insert *rows* (list of dicts) into the database using the supplied
    psycopg connection.  The connection is **not** closed by this function.

    Idempotency: rows are upserted on the unique constraint
    ``(comments, date_added, url)`` so that re-running the loader with
    identical data produces no duplicates.

main()
    CLI entry point: reads the JSON file and calls load_rows.

Parsing helpers are module-level so they can be imported and unit-tested.
"""

import json
import os
import re
from datetime import datetime

import psycopg


# ===============================
# CONFIGURATION
# ===============================

# Input JSON file produced by Module 2 pipeline (used by CLI main only)
_DEFAULT_INPUT_JSON = os.path.join(
    os.path.dirname(__file__), "..", "module_2", "llm_extend_applicant_data.json"
)

BASE_URL = "https://www.thegradcafe.com/survey/"


# ===============================
# PARSING HELPERS
# ===============================

def parse_float(value):
    """
    Safely convert *value* to float.

    Returns:
        float or None.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    """
    Parse *value* string into a :class:`datetime.date`.

    Tries multiple common formats; returns ``None`` if none match.
    """
    if not value:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def extract_term(text):
    """
    Extract academic term (Fall/Spring/Summer + 4-digit year) from *text*.

    Returns:
        str like ``"Fall 2026"`` or ``None``.
    """
    if not text:
        return None
    match = re.search(r"(Fall|Spring|Summer)\s+\d{4}", text, re.I)
    return match.group(0) if match else None


def extract_nationality(text):
    """
    Infer nationality classification from free-text *text*.

    Returns:
        ``"International"``, ``"American"``, or ``None``.
    """
    if not text:
        return None
    if re.search(r"\binternational\b", text, re.I):
        return "International"
    if re.search(r"\bamerican\b|\bus citizen\b", text, re.I):
        return "American"
    return None


def extract_degree(text):
    """
    Infer degree type from *text*.

    Returns:
        ``"PhD"``, ``"Masters"``, or ``None``.
    """
    if not text:
        return None
    if re.search(r"\bphd\b", text, re.I):
        return "PhD"
    if re.search(r"\bmaster", text, re.I):
        return "Masters"
    return None


def extract_gre_parts(text):
    """
    Extract GRE total, verbal, and AW scores from *text*.

    Returns:
        Tuple ``(gre_total, gre_verbal, gre_aw)`` — each float or None.
    """
    gre = gre_v = gre_aw = None
    if not text:
        return gre, gre_v, gre_aw
    m_total = re.search(r"GRE\s+(\d{3})", text)
    m_v = re.search(r"GRE\s*V\s*(\d{2,3})", text)
    m_aw = re.search(r"GRE\s*AW\s*([\d.]+)", text)
    if m_total:
        gre = parse_float(m_total.group(1))
    if m_v:
        gre_v = parse_float(m_v.group(1))
    if m_aw:
        gre_aw = parse_float(m_aw.group(1))
    return gre, gre_v, gre_aw


def split_notes(text):
    """Split *text* on ``|`` and return non-empty, stripped segments."""
    if not text:
        return []
    return [s.strip() for s in text.split("|") if s.strip()]


def extract_university_from_notes(text):
    """Return the first ``|``-delimited segment of *text* (university name)."""
    parts = split_notes(text)
    return parts[0] if parts else None


def extract_program_from_notes(text):
    """Return the second ``|``-delimited segment of *text* (program name)."""
    parts = split_notes(text)
    return parts[1] if len(parts) >= 2 else None


def extract_status_from_notes(text):
    """
    Detect decision status keyword from *text*.

    Returns:
        ``"Accepted"``, ``"Rejected"``, ``"Waitlisted"``, or ``None``.
    """
    if not text:
        return None
    if re.search(r"\baccepted\b", text, re.I):
        return "Accepted"
    if re.search(r"\brejected\b", text, re.I):
        return "Rejected"
    if re.search(r"\bwait\s*listed\b|\bwaitlisted\b", text, re.I):
        return "Waitlisted"
    return None


# ===============================
# TABLE DDL (used by tests)
# ===============================

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applicants (
    id                       SERIAL PRIMARY KEY,
    program                  TEXT,
    comments                 TEXT,
    date_added               DATE,
    url                      TEXT,
    status                   TEXT,
    term                     TEXT,
    us_or_international      TEXT,
    gpa                      NUMERIC(4,2),
    gre                      NUMERIC(6,2),
    gre_v                    NUMERIC(6,2),
    gre_aw                   NUMERIC(4,2),
    degree                   TEXT,
    llm_generated_program    TEXT,
    llm_generated_university TEXT,
    UNIQUE (comments, date_added, url)
);
"""


# ===============================
# CORE LOAD FUNCTION
# ===============================

def load_rows(rows, conn):
    """
    Insert *rows* into the ``applicants`` table using *conn*.

    Each element of *rows* is a dict with the same keys produced by the
    Module 2 scraper / LLM pipeline.

    Idempotency is enforced via ``ON CONFLICT DO NOTHING`` on the unique
    constraint ``(comments, date_added, url)``.

    Args:
        rows (list[dict]): Raw applicant dicts from the scraper.
        conn: Active psycopg connection.  The caller is responsible for
              closing / committing it.

    Returns:
        int: Number of rows actually inserted (conflicts excluded).
    """
    inserted = 0
    with conn.cursor() as cur:
        for row in rows:
            notes = row.get("notes") or row.get("comments") or ""
            program = row.get("program") or extract_program_from_notes(notes)
            status = row.get("decision") or extract_status_from_notes(notes)
            term = extract_term(notes)
            nationality = extract_nationality(notes)
            degree = extract_degree(notes)
            gre, gre_v, gre_aw = extract_gre_parts(notes)
            gpa = parse_float(row.get("gpa"))
            date_added = parse_date(row.get("decision_date"))

            cur.execute(
                """
                INSERT INTO applicants (
                    program, comments, date_added, url,
                    status, term, us_or_international,
                    gpa, gre, gre_v, gre_aw, degree,
                    llm_generated_program, llm_generated_university
                )
                VALUES (
                    %(program)s, %(comments)s, %(date_added)s, %(url)s,
                    %(status)s, %(term)s, %(us_or_international)s,
                    %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s, %(degree)s,
                    %(llm_generated_program)s, %(llm_generated_university)s
                )
                ON CONFLICT (comments, date_added, url) DO NOTHING
                """,
                {
                    "program": program,
                    "comments": notes,
                    "date_added": date_added,
                    "url": BASE_URL,
                    "status": status,
                    "term": term,
                    "us_or_international": nationality,
                    "gpa": gpa,
                    "gre": gre,
                    "gre_v": gre_v,
                    "gre_aw": gre_aw,
                    "degree": degree,
                    "llm_generated_program": row.get("llm-generated-program"),
                    "llm_generated_university": row.get("llm-generated-university"),
                },
            )
            if cur.rowcount:
                inserted += 1
    conn.commit()
    return inserted


# ===============================
# CLI ENTRY POINT
# ===============================

def main(input_json=None, database_url=None):
    """
    CLI entry point.  Reads a JSON file and loads it into the database.

    Args:
        input_json (str|None): Path to the JSON file.  Defaults to the
            Module 2 output file relative to this script.
        database_url (str|None): libpq connection string.  Defaults to
            the ``DATABASE_URL`` environment variable.
    """
    if input_json is None:
        input_json = _DEFAULT_INPUT_JSON
    if database_url is None:
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:59061076@localhost:5432/gradcafe_module3",
        )

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = psycopg.connect(database_url)
    try:
        n = load_rows(data, conn)
        print(f"LOAD COMPLETE — {n} rows inserted")
    finally:
        conn.close()


if __name__ == "__main__":  # pragma: no cover
    main()
