# Multi-Agent System using LangGraph

An asynchronous, production-oriented backend that coordinates research and writing agents through a durable Celery queue and a stateful LangGraph workflow.

## Architecture

```text
Client
  |
FastAPI
  |
Celery -> Redis broker
  |
LangGraph
  |
Research Agent + Writing Agent
  |
Groq LLM (openai/gpt-oss-120b)

PostgreSQL persists task state, logs, and completed results.
```

FastAPI creates tasks and returns immediately. Celery workers execute the workflow asynchronously. LangGraph analyzes the prompt, researches topics, drafts content, interrupts for human approval, and resumes through the same graph after approval or rejection.

## Features

- 🚀 Multi-Agent Workflow
- ⚡ Asynchronous Task Processing
- 🧠 LangGraph Orchestration
- 🔄 Human-in-the-Loop Approval
- 🛡️ Reliability Engineering
- 🔐 Idempotency & Rate Limiting
- 📊 Structured Observability
- 🐳 Docker Deployment

## Tech Stack

- **FastAPI** provides the async REST and WebSocket API.
- **Celery** moves long-running workflow execution out of HTTP requests and supports distributed workers.
- **Redis** provides the Celery broker, result backend, rate-limit counters, idempotency claims, and temporary agent workspace.
- **PostgreSQL** is the durable store for task lifecycle, logs, and results.
- **LangGraph** models explicit agent state, interrupt, approval, rejection, and resume behavior.
- **Groq/LLM** supplies provider-backed analysis, research, and writing through the centralized `get_llm()` factory.
- **Docker Compose** provides reproducible local orchestration with health-gated startup.

## Reliability

The worker classifies failures before retrying. Transient failures use bounded exponential backoff with jitter; configuration and credential errors become `FAILED` without unnecessary retries. Celery time limits protect workers, and an atomic Redis execution claim prevents concurrent duplicate workflow delivery.

LLM calls use configurable timeouts and a circuit breaker with closed, open, and recovery-probe behavior. Redis `SET NX` claims make idempotent task creation concurrency-safe. Task creation is protected by a configurable fixed-window rate limit that returns `429` and `Retry-After` when exceeded.

## API

### Create a task

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: research-001" \
  -d '{"prompt":"Compare Redis and PostgreSQL for caching"}'
```

### Read task status

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### Approve or reject a draft

```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/approve \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: approval-001" \
  -d '{"approved":true,"feedback":"Looks good"}'
```

Additional endpoints are `GET /health`, `GET /metrics`, and `WS /ws/tasks/{task_id}`.

## Setup

1. Copy `.env.example` to `.env`.
2. Add your own Groq API key to `.env`; never add it to Git or `.env.example`.
3. Start the services with `docker compose up --build`.
4. Check `http://localhost:8000/health`.
5. Create a task and note its `task_id`.
6. Poll the task until it reaches `AWAITING_APPROVAL`.
7. Approve or reject the draft.
8. Retrieve the completed result from the task endpoint.

The required model is configured as `LLM_MODEL=openai/gpt-oss-120b`. Database and Redis service URLs use the Docker service names `db` and `redis`.

## Environment Variables

The main variables are `LLM_PROVIDER`, `LLM_MODEL`, `GROQ_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `TASK_RATE_LIMIT_REQUESTS`, `TASK_RATE_LIMIT_WINDOW_SECONDS`, and `TASK_IDEMPOTENCY_TTL_SECONDS`. See `.env.example` for the complete list.

## License

MIT License.
