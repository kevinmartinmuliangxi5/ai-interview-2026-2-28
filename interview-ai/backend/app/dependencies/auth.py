from __future__ import annotations

import asyncio
from typing import Any

from fastapi import Header, HTTPException, Request


async def get_current_user(
    request: Request,
    authorization: str = Header(...),
) -> dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error_code": "ERR_UNAUTHORIZED"})

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail={"error_code": "ERR_UNAUTHORIZED"})

    supabase = getattr(request.app.state, "supabase", None)
    if supabase is None:
        raise HTTPException(status_code=401, detail={"error_code": "ERR_UNAUTHORIZED"})

    try:
        async with asyncio.timeout(3.0):
            user_response = await supabase.auth.get_user(token)
        if getattr(user_response, "user", None) is None:
            raise HTTPException(status_code=401, detail={"error_code": "ERR_UNAUTHORIZED"})
        return {"id": str(user_response.user.id), "email": user_response.user.email}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail={"error_code": "ERR_UNAUTHORIZED"}) from exc

