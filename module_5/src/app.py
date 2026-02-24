"""
app.py

Flask web application for Module 5.

Provides an app factory (create_app) so that tests can instantiate
the application without side-effects at import time.

The application:
- Connects to a PostgreSQL database via DATABASE_URL (env var or config)
- Executes analytical queries defined in query_data.py
- Displays results on a styled analysis page
- Provides /pull-data and /update-analysis endpoints with busy-state gating

Dependency injection:
- scraper_fn  : callable() -> list[dict]  (default: real scraper)
- loader_fn   : callable(rows, conn)      (default: real loader)
- query_fn    : callable(conn) -> dict    (default: real query_all)

These are stored on app.config so tests can override them.
"""

import importlib.util
import inspect
import os
from pathlib import Path

import psycopg
from flask import Flask, current_app, jsonify, render_template

from . import load_data as _load_data_mod
from . import query_data as _query_data_mod


# ---------------------------------------------------------------------------
# Busy-state
# ---------------------------------------------------------------------------
# Use a mutable dict so _set_busy can update the value without a
# `global` statement (which pylint W0603 forbids).
_STATE = {"busy": False}


def _is_busy():
    """Return current busy state (injectable in tests via app.config)."""
    getter = current_app.config.get("BUSY_GETTER")
    if getter is not None:
        return getter()
    return _STATE["busy"]


def _set_busy(value: bool):
    """Set busy state (injectable in tests via app.config)."""
    setter = current_app.config.get("BUSY_SETTER")
    if setter is not None:
        setter(value)
    else:
        _STATE["busy"] = value


# ---------------------------------------------------------------------------
# Default scraper / loader / query callables
# ---------------------------------------------------------------------------

def _default_scraper():
    """
    Real scraper: import and call the module_2 scrape pipeline.

    Returns a list of raw row dicts scraped from GradCafe.

    The path to ``scrape.py`` is resolved as follows:

    1. If the environment variable ``MODULE2_SCRAPE_PY`` is set, its value
       is used as the absolute path to ``scrape.py``.  This lets tests
       redirect the import to a temporary fake file without any monkeypatching
       of ``pathlib``.
    2. Otherwise the path is derived from this file's location:
       ``<repo_root>/module_2/scrape.py``.
    """
    override = os.environ.get("MODULE2_SCRAPE_PY")
    if override:
        scrape_path = Path(override)
    else:
        scrape_path = (
            Path(__file__).resolve().parent.parent.parent / "module_2" / "scrape.py"
        )

    spec = importlib.util.spec_from_file_location("_scrape", scrape_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.scrape()  # expects scrape.py to expose scrape() -> list[dict]


def _default_loader(rows, conn):
    """
    Real loader: insert rows into the database.

    Delegates to load_data.load_rows(rows, conn).
    """
    _load_data_mod.load_rows(rows, conn)


def _default_query_all(conn):
    """
    Real query runner: execute all analysis queries.

    Delegates to query_data.query_all(conn) -> dict.
    """
    return _query_data_mod.query_all(conn)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config_object=None):
    """
    Flask application factory.

    Args:
        config_object: Optional dict (or object with attributes) to
                       override default configuration values.
                       Tests pass a dict with DATABASE_URL, SCRAPER_FN, etc.

    Returns:
        A configured Flask application instance.

    Configuration keys understood by the app:

    - **DATABASE_URL**: libpq-compatible connection string.
      Must be provided via the ``DATABASE_URL`` environment variable or
      passed explicitly in ``config_object``.  No hard-coded default.
      A ``RuntimeError`` is raised at request time if the key is absent.
    - **SCRAPER_FN**: callable() -> list[dict]  – override the real scraper.
    - **LOADER_FN**: callable(rows, conn)      – override the real loader.
    - **QUERY_FN**: callable(conn) -> dict    – override the real queries.
    - **BUSY_GETTER**: callable() -> bool        – override busy-state read.
    - **BUSY_SETTER**: callable(bool)            – override busy-state write.
    - **TESTING**: bool – standard Flask testing flag.
    - **SECRET_KEY**: str  – Flask secret key.
    """
    flask_app = Flask(__name__, template_folder="templates")

    # ---- Defaults (no hard-coded DB credentials) ----
    flask_app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "module4-dev-key")

    # DATABASE_URL: read from environment; do NOT provide a hard-coded fallback
    # so that missing config fails loudly rather than silently connecting to the
    # wrong database.
    env_db_url = os.environ.get("DATABASE_URL")
    if env_db_url:
        flask_app.config["DATABASE_URL"] = env_db_url
    # If not in env, leave unset here — caller must supply it via config_object,
    # or _get_db_connection() will raise a clear RuntimeError at request time.

    flask_app.config["SCRAPER_FN"] = _default_scraper
    flask_app.config["LOADER_FN"] = _default_loader
    flask_app.config["QUERY_FN"] = _default_query_all
    flask_app.config["BUSY_GETTER"] = None
    flask_app.config["BUSY_SETTER"] = None

    # ---- Apply caller overrides ----
    if config_object:
        if isinstance(config_object, dict):
            flask_app.config.update(config_object)
        else:
            flask_app.config.from_object(config_object)

    # ---- Register routes ----
    _register_routes(flask_app)

    return flask_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_connection():
    """Open and return a psycopg connection using DATABASE_URL from config."""
    url = current_app.config.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set.  "
            "Provide it via the DATABASE_URL environment variable or "
            "pass it in the config_object to create_app()."
        )
    return psycopg.connect(url)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _register_routes(flask_app: Flask):
    """Register all URL routes on *flask_app*."""

    @flask_app.route("/")
    @flask_app.route("/analysis")
    def analysis():
        """
        Render the main analysis page.

        Calls QUERY_FN(conn) to obtain a dict of results and passes
        them to the analysis.html template.

        If QUERY_FN is set to a function that accepts zero arguments
        (detected via ``inspect.signature``), the DB connection is not
        opened — this is used by tests that supply a pure fake.
        Otherwise a real connection is opened via context manager and
        automatically closed on exit.
        """
        query_fn = current_app.config["QUERY_FN"]
        sig = inspect.signature(query_fn)
        needs_conn = len(sig.parameters) > 0

        if needs_conn:
            with _get_db_connection() as conn:
                results = query_fn(conn)
        else:
            results = query_fn()

        return render_template(
            "analysis.html",
            results=results,
            busy=_is_busy(),
        )

    @flask_app.route("/pull-data", methods=["POST"])
    def pull_data():
        """
        Trigger data scraping and loading.

        Returns:
            409 JSON {"busy": true}  if already busy.
            200 JSON {"ok": true}    on success.
        """
        if _is_busy():
            return jsonify({"busy": True}), 409

        _set_busy(True)
        try:
            scraper_fn = current_app.config["SCRAPER_FN"]
            loader_fn = current_app.config["LOADER_FN"]
            rows = scraper_fn()
            with _get_db_connection() as conn:
                loader_fn(rows, conn)
        finally:
            _set_busy(False)

        return jsonify({"ok": True}), 200

    @flask_app.route("/update-analysis", methods=["POST"])
    def update_analysis():
        """
        Signal that analysis should refresh.

        Returns:
            409 JSON {"busy": true}  if a pull is in progress.
            200 JSON {"ok": true}    otherwise.
        """
        if _is_busy():
            return jsonify({"busy": True}), 409

        return jsonify({"ok": True}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    _app = create_app()
    _app.run(debug=True)
