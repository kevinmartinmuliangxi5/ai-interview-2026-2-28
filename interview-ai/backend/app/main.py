from __future__ import annotations

from contextlib import asynccontextmanager
import os
from collections.abc import AsyncIterator

from fastapi import FastAPI

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


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "model": getattr(app.state, "model", os.getenv("OPENAI_MODEL", DEFAULT_MODEL)),
    }
