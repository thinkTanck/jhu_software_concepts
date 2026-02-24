# Dependency Summary — Module 5 `src` Package

The `src` package forms a directed acyclic graph (DAG) with `app.py` at the root; every import
arrow flows *into* `app.py` or *down* toward third-party libraries, with no circular dependencies.
`app.py` is the sole internal orchestrator: it directly imports both `load_data` and `query_data`,
wiring together the ETL pipeline and the analytical query layer through Flask's dependency-injection
config keys (`LOADER_FN`, `QUERY_FN`).
`query_data.py` is the most isolated module in the graph — its only external dependency is
`psycopg.sql` — making it the easiest layer to unit-test with a minimal in-memory double.
`load_data.py` carries the broadest standard-library footprint (`json`, `re`, `datetime`, `os`),
reflecting its ETL role of parsing and normalising raw scraper output before insertion.
`scrape_status.py` has zero imports and zero side-effects; it is a pure module-level boolean
sentinel whose sole purpose is to allow the busy-state flag to live outside `app.py` without
requiring a global variable.
The clean layering — `app` → `load_data` / `query_data` → `psycopg` / stdlib — means that
any layer can be replaced or mocked in isolation, which is precisely the design exploited by
the 99-test suite through Flask's `config_object` dependency-injection mechanism.

## Regenerating dependency.svg

1. Install Graphviz (one-time system install):
   ```powershell
   winget install --id Graphviz.Graphviz -e
   ```
2. Restart your terminal so `dot` is on PATH, then verify:
   ```powershell
   dot -V
   ```
3. From the `module_5/` directory, run:
   ```
   .venv\Scripts\pydeps src --noshow -o dependency.svg -x src.module_2
   ```
   The `-x src.module_2` flag excludes the nested `src/module_2/` sub-package
   (and its bundled `.venv`) so the graph shows only the four main application modules.
