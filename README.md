# Pelgo Match Pipeline

An asynchronous job processing system designed to evaluate job descriptions against a specific candidate profile. It features a backend API that queues matching tasks and a frontend interface that polls and displays real-time scoring results. This project demonstrates reliable background job processing, deterministic rule-based scoring, and optional AI-driven text insights.

## Running it locally

### Prerequisites
Ensure that Docker and Docker Compose are installed on your machine.

### Setup

```bash
git clone https://github.com/ayuamelia/match-pipeline
cd pelgo-match-pipeline
cp .env.example .env

docker compose up --build --scale worker=2
```

Migrations and seed data run automatically on first boot. Once everything is up:

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

`CANDIDATE_ID` in `.env.example` is already set to the seeded UUID so you don't need to change anything for local dev. If you want richer score explanations, drop an `OPENAI_API_KEY` in `.env` — the system works fine without it and falls back to rule-based text.

---

## Running without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
python scripts/seed.py

# API in one terminal
uvicorn app.main:app --reload --port 8000

# Two workers in separate terminals
celery -A app.worker worker --loglevel=INFO --concurrency=4 -n worker1@%h
celery -A app.worker worker --loglevel=INFO --concurrency=4 -n worker2@%h
```

---

## Tests

```bash
# Backend (needs a running Postgres)
cd backend
export TEST_DATABASE_URL=postgresql+asyncpg://pelgo:pelgo_secret@localhost:5432/pelgo_test
pytest -v

# Frontend
cd frontend
npm install && npm test
```

---

## Architecture

**Why Celery + Redis and not Postgres-based queuing?**

I did consider `SELECT ... FOR UPDATE SKIP LOCKED` on Postgres — it's a valid approach. I went with Celery + Redis because atomic job claiming comes free at the broker level, and `task_acks_late=True` means a worker crash re-queues the task automatically instead of silently dropping it. Less code I have to maintain myself.

`worker_prefetch_multiplier=1` is set intentionally. The default of 4 lets one worker hold multiple tasks while another sits idle. With 1, each worker only holds what it's currently processing.

**Why one worker file instead of a package?**

At this size it would just be indirection for its own sake. The Celery app and the task are tightly coupled anyway.

**Why no separate `match_batches` table?**

A `batch_id` column on `match_jobs` covers everything the frontend actually needs. The client counts completed jobs itself. Adding a separate table would mean an extra join on every list query for a feature the UI already handles fine.

**Why rule-based scoring?**

LLM scores are non-deterministic — the same prompt returns different numbers on different calls. That would make retries feel broken. Numbers come from deterministic rules, LLM is only used optionally for the explanation text. If no API key is set, explanation text falls back to templates.

**Scoring weights**

| Dimension  | Weight | Why |
|-----------|--------|-----|
| Skills     | 50%    | Most objective signal, what recruiters check first |
| Experience | 30%    | Seniority matters but there's room for flexibility |
| Location   | 20%    | Real factor, but relocation and remote work offset it |

**Why async API but sync worker?**

FastAPI shines with async I/O — the async SQLAlchemy engine means the event loop never blocks on DB calls. Celery is synchronous by default and creating a new event loop per task is messy and conflicts with Celery internals. So the worker uses psycopg2 directly. It's a known trade-off, not an oversight.

---

## What I cut

| Feature | Why |
|---------|-----|
| URL scraping | A naive implementation would fail on most real job boards. Shipping something that works 40% of the time is worse than documenting the gap. |
| Admin requeue endpoint | Makes sense in production but needs auth middleware first. Without it, any request could requeue any job. |
| Flower dashboard | The `/metrics` endpoint covers what a reviewer needs. Flower adds infra overhead for not much gain here. |
| Per-user rate limiting | Needs auth to identify the requester. IP-based limiting via `slowapi` is in place as a baseline. |

---

## AI prompts used

I used Claude throughout. A few that shaped the actual decisions:

- *"Two Celery workers need to process jobs concurrently without duplicates. Walk me through task_acks_late and worker_prefetch_multiplier."* — This is where the Celery config came from.
- *"Do I need a separate batches table or can a batch_id column cover it for a polling-heavy read pattern?"* — Settled the schema question.
- *"React hook that polls every 3 seconds and stops when all items hit a terminal state — what are the setInterval pitfalls in useEffect?"* — Shaped the cleanup logic in `usePolling.ts`.

---

## Deploy

I used Railway for the backend (Postgres, Redis, API, and Worker as separate services) and Vercel for the frontend. Both have free tiers that cover this easily.

Set `NEXT_PUBLIC_API_URL` in Vercel's environment variables to point at your Railway API URL and it works.

---

Actual time spent: around 7 hours. Longer than the suggested 4–6 mainly because of Docker and Pydantic Settings config issues that took a while to debug.
