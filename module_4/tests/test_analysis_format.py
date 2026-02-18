"""
test_analysis_format.py

Analysis Formatting tests.

Verifies:
- "Answer:" labels exist in the rendered page
- Any percentage rendered uses two decimal places (e.g. 39.28%)
- Uses BeautifulSoup for HTML assertions
- Uses regex for two-decimal percent pattern

All tests are marked ``analysis``.
"""

import re
import pytest
from bs4 import BeautifulSoup
from src.app import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_analysis_app(q2=39.28, q5=55.56, extra_2=39.28):
    """
    Create an app whose QUERY_FN returns controllable percentage values.

    The query function takes zero arguments so no DB connection is needed.
    """

    def fake_query():
        return {
            "q1": 100,
            "q2": q2,
            "q3": (3.75, 320.00, 160.00, 4.50),
            "q4": 3.80,
            "q5": q5,
            "q6": 3.85,
            "q7": 5,
            "q8": 3,
            "q9": 2,
            "extra_1": [("Masters", 3.75), ("PhD", 3.85)],
            "extra_2": extra_2,
        }

    return create_app({
        "TESTING": True,
        "DATABASE_URL": "postgresql://localhost/test",
        "QUERY_FN": fake_query,
    })


# The default ``client`` fixture uses conftest's _fake_query_fn which takes
# ``conn`` as an argument (but the conn fixture is the real DB).
# For analysis-only tests we use our own local client that needs no DB.

@pytest.fixture()
def analysis_client():
    app = _make_analysis_app()
    return app.test_client()


# ---------------------------------------------------------------------------
# C) Analysis Formatting
# ---------------------------------------------------------------------------

@pytest.mark.analysis
def test_answer_labels_exist(analysis_client):
    """The page must contain at least one 'Answer:' label."""
    resp = analysis_client.get("/analysis")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Answer:" in text


@pytest.mark.analysis
def test_multiple_answer_labels(analysis_client):
    """The page must contain multiple 'Answer:' labels (one per question)."""
    resp = analysis_client.get("/analysis")
    text = resp.data.decode()
    count = text.count("Answer:")
    assert count >= 9, f"Expected at least 9 'Answer:' labels, found {count}"


@pytest.mark.analysis
def test_percent_two_decimals_q2():
    """q2 percentage must render with exactly two decimal places."""
    app = _make_analysis_app(q2=39.28)
    client = app.test_client()
    resp = client.get("/analysis")
    text = resp.data.decode()
    assert re.search(r"39\.28%", text), "q2 percentage 39.28% not found in output"


@pytest.mark.analysis
def test_percent_two_decimals_q5():
    """q5 percentage must render with exactly two decimal places."""
    app = _make_analysis_app(q5=55.56)
    client = app.test_client()
    resp = client.get("/analysis")
    text = resp.data.decode()
    assert re.search(r"55\.56%", text), "q5 percentage 55.56% not found in output"


@pytest.mark.analysis
def test_percent_two_decimals_extra2():
    """extra_2 percentage must render with exactly two decimal places."""
    app = _make_analysis_app(extra_2=12.50)
    client = app.test_client()
    resp = client.get("/analysis")
    text = resp.data.decode()
    assert re.search(r"12\.50%", text), "extra_2 percentage 12.50% not found in output"


@pytest.mark.analysis
def test_percent_pattern_regex():
    """All rendered percentages must match the NN.NN% two-decimal pattern."""
    app = _make_analysis_app(q2=39.28, q5=55.56, extra_2=39.28)
    client = app.test_client()
    resp = client.get("/analysis")
    text = resp.data.decode()
    matches = re.findall(r"\d+\.\d{2}%", text)
    assert len(matches) >= 3, f"Expected at least 3 two-decimal percentages, found: {matches}"
    for m in matches:
        assert re.fullmatch(r"\d+\.\d{2}%", m), f"Percentage '{m}' is not in NN.NN% format"


@pytest.mark.analysis
def test_percent_none_renders_na():
    """When percentage value is None, the template must render 'N/A' not an error."""
    app = _make_analysis_app(q2=None, q5=None, extra_2=None)
    client = app.test_client()
    resp = client.get("/analysis")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "N/A" in text


@pytest.mark.analysis
def test_beautifulsoup_answer_divs(analysis_client):
    """Using BeautifulSoup: all .answer divs must contain 'Answer:'."""
    resp = analysis_client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    answer_divs = soup.find_all(class_="answer")
    assert len(answer_divs) >= 9, f"Expected at least 9 .answer divs, found {len(answer_divs)}"
    for div in answer_divs:
        assert "Answer:" in div.get_text(), f"Missing 'Answer:' in div: {div}"


@pytest.mark.analysis
def test_pull_data_button_text_bs(analysis_client):
    """BeautifulSoup: Pull Data button text must be exactly 'Pull Data'."""
    resp = analysis_client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    btn = soup.find("button", attrs={"data-testid": "pull-data-btn"})
    assert btn is not None
    assert "Pull Data" in btn.get_text(strip=True)


@pytest.mark.analysis
def test_update_analysis_button_text_bs(analysis_client):
    """BeautifulSoup: Update Analysis button text must be 'Update Analysis'."""
    resp = analysis_client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    btn = soup.find("button", attrs={"data-testid": "update-analysis-btn"})
    assert btn is not None
    assert "Update Analysis" in btn.get_text(strip=True)


@pytest.mark.analysis
def test_integer_values_render_without_percent(analysis_client):
    """Integer answer values (q1, q7, q8, q9) must not be formatted as %."""
    resp = analysis_client.get("/analysis")
    soup = BeautifulSoup(resp.data, "html.parser")
    answer_divs = soup.find_all(class_="answer")
    texts = [d.get_text() for d in answer_divs]
    # q1 answer is 100 from the fake — should not contain "100%"
    q1_texts = [t for t in texts if "100" in t]
    assert q1_texts, "Could not find q1 answer in page"
    for t in q1_texts:
        # The only numbers formatted as % are q2, q5, extra_2 (39.28, 55.56)
        # 100 should NOT appear as a percentage
        assert "100%" not in t, f"Integer value wrongly formatted as percentage: {t}"
