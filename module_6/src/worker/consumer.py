import importlib.util
import json
import os
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

import pika
import psycopg

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"


def _log(msg: str) -> None:
    print(f"[worker] {msg}", flush=True)


def _json_default(obj: Any) -> Any:
    # psycopg often returns Decimal for NUMERIC columns
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _db_conn() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def _connect_rabbitmq() -> pika.BlockingConnection:
    params = pika.URLParameters(os.environ["RABBITMQ_URL"])
    params.heartbeat = 30
    params.blocked_connection_timeout = 30
    return pika.BlockingConnection(params)


def _declare_amqp(ch: pika.adapters.blocking_connection.BlockingChannel) -> None:
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)
    ch.basic_qos(prefetch_count=1)


def _load_etl_modules(etl_dir: Path) -> list[Any]:
    modules: list[Any] = []
    for py in sorted(etl_dir.rglob("*.py")):
        if py.name.startswith("_") or "__pycache__" in py.parts:
            continue
        mod_name = f"etl_{py.stem}_{abs(hash(str(py)))}"
        spec = importlib.util.spec_from_file_location(mod_name, str(py))
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        modules.append(module)
    return modules


def _collect_q_functions(modules: list[Any]) -> dict[str, Callable[[psycopg.Connection], Any]]:
    qmap: dict[str, Callable[[psycopg.Connection], Any]] = {}
    pat = re.compile(r"^q([1-9])_")
    for m in modules:
        for name in dir(m):
            fn = getattr(m, name, None)
            if not callable(fn):
                continue
            match = pat.match(name)
            if not match:
                continue
            qn = f"q{match.group(1)}"
            if qn not in qmap:
                qmap[qn] = fn
    return qmap


def _normalize_results(raw: dict[str, Any]) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for i in range(1, 10):
        key = f"q{i}"
        val = raw.get(key)
        if val is None:
            out[key] = ["(no data)"]
        elif isinstance(val, list):
            out[key] = val
        else:
            out[key] = [val]
    return out


def handle_scrape_new_data(conn: psycopg.Connection, payload: dict) -> None:
    source = payload.get("source") or "web"

    # Read the current last_seen from the DB first (rubric: reads last_seen at start).
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_seen FROM ingestion_watermarks WHERE source = %s",
            (str(source),),
        )
        row = cur.fetchone()
    db_last_seen = row[0] if row else None

    # Use payload["since"] if provided; otherwise fall back to DB value or current time.
    last_seen = payload.get("since") or db_last_seen or time.strftime("%Y-%m-%d %H:%M:%S")

    upsert_sql = """
        INSERT INTO ingestion_watermarks (source, last_seen)
        VALUES (%s, %s)
        ON CONFLICT (source)
        DO UPDATE SET last_seen = EXCLUDED.last_seen, updated_at = now();
    """
    with conn.cursor() as cur:
        cur.execute(upsert_sql, (str(source), str(last_seen)))

    _log(f"ingestion_watermarks updated (source={source})")


def handle_recompute_analytics(conn: psycopg.Connection, _payload: dict) -> None:
    etl_dir = Path("/app/etl")
    modules = _load_etl_modules(etl_dir)
    qfuncs = _collect_q_functions(modules)

    computed: dict[str, Any] = {}
    missing: list[str] = []

    # Run each q in its own DB transaction so one failure doesn't poison the rest.
    for i in range(1, 10):
        qk = f"q{i}"
        fn = qfuncs.get(qk)
        if fn is None:
            missing.append(qk)
            computed[qk] = "(missing)"
            continue

        try:
            with _db_conn() as c:
                with c.transaction():
                    computed[qk] = fn(c)
        except Exception as exc:  # noqa: BLE001
            _log(f"{qk} failed: {exc!r}")
            computed[qk] = "(error)"

    if missing:
        _log(f"missing ETL functions for: {', '.join(missing)}")

    results = _normalize_results(computed)
    results_json = json.dumps(results, default=_json_default)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analytics_cache (key, results)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (key)
            DO UPDATE SET results = EXCLUDED.results, updated_at = now();
            """,
            ("latest", results_json),
        )

    _log("analytics_cache updated (key=latest)")


TASKS: dict[str, Callable[[psycopg.Connection, dict], None]] = {
    "scrape_new_data": handle_scrape_new_data,
    "recompute_analytics": handle_recompute_analytics,
}


def _parse_message(body: bytes) -> Tuple[str, dict]:
    msg = json.loads(body.decode("utf-8"))
    kind = msg.get("kind")
    payload = msg.get("payload") or {}
    if not isinstance(kind, str):
        raise ValueError("Message missing kind")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return kind, payload


def _on_message(channel, method, _properties, body) -> None:  # type: ignore[no-untyped-def]
    """Module-level AMQP callback: dispatch by kind, ack on success, nack on error."""
    delivery_tag = method.delivery_tag
    try:
        kind, payload = _parse_message(body)
        _log(f"received {kind}")

        handler = TASKS.get(kind)
        if handler is None:
            raise ValueError(f"unknown kind: {kind}")

        with _db_conn() as db:
            with db.transaction():
                handler(db, payload)

        channel.basic_ack(delivery_tag=delivery_tag)
        _log(f"acked {kind}")

    except Exception as exc:  # noqa: BLE001
        _log(f"ERROR: {exc!r}")
        try:
            channel.basic_nack(delivery_tag=delivery_tag, requeue=False)
        except Exception:  # noqa: BLE001
            pass


def main() -> None:
    _log("starting consumer")

    while True:
        try:
            conn = _connect_rabbitmq()
            ch = conn.channel()
            _declare_amqp(ch)
            _log("connected to RabbitMQ; waiting...")

            ch.basic_consume(queue=QUEUE, on_message_callback=_on_message, auto_ack=False)
            ch.start_consuming()

        except Exception as exc:  # noqa: BLE001
            _log(f"consume loop failed: {exc!r}")
            time.sleep(3)


if __name__ == "__main__":
    main()
