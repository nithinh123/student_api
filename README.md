# Student Management API — Jenkins Pipeline Demo

A minimal Flask REST API with a full 12-stage Jenkins pipeline covering
lint, build, smoke, functional, contract, and performance testing.

---

## Project Structure

```
student_api/
├── app.py                  # Flask API (add / list / delete students)
├── locustfile.py           # Locust performance test
├── Dockerfile              # API image
├── Dockerfile.test         # Test runner image
├── requirements.txt        # API runtime deps
├── requirements-test.txt   # Test deps (pytest, locust, jsonschema …)
├── pytest.ini
├── .flake8
├── Jenkinsfile             # Full 12-stage pipeline
└── tests/
    ├── test_smoke.py       # Stage 6 — health + one transaction
    ├── test_functional.py  # Stage 7 — full CRUD integration tests
    └── test_contract.py    # Stage 8 — JSON schema + SLA assertions
```

---

## API Endpoints

| Method | Path                  | Description             |
|--------|-----------------------|-------------------------|
| GET    | `/health`             | Health check            |
| GET    | `/students`           | List all students       |
| GET    | `/students/<id>`      | Get a single student    |
| POST   | `/students`           | Add a student           |
| DELETE | `/students/<id>`      | Delete a student        |

### POST /students  — Request body

```json
{ "name": "Alice Smith", "grade": "A", "email": "alice@uni.ac.uk" }
```

---

## Run locally (no Docker)

```bash
pip install -r requirements.txt
python app.py
# API available at http://localhost:5000
```

## Run tests locally

```bash
pip install -r requirements-test.txt
# Start the API first (above), then:
API_BASE_URL=http://localhost:5000 pytest tests/ -v
```

## Locust load test

```bash
locust -f locustfile.py --headless \
    --host http://localhost:5000 \
    -u 10 -r 2 -t 30s \
    --csv=reports/locust --html=reports/locust-report.html
```

---

## Jenkins Setup

### Required plugins
- **Pipeline** (built-in)
- **HTML Publisher** — for test report tab
- **AnsiColor** — coloured console output

### Pipeline parameters (with defaults)

| Parameter      | Default | Description                         |
|----------------|---------|-------------------------------------|
| `API_PORT`     | `5000`  | Host port mapped to Flask container |
| `SLA_MS`       | `300`   | Contract test response-time budget  |
| `LOCUST_USERS` | `10`    | Concurrent virtual users            |
| `LOCUST_RATE`  | `2`     | Spawn rate per second               |
| `LOCUST_TIME`  | `30s`   | Load test duration                  |

### Quick start
1. Create a **Pipeline** job in Jenkins
2. Set SCM to your repo, script path = `Jenkinsfile`
3. Click **Build with Parameters**

---

## Pipeline stages at a glance

```
1  Checkout         — git pull, stash source
2  Environment Prep — create roku_net docker network (idempotent)
3  Code Quality     — flake8 + black --check
4  Build Images     — app & test images built in parallel
5  Start API        — docker run + /health polling (60s timeout)
6  Smoke Tests      — 2 tests, <5s
7  Functional Tests — 16 tests, parallel workers (pytest-xdist)
8  Contract Tests   — JSON schema + SLA assertions
10 Performance      — Locust 10u × 30s headless
11 Archive Reports  — JUnit XML + HTML (pytest-html + Locust)
12 Teardown         — ALWAYS runs: stop container, remove images
```
