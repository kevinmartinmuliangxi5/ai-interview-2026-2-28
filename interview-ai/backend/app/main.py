from __future__ import annotations

import os

from fastapi import FastAPI

APP_VERSION = "1.0.0"
DEFAULT_MODEL = "gpt-4o-mini"

app = FastAPI(title="Interview AI Backend", version=APP_VERSION)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
    }

