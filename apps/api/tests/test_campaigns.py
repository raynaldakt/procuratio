from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def _register(client: TestClient, email: str, password: str = "StrongPass123!") -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201


def _login_token(client: TestClient, email: str, password: str = "StrongPass123!") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _set_role(email: str, role: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()
        return user.id


def _user_id(email: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return user.id


def test_campaign_email_opt_in_and_notification_status_update() -> None:
    client = TestClient(app)

    manager_email = _unique_email("manager-campaign")
    cust1_email = _unique_email("cust-c1")
    cust2_email = _unique_email("cust-c2")

    _register(client, manager_email)
    _register(client, cust1_email)
    _register(client, cust2_email)

    _set_role(manager_email, "manager")
    manager_token = _login_token(client, manager_email)
    c1_token = _login_token(client, cust1_email)
    c2_token = _login_token(client, cust2_email)

    client.patch(
        "/customers/me/profile",
        headers={"Authorization": f"Bearer {c1_token}"},
        json={"marketing_email_opt_in": True},
    )
    client.patch(
        "/customers/me/profile",
        headers={"Authorization": f"Bearer {c2_token}"},
        json={"marketing_email_opt_in": False},
    )

    send = client.post(
        "/campaigns/send",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "Mother Day Offer",
            "channel": "email",
            "target_mode": "email_opt_in",
            "subject": "Special Offer",
            "message": "Enjoy 20% off this week.",
        },
    )
    assert send.status_code == 201
    assert send.json()["queued_notifications"] >= 1

    queued = client.get(
        "/campaigns/notifications?status=pending",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert queued.status_code == 200
    rows = queued.json()
    assert len(rows) >= 1

    one = rows[0]
    mark = client.post(
        f"/campaigns/notifications/{one['id']}/status",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"status": "sent"},
    )
    assert mark.status_code == 200
    assert mark.json()["status"] == "sent"


def test_campaign_birthday_and_min_points_targeting() -> None:
    client = TestClient(app)

    manager_email = _unique_email("manager-target")
    cust_bday = _unique_email("cust-bday")
    cust_other = _unique_email("cust-other")

    _register(client, manager_email)
    _register(client, cust_bday)
    _register(client, cust_other)

    _set_role(manager_email, "manager")
    manager_token = _login_token(client, manager_email)
    bday_token = _login_token(client, cust_bday)
    other_token = _login_token(client, cust_other)

    today = datetime.now(timezone.utc).date()

    client.patch(
        "/customers/me/profile",
        headers={"Authorization": f"Bearer {bday_token}"},
        json={
            "birthdate": today.isoformat(),
            "marketing_email_opt_in": True,
            "marketing_sms_opt_in": True,
        },
    )
    client.patch(
        "/customers/me/profile",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "birthdate": "1990-01-01",
            "marketing_email_opt_in": True,
            "marketing_sms_opt_in": True,
        },
    )

    bday_id = _user_id(cust_bday)
    other_id = _user_id(cust_other)

    grant_points = client.post(
        "/loyalty/adjust-points",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"user_id": bday_id, "points_delta": 120, "description": "VIP bonus"},
    )
    assert grant_points.status_code == 200

    min_points_campaign = client.post(
        "/campaigns/send",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "name": "VIP campaign",
            "channel": "sms",
            "target_mode": "min_points",
            "min_points": 100,
            "message": "VIP private offer",
        },
    )
    # In CI/dev default, Twilio is not configured, SMS campaigns are rejected.
    assert min_points_campaign.status_code == 422

    birthday_campaign = client.post(
        "/campaigns/birthday/send-today",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert birthday_campaign.status_code == 201
    # Falls back to email-only when Twilio is not configured.
    assert birthday_campaign.json()["queued_notifications"] >= 1

    all_campaigns = client.get("/campaigns/", headers={"Authorization": f"Bearer {manager_token}"})
    assert all_campaigns.status_code == 200
    names = [row["name"] for row in all_campaigns.json()]
    assert any("VIP" in name for name in names)
    assert any("Birthday" in name for name in names)

    _ = other_id
