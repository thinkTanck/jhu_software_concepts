"""
test_flask_page.py

Flask App & Page Rendering tests.

Verifies:
- App factory creates a testable Flask app with required routes
- GET /analysis returns 200
- HTML contains both buttons ("Pull Data", "Update Analysis")
- Page includes "Analysis" and at least one "Answer:"

All tests are marked ``web``.
"""

import pytest
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# A) Flask App & Page Rendering
# ---------------------------------------------------------------------------

@pytest.mark.web
def test_app_factory_creates_app(app):
    """App factory must return a Flask application object."""
    from flask import Flask
    assert isinstance(app, Flask)


@pytest.mark.web
def test_app_has_analysis_route(app):
    """The app must expose a route at /analysis."""
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/analysis" in rules


@pytest.mark.web
def test_app_has_pull_data_route(app):
    """The app must expose a POST route at /pull-data."""
    rules = {rule.rule: list(rule.methods) for rule in app.url_map.iter_rules()}
    assert "/pull-data" in rules
    assert "POST" in rules["/pull-data"]


@pytest.mark.web
def test_app_has_update_analysis_route(app):
    """The app must expose a POST route at /update-analysis."""
    rules = {rule.rule: list(rule.methods) for rule in app.url_map.iter_rules()}
    assert "/update-analysis" in rules
    assert "POST" in rules["/update-analysis"]


@pytest.mark.web
def test_get_analysis_returns_200(client):
    """GET /analysis must return HTTP 200."""
    resp = client.get("/analysis")
    assert resp.status_code == 200


@pytest.mark.web
def test_get_root_redirects_or_200(client):
    """GET / must return 200 (same view as /analysis)."""
    resp = client.get("/")
    assert resp.status_code == 200


@pytest.mark.web
def test_analysis_page_contains_analysis_heading(client):
    """Response HTML must include the word 'Analysis'."""
    resp = client.get("/analysis")
    text = resp.data.decode()
    assert "Analysis" in text


@pytest.mark.web
def test_analysis_page_contains_pull_data_button(client):
    """Response HTML must include a 'Pull Data' button."""
    resp = client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    buttons = soup.find_all("button")
    texts = [b.get_text(strip=True) for b in buttons]
    assert any("Pull Data" in t for t in texts), f"No 'Pull Data' button found. Buttons: {texts}"


@pytest.mark.web
def test_analysis_page_contains_update_analysis_button(client):
    """Response HTML must include an 'Update Analysis' button."""
    resp = client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    buttons = soup.find_all("button")
    texts = [b.get_text(strip=True) for b in buttons]
    assert any("Update Analysis" in t for t in texts), f"No 'Update Analysis' button found. Buttons: {texts}"


@pytest.mark.web
def test_analysis_page_contains_answer_label(client):
    """Response HTML must contain at least one 'Answer:' label."""
    resp = client.get("/analysis")
    text = resp.data.decode()
    assert "Answer:" in text


@pytest.mark.web
def test_pull_data_btn_has_testid(client):
    """Pull Data button must have data-testid='pull-data-btn'."""
    resp = client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    btn = soup.find("button", attrs={"data-testid": "pull-data-btn"})
    assert btn is not None, "No element with data-testid='pull-data-btn' found"


@pytest.mark.web
def test_update_analysis_btn_has_testid(client):
    """Update Analysis button must have data-testid='update-analysis-btn'."""
    resp = client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    btn = soup.find("button", attrs={"data-testid": "update-analysis-btn"})
    assert btn is not None, "No element with data-testid='update-analysis-btn' found"


@pytest.mark.web
def test_no_db_connection_at_import():
    """
    Importing create_app must not attempt a DB connection.

    This ensures the app factory pattern avoids side-effects at import time.
    We verify by creating an app with an invalid DATABASE_URL and confirming
    that the import itself succeeds (the error only occurs on first request).
    """
    from src.app import create_app as _factory
    # A deliberately invalid URL — should NOT raise at factory call time
    bad_app = _factory({"DATABASE_URL": "postgresql://invalid:1/nodb", "TESTING": True})
    assert bad_app is not None


@pytest.mark.web
def test_create_app_with_object_config():
    """create_app must handle a non-dict config object (from_object path)."""
    from src.app import create_app as _factory

    class Cfg:
        TESTING = True
        DATABASE_URL = "postgresql://localhost/test"
        QUERY_FN = staticmethod(lambda: {
            "q1": 0, "q2": None, "q3": (None, None, None, None),
            "q4": None, "q5": None, "q6": None,
            "q7": 0, "q8": 0, "q9": 0,
            "extra_1": [], "extra_2": None,
        })

    app = _factory(Cfg())
    assert app is not None
    assert app.config["TESTING"] is True


@pytest.mark.web
def test_default_loader_is_callable():
    """The default LOADER_FN must be the _default_loader function."""
    from src.app import create_app as _factory, _default_loader
    app = _factory({"TESTING": True, "QUERY_FN": lambda: {}})
    assert app.config["LOADER_FN"] is _default_loader


@pytest.mark.web
def test_default_scraper_is_callable():
    """The default SCRAPER_FN must be the _default_scraper function."""
    from src.app import create_app as _factory, _default_scraper
    app = _factory({"TESTING": True, "QUERY_FN": lambda: {}})
    assert app.config["SCRAPER_FN"] is _default_scraper


@pytest.mark.web
def test_default_query_fn_is_callable():
    """The default QUERY_FN must be _default_query_all."""
    from src.app import create_app as _factory, _default_query_all
    app = _factory()
    assert app.config["QUERY_FN"] is _default_query_all


@pytest.mark.web
def test_default_loader_delegates_to_load_data(db_transaction):
    """_default_loader must call load_data.load_rows with the provided conn."""
    from src.app import _default_loader
    from src import load_data as ld
    from tests.conftest import FAKE_ROWS

    # _default_loader(rows, conn) should not raise for valid rows+conn
    _default_loader(FAKE_ROWS, db_transaction)
    with db_transaction.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applicants")
        count = cur.fetchone()[0]
    assert count == len(FAKE_ROWS)


@pytest.mark.web
def test_default_query_fn_delegates_to_query_data(db_transaction):
    """_default_query_all must call query_data.query_all with the provided conn."""
    from src.app import _default_query_all
    from src import load_data as ld
    from tests.conftest import FAKE_ROWS

    ld.load_rows(FAKE_ROWS, db_transaction)
    result = _default_query_all(db_transaction)
    assert isinstance(result, dict)
    assert "q1" in result


@pytest.mark.web
def test_busy_state_visible_on_page(app):
    """When busy, GET /analysis must show busy=True in the template."""
    app.config["BUSY_GETTER"] = lambda: True
    client = app.test_client()
    resp = client.get("/analysis")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "pull in progress" in text.lower() or "busy" in text.lower() or "unavailable" in text.lower()


@pytest.mark.web
def test_scrape_status_module_importable():
    """scrape_status module must be importable and expose scrape_running."""
    from src import scrape_status
    assert hasattr(scrape_status, "scrape_running")
    assert scrape_status.scrape_running is False


@pytest.mark.web
def test_default_scraper_loads_scrape_py(monkeypatch, tmp_path):
    """
    _default_scraper must dynamically load module_2/scrape.py and call
    its scrape() function.  We patch pathlib.Path inside src.app to redirect
    to a fake scrape.py so no real network call is made.
    """
    import pathlib as _pathlib
    import src.app as app_mod

    # Create a minimal fake scrape.py
    fake_scrape_py = tmp_path / "scrape.py"
    fake_scrape_py.write_text("def scrape(): return [{'test': True}]\n")

    _real_Path = _pathlib.Path

    class _PatchedPath(_real_Path):
        # Override division to intercept the module_2/scrape.py chain
        def __truediv__(self, other):
            result = super().__truediv__(other)
            if result.name == "scrape.py":
                return _real_Path(str(fake_scrape_py))
            return result

    # Monkey-patch pathlib.Path used inside src.app._default_scraper
    import pathlib as pathlib_mod
    monkeypatch.setattr(pathlib_mod, "Path", _PatchedPath)

    rows = app_mod._default_scraper()
    assert rows == [{"test": True}]
