# Module 4 — Testing and Documentation

## Overview

This module adds a comprehensive test suite, 100% code coverage, GitHub Actions CI, and
Sphinx documentation to the GradCafe admissions analysis application built in Module 3.

---

## Documentation

Full API reference and developer guides are hosted on Read the Docs:

**[https://your-rtd-project.readthedocs.io](https://your-rtd-project.readthedocs.io)**
*(Replace this URL with the real Read the Docs link after publishing.)*

To build the docs locally:

```bash
cd module_4/docs
py -m sphinx -b html . _build/html
# then open _build/html/index.html in a browser
```

---

## Technologies Used

- Python 3.13
- Flask 3+
- PostgreSQL + psycopg v3
- pytest + pytest-cov (100% coverage enforced)
- BeautifulSoup4 (HTML assertions)
- Sphinx + sphinx-rtd-theme (documentation)
- GitHub Actions (CI)

---

## Running the Application

Set the `DATABASE_URL` environment variable, then from the **repository root**:

```bash
py -m flask --app module_4/src/app.py run
```

Or create a `.env` file in `module_4/` with:

```
DATABASE_URL=postgresql://user:password@localhost:5432/gradcafe_module3
```

---

## Running the Tests

From the **repository root**:

```bash
pytest -m "web or buttons or analysis or db or integration" module_4/tests/
```

The `pytest.ini` in `module_4/` enforces:

- Coverage over `module_4/src` (100% required)
- All five custom markers: `web`, `buttons`, `analysis`, `db`, `integration`

### Coverage Summary

See [`coverage_summary.txt`](coverage_summary.txt) for the latest coverage report.
All source files reach **100%** coverage:

```
Name                            Stmts   Miss  Cover
----------------------------------------------------
module_4\src\__init__.py            0      0   100%
module_4\src\app.py                81      0   100%
module_4\src\load_data.py         107      0   100%
module_4\src\query_data.py         46      0   100%
module_4\src\scrape_status.py       1      0   100%
----------------------------------------------------
TOTAL                             235      0   100%
```

---

## CI / GitHub Actions

The workflow file is at [`.github/workflows/tests.yml`](../.github/workflows/tests.yml).

It spins up a PostgreSQL 16 service container, installs dependencies, and runs the
full marked test suite on every push and pull request.

**Proof of passing CI:** see [`actions_success.png`](actions_success.png)
*(Replace the placeholder image with a real screenshot from your GitHub Actions run.)*

---

## Project Structure

```
module_4/
├── src/
│   ├── __init__.py
│   ├── app.py               # Flask app factory with DI
│   ├── load_data.py         # ETL: parse + insert rows
│   ├── query_data.py        # SQL queries + query_all()
│   └── scrape_status.py     # Busy-state sentinel
├── tests/
│   ├── conftest.py          # Fixtures (schema, DB, fake fns)
│   ├── test_flask_page.py   # [web] Route + rendering tests
│   ├── test_buttons.py      # [buttons] Pull/update endpoints
│   ├── test_analysis_format.py  # [analysis] Formatting tests
│   ├── test_db_insert.py    # [db] DB insert + helper tests
│   └── test_integration_end_to_end.py  # [integration] E2E tests
├── docs/
│   ├── conf.py
│   ├── index.rst
│   ├── overview.rst
│   ├── architecture.rst
│   ├── testing.rst
│   └── api/
│       ├── index.rst
│       ├── app.rst
│       ├── load_data.rst
│       ├── query_data.rst
│       ├── scrape.rst
│       └── clean.rst
├── pytest.ini
├── requirements.txt
├── coverage_summary.txt
└── actions_success.png      # Replace with real CI screenshot
```

---

## Database Design

The production `public.applicants` table and the isolated test schema
`test_module4.applicants` both use this structure:

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment |
| `program` | TEXT | Academic program |
| `comments` | TEXT | Raw GradCafe notes |
| `date_added` | DATE | Decision date |
| `url` | TEXT | Source URL |
| `status` | TEXT | Accepted / Rejected / Wait Listed |
| `term` | TEXT | e.g. Fall 2026 |
| `us_or_international` | TEXT | American / International |
| `gpa` | NUMERIC(10,2) | GPA |
| `gre` | NUMERIC(10,2) | Total GRE |
| `gre_v` | NUMERIC(10,2) | Verbal GRE |
| `gre_aw` | NUMERIC(10,2) | Analytical Writing |
| `degree` | TEXT | Masters / PhD |
| `llm_generated_program` | TEXT | LLM-parsed program |
| `llm_generated_university` | TEXT | LLM-parsed university |
