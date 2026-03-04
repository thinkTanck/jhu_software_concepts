Testing Guide
=============

Overview
--------

The test suite is located in ``module_4/tests/`` and consists of **five** test
files, each covering a specific aspect of the application.  All tests are
marked with at least one custom pytest marker.

Running the Tests
-----------------

From the **repository root**::

    pytest -m "web or buttons or analysis or db or integration" module_4/tests/

The ``pytest.ini`` file (in ``module_4/``) configures:

- Coverage measurement over ``module_4/src``
- ``--cov-fail-under=100`` — the suite **must** reach 100% coverage
- All five custom markers

Test Files
----------

``test_flask_page.py``
   Tests marked ``web``.

   Verifies that:

   - ``create_app()`` creates a valid Flask app with all required routes.
   - ``GET /analysis`` returns HTTP 200.
   - The HTML contains both buttons ("Pull Data", "Update Analysis").
   - The page contains the word "Analysis" and at least one "Answer:" label.
   - Both buttons have the required ``data-testid`` attributes.

``test_buttons.py``
   Tests marked ``buttons``.

   Verifies that:

   - ``POST /pull-data`` returns ``200 {"ok": true}`` and calls the loader.
   - ``POST /update-analysis`` returns ``200 {"ok": true}`` when not busy.
   - When busy, both ``POST /pull-data`` and ``POST /update-analysis`` return
     ``409 {"busy": true}`` and do **not** call the loader.
   - The busy state resets to ``False`` after a successful pull.

``test_analysis_format.py``
   Tests marked ``analysis``.

   Verifies that:

   - All ``Answer:`` labels are present in the rendered HTML.
   - Percentage values are formatted to exactly two decimal places (e.g.
     ``39.28%``), verified with ``re.fullmatch``.
   - ``None`` percentage values render as ``N/A`` without raising a template
     error.

``test_db_insert.py``
   Tests marked ``db``.

   Verifies that:

   - The test table is empty before each insert (isolation via TRUNCATE).
   - ``load_rows()`` inserts the correct number of rows.
   - Required non-null fields (``comments``, ``url``) are populated.
   - Running ``load_rows()`` twice with identical data does **not** create
     duplicates (idempotency via ``ON CONFLICT DO NOTHING``).
   - All parsing helper functions handle edge cases (None, empty, no-match).
   - ``query_all()`` returns a dict with all required keys.

``test_integration_end_to_end.py``
   Tests marked ``integration``.

   Verifies the complete flow:

   1. Inject fake scraper returning multiple records.
   2. ``POST /pull-data`` succeeds and rows appear in the DB.
   3. ``POST /update-analysis`` succeeds when not busy.
   4. ``GET /analysis`` shows updated results with correct formatting.
   5. Multiple pulls with overlapping data remain consistent with the
      uniqueness policy.

Markers
-------

+-------------+-----------------------------------------------+
| Marker      | Description                                   |
+=============+===============================================+
| ``web``     | Flask route/page rendering tests              |
+-------------+-----------------------------------------------+
| ``buttons`` | Pull Data and Update Analysis behavior        |
+-------------+-----------------------------------------------+
| ``analysis``| Formatting/rounding of analysis output        |
+-------------+-----------------------------------------------+
| ``db``      | Database schema, inserts, selects             |
+-------------+-----------------------------------------------+
| ``integration`` | End-to-end flows                          |
+-------------+-----------------------------------------------+

Fixtures and Test Doubles
--------------------------

``conftest.py`` provides:

``_schema_setup`` (session, autouse)
   Creates the ``test_module4`` schema and ``applicants`` table once per
   session; drops it at session end.

``db_transaction`` (function)
   Opens a fresh psycopg connection, sets ``search_path`` to
   ``test_module4``, and TRUNCATEs the table for isolation.

``app`` (function)
   A Flask app with ``QUERY_FN`` set to a zero-argument fake that returns
   hardcoded results — no DB connection needed for page rendering tests.

``client`` (function)
   A ``werkzeug.test.Client`` wrapping the ``app`` fixture.

``db_app`` (function)
   A Flask app with real ``LOADER_FN`` and ``QUERY_FN`` targeting the
   ``test_module4`` schema via the ``db_transaction`` connection.

``db_client`` (function)
   A test client wrapping ``db_app``.

Stable Selectors
----------------

The ``analysis.html`` template includes ``data-testid`` attributes on
both action buttons:

- ``data-testid="pull-data-btn"``
- ``data-testid="update-analysis-btn"``

These are used by tests for stable element selection::

    btn = soup.find("button", attrs={"data-testid": "pull-data-btn"})

Database Isolation
------------------

Tests that write to the database use the ``test_module4`` schema — a
completely separate schema from the production ``public.applicants`` table.
Each test gets a fresh connection and a ``TRUNCATE … RESTART IDENTITY``
before execution, ensuring fully deterministic results.
