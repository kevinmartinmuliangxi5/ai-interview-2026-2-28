from fastapi.testclient import TestClient


def test_health_endpoint_returns_expected_payload() -> None:
    from app.main import app

    client = TestClient(app)
    resp = client.get('/api/v1/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok', 'version': '1.0.0', 'model': 'gpt-4o-mini'}
