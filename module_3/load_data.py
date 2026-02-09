import json
import re
from datetime import datetime
import psycopg2

# ===============================
# CONFIG
# ===============================
DB_NAME = "gradcafe_module3"
DB_USER = "postgres"
DB_PASSWORD = "59061076"
DB_HOST = "localhost"
DB_PORT = "5432"

# JSON file (relative to module_3)
INPUT_JSON = "module_2/llm_extend_applicant_data.json"

BASE_URL = "https://www.thegradcafe.com/survey/"

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
    m = re.search(r"(Fall|Spring|Summer)\s+\d{4}", text, re.I)
    return m.group(0) if m else None


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
    if not text:
        return []
    return [p.strip() for p in text.split("|") if p.strip()]


def extract_university_from_notes(text):
    parts = split_notes(text)
    return parts[0] if len(parts) >= 1 else None


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


# ===============================
# MAIN LOAD
# ===============================

def main():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    inserted = 0

    for row in data:
        notes = row.get("notes") or row.get("comments") or ""

        # ----- program -----
        program = row.get("program")
        if not program:
            program = extract_program_from_notes(notes)

        # ----- university -----
        university = row.get("school")
        if not university:
            university = extract_university_from_notes(notes)

        # ----- status -----
        status = row.get("decision")
        if not status:
            status = extract_status_from_notes(notes)

        # ----- other derived fields -----
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
        if inserted % 1000 == 0:
            conn.commit()
            print(f"Inserted {inserted} rows...")

    conn.commit()
    cur.close()
    conn.close()

    print(f"LOAD COMPLETE — {inserted} rows inserted")


if __name__ == "__main__":
    main()
