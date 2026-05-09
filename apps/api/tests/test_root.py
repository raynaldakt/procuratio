from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint_returns_status_message() -> None:
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Procuratio API is running"
    assert body["environment"] in {"development", "test", "staging", "production"}
