# Module 5 — Software Assurance: Secure SQL & SQLi Defense

## Overview

Module 5 extends the GradCafe admissions analysis application built in Modules 3–4 with
three security and quality checkpoints:

- **Step 1 — Pylint 10/10**: All `src/` modules score 10.00/10 with zero warnings or
  `# pylint: disable` suppressions.
- **Step 2 — SQL Injection Defense**: Every SQL statement uses `psycopg.sql.SQL`, positional
  `%s` / named `%(name)s` placeholders for all literal values, statement construction separated
  from execution, and a hard-coded `LIMIT` with a server-side clamp `[1–100]` on every
  multi-row query.
- **Step 3 — Credential Hardening**: No hard-coded database credentials anywhere in source.
  The `DATABASE_URL` (and `SECRET_KEY`) are read exclusively from environment variables.
  `.env.example` provides a template; `.env` is listed in `.gitignore` and never committed.
- **Step 4 — Dependency Graph**: `pydeps` + Graphviz generate `dependency.svg` showing the
  internal import DAG of the `src` package.
- **Step 5 — Packaging**: `setup.py`, updated `requirements.txt`, and this README provide a
  reproducible fresh-install path via both `pip` and `uv`.
- **Step 6 — Security Scan**: Snyk CLI scans open-source dependencies for known CVEs.
  See [`SECURITY_SCAN_NOTES.md`](SECURITY_SCAN_NOTES.md) for authentication and run instructions.

---

## Technologies Used

| Technology | Version | Purpose |
|---|---|---|
| Python | ≥ 3.11 | Runtime |
| Flask | ≥ 3.0 | Web framework |
| psycopg | ≥ 3.1 (v3) | PostgreSQL adapter (binary extras) |
| PostgreSQL | ≥ 14 | Relational database |
| pytest + pytest-cov | ≥ 8.0 / 5.0 | Test suite + coverage |
| BeautifulSoup4 | ≥ 4.12 | HTML assertions in tests |
| pylint | ≥ 3.0 | Static analysis (target: 10.00/10) |
| pydeps | ≥ 2.0 | Dependency graph visualisation |
| Graphviz | any | SVG rendering for pydeps (system install) |
| Snyk CLI | latest | Open-source vulnerability scanning |
| Node.js / npm | ≥ 18 | Required to install Snyk CLI |
| Sphinx + sphinx-rtd-theme | ≥ 7.0 / 2.0 | API documentation |

---

## Fresh Install

### Option A — pip (Windows, recommended)

```powershell
# 1. Create a virtual environment
py -m venv .venv

# 2. Activate it
.venv\Scripts\activate

# 3. Install all dependencies
py -m pip install -r requirements.txt
```

### Option B — uv (Windows)

[uv](https://docs.astral.sh/uv/) is a fast, modern Python package manager.

```powershell
# 1. Install uv (one-time, requires winget from Windows 10/11)
winget install --id astral-sh.uv -e
# OR via pip if winget is unavailable:
py -m pip install uv

# 2. Create a virtual environment
uv venv .venv

# 3. Install all dependencies
uv pip install -r requirements.txt
```

---

## Environment Setup

Copy `.env.example` to `.env` and fill in your real values:

```powershell
copy .env.example .env
```

Then edit `.env`:

```
DATABASE_URL=postgresql://DB_USER:DB_PASSWORD@DB_HOST:DB_PORT/DB_NAME
SECRET_KEY=your-random-secret-key-here
```

> `.env` is listed in `.gitignore` and must never be committed.
> Generate a strong SECRET_KEY with:
> `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Running the Application

With `DATABASE_URL` set in your environment (or in `.env` via `python-dotenv`):

```powershell
py -m flask --app src/app.py run
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Running the Tests

`DATABASE_URL` must be exported in your shell session before running tests:

```powershell
py -m pytest -c .\pytest.ini .\tests -q
```

Expected result: **99 tests pass**.

---

## Dependency Graph

The import dependency graph for the `src` package is in [`dependency.svg`](dependency.svg).
A written summary of the graph structure is in [`dependency_summary.md`](dependency_summary.md).

### Regenerating the graph

1. Install Graphviz (system-level, one-time):
   ```powershell
   winget install --id Graphviz.Graphviz -e
   ```
2. Restart your terminal, verify `dot -V` prints a version string.
3. From this directory (`module_5/`):
   ```
   .venv\Scripts\pydeps src --noshow -o dependency.svg -x src.module_2
   ```

---

## Security Scan

See [`SECURITY_SCAN_NOTES.md`](SECURITY_SCAN_NOTES.md) for full Snyk installation,
authentication, and scan instructions.

Screenshot evidence of the scan is in [`snyk-analysis.png`](snyk-analysis.png)
(added after running `snyk auth` + `snyk test` — see SECURITY_SCAN_NOTES.md).

---

## Security Notes

See [`SECURITY_NOTES.md`](SECURITY_NOTES.md) for the least-privilege PostgreSQL role
configuration used by this application.

---

## Project Structure

```
module_5/
├── src/
│   ├── __init__.py
│   ├── app.py               # Flask app factory + DI config
│   ├── load_data.py         # ETL: parse + INSERT rows (sql.SQL, _INSERT_SQL)
│   ├── query_data.py        # Analytical SQL queries (sql.SQL, LIMIT/clamp)
│   └── scrape_status.py     # SCRAPE_RUNNING sentinel
├── tests/
│   ├── conftest.py          # Fixtures (schema, DB, fake callables)
│   ├── test_flask_page.py   # [web] Route + rendering tests
│   ├── test_buttons.py      # [buttons] Pull/update endpoint tests
│   ├── test_analysis_format.py  # [analysis] Result formatting tests
│   ├── test_db_insert.py    # [db] DB insert + parsing helper tests
│   └── test_integration_end_to_end.py  # [integration] E2E tests
├── docs/
│   ├── conf.py
│   ├── index.rst
│   └── api/
├── pytest.ini
├── requirements.txt         # All runtime + dev dependencies
├── setup.py                 # Setuptools packaging config
├── .env.example             # Template — copy to .env and fill in real values
├── .gitignore
├── SECURITY_NOTES.md        # Least-privilege DB role configuration
├── SECURITY_SCAN_NOTES.md   # Snyk scan instructions + evidence
├── dependency.svg           # Import graph (generated by pydeps + Graphviz)
├── dependency_summary.md    # Written analysis of the dependency graph
└── snyk-analysis.png        # Screenshot of snyk test output
```

---

## Database Design

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
| `gpa` | NUMERIC(4,2) | GPA |
| `gre` | NUMERIC(6,2) | Total GRE |
| `gre_v` | NUMERIC(6,2) | Verbal GRE |
| `gre_aw` | NUMERIC(4,2) | Analytical Writing |
| `degree` | TEXT | Masters / PhD |
| `llm_generated_program` | TEXT | LLM-parsed program |
| `llm_generated_university` | TEXT | LLM-parsed university |
