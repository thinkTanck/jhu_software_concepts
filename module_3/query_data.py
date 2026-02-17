"""
query_data.py

Contains all SQL query functions used by the Flask web application
for Module 3. Each function accepts an active psycopg3 connection
object and executes a specific query against the `applicants` table.

All queries return computed values used to answer the assignment
analysis questions.
"""


# All query functions accept a psycopg connection passed from Flask.


def q1_fall_2026_count(conn):
    """
    Return the total number of applicants for the Fall 2026 term.

    Args:
        conn: Active psycopg3 database connection.

    Returns:
        Integer count of Fall 2026 applicants.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM applicants
            WHERE term = 'Fall 2026';
        """)
        # fetchone()[0] retrieves the scalar COUNT(*) value
        return cur.fetchone()[0]


def q2_percent_international(conn):
    """
    Calculate the percentage of applicants classified as International.

    Only rows with a non-null us_or_international value are included
    in the denominator.

    Returns:
        Float percentage rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(
                    CASE WHEN us_or_international = 'International'
                         THEN 1 ELSE 0 END
                ) / COUNT(*), 2
            )
            FROM applicants
            WHERE us_or_international IS NOT NULL;
        """)
        return cur.fetchone()[0]


def q3_avg_scores(conn):
    """
    Compute the average GPA and GRE scores for all applicants.

    Returns:
        Tuple containing:
        (avg_gpa, avg_gre_total, avg_gre_verbal, avg_gre_aw)
        Each value rounded to two decimal places.
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
    Calculate the average GPA of American applicants
    for the Fall 2026 term.

    Returns:
        Float average GPA rounded to two decimal places.
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
    Calculate the percentage of Fall 2026 applicants
    who were accepted.

    Uses ILIKE 'accepted%' to capture any status values
    that begin with 'accepted', case-insensitive.

    Returns:
        Float percentage rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(
                    CASE WHEN status ILIKE 'accepted%'
                         THEN 1 ELSE 0 END
                ) / COUNT(*), 2
            )
            FROM applicants
            WHERE term = 'Fall 2026';
        """)
        return cur.fetchone()[0]


def q6_avg_gpa_accept_fall_2026(conn):
    """
    Calculate the average GPA of applicants who were
    accepted for Fall 2026.

    Returns:
        Float average GPA rounded to two decimal places.
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
    Count the number of Master's applicants in Computer Science
    who mentioned Johns Hopkins in their comments.

    Uses case-insensitive pattern matching (ILIKE)
    to search free-text fields.

    Returns:
        Integer count of matching records.
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
    Count accepted PhD Computer Science applicants (2026)
    who referenced selected universities in their comments.

    Universities included:
    - Georgetown
    - MIT
    - Stanford
    - Carnegie Mellon

    Returns:
        Integer count of matching records.
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
    Perform the same analysis as Question 8, but using
    structured LLM-generated fields instead of raw comments.

    This allows comparison between raw text matching
    and LLM-standardized data extraction.

    Returns:
        Integer count of matching records.
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
    Compute the average GPA grouped by degree type.

    Returns:
        List of tuples in the format:
        [(degree, avg_gpa), ...]
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
    Calculate the overall acceptance percentage
    across the entire dataset.

    Returns:
        Float percentage rounded to two decimal places.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(
                    CASE WHEN status ILIKE 'accepted%'
                         THEN 1 ELSE 0 END
                ) / COUNT(*), 2
            )
            FROM applicants;
        """)
        return cur.fetchone()[0]
