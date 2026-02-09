# Module 3 — Database Queries and Web-Based Analysis

## Overview

This module extends the data collection work from Module 2 by loading scraped GradCafe admissions data into a PostgreSQL database and providing a web-based interface for querying and analyzing that data. A Flask application is used to execute SQL queries dynamically and display analysis results in a browser.

The module also supports controlled data updates, allowing newly available GradCafe submissions to be added to the database and reflected in subsequent analyses.

---

## Technologies Used

- Python 3
- Flask
- PostgreSQL
- psycopg (v3)
- SQL
- HTML / Jinja templates

---

## Database Design

The PostgreSQL database contains a single table named `applicants`. Each record represents one graduate admissions submission scraped from GradCafe. The table includes structured fields such as:

- Application term
- Degree type
- Program and institution
- GPA and GRE metrics
- Admission status
- Applicant nationality
- Parsed and derived fields used for analysis

This structure supports aggregate queries across application cycles, degree types, and admission outcomes.

---

## Analysis Queries

The Analysis page displays the results of **nine required queries** and **two additional queries**, all executed dynamically against the database. These queries include:

1. Counts of applicants by term
2. Percentage of international applicants
3. Average GPA and GRE metrics
4. GPA comparisons by applicant group
5. Acceptance rates for specific application cycles
6. Institution- and program-specific applicant counts
7. Comparisons using parsed versus derived fields
8. Average GPA by degree type (Masters vs PhD)
9. Overall acceptance percentage

All queries are written in SQL and executed through Python using a shared database connection.

---

## Web Application

The Flask application exposes a single primary page (`/analysis`) that displays all analysis results. The page renders dynamically using Jinja templates and reflects the current state of the database.

### Data Management Controls

Two user controls are provided at the bottom of the Analysis page:

- **Pull Data**  
  Launches the Module 2 scraper as a background subprocess to retrieve any newly available GradCafe submissions and append them to the database.

- **Update Analysis**  
  Refreshes the analysis page so that all queries reflect the most recent database state. This action is disabled while a data pull is in progress.

User feedback is displayed when actions are unavailable to clearly communicate system state.

---

## Running the Application

From the `module_3` directory, run:

```bash
py app.py
