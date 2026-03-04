from __future__ import annotations

import json
import os
from typing import Any

import psycopg
from flask import Flask, make_response, render_template, request

from publisher import publish_task

APP_TITLE = "GradCafe Admissions Analysis (Module 3)"
DEFAULT_CACHE_KEY = "latest"


def _db_conn() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def _default_results() -> dict[str, Any]:
    return {
        "q1": 0,
        "q2": None,
        "q3": [None, None, None, None],
        "q4": None,
        "q5": None,
        "q6": None,
        "q7": 0,
        "q8": 0,
        "q9": 0,
    }


def _fetch_cached_results() -> dict[str, Any]:
    """
    Read the latest analytics from analytics_cache.results for key='latest'.
    """
    results = _default_results()
    try:
        with _db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT results FROM analytics_cache WHERE key = %s",
                    (DEFAULT_CACHE_KEY,),
                )
                row = cur.fetchone()
                if not row:
                    return results

                payload = row[0]
                # psycopg may give dict (jsonb) or str; support both
                if isinstance(payload, dict):
                    results.update(payload)
                elif isinstance(payload, str):
                    try:
                        obj = json.loads(payload)
                        if isinstance(obj, dict):
                            results.update(obj)
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return results


def create_app() -> Flask:
    # Use flask_app locally to avoid redefined-outer-name with module-level `app`.
    flask_app = Flask(__name__)

    @flask_app.get("/")
    def index():
        results = _fetch_cached_results()
        return render_template("analysis.html", results=results, queued_msg=None, title=APP_TITLE)

    @flask_app.get("/analysis")
    def analysis():
        results = _fetch_cached_results()
        return render_template("analysis.html", results=results, queued_msg=None, title=APP_TITLE)

    @flask_app.post("/analyze")
    def analyze():
        action = (request.form.get("action") or "").strip()

        if action == "scrape_new_data":
            publish_task("scrape_new_data", payload={"source": "web"})
            queued_msg = "Request queued: Scrape New Data."
        elif action == "recompute_analytics":
            publish_task("recompute_analytics", payload={"source": "web"})
            queued_msg = "Request queued: Recompute Analytics."
        else:
            queued_msg = "Unknown action. Nothing queued."

        # Return immediately per rubric (202)
        results = _fetch_cached_results()
        return make_response(
            render_template(
                "analysis.html",
                results=results,
                queued_msg=queued_msg,
                title=APP_TITLE,
            ),
            202,
        )

    # Backward compatible endpoints (avoid 404s from old cached pages)
    @flask_app.post("/pull-data")
    def pull_data_alias():
        publish_task("scrape_new_data", payload={"source": "web"})
        results = _fetch_cached_results()
        return make_response(
            render_template(
                "analysis.html",
                results=results,
                queued_msg="Request queued: Scrape New Data.",
                title=APP_TITLE,
            ),
            202,
        )

    @flask_app.post("/update-analysis")
    def update_analysis_alias():
        publish_task("recompute_analytics", payload={"source": "web"})
        results = _fetch_cached_results()
        return make_response(
            render_template(
                "analysis.html",
                results=results,
                queued_msg="Request queued: Recompute Analytics.",
                title=APP_TITLE,
            ),
            202,
        )

    @flask_app.get("/healthz")
    def healthz():
        return {"ok": True}, 200

    return flask_app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
