# Single Problem Judge

Minimal multi-user single-problem judge with a Streamlit UI, FastAPI backend, Redis queue, SQLite storage, and Docker-based sandbox workers.

## Architecture

- `app/`: FastAPI API and Streamlit UI
- `worker/`: background judge worker
- `sandbox/`: Docker image used to compile and run submissions
- `data/`: SQLite database and runtime artifacts

## Features

- One built-in problem with C and C++17 submissions
- Multi-user submissions through a web page
- Async judging via Redis queue
- Compile error, runtime error, time limit, and wrong answer reporting
- Docker sandbox with no network and resource limits

## Quick Start

1. Install Docker and Docker Compose.
2. From this directory, run:

```bash
docker compose up --build
```

3. Open:

- Streamlit UI: `http://localhost:8501`
- FastAPI docs: `http://localhost:8000/docs`

## Built-in Problem

Given two integers `a` and `b`, output their sum.

Example input:

```text
1 2
```

Example output:

```text
3
```

## Notes

- Supported languages: `C (c11)` and `C++17`.
- The worker compiles and runs submissions inside the `sandbox-runner` image.
- SQLite is used for simplicity; replace it with PostgreSQL for larger deployments.
- This is suitable for a small internal service or class demo, not a public internet OJ.
