from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user
from app.main import app



def _override_user() -> dict[str, str]:
    return {'id': 'user-1', 'email': 'user@example.com'}



def test_questions_draw_route_exists_and_returns_count() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    with TestClient(app) as client:
        response = client.get('/api/v1/questions/draw?count=3', headers={'Authorization': 'Bearer token'})
        assert response.status_code == 200
        assert len(response.json()) == 3



def test_questions_get_route_not_found() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    with TestClient(app) as client:
        response = client.get('/api/v1/questions/not-exist', headers={'Authorization': 'Bearer token'})
        assert response.status_code == 404



def test_submit_route_returns_201_with_mocked_pipeline(monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = _override_user

    async def _fake_pipeline(**_kwargs):
        return {'id': 'ev-1', 'final_score': 80.0}

    import app.routers.evaluations as evaluations_router

    monkeypatch.setattr(evaluations_router, 'run_evaluation_pipeline', _fake_pipeline)
    with TestClient(app) as client:
        files = {
            'audio': ('test.webm', b'\x1a\x45\xdf\xa3abc', 'audio/webm'),
        }
        data = {'question_id': '4f3af2b0-9e8f-48fe-8d05-8f52332f1001'}
        response = client.post('/api/v1/evaluations/submit', files=files, data=data, headers={'Authorization': 'Bearer token'})

        assert response.status_code == 201
        assert response.json()['id'] == 'ev-1'


def test_get_evaluation_by_id_returns_record_for_owner() -> None:
    app.dependency_overrides[get_current_user] = _override_user

    with TestClient(app) as client:
        app.state.evaluations = [
            {
                "id": "ev-1",
                "user_id": "user-1",
                "final_score": 86.5,
            }
        ]
        response = client.get("/api/v1/evaluations/ev-1", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json()["id"] == "ev-1"
    assert response.json()["user_id"] == "user-1"


def test_get_evaluation_by_id_returns_404_when_missing() -> None:
    app.dependency_overrides[get_current_user] = _override_user

    with TestClient(app) as client:
        app.state.evaluations = []
        response = client.get("/api/v1/evaluations/not-found", headers={"Authorization": "Bearer token"})

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "ERR_NOT_FOUND"
