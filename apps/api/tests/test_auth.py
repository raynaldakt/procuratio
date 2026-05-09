from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


def _unique_email() -> str:
    return f"test-{uuid4().hex}@example.com"


def _register(client: TestClient, email: str, password: str = "StrongPass123!"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )


def _login(client: TestClient, email: str, password: str = "StrongPass123!"):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def test_auth_register_login_and_me() -> None:
    client = TestClient(app)
    email = _unique_email()

    register_response = _register(client, email)
    assert register_response.status_code == 201
    assert register_response.json()["email"] == email

    login_response = _login(client, email)
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_register_duplicate_email_returns_conflict() -> None:
    client = TestClient(app)
    email = _unique_email()

    first = _register(client, email)
    second = _register(client, email)

    assert first.status_code == 201
    assert second.status_code == 409


def test_users_list_requires_admin_or_manager() -> None:
    client = TestClient(app)
    email = _unique_email()

    _register(client, email)
    login_response = _login(client, email)
    access_token = login_response.json()["access_token"]

    forbidden_response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert forbidden_response.status_code == 403

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()

    admin_login = _login(client, email)
    admin_access = admin_login.json()["access_token"]

    allowed_response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {admin_access}"},
    )
    assert allowed_response.status_code == 200
    assert any(row["email"] == email for row in allowed_response.json())
