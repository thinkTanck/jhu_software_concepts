"""
test_consumer.py

Unit tests for src/worker/consumer.py.
pika and psycopg are fully mocked — no real connections made.
"""

import json
import runpy
import types
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import consumer
from consumer import (
    _collect_q_functions,
    _db_conn,
    _declare_amqp,
    _json_default,
    _load_etl_modules,
    _log,
    _normalize_results,
    _on_message,
    _parse_message,
    handle_recompute_analytics,
    handle_scrape_new_data,
)

_WORKER_SRC = Path(__file__).resolve().parents[1] / "src" / "worker"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cur_conn_mock(fetchone_result=None):
    """Return (mock_conn, mock_cur) for functions that use conn.cursor() as ctx-mgr."""
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = fetchone_result

    cur_cm = MagicMock()
    cur_cm.__enter__.return_value = mock_cur
    cur_cm.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cur_cm
    return mock_conn, mock_cur


def _db_conn_mock():
    """Return a mock that mimics `with _db_conn() as db: with db.transaction():`."""
    mock_tx = MagicMock()
    mock_tx.__enter__ = MagicMock(return_value=None)
    mock_tx.__exit__ = MagicMock(return_value=False)

    mock_db = MagicMock()
    mock_db.__enter__ = MagicMock(return_value=mock_db)
    mock_db.__exit__ = MagicMock(return_value=False)
    mock_db.transaction.return_value = mock_tx
    return mock_db


# ---------------------------------------------------------------------------
# _log
# ---------------------------------------------------------------------------

def test_log_prints_without_error(capsys):
    _log("hello test")
    captured = capsys.readouterr()
    assert "[worker] hello test" in captured.out


# ---------------------------------------------------------------------------
# _json_default
# ---------------------------------------------------------------------------

def test_json_default_decimal_to_float():
    assert _json_default(Decimal("3.14")) == pytest.approx(3.14)


def test_json_default_fallback_to_str():
    result = _json_default(object())
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _db_conn — covers `return psycopg.connect(os.environ["DATABASE_URL"])`
# ---------------------------------------------------------------------------

def test_db_conn_calls_psycopg_connect():
    with patch("psycopg.connect") as mock_connect:
        _db_conn()
    mock_connect.assert_called_once()


# ---------------------------------------------------------------------------
# _connect_rabbitmq
# ---------------------------------------------------------------------------

def test_connect_rabbitmq_configures_params():
    mock_params = MagicMock()
    with patch("pika.URLParameters", return_value=mock_params) as mock_url_params, \
            patch("pika.BlockingConnection") as mock_bc:
        from consumer import _connect_rabbitmq
        _connect_rabbitmq()
    mock_url_params.assert_called_once()
    assert mock_params.heartbeat == 30
    assert mock_params.blocked_connection_timeout == 30
    mock_bc.assert_called_once_with(mock_params)


# ---------------------------------------------------------------------------
# _declare_amqp
# ---------------------------------------------------------------------------

def test_declare_amqp_declares_exchange_queue_bind_qos():
    mock_ch = MagicMock()
    _declare_amqp(mock_ch)
    mock_ch.exchange_declare.assert_called_once_with(
        exchange="tasks", exchange_type="direct", durable=True
    )
    mock_ch.queue_declare.assert_called_once_with(queue="tasks_q", durable=True)
    mock_ch.queue_bind.assert_called_once_with(
        exchange="tasks", queue="tasks_q", routing_key="tasks"
    )
    mock_ch.basic_qos.assert_called_once_with(prefetch_count=1)


# ---------------------------------------------------------------------------
# _load_etl_modules
# ---------------------------------------------------------------------------

def test_load_etl_modules_loads_valid_py_file(tmp_path):
    """A regular .py file is loaded and its module object is returned."""
    py = tmp_path / "q1_test.py"
    py.write_text("def q1_func(conn): return 42\n", encoding="utf-8")
    mods = _load_etl_modules(tmp_path)
    assert len(mods) == 1
    assert callable(mods[0].q1_func)


def test_load_etl_modules_skips_underscore_files(tmp_path):
    """Files whose names start with _ are skipped."""
    (tmp_path / "_private.py").write_text("X = 1\n", encoding="utf-8")
    assert _load_etl_modules(tmp_path) == []


def test_load_etl_modules_skips_pycache(tmp_path):
    """Files inside __pycache__ are skipped."""
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "cached.py").write_text("X = 1\n", encoding="utf-8")
    assert _load_etl_modules(tmp_path) == []


def test_load_etl_modules_skips_when_spec_is_none(tmp_path):
    """If spec_from_file_location returns None the file is skipped."""
    (tmp_path / "query.py").write_text("X = 1\n", encoding="utf-8")
    with patch("importlib.util.spec_from_file_location", return_value=None):
        assert _load_etl_modules(tmp_path) == []


def test_load_etl_modules_skips_when_loader_is_none(tmp_path):
    """If spec.loader is None the file is skipped."""
    (tmp_path / "query.py").write_text("X = 1\n", encoding="utf-8")
    mock_spec = MagicMock()
    mock_spec.loader = None
    with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
        assert _load_etl_modules(tmp_path) == []


# ---------------------------------------------------------------------------
# _collect_q_functions
# ---------------------------------------------------------------------------

def test_collect_q_functions_finds_q_functions_and_deduplicates():
    """
    Covers: callable check, pattern match/no-match, and duplicate-qn suppression.
    """
    fn1 = lambda c: 1  # noqa: E731
    fn1b = lambda c: 9  # noqa: E731  duplicate q1
    fn5 = lambda c: 5  # noqa: E731

    mod1 = types.SimpleNamespace(q1_fall=fn1, q5_accept=fn5, NOT_A_Q=lambda c: 0)
    mod2 = types.SimpleNamespace(q1_second=fn1b)   # duplicate — should be ignored

    qmap = _collect_q_functions([mod1, mod2])

    assert "q1" in qmap
    assert "q5" in qmap
    assert qmap["q1"] is fn1   # first module wins
    assert "q9" not in qmap


# ---------------------------------------------------------------------------
# _normalize_results
# ---------------------------------------------------------------------------

def test_normalize_results_wraps_scalar_marks_none_keeps_list():
    raw = {
        "q1": 42,             # scalar → [42]
        "q2": None,           # None → ["(no data)"]
        "q3": [1, 2, 3, 4],  # list → unchanged
        "q4": None, "q5": None, "q6": None,
        "q7": 0,              # 0 (falsy but not None) → [0]
        "q8": 0, "q9": 0,
    }
    out = _normalize_results(raw)
    assert out["q1"] == [42]
    assert out["q2"] == ["(no data)"]
    assert out["q3"] == [1, 2, 3, 4]
    assert out["q7"] == [0]


# ---------------------------------------------------------------------------
# handle_scrape_new_data
# ---------------------------------------------------------------------------

def test_handle_scrape_new_data_uses_payload_since():
    """payload['since'] takes priority over DB value."""
    conn, cur = _cur_conn_mock(fetchone_result=("2024-01-01",))
    handle_scrape_new_data(conn, {"source": "web", "since": "2025-06-01"})
    last_call_args = str(cur.execute.call_args_list[-1])
    assert "2025-06-01" in last_call_args


def test_handle_scrape_new_data_falls_back_to_db_last_seen():
    """When no 'since', the DB row value is used."""
    conn, cur = _cur_conn_mock(fetchone_result=("2024-12-01",))
    handle_scrape_new_data(conn, {"source": "web"})
    last_call_args = str(cur.execute.call_args_list[-1])
    assert "2024-12-01" in last_call_args


def test_handle_scrape_new_data_falls_back_to_current_time_when_no_row():
    """When no 'since' and no DB row, current time is used."""
    conn, cur = _cur_conn_mock(fetchone_result=None)
    with patch("time.strftime", return_value="2026-03-01 00:00:00"):
        handle_scrape_new_data(conn, {"source": "web"})
    last_call_args = str(cur.execute.call_args_list[-1])
    assert "2026-03-01" in last_call_args


def test_handle_scrape_new_data_default_source():
    """payload without 'source' defaults to 'web'."""
    conn, cur = _cur_conn_mock(fetchone_result=None)
    with patch("time.strftime", return_value="2026-01-01 00:00:00"):
        handle_scrape_new_data(conn, {})
    select_call = str(cur.execute.call_args_list[0])
    assert "web" in select_call


# ---------------------------------------------------------------------------
# handle_recompute_analytics
# ---------------------------------------------------------------------------

def test_handle_recompute_analytics_missing_etl_writes_cache():
    """All queries missing → '(missing)' entries written to analytics_cache."""
    conn, cur = _cur_conn_mock()
    with patch("consumer._load_etl_modules", return_value=[]), \
            patch("consumer._collect_q_functions", return_value={}):
        handle_recompute_analytics(conn, {})
    cur.execute.assert_called()


def test_handle_recompute_analytics_failing_etl_records_error():
    """ETL function that raises → '(error)' written, remaining queries still run."""
    conn, cur = _cur_conn_mock()
    failing = MagicMock(side_effect=RuntimeError("sql error"))
    inner_db = _db_conn_mock()

    with patch("consumer._load_etl_modules", return_value=[]), \
            patch("consumer._collect_q_functions", return_value={"q1": failing}), \
            patch("consumer._db_conn", return_value=inner_db):
        handle_recompute_analytics(conn, {})
    cur.execute.assert_called()


def test_handle_recompute_analytics_successful_etl():
    """Successful ETL function value is serialised and written to analytics_cache."""
    conn, cur = _cur_conn_mock()
    success_fn = MagicMock(return_value=99)
    inner_db = _db_conn_mock()

    with patch("consumer._load_etl_modules", return_value=[]), \
            patch("consumer._collect_q_functions", return_value={"q1": success_fn}), \
            patch("consumer._db_conn", return_value=inner_db):
        handle_recompute_analytics(conn, {})
    cur.execute.assert_called()


# ---------------------------------------------------------------------------
# _parse_message
# ---------------------------------------------------------------------------

def test_parse_message_valid():
    body = json.dumps({"kind": "scrape_new_data", "payload": {"src": "web"}}).encode()
    kind, payload = _parse_message(body)
    assert kind == "scrape_new_data"
    assert payload == {"src": "web"}


def test_parse_message_missing_kind_raises():
    body = json.dumps({"payload": {}}).encode()
    with pytest.raises(ValueError, match="missing kind"):
        _parse_message(body)


def test_parse_message_payload_not_dict_raises():
    body = json.dumps({"kind": "test", "payload": "not-a-dict"}).encode()
    with pytest.raises(ValueError, match="payload must be an object"):
        _parse_message(body)


# ---------------------------------------------------------------------------
# _on_message
# ---------------------------------------------------------------------------

def _make_body(kind, payload=None):
    return json.dumps({"kind": kind, "payload": payload or {}}).encode()


def test_on_message_success_acks():
    ch = MagicMock()
    method = MagicMock()
    method.delivery_tag = 42
    inner_db = _db_conn_mock()

    mock_handler = MagicMock()
    with patch("consumer._db_conn", return_value=inner_db), \
            patch.object(consumer, "TASKS", {"scrape_new_data": mock_handler}):
        _on_message(ch, method, None, _make_body("scrape_new_data"))

    ch.basic_ack.assert_called_once_with(delivery_tag=42)
    ch.basic_nack.assert_not_called()


def test_on_message_unknown_kind_nacks():
    ch = MagicMock()
    method = MagicMock()
    method.delivery_tag = 7
    _on_message(ch, method, None, _make_body("no_such_kind"))
    ch.basic_nack.assert_called_once_with(delivery_tag=7, requeue=False)
    ch.basic_ack.assert_not_called()


def test_on_message_handler_exception_nacks():
    ch = MagicMock()
    method = MagicMock()
    method.delivery_tag = 3
    inner_db = _db_conn_mock()
    failing = MagicMock(side_effect=RuntimeError("boom"))

    with patch("consumer._db_conn", return_value=inner_db), \
            patch.object(consumer, "TASKS", {"scrape_new_data": failing}):
        _on_message(ch, method, None, _make_body("scrape_new_data"))

    ch.basic_nack.assert_called_once_with(delivery_tag=3, requeue=False)


def test_on_message_nack_exception_swallowed():
    """If basic_nack itself raises, the inner except silently swallows it."""
    ch = MagicMock()
    ch.basic_nack.side_effect = RuntimeError("channel dead")
    method = MagicMock()
    method.delivery_tag = 1
    # unknown kind triggers nack path; nack raises but must not propagate
    _on_message(ch, method, None, _make_body("unknown_xyz"))
    # reaching here means no exception escaped


# ---------------------------------------------------------------------------
# main() — break loop via mocked time.sleep raising SystemExit
# ---------------------------------------------------------------------------

def test_main_retries_then_exits():
    """
    main() enters while-True, _connect_rabbitmq succeeds, start_consuming raises,
    loop retries, then time.sleep raises SystemExit to stop the test.
    """
    mock_ch = MagicMock()
    mock_ch.start_consuming.side_effect = RuntimeError("connection dropped")
    mock_pika_conn = MagicMock()
    mock_pika_conn.channel.return_value = mock_ch

    sleep_calls = []

    def _mock_sleep(n):
        sleep_calls.append(n)
        raise SystemExit(0)

    with patch("consumer._connect_rabbitmq", return_value=mock_pika_conn), \
            patch("time.sleep", side_effect=_mock_sleep):
        with pytest.raises(SystemExit):
            consumer.main()

    assert sleep_calls == [3]


# ---------------------------------------------------------------------------
# if __name__ == "__main__" — covers the `main()` call line in consumer.py
# ---------------------------------------------------------------------------

def test_consumer_main_guard_covered():
    """runpy executes consumer.py as __main__, covering the guard body line."""
    def _fail_sleep(n):
        raise SystemExit(0)

    with patch("pika.BlockingConnection", side_effect=RuntimeError("no pika")), \
            patch("psycopg.connect"), \
            patch("time.sleep", side_effect=_fail_sleep):
        with pytest.raises(SystemExit):
            runpy.run_path(str(_WORKER_SRC / "consumer.py"), run_name="__main__")
