"""
app.py

Flask web application for Module 3.

This application:
- Connects to the PostgreSQL database
- Executes analytical queries defined in query_data.py
- Displays results on a styled webpage
- Provides buttons to trigger data scraping and analysis updates

Database access is implemented using psycopg3.
"""

import subprocess
from flask import Flask, render_template, redirect, url_for, flash
import psycopg
import scrape_status
import query_data


# Initialize Flask application
app = Flask(__name__)
app.secret_key = "module3-dev-key"


# -------------------------
# Database Connection
# -------------------------

def get_db_connection():
    """
    Establish and return a new psycopg3 database connection.

    Returns:
        psycopg.Connection object connected to the
        gradcafe_module3 database.
    """
    return psycopg.connect(
        host="localhost",
        dbname="gradcafe_module3",
        user="postgres",
        password="59061076",
        port=5432
    )


# -------------------------
# Analysis Page Route
# -------------------------

@app.route("/")
@app.route("/analysis")
def analysis():
    """
    Render the main analysis page.

    Executes all defined SQL query functions and passes
    results to the Jinja2 template for display.
    """

    conn = get_db_connection()

    # Execute all assignment queries
    results = {
        "q1": query_data.q1_fall_2026_count(conn),
        "q2": query_data.q2_percent_international(conn),
        "q3": query_data.q3_avg_scores(conn),
        "q4": query_data.q4_avg_gpa_us_fall_2026(conn),
        "q5": query_data.q5_percent_accept_fall_2026(conn),
        "q6": query_data.q6_avg_gpa_accept_fall_2026(conn),
        "q7": query_data.q7_jhu_ms_cs_count(conn),
        "q8": query_data.q8_top_cs_phd_accepts(conn),
        "q9": query_data.q9_llm_vs_raw_comparison(conn),
        "extra_1": query_data.extra_question_1(conn),
        "extra_2": query_data.extra_question_2(conn),
    }

    conn.close()

    return render_template(
        "analysis.html",
        results=results,
        scrape_running=scrape_status.scrape_running
    )


# -------------------------
# Pull Data Route
# -------------------------

@app.route("/pull-data", methods=["POST"])
def pull_data():
    """
    Trigger the Module 2 scraping script in a background subprocess.

    Prevents duplicate runs using scrape_status flag.
    Displays status messages using Flask flash messaging.
    """

    if scrape_status.scrape_running:
        flash("Data pull already in progress.", "warning")
        return redirect(url_for("analysis"))

    scrape_status.scrape_running = True

    # Launch scraper as background process (non-blocking)
    subprocess.Popen(
        ["py", "../module_2/scrape.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    flash("Pull Data started. This may take several minutes.", "info")
    return redirect(url_for("analysis"))


# -------------------------
# Update Analysis Route
# -------------------------

@app.route("/update-analysis", methods=["POST"])
def update_analysis():
    """
    Refresh analysis results after scraping completes.

    Prevents execution while scraping is active.
    """

    if scrape_status.scrape_running:
        flash("Cannot update analysis while data is being pulled.", "warning")
        return redirect(url_for("analysis"))

    flash("Analysis updated with latest data.", "success")
    return redirect(url_for("analysis"))


# -------------------------
# Application Entry Point
# -------------------------

if __name__ == "__main__":
    # Run Flask development server
    app.run(debug=True)
