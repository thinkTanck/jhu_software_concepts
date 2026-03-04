# module_6/src/web/app.py
from __future__ import annotations

import os
from typing import Any, Optional

import psycopg
from psycopg import sql
from flask import Flask, make_response, render_template, request

from publisher import publish_task  # src/web/publisher.py

APP_TITLE = "Module 6 - Deploy Anywhere"
DEFAULT_CACHE_KEY = "latest"

# Try these column names for the cached JSON payload in analytics_cache
PAYLOAD_COL_CANDIDATES = ("payload", "data", "value", "results", "result", "json")
UPDATED_COL_CANDIDATES = ("updated_at", "updated", "ts", "timestamp")


def _db_conn() -> psycopg.Connection:
    dsn = os.environ["DATABASE_URL"]
    return psycopg.connect(dsn)


def _default_results() -> dict[str, Any]:
    return {
        "has_data": False,
        "row_count": 0,
        "latest_run": None,
        "top_schools": [],
        "top_programs": [],
        "notes": "No analytics cached yet.",
        # index.html / analysis.html may reference q1..q9
        "q1": None,
        "q2": None,
        "q3": None,
        "q4": None,
        "q5": None,
        "q6": None,
        "q7": None,
        "q8": None,
        "q9": None,
    }


def _first_existing_column(
    cur: psycopg.Cursor, table: str, candidates: tuple[str, ...]
) -> Optional[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    cols = {row[0] for row in cur.fetchall()}
    for name in candidates:
        if name in cols:
            return name
    return None


def _fetch_cached_analytics(cache_key: str = DEFAULT_CACHE_KEY) -> dict[str, Any]:
    results = _default_results()

    try:
        with _db_conn() as conn:
            with conn.cursor() as cur:
                # Detect actual column names in your analytics_cache table
                payload_col = _first_existing_column(cur, "analytics_cache", PAYLOAD_COL_CANDIDATES)
                updated_col = _first_existing_column(cur, "analytics_cache", UPDATED_COL_CANDIDATES)

                if payload_col is None:
                    results["notes"] = (
                        "Could not load analytics cache: analytics_cache table has no known payload column "
                        f"(tried: {', '.join(PAYLOAD_COL_CANDIDATES)})."
                    )
                    return results

                # updated column is optional; if missing we still render
                if updated_col is None:
                    query = sql.SQL("SELECT key, {payload} FROM analytics_cache WHERE key = %s").format(
                        payload=sql.Identifier(payload_col)
                    )
                    cur.execute(query, (cache_key,))
                    row = cur.fetchone()
                    if not row:
                        return results
                    _key, payload = row
                    updated_at = None
                else:
                    query = sql.SQL("SELECT key, {payload}, {updated} FROM analytics_cache WHERE key = %s").format(
                        payload=sql.Identifier(payload_col),
                        updated=sql.Identifier(updated_col),
                    )
                    cur.execute(query, (cache_key,))
                    row = cur.fetchone()
                    if not row:
                        return results
                    _key, payload, updated_at = row

                merged = _default_results()
                if isinstance(payload, dict):
                    merged.update(payload)
                else:
                    # If JSON isn't decoded, still show a note rather than 500
                    merged["notes"] = f"Analytics cache present but {payload_col} was not decoded as dict."

                merged["has_data"] = True
                merged["latest_run"] = str(updated_at) if updated_at is not None else None
                return merged

    except Exception as exc:  # pylint: disable=broad-except
        results["notes"] = f"Could not load analytics cache: {exc}"
        return results


def _publish_task(kind: str, payload: dict | None = None) -> None:
    publish_task(kind=kind, payload=payload or {})


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        # index.html expects results
        results = _fetch_cached_analytics(DEFAULT_CACHE_KEY)
        return render_template("index.html", title=APP_TITLE, results=results)

    @app.get("/analysis")
    def analysis():
        results = _fetch_cached_analytics(DEFAULT_CACHE_KEY)
        queued_msg = request.args.get("queued_msg")
        return render_template("analysis.html", title=APP_TITLE, results=results, queued_msg=queued_msg)

    @app.post("/analyze")
    def analyze():
        # Robust: accept action from form field OR query param
        action = (request.form.get("action") or request.args.get("action") or "").strip()

        if action == "scrape_new_data":
            _publish_task("scrape_new_data", {"source": "web"})
            queued_msg = "Request queued: scrape new data."
        elif action == "recompute_analytics":
            _publish_task("recompute_analytics", {"source": "web"})
            queued_msg = "Request queued: recompute analytics."
        else:
            queued_msg = "Unknown action. Nothing queued."

        results = _fetch_cached_analytics(DEFAULT_CACHE_KEY)
        return make_response(
            render_template("analysis.html", title=APP_TITLE, results=results, queued_msg=queued_msg),
            202,
        )

    @app.get("/healthz")
    def healthz():
        return {"ok": True}, 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))