"""FastAPI application for the multi-agent system."""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src.database.connection import init_db, close_db
from src.api.routes.tasks import router as tasks_router
from src.api.websocket import websocket_endpoint
from src.shared.metrics import snapshot
from src.shared.reliability import rate_limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path.startswith("/api/v1/tasks"):
            subject = request.client.host if request.client else "unknown"
            try:
                allowed, retry_after = rate_limit(subject)
            except Exception:
                allowed, retry_after = True, 0
            if not allowed:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": os.getenv("TASK_RATE_LIMIT_REQUESTS", "30"),
                        "X-RateLimit-Remaining": "0",
                    },
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    - Initializes database tables on startup
    - Closes database connections on shutdown
    """
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Multi-Agent System API",
    description="API for orchestrating collaborative AI agents using LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(RateLimitMiddleware)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Include routers
app.include_router(tasks_router)


@app.get("/")
async def dashboard() -> FileResponse:
    """Serve the workflow visualization dashboard."""
    return FileResponse(_STATIC_DIR / "dashboard.html")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics() -> dict[str, dict[str, int]]:
    return {"counters": snapshot()}


@app.websocket("/ws/tasks/{task_id}")
async def ws_task_updates(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time task status updates.
    
    Connect to subscribe to updates for a specific task.
    """
    await websocket_endpoint(websocket, task_id)