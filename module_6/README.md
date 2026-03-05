
# Module 6 — Deploy Anywhere

GradCafe Admissions Analysis application containerized with Docker Compose and published to Docker Hub.

---

## Services

| Service | Image | Purpose |
|---|---|---|
| db | postgres:16 | PostgreSQL database |
| rabbitmq | rabbitmq:3-management | Message broker |
| db_init | built from src/worker | One-shot loader (exits 0 after seeding) |
| worker | built from src/worker | RabbitMQ consumer / analytics worker |
| web | built from src/web | Flask web application |

---

# Quick Start (Run the Full System)

All commands run from the module_6 directory.

Start the full stack:

docker compose up --build

Open the web app:

http://localhost:8080

RabbitMQ Management UI:

http://localhost:15672

Login:

guest / guest

Stop containers:

docker compose down

Remove containers and database volume:

docker compose down -v

---

# Port Mappings

| URL | Purpose |
|---|---|
| http://localhost:8080 | Web application |
| http://localhost:15672 | RabbitMQ management console |
| localhost:5432 | PostgreSQL (debug only) |

---

# Using the Application

1. Open http://localhost:8080 in a browser.
2. The page shows GradCafe Admissions Analysis with two buttons.

### Button Behavior

| Button | Action | HTTP Response |
|---|---|---|
| Scrape New Data (Queue) | Publishes scrape_new_data task to RabbitMQ | 202 Accepted |
| Recompute Analytics (Queue) | Publishes recompute_analytics task | 202 Accepted |

The Flask web server immediately returns HTTP 202 and queues the task.

The worker container consumes the message and processes it asynchronously.

Refresh the page after a few seconds to see updated results.

---

# Worker Verification

View worker logs:

docker compose logs -f worker

Example output:

[worker] received recompute_analytics
[worker] analytics_cache updated
[worker] acked recompute_analytics

---

# RabbitMQ Management Console

Open:

http://localhost:15672

Login:

guest / guest

Navigate to:

Queues → tasks_q

You can observe:
- queued tasks
- message rates
- acknowledgements from the worker.

---

# Running Tests

Run tests from module_6:

py -m pytest tests/ -q

Run with coverage:

py -m pytest tests/ --cov=src --cov-report=term-missing

---

# Linting

Run pylint:

py -m pylint src/

Target score:

10.00 / 10

---

# DockerHub Images

Public repository:

https://hub.docker.com/r/thinktanck/module_6

Published images:

thinktanck/module_6:web-v1
thinktanck/module_6:worker-v1

Build and push:

docker build -t thinktanck/module_6:web-v1 ./src/web
docker build -t thinktanck/module_6:worker-v1 ./src/worker

docker push thinktanck/module_6:web-v1
docker push thinktanck/module_6:worker-v1

---

# Evidence for Assignment Submission

The following evidence screenshots are included in:

module_6/evidence.pdf

Screenshots include:
- running website
- Docker containers running
- RabbitMQ management console
- DockerHub web image tag
- DockerHub worker image tag

---

# Project Structure

module_6/
├── docker-compose.yml
├── README.md
├── requirements.txt
├── pytest.ini
├── evidence.pdf
├── src/
│   ├── web/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   ├── publisher.py
│   │   ├── run.py
│   │   └── templates/
│   │       └── analysis.html
│   ├── worker/
│   │   ├── Dockerfile
│   │   ├── consumer.py
│   │   └── etl/
│   │       └── query_data.py
│   ├── db/
│   │   └── load_data.py
│   └── data/
│       └── applicant_data.json
├── tests/
│   ├── conftest.py
│   ├── test_web_app.py
│   ├── test_publisher.py
│   ├── test_consumer.py
│   ├── test_load_data.py
│   └── test_query_data.py

---

# Submission Checklist

Before submitting:

✔ Docker images pushed to DockerHub
✔ docker compose up runs successfully
✔ RabbitMQ queue working
✔ Worker processing tasks
✔ Evidence screenshots included in evidence.pdf
✔ Code pushed to GitHub
✔ module_6 folder zipped and uploaded to Canvas
