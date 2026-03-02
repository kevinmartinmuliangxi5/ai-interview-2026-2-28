from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.dependencies.auth import get_current_user


@pytest.mark.asyncio
async def test_invalid_bearer_header_raises_401() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(supabase=None)))
    with pytest.raises(HTTPException) as exc:
        await get_current_user(request=request, authorization='invalid')
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_supabase_returns_none_user_raises_401() -> None:
    class _Auth:
        async def get_user(self, _token: str) -> SimpleNamespace:
            return SimpleNamespace(user=None)

    supabase = SimpleNamespace(auth=_Auth())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(supabase=supabase)))
    with pytest.raises(HTTPException) as exc:
        await get_current_user(request=request, authorization='Bearer bad.token')
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_token_returns_user_payload() -> None:
    class _User:
        id = 'u-1'
        email = 'u@example.com'

    class _Auth:
        async def get_user(self, _token: str) -> SimpleNamespace:
            return SimpleNamespace(user=_User())

    supabase = SimpleNamespace(auth=_Auth())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(supabase=supabase)))
    user = await get_current_user(request=request, authorization='Bearer good.token')
    assert user['id'] == 'u-1'
    assert user['email'] == 'u@example.com'
