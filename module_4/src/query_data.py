"""
query_data.py

SQL query functions for the GradCafe analysis application.

Each individual function accepts an active psycopg connection and
returns a scalar value, tuple, or list of tuples.

``query_all(conn)`` is the primary entry point used by app.py — it calls
every query function and returns a dict whose keys are consumed by the
analysis.html template.

The dict always contains these keys:

    q1, q2, q3, q4, q5, q6, q7, q8, q9, extra_1, extra_2

This module is designed to be completely DB-agnostic: callers supply
the connection object, making it straightforward to inject test doubles.
"""


# ---------------------------------------------------------------------------
# Individual query functions
# ---------------------------------------------------------------------------

def q1_fall_2026_count(conn):
    """
    Return the total number of applicants for the Fall 2026 term.

    Args:
        conn: Active psycopg connection.

    Returns:
        int: Count of Fall 2026 applicants.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026';"
        )
        return cur.fetchone()[0]


def q2_percent_international(conn):
    """
    Calculate the percentage of applicants classified as International.

    Only rows with a non-null ``us_or_international`` value are included
    in the denominator.

    Args:
        conn: Active psycopg connection.

    Returns:
        Decimal | None: Percentage rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(
                    CASE WHEN us_or_international = 'International'
                         THEN 1 ELSE 0 END
                ) / NULLIF(COUNT(*), 0), 2
            )
            FROM applicants
            WHERE us_or_international IS NOT NULL;
        """)
        return cur.fetchone()[0]


def q3_avg_scores(conn):
    """
    Compute average GPA and GRE scores for all applicants.

    Args:
        conn: Active psycopg connection.

    Returns:
        tuple: ``(avg_gpa, avg_gre_total, avg_gre_verbal, avg_gre_aw)``
               each rounded to two decimal places (may be None if no data).
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                ROUND(AVG(gpa)::numeric, 2),
                ROUND(AVG(gre)::numeric, 2),
                ROUND(AVG(gre_v)::numeric, 2),
                ROUND(AVG(gre_aw)::numeric, 2)
            FROM applicants;
        """)
        return cur.fetchone()


def q4_avg_gpa_us_fall_2026(conn):
    """
    Average GPA of American applicants for Fall 2026.

    Args:
        conn: Active psycopg connection.

    Returns:
        Decimal | None: Average GPA rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(AVG(gpa)::numeric, 2)
            FROM applicants
            WHERE term = 'Fall 2026'
              AND us_or_international = 'American';
        """)
        return cur.fetchone()[0]


def q5_percent_accept_fall_2026(conn):
    """
    Percentage of Fall 2026 applicants who were accepted.

    Args:
        conn: Active psycopg connection.

    Returns:
        Decimal | None: Percentage rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(
                    CASE WHEN status ILIKE 'accepted%'
                         THEN 1 ELSE 0 END
                ) / NULLIF(COUNT(*), 0), 2
            )
            FROM applicants
            WHERE term = 'Fall 2026';
        """)
        return cur.fetchone()[0]


def q6_avg_gpa_accept_fall_2026(conn):
    """
    Average GPA of accepted Fall 2026 applicants.

    Args:
        conn: Active psycopg connection.

    Returns:
        Decimal | None: Average GPA rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(AVG(gpa)::numeric, 2)
            FROM applicants
            WHERE term = 'Fall 2026'
              AND status ILIKE 'accepted%';
        """)
        return cur.fetchone()[0]


def q7_jhu_ms_cs_count(conn):
    """
    Count Master's Computer Science applicants who mentioned JHU.

    Args:
        conn: Active psycopg connection.

    Returns:
        int: Matching record count.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM applicants
            WHERE degree = 'Masters'
              AND program ILIKE '%computer science%'
              AND comments ILIKE '%johns hopkins%';
        """)
        return cur.fetchone()[0]


def q8_top_cs_phd_accepts(conn):
    """
    Count accepted PhD CS applicants (2026) at top universities.

    Universities: Georgetown, MIT, Stanford, Carnegie Mellon.

    Args:
        conn: Active psycopg connection.

    Returns:
        int: Matching record count.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM applicants
            WHERE term LIKE '%2026%'
              AND status ILIKE 'accepted%'
              AND degree = 'PhD'
              AND program ILIKE '%computer science%'
              AND (
                   comments ILIKE '%georgetown%'
                OR comments ILIKE '%mit%'
                OR comments ILIKE '%stanford%'
                OR comments ILIKE '%carnegie mellon%'
              );
        """)
        return cur.fetchone()[0]


def q9_llm_vs_raw_comparison(conn):
    """
    Same analysis as Q8 using LLM-generated structured fields.

    Args:
        conn: Active psycopg connection.

    Returns:
        int: Matching record count.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM applicants
            WHERE term LIKE '%2026%'
              AND status ILIKE 'accepted%'
              AND degree = 'PhD'
              AND llm_generated_program ILIKE '%computer science%'
              AND (
                   llm_generated_university ILIKE '%georgetown%'
                OR llm_generated_university ILIKE '%mit%'
                OR llm_generated_university ILIKE '%stanford%'
                OR llm_generated_university ILIKE '%carnegie mellon%'
              );
        """)
        return cur.fetchone()[0]


def extra_question_1(conn):
    """
    Average GPA grouped by degree type.

    Args:
        conn: Active psycopg connection.

    Returns:
        list[tuple]: ``[(degree, avg_gpa), ...]``
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT degree, ROUND(AVG(gpa)::numeric, 2)
            FROM applicants
            WHERE gpa IS NOT NULL
            GROUP BY degree;
        """)
        return cur.fetchall()


def extra_question_2(conn):
    """
    Overall acceptance percentage across all applicants.

    Args:
        conn: Active psycopg connection.

    Returns:
        Decimal | None: Percentage rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(
                    CASE WHEN status ILIKE 'accepted%'
                         THEN 1 ELSE 0 END
                ) / NULLIF(COUNT(*), 0), 2
            )
            FROM applicants;
        """)
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------

def query_all(conn):
    """
    Run all analysis queries and return results as a dict.

    Keys match the variable names expected by the ``analysis.html``
    Jinja2 template:

    ``q1``, ``q2``, ``q3``, ``q4``, ``q5``, ``q6``, ``q7``,
    ``q8``, ``q9``, ``extra_1``, ``extra_2``

    Args:
        conn: Active psycopg connection.

    Returns:
        dict: Query results keyed by question label.
    """
    return {
        "q1": q1_fall_2026_count(conn),
        "q2": q2_percent_international(conn),
        "q3": q3_avg_scores(conn),
        "q4": q4_avg_gpa_us_fall_2026(conn),
        "q5": q5_percent_accept_fall_2026(conn),
        "q6": q6_avg_gpa_accept_fall_2026(conn),
        "q7": q7_jhu_ms_cs_count(conn),
        "q8": q8_top_cs_phd_accepts(conn),
        "q9": q9_llm_vs_raw_comparison(conn),
        "extra_1": extra_question_1(conn),
        "extra_2": extra_question_2(conn),
    }
