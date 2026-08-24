# Multi-Agent System using LangGraph

An asynchronous backend for turning a research prompt into an AI-generated draft. FastAPI accepts the request, Celery executes the long-running work, LangGraph coordinates research and writing agents, and a human approval checkpoint controls publication of the final result.

## Overview

The system is designed for workflows where an LLM should gather context and produce content, but a person must review the draft before completion. PostgreSQL stores the durable task record and audit log; Redis supports queueing, coordination, rate limiting, idempotency, and temporary research workspace data.

```text
User
  |
FastAPI REST / WebSocket API
  |
Celery worker
  |
Redis broker and coordination
  |
LangGraph workflow
  |
Prompt Analyzer -> Research Agent -> Writing Agent
                                      |
                                  Human approval
                                      |
                              PostgreSQL result
```

## Features

- 🚀 Multi-agent orchestration with explicit workflow state
- ⚡ Asynchronous task processing through Celery and Redis
- 🧠 LangGraph interrupt and resume approval flow
- 👤 Human-in-the-loop review before completion
- 🔄 Retries, exponential backoff, jitter, and failure classification
- 🛡️ Circuit breaker, timeouts, idempotency, and rate limiting
- 📊 JSON activity logs and process metrics
- 🐳 Docker Compose deployment for local environments

## Tech Stack

- **Python** is the implementation language.
- **FastAPI** exposes asynchronous task, health, metrics, and WebSocket endpoints.
- **Pydantic** validates request and response payloads.
- **SQLAlchemy** models tasks and manages asynchronous API and synchronous worker database sessions.
- **LangGraph** coordinates prompt analysis, research, writing, interrupt, approval, and finalization nodes.
- **LangChain** provides the chat-model and tool interfaces used by the agents.
- **Groq** is the default LLM provider; an OpenAI provider is also supported through the shared factory.
- **Celery** runs long-lived workflow execution outside the API process and retries transient failures.
- **Redis** is the Celery broker/result backend and stores rate-limit counters, idempotency claims, execution claims, and temporary research workspace data.
- **PostgreSQL** durably stores task status, prompts, results, timestamps, and agent logs.
- **Tenacity** retries research-tool calls with exponential backoff.
- **Docker and Docker Compose** package the API, worker, PostgreSQL, and Redis services with health-gated startup.

## Workflow Lifecycle

```text
Task creation
     |
     v
Prompt analysis -> Topic research -> Draft writing
                                      |
                                      v
                             Awaiting approval
                              /            \
                         Approved       Rejected
                             |              |
                         Completed       Failed
```

The initial Celery task pauses at LangGraph's approval interrupt. The approval endpoint queues a second Celery task that resumes the same workflow thread with the review decision and optional feedback.

## Reliability Engineering

- **Retry strategy:** Celery retries a workflow up to three times; research tool calls retry up to three times.
- **Backoff and jitter:** worker delays are bounded exponential backoff with random jitter; Tenacity uses exponential waits for tool calls.
- **Retry classification:** configuration, authentication, type, token-limit, and payload errors are treated as permanent; other failures are eligible for retry.
- **Circuit breaker:** LLM calls share a process-local breaker with open and recovery-probe behavior.
- **Timeout protection:** LLM and Celery soft/hard time limits prevent unbounded work.
- **Rate limiting:** task POST requests use a Redis fixed-window counter and return `429` with `Retry-After`.
- **Idempotency:** `Idempotency-Key` claims use Redis `SET NX`; duplicate workflow deliveries use an atomic execution claim.
- **Observability:** agent activity is emitted as JSON logs and counters are available from `/metrics`.

Important limitation: LangGraph currently uses an in-memory checkpointer. PostgreSQL task records survive worker restarts, but an approval interrupt cannot be guaranteed to resume after the worker process that owns the checkpoint is lost. A production deployment should replace this with a shared durable LangGraph checkpointer.

## API Documentation

### `POST /api/v1/tasks`

Creates a task and returns `202 Accepted`.

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: research-001" \
  -d '{"prompt":"Compare Redis and PostgreSQL for caching"}'
```

### `GET /api/v1/tasks/{id}`

Returns task status, result when available, timestamps, and agent logs.

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### `POST /api/v1/tasks/{id}/approve`

Approves or rejects a draft and queues workflow resume.

```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/approve \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: approval-001" \
  -d '{"approved":true,"feedback":"Looks good"}'
```

Operational endpoints are `GET /health`, `GET /metrics`, and `WS /ws/tasks/{id}`.

## Running Locally

1. Copy `.env.example` to `.env`.
2. Set `GROQ_API_KEY` to your own key. Never commit `.env` or real credentials.
3. Start the stack: `docker compose up --build`.
4. Verify the API: `curl http://localhost:8000/health`.
5. Create a task, poll it until `AWAITING_APPROVAL`, then approve or reject it.
6. Retrieve the final record with `GET /api/v1/tasks/{id}`.

The default model is `openai/gpt-oss-120b` through Groq. Docker service URLs use `db` and `redis`. The Compose password defaults are suitable only for local development and must be overridden in any shared environment.

## Project Structure

```text
src/
├── api/       FastAPI application, routes, schemas, and WebSocket handling
├── agents/    Workflow state, prompt analysis, research, writing, and tools
├── database/  SQLAlchemy models, connections, and CRUD operations
├── shared/    LLM provider, Redis client, logging, metrics, and reliability
└── worker/    Celery application and workflow execution tasks
```

## Future Improvements

- Replace `MemorySaver` with a shared durable LangGraph checkpointer.
- Add API authentication and authorization before exposing endpoints beyond a trusted network.
- Export metrics to a multi-process monitoring system such as Prometheus/OpenTelemetry.
- Add automated output evaluation and source-aware web research.
- Parallelize independent topic research and optionally stream progress updates.

## License

MIT License.
