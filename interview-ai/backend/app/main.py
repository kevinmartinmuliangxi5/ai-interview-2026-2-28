from __future__ import annotations

from contextlib import asynccontextmanager
import os
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.middleware.rate_limit import limiter

try:  # Optional at import time when slowapi not installed yet.
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
except ImportError:  # pragma: no cover
    RateLimitExceeded = None  # type: ignore[assignment]
    SlowAPIMiddleware = None  # type: ignore[assignment]

APP_VERSION = "1.0.0"
DEFAULT_MODEL = "gpt-4o-mini"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.supabase = None
    app.state.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if supabase_url and supabase_service_role_key:
        try:
            from supabase import acreate_client

            app.state.supabase = await acreate_client(supabase_url, supabase_service_role_key)
        except Exception:
            app.state.supabase = None

    yield


app = FastAPI(title="Interview AI Backend", version=APP_VERSION, lifespan=lifespan)
app.state.limiter = limiter
if SlowAPIMiddleware is not None:
    app.add_middleware(SlowAPIMiddleware)


if RateLimitExceeded is not None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"error_code": "ERR_RATE_LIMIT_EXCEEDED", "message": "请求过于频繁，请稍后重试。"},
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": "3",
                "X-RateLimit-Remaining": "0",
            },
        )


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "model": getattr(app.state, "model", os.getenv("OPENAI_MODEL", DEFAULT_MODEL)),
    }
