"""
load_data.py

Loads cleaned and LLM-extended applicant data from a JSON file
into the PostgreSQL database table `applicants`.

This script:
- Parses semi-structured note fields
- Normalizes derived attributes (term, nationality, degree, GRE, etc.)
- Inserts records into the database
- Commits periodically for performance stability

Designed for use in Module 3 of the course project.
"""

import json
import re
from datetime import datetime
import psycopg2


# ===============================
# CONFIGURATION
# ===============================

DB_NAME = "gradcafe_module3"
DB_USER = "postgres"
DB_PASSWORD = "59061076"
DB_HOST = "localhost"
DB_PORT = "5432"

# Input JSON file produced by Module 2 pipeline
INPUT_JSON = "module_2/llm_extend_applicant_data.json"

BASE_URL = "https://www.thegradcafe.com/survey/"


# ===============================
# PARSING HELPERS
# ===============================

def parse_float(value):
    """
    Safely convert a value to float.

    Returns:
        float value or None if conversion fails.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    """
    Parse a string into a Python date object using
    multiple possible formats.

    Returns:
        datetime.date object or None if parsing fails.
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
    Extract academic term (Fall, Spring, Summer + year)
    from free-text notes.
    """
    if not text:
        return None

    match = re.search(r"(Fall|Spring|Summer)\s+\d{4}", text, re.I)
    return match.group(0) if match else None


def extract_nationality(text):
    """
    Identify applicant nationality classification
    based on keyword matching in notes.
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
    Identify degree type (PhD or Masters)
    from note content.
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
    Extract GRE total, verbal, and analytical writing scores
    from note text using regular expressions.

    Returns:
        Tuple (gre_total, gre_verbal, gre_aw)
    """
    gre = gre_v = gre_aw = None

    if not text:
        return gre, gre_v, gre_aw

    m_total = re.search(r"GRE\s+(\d{3})", text)
    m_v = re.search(r"GRE\s*V\s*(\d{2,3})", text)
    m_aw = re.search(r"GRE\s*AW\s*([\d\.]+)", text)

    if m_total:
        gre = parse_float(m_total.group(1))

    if m_v:
        gre_v = parse_float(m_v.group(1))

    if m_aw:
        gre_aw = parse_float(m_aw.group(1))

    return gre, gre_v, gre_aw


# ===============================
# NOTES NORMALIZATION
# ===============================

def split_notes(text):
    """
    Split note field using '|' delimiter
    and return cleaned segments.
    """
    if not text:
        return []

    return [segment.strip() for segment in text.split("|") if segment.strip()]


def extract_university_from_notes(text):
    """
    Extract university name from first segment of notes.
    """
    parts = split_notes(text)
    return parts[0] if len(parts) >= 1 else None


def extract_program_from_notes(text):
    """
    Extract program name from second segment of notes.
    """
    parts = split_notes(text)
    return parts[1] if len(parts) >= 2 else None


def extract_status_from_notes(text):
    """
    Determine decision status (Accepted, Rejected, Waitlisted)
    using keyword matching.
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
# MAIN LOAD FUNCTION
# ===============================

def main():
    """
    Connect to PostgreSQL, load JSON applicant data,
    normalize fields, and insert records into the
    applicants table.

    Commits every 1000 rows to reduce transaction size.
    """

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

    cur = conn.cursor()

    # Load JSON data produced by Module 2 pipeline
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    inserted = 0

    for row in data:
        # Prefer notes field; fallback to comments
        notes = row.get("notes") or row.get("comments") or ""

        # Program field (prefer structured, fallback to notes)
        program = row.get("program") or extract_program_from_notes(notes)

        # University field (prefer structured, fallback to notes)
        university = row.get("school") or extract_university_from_notes(notes)

        # Decision status (prefer structured, fallback to notes)
        status = row.get("decision") or extract_status_from_notes(notes)

        # Derived structured fields
        term = extract_term(notes)
        nationality = extract_nationality(notes)
        degree = extract_degree(notes)

        gre, gre_v, gre_aw = extract_gre_parts(notes)
        gpa = parse_float(row.get("gpa"))
        date_added = parse_date(row.get("decision_date"))

        cur.execute(
            """
            INSERT INTO applicants (
                program,
                comments,
                date_added,
                url,
                status,
                term,
                us_or_international,
                gpa,
                gre,
                gre_v,
                gre_aw,
                degree,
                llm_generated_program,
                llm_generated_university
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                program,
                notes,
                date_added,
                BASE_URL,
                status,
                term,
                nationality,
                gpa,
                gre,
                gre_v,
                gre_aw,
                degree,
                row.get("llm-generated-program"),
                row.get("llm-generated-university"),
            )
        )

        inserted += 1

        # Commit in batches to improve performance
        if inserted % 1000 == 0:
            conn.commit()
            print(f"Inserted {inserted} rows...")

    # Final commit after loop
    conn.commit()

    cur.close()
    conn.close()

    print(f"LOAD COMPLETE — {inserted} rows inserted")


if __name__ == "__main__":
    main()
