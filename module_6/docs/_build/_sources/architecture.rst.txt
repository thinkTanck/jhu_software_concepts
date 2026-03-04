Architecture
============

The application is divided into three primary layers:

Web Layer (``app.py``)
----------------------

The Flask application created by ``create_app()`` serves as the entry point for
all HTTP traffic.

Responsibilities:

- Serve the ``/analysis`` page by calling the configured ``QUERY_FN``.
- Handle ``POST /pull-data`` — invoke ``SCRAPER_FN`` then ``LOADER_FN``.
- Handle ``POST /update-analysis`` — signal that results should refresh.
- Enforce **busy-state gating**: if a pull is in progress, subsequent pull or
  update requests return ``409 {"busy": true}``.

Dependency injection is provided via ``app.config``:

+---------------+---------------------------------------------+
| Key           | Default                                     |
+===============+=============================================+
| DATABASE_URL  | from environment variable                   |
+---------------+---------------------------------------------+
| SCRAPER_FN    | ``_default_scraper`` (calls module_2)       |
+---------------+---------------------------------------------+
| LOADER_FN     | ``_default_loader`` (calls load_data)       |
+---------------+---------------------------------------------+
| QUERY_FN      | ``_default_query_all`` (calls query_data)   |
+---------------+---------------------------------------------+
| BUSY_GETTER   | reads module-level ``_busy`` flag           |
+---------------+---------------------------------------------+
| BUSY_SETTER   | writes module-level ``_busy`` flag          |
+---------------+---------------------------------------------+

ETL Layer (``load_data.py``)
------------------------------

Responsibilities:

- Parse semi-structured GradCafe note fields into typed columns.
- Insert rows into the ``applicants`` table.
- Enforce idempotency via ``ON CONFLICT (comments, date_added, url) DO NOTHING``.

Key public API::

    load_rows(rows: list[dict], conn) -> int
    main(input_json=None, database_url=None)

Database Layer (``query_data.py``)
------------------------------------

Responsibilities:

- Execute all eleven analysis queries against the ``applicants`` table.
- Return typed scalars, tuples, and lists consumed by the Jinja2 template.

Key public API::

    query_all(conn) -> dict

The ``applicants`` table schema
--------------------------------

+-------------------------+----------------+-------------------------------------+
| Column                  | Type           | Description                         |
+=========================+================+=====================================+
| id                      | SERIAL PK      | Auto-increment primary key          |
+-------------------------+----------------+-------------------------------------+
| program                 | TEXT           | Graduate program name               |
+-------------------------+----------------+-------------------------------------+
| comments                | TEXT           | Raw scraped note (unique key part)  |
+-------------------------+----------------+-------------------------------------+
| date_added              | DATE           | Decision date (unique key part)     |
+-------------------------+----------------+-------------------------------------+
| url                     | TEXT           | Source URL (unique key part)        |
+-------------------------+----------------+-------------------------------------+
| status                  | TEXT           | Accepted / Rejected / Waitlisted    |
+-------------------------+----------------+-------------------------------------+
| term                    | TEXT           | e.g. "Fall 2026"                    |
+-------------------------+----------------+-------------------------------------+
| us_or_international     | TEXT           | "American" or "International"       |
+-------------------------+----------------+-------------------------------------+
| gpa                     | NUMERIC(10,2)  | GPA score                           |
+-------------------------+----------------+-------------------------------------+
| gre                     | NUMERIC(10,2)  | GRE total score                     |
+-------------------------+----------------+-------------------------------------+
| gre_v                   | NUMERIC(10,2)  | GRE Verbal score                    |
+-------------------------+----------------+-------------------------------------+
| gre_aw                  | NUMERIC(10,2)  | GRE Analytical Writing score        |
+-------------------------+----------------+-------------------------------------+
| degree                  | TEXT           | "PhD" or "Masters"                  |
+-------------------------+----------------+-------------------------------------+
| llm_generated_program   | TEXT           | LLM-extracted program name          |
+-------------------------+----------------+-------------------------------------+
| llm_generated_university| TEXT           | LLM-extracted university name       |
+-------------------------+----------------+-------------------------------------+

Unique constraint: ``(comments, date_added, url)``
