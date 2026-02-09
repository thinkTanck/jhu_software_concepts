# All query functions accept a psycopg connection passed from Flask

def q1_fall_2026_count(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM applicants
            WHERE term = 'Fall 2026';
        """)
        return cur.fetchone()[0]


def q2_percent_international(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(CASE WHEN us_or_international = 'International' THEN 1 ELSE 0 END)
                / COUNT(*), 2
            )
            FROM applicants
            WHERE us_or_international IS NOT NULL;
        """)
        return cur.fetchone()[0]


def q3_avg_scores(conn):
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
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(AVG(gpa)::numeric, 2)
            FROM applicants
            WHERE term = 'Fall 2026'
              AND us_or_international = 'American';
        """)
        return cur.fetchone()[0]


def q5_percent_accept_fall_2026(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(CASE WHEN status ILIKE 'accepted%' THEN 1 ELSE 0 END)
                / COUNT(*), 2
            )
            FROM applicants
            WHERE term = 'Fall 2026';
        """)
        return cur.fetchone()[0]


def q6_avg_gpa_accept_fall_2026(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(AVG(gpa)::numeric, 2)
            FROM applicants
            WHERE term = 'Fall 2026'
              AND status ILIKE 'accepted%';
        """)
        return cur.fetchone()[0]


def q7_jhu_ms_cs_count(conn):
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
    with conn.cursor() as cur:
        cur.execute("""
            SELECT degree, ROUND(AVG(gpa)::numeric, 2)
            FROM applicants
            WHERE gpa IS NOT NULL
            GROUP BY degree;
        """)
        return cur.fetchall()


def extra_question_2(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ROUND(
                100.0 * SUM(CASE WHEN status ILIKE 'accepted%' THEN 1 ELSE 0 END)
                / COUNT(*), 2
            )
            FROM applicants;
        """)
        return cur.fetchone()[0]
