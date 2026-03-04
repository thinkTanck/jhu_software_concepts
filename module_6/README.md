# Module 6 — Deploy Anywhere

GradCafe Admissions Analysis application containerised with Docker Compose and
published to Docker Hub.

---

## Services

| Service | Image | Purpose |
|---|---|---|
| `db` | `postgres:16` | PostgreSQL database |
| `rabbitmq` | `rabbitmq:3-management` | Message broker |
| `db_init` | built from `src/worker` | One-shot loader (exits 0 after seeding) |
| `worker` | built from `src/worker` | RabbitMQ consumer / analytics worker |
| `web` | built from `src/web` | Flask web application |

---

## Port Mappings

| URL | Purpose |
|---|---|
| <http://localhost:8080> | Web application (Q1–Q9 analysis page) |
| <http://localhost:15672> | RabbitMQ Management UI (login: `guest` / `guest`) |
| `localhost:5432` | PostgreSQL (internal use only; exposed for debugging) |

---

## Quick Start

All commands run from the **`module_6/`** directory.

### Build and start the full stack

```powershell
docker compose up --build
```

Services start in dependency order. `db_init` exits once the database is seeded;
`worker` and `web` stay running.

### Start without rebuilding (subsequent runs)

```powershell
docker compose up
```

### Stop and remove containers

```powershell
docker compose down
```

### Stop and remove containers **and** the database volume

```powershell
docker compose down -v
```

### Rebuild a single service

```powershell
docker compose build web
docker compose build worker
```

---

## Using the Application

1. Open <http://localhost:8080> in a browser.
2. The page shows **GradCafe Admissions Analysis (Module 3)** with two action buttons
   and Q1–Q9 answer values.

### Button behaviour (rubric-required)

| Button | Action | HTTP response |
|---|---|---|
| **Scrape New Data (Queue)** | Publishes a `scrape_new_data` task to RabbitMQ | 202 Accepted — queued indication shown immediately |
| **Recompute Analytics (Queue)** | Publishes a `recompute_analytics` task to RabbitMQ | 202 Accepted — queued indication shown immediately |

- The web process returns **202** without waiting for the worker.
- The worker consumes the message, runs the appropriate handler inside a DB
  transaction, commits, and acks the message.
- **Refresh the page** after a few seconds to see updated Q1–Q9 values written by
  the worker.

---

## Verifying the Worker

Watch worker logs while the stack is running:

```powershell
docker compose logs -f worker
```

Expected output after clicking **Recompute Analytics (Queue)**:

```
[worker] received recompute_analytics
[worker] analytics_cache updated (key=latest)
[worker] acked recompute_analytics
```

Expected output after clicking **Scrape New Data (Queue)**:

```
[worker] received scrape_new_data
[worker] ingestion_watermarks updated (source=web)
[worker] acked scrape_new_data
```

---

## RabbitMQ Management UI

Open <http://localhost:15672> and log in with `guest` / `guest`.

- **Queues** tab → `tasks_q` shows message rates and queue depth.
- Exchange `tasks` (direct, durable) routes all tasks via routing key `tasks`.

---

## Running Tests

```powershell
py -m pytest tests/ -q
```

With coverage (run from `module_6/`):

```powershell
py -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## Linting

```powershell
py -m pylint src/
```

Target: **10.00 / 10**.

---

## Docker Hub

Create a PUBLIC Docker Hub repository named exactly `module_6` (underscore required) before pushing images.

Public repository: **<https://hub.docker.com/r/YOURNAME/module_6>**

Images are published as:

```
YOURNAME/module_6:web-v1
YOURNAME/module_6:worker-v1
```

---

## Project Structure

```
module_6/
├── docker-compose.yml
├── README.md
├── setup.py
├── requirements.txt          # host / CI deps (pytest, pylint, etc.)
├── pytest.ini
├── src/
│   ├── web/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app.py            # Flask app factory; reads analytics_cache.results
│   │   ├── publisher.py      # pika publisher (_open_channel, publish_task)
│   │   ├── run.py            # entrypoint (python run.py)
│   │   └── templates/
│   │       └── analysis.html
│   ├── worker/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── consumer.py       # RabbitMQ consumer; routes scrape/recompute tasks
│   │   └── etl/
│   │       └── query_data.py # SQL analytics functions (q1–q9)
│   ├── db/
│   │   └── load_data.py      # Schema creation + JSON loader
│   └── data/
│       └── applicant_data.json
├── tests/
│   ├── conftest.py
│   └── (test_web_app.py, test_publisher.py, test_consumer.py,
│      test_load_data.py, test_query_data.py — added in later steps)
└── docs/
```
