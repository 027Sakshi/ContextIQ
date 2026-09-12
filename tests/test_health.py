from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert payload["database"] in {"healthy", "unhealthy"}


def test_protected_endpoint_requires_user_context():
    with TestClient(app) as client:
        response = client.get("/emails/")

    assert response.status_code == 401
