from datetime import datetime, timedelta, timezone
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


def _set_role(email: str, role: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()


def test_gift_voucher_amount_create_redeem_and_cancel_rules() -> None:
    client = TestClient(app)

    staff_email = _unique_email("staff-gift")
    manager_email = _unique_email("manager-gift")
    _register(client, staff_email)
    _register(client, manager_email)
    _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    create = client.post(
        "/gifts/vouchers",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "voucher_type": "amount",
            "amount_cents": 10000,
            "purchaser_name": "Alice",
            "recipient_name": "Bob",
            "recipient_email": "bob@example.com",
            "effective_date": datetime.now(timezone.utc).date().isoformat(),
            "duration_days": 365,
        },
    )
    assert create.status_code == 201
    voucher = create.json()
    voucher_id = voucher["id"]
    assert voucher["remaining_amount_cents"] == 10000

    redeem1 = client.post(
        f"/gifts/vouchers/{voucher_id}/redeem",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"amount_cents": 3000, "notes": "Used for haircut"},
    )
    assert redeem1.status_code == 200
    assert redeem1.json()["voucher"]["remaining_amount_cents"] == 7000

    redeem2 = client.post(
        f"/gifts/vouchers/{voucher_id}/redeem",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"amount_cents": 7000, "notes": "Final usage"},
    )
    assert redeem2.status_code == 200
    assert redeem2.json()["voucher"]["status"] == "redeemed"

    cancel_redeemed = client.post(
        f"/gifts/vouchers/{voucher_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert cancel_redeemed.status_code == 422


def test_gift_voucher_service_requires_service_offering() -> None:
    client = TestClient(app)

    staff_email = _unique_email("staff-gift2")
    _register(client, staff_email)
    _set_role(staff_email, "staff")
    staff_token = _login_token(client, staff_email)

    missing_service = client.post(
        "/gifts/vouchers",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "voucher_type": "service",
            "purchaser_name": "Alice",
            "recipient_name": "Bob",
            "effective_date": datetime.now(timezone.utc).date().isoformat(),
            "duration_days": 365,
        },
    )
    assert missing_service.status_code == 422

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Coloring", "description": "Color", "duration_minutes": 60, "price_cents": 8000},
    )
    assert service.status_code == 201
    service_id = service.json()["id"]

    ok_service_voucher = client.post(
        "/gifts/vouchers",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "voucher_type": "service",
            "service_offering_id": service_id,
            "purchaser_name": "Alice",
            "recipient_name": "Bob",
            "effective_date": datetime.now(timezone.utc).date().isoformat(),
            "duration_days": 365,
        },
    )
    assert ok_service_voucher.status_code == 201
    assert ok_service_voucher.json()["initial_amount_cents"] == 8000


def test_gift_voucher_expired_cannot_be_redeemed() -> None:
    client = TestClient(app)

    manager_email = _unique_email("manager-gift3")
    _register(client, manager_email)
    _set_role(manager_email, "manager")
    manager_token = _login_token(client, manager_email)

    past_date = (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
    create = client.post(
        "/gifts/vouchers",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "voucher_type": "amount",
            "amount_cents": 5000,
            "purchaser_name": "Alice",
            "recipient_name": "Bob",
            "effective_date": past_date,
            "duration_days": 1,
        },
    )
    assert create.status_code == 201
    voucher_id = create.json()["id"]

    redeem = client.post(
        f"/gifts/vouchers/{voucher_id}/redeem",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"amount_cents": 1000},
    )
    assert redeem.status_code == 422

    get_expired = client.get(
        f"/gifts/vouchers?code={create.json()['code']}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert get_expired.status_code == 200
    assert len(get_expired.json()) == 1
