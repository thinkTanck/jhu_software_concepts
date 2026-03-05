"""
test_publisher.py

Unit tests for src/web/publisher.py.
pika is fully mocked — no real RabbitMQ connection is made.
"""

import json
from unittest.mock import MagicMock, call, patch

import pytest

from publisher import publish_task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pika_mocks():
    """
    Return (mock_channel, mock_conn) wired so that:
        pika.BlockingConnection(params).channel() → mock_channel
        pika.BlockingConnection(params)           → mock_conn
    """
    mock_ch = MagicMock()
    mock_conn = MagicMock()
    mock_conn.channel.return_value = mock_ch
    return mock_ch, mock_conn


# ---------------------------------------------------------------------------
# publish_task — core behaviour
# ---------------------------------------------------------------------------

class TestPublishTask:

    def test_body_contains_kind_ts_payload(self):
        """publish_task builds a JSON body with 'kind', 'ts', and 'payload' keys."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties"):
            publish_task("scrape_new_data", payload={"source": "web"})

        mock_ch.basic_publish.assert_called_once()
        kwargs = mock_ch.basic_publish.call_args.kwargs
        body = json.loads(kwargs["body"].decode("utf-8"))

        assert body["kind"] == "scrape_new_data"
        assert body["payload"] == {"source": "web"}
        assert "ts" in body  # ISO-8601 timestamp present

    def test_exchange_and_routing_key(self):
        """basic_publish uses exchange='tasks' and routing_key='tasks'."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties"):
            publish_task("recompute_analytics")

        kwargs = mock_ch.basic_publish.call_args.kwargs
        assert kwargs["exchange"] == "tasks"
        assert kwargs["routing_key"] == "tasks"

    def test_delivery_mode_2(self):
        """BasicProperties is called with delivery_mode=2 (persistent)."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties") as mock_props:
            publish_task("recompute_analytics")

        mock_props.assert_called_once()
        assert mock_props.call_args.kwargs["delivery_mode"] == 2

    def test_conn_closed_in_finally(self):
        """conn.close() is always called (finally block) after publish."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties"):
            publish_task("scrape_new_data")

        mock_conn.close.assert_called_once()

    def test_conn_closed_even_when_publish_raises(self):
        """conn.close() is called even if basic_publish raises (finally)."""
        mock_ch, mock_conn = _make_pika_mocks()
        mock_ch.basic_publish.side_effect = RuntimeError("broker gone")

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties"):
            with pytest.raises(RuntimeError):
                publish_task("scrape_new_data")

        mock_conn.close.assert_called_once()

    def test_none_payload_defaults_to_empty_dict(self):
        """payload=None → body['payload'] is {} (not None)."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties"):
            publish_task("scrape_new_data", payload=None)

        kwargs = mock_ch.basic_publish.call_args.kwargs
        body = json.loads(kwargs["body"].decode("utf-8"))
        assert body["payload"] == {}

    def test_none_headers_defaults_to_empty_dict(self):
        """headers=None → BasicProperties receives headers={}."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties") as mock_props:
            publish_task("scrape_new_data", headers=None)

        assert mock_props.call_args.kwargs["headers"] == {}

    def test_custom_headers_forwarded(self):
        """Explicit headers dict is forwarded to BasicProperties unchanged."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties") as mock_props:
            publish_task("scrape_new_data", headers={"x-source": "test"})

        assert mock_props.call_args.kwargs["headers"] == {"x-source": "test"}

    def test_open_channel_declares_exchange_queue_bind(self):
        """_open_channel() declares exchange, queue, and binding on the channel."""
        mock_ch, mock_conn = _make_pika_mocks()

        with patch("pika.BlockingConnection", return_value=mock_conn), \
                patch("pika.URLParameters"), \
                patch("pika.BasicProperties"):
            publish_task("scrape_new_data")

        mock_ch.exchange_declare.assert_called_once_with(
            exchange="tasks", exchange_type="direct", durable=True
        )
        mock_ch.queue_declare.assert_called_once_with(queue="tasks_q", durable=True)
        mock_ch.queue_bind.assert_called_once_with(
            exchange="tasks", queue="tasks_q", routing_key="tasks"
        )
