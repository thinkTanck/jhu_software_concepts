"""
conftest.py — Module 6 shared fixtures.

No real database or RabbitMQ connections are created here.
All external I/O is mocked inside individual test modules.
"""

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path — expose flat Docker-style imports from every service directory
# Tests can then do:
#   from app      import create_app        (src/web)
#   from publisher import publish_task     (src/web)
#   from consumer  import _on_message      (src/worker)
#   from load_data import main             (src/db)
#   from query_data import ...             (src/worker/etl)
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parent.parent / "src"
for _p in (
    _SRC / "web",
    _SRC / "worker",
    _SRC / "worker" / "etl",
    _SRC / "db",
):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# ---------------------------------------------------------------------------
# Stub environment variables so modules can be imported without real services.
# Individual tests may override with monkeypatch.setenv().
# ---------------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
os.environ.setdefault("RABBITMQ_URL", "amqp://test:test@localhost:5672/")

# ---------------------------------------------------------------------------
# Late import — must come AFTER sys.path is extended above.
# ---------------------------------------------------------------------------
from app import create_app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    """
    Flask application in TESTING mode.

    _fetch_cached_results() catches all DB errors and returns safe defaults,
    so no real DATABASE_URL is required for most route tests.
    """
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):  # pylint: disable=redefined-outer-name
    """Flask test client bound to the test app fixture."""
    return app.test_client()
