"""
load_data.py

Module 6 DB initializer.

Responsibilities:
1) Create required tables:
   - applicants
   - ingestion_watermarks
   - analytics_cache
2) Load applicant rows from JSON into applicants.

Default input: module_6/src/data/applicant_data.json
Override input by env var DATA_PATH
"""

import json
import os
import re
from datetime import datetime

import psycopg
from psycopg import sql


# ===============================
# CONFIGURATION
# ===============================

_DEFAULT_INPUT_JSON = os.environ.get(
    "DATA_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "applicant_data.json"),
)

BASE_URL = "https://www.thegradcafe.com/survey/"


# ===============================
# TABLE DDL
# ===============================

CREATE_APPLICANTS_SQL = """
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

CREATE_INGESTION_WATERMARKS_SQL = """
CREATE TABLE IF NOT EXISTS ingestion_watermarks (
    source     TEXT PRIMARY KEY,
    last_seen  TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

CREATE_ANALYTICS_CACHE_SQL = """
CREATE TABLE IF NOT EXISTS analytics_cache (
    key        TEXT PRIMARY KEY,
    results    JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


# ===============================
# INSERT STATEMENT
# ===============================

_INSERT_SQL = sql.SQL("""
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
""")


# ===============================
# PARSING HELPERS
# ===============================

def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    if not value:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def extract_term(text):
    if not text:
        return None
    match = re.search(r"(Fall|Spring|Summer)\s+\d{4}", text, re.I)
    return match.group(0) if match else None


def extract_nationality(text):
    if not text:
        return None
    if re.search(r"\binternational\b", text, re.I):
        return "International"
    if re.search(r"\bamerican\b|\bus citizen\b", text, re.I):
        return "American"
    return None


def extract_degree(text):
    if not text:
        return None
    if re.search(r"\bphd\b", text, re.I):
        return "PhD"
    if re.search(r"\bmaster", text, re.I):
        return "Masters"
    return None


def extract_gre_parts(text):
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
    if not text:
        return []
    return [s.strip() for s in text.split("|") if s.strip()]


def extract_program_from_notes(text):
    parts = split_notes(text)
    return parts[1] if len(parts) >= 2 else None


def extract_status_from_notes(text):
    if not text:
        return None
    if re.search(r"\baccepted\b", text, re.I):
        return "Accepted"
    if re.search(r"\brejected\b", text, re.I):
        return "Rejected"
    if re.search(r"\bwait\s*listed\b|\bwaitlisted\b", text, re.I):
        return "Waitlisted"
    return None


def _build_row_params(row: dict) -> dict:
    notes = row.get("notes") or row.get("comments") or ""
    program = row.get("program") or extract_program_from_notes(notes)
    status = row.get("decision") or extract_status_from_notes(notes)
    term = extract_term(notes)
    nationality = extract_nationality(notes)
    degree = extract_degree(notes)
    gre, gre_v, gre_aw = extract_gre_parts(notes)
    gpa = parse_float(row.get("gpa"))
    date_added = parse_date(row.get("decision_date"))

    return {
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
    }


def load_rows(rows, conn):
    inserted = 0
    with conn.cursor() as cur:
        for row in rows:
            params = _build_row_params(row)
            cur.execute(_INSERT_SQL, params)
            if cur.rowcount:
                inserted += 1
    conn.commit()
    return inserted


def main(input_json=None, database_url=None):
    if input_json is None:
        input_json = _DEFAULT_INPUT_JSON

    if database_url is None:
        database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not set.")

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_APPLICANTS_SQL)
            cur.execute(CREATE_INGESTION_WATERMARKS_SQL)
            cur.execute(CREATE_ANALYTICS_CACHE_SQL)
        conn.commit()

        n = load_rows(data, conn)
        print(f"LOAD COMPLETE — {n} rows inserted", flush=True)


if __name__ == "__main__":
    main()
