from __future__ import annotations

from types import SimpleNamespace

from app.middleware.rate_limit import get_rate_limit_key



def test_rate_key_from_jwt_sub() -> None:
    # Header: {"alg":"none"}.{"sub":"u-123"}.
    request = SimpleNamespace(headers={
        'Authorization': 'Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJ1LTEyMyJ9.'
    }, client=SimpleNamespace(host='127.0.0.1'))
    assert get_rate_limit_key(request).startswith('user:u-123')



def test_rate_key_fallback_to_ip() -> None:
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host='10.0.0.8'))
    assert get_rate_limit_key(request) == 'anon:10.0.0.8'
