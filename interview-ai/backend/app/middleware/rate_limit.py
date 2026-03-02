from __future__ import annotations

import base64
import json
from typing import Any

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
except ImportError:  # pragma: no cover
    class Limiter:  # type: ignore[override]
        def __init__(self, key_func: Any) -> None:
            self.key_func = key_func

        def limit(self, _rule: str) -> Any:
            def decorator(func: Any) -> Any:
                return func

            return decorator

    def get_remote_address(request: Any) -> str:
        return getattr(getattr(request, "client", None), "host", "0.0.0.0")


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}


def get_rate_limit_key(request: Any) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return f"anon:{get_remote_address(request)}"

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_jwt_payload(token)
    uid = payload.get("sub") or payload.get("user_id")
    if uid:
        return f"user:{uid}"
    return f"anon:{get_remote_address(request)}"


limiter = Limiter(key_func=get_rate_limit_key)

