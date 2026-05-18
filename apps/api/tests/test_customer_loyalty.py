from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


def _unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def _register(client: TestClient, email: str, password: str = "StrongPass123!") -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201


def _login_token(client: TestClient, email: str, password: str = "StrongPass123!") -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _set_role(email: str, role: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()


def test_customer_profile_get_and_patch() -> None:
    client = TestClient(app)
    email = _unique_email("customer")

    _register(client, email)
    token = _login_token(client, email)

    get_response = client.get("/customers/me/profile", headers={"Authorization": f"Bearer {token}"})
    assert get_response.status_code == 200
    assert get_response.json()["user_id"] > 0

    patch_response = client.patch(
        "/customers/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "+33600000000", "marketing_sms_opt_in": True},
    )
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["phone"] == "+33600000000"
    assert body["marketing_sms_opt_in"] is True


def test_staff_can_grant_purchase_points_customer_cannot() -> None:
    client = TestClient(app)
    customer_email = _unique_email("cust")
    staff_email = _unique_email("staff")

    _register(client, customer_email)
    _register(client, staff_email)
    _set_role(staff_email, "staff")

    customer_token = _login_token(client, customer_email)
    staff_token = _login_token(client, staff_email)

    with SessionLocal() as db:
        customer = db.scalar(select(User).where(User.email == customer_email))
        assert customer is not None
        customer_id = customer.id

    forbidden = client.post(
        "/loyalty/earn-purchase",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"user_id": customer_id, "amount_spent_cents": 2500, "description": "POS sale"},
    )
    assert forbidden.status_code == 403

    granted = client.post(
        "/loyalty/earn-purchase",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"user_id": customer_id, "amount_spent_cents": 2500, "description": "POS sale"},
    )
    assert granted.status_code == 200
    assert granted.json()["points_delta"] == 25

    profile = client.get(
        "/customers/me/profile",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["points_balance"] >= 25
    assert profile.json()["total_spent_cents"] >= 2500


def test_loyalty_adjustment_requires_manager_or_admin() -> None:
    client = TestClient(app)
    customer_email = _unique_email("cust2")
    staff_email = _unique_email("staff2")
    manager_email = _unique_email("manager")

    _register(client, customer_email)
    _register(client, staff_email)
    _register(client, manager_email)

    _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    with SessionLocal() as db:
        customer = db.scalar(select(User).where(User.email == customer_email))
        assert customer is not None
        customer_id = customer.id

    denied = client.post(
        "/loyalty/adjust-points",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"user_id": customer_id, "points_delta": 30, "description": "manual fix"},
    )
    assert denied.status_code == 403

    allowed = client.post(
        "/loyalty/adjust-points",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"user_id": customer_id, "points_delta": 30, "description": "manual fix"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["kind"] == "manual_adjustment"

    txns = client.get(
        f"/loyalty/users/{customer_id}/transactions",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert txns.status_code == 200
    assert any(txn["kind"] == "manual_adjustment" for txn in txns.json())


def test_subscription_flow_with_bonus_and_cancellation() -> None:
    client = TestClient(app)
    customer_email = _unique_email("sub-customer")
    staff_email = _unique_email("sub-staff")
    manager_email = _unique_email("sub-manager")

    _register(client, customer_email)
    _register(client, staff_email)
    _register(client, manager_email)
    _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    customer_token = _login_token(client, customer_email)
    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    with SessionLocal() as db:
        customer = db.scalar(select(User).where(User.email == customer_email))
        assert customer is not None
        customer_id = customer.id

    created = client.post(
        "/loyalty/subscriptions",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "user_id": customer_id,
            "plan_name": "Premium 30j",
            "amount_cents": 5900,
            "duration_days": 30,
            "payment_method": "card",
            "bonus_points_granted": 40,
        },
    )
    assert created.status_code == 201
    sub = created.json()
    assert sub["status"] == "active"
    assert sub["bonus_points_granted"] == 40

    my_subs = client.get("/loyalty/me/subscriptions", headers={"Authorization": f"Bearer {customer_token}"})
    assert my_subs.status_code == 200
    assert any(row["id"] == sub["id"] for row in my_subs.json())

    txns = client.get(f"/loyalty/users/{customer_id}/transactions", headers={"Authorization": f"Bearer {manager_token}"})
    assert txns.status_code == 200
    assert any(txn["kind"] == "subscription_bonus" for txn in txns.json())

    denied_cancel = client.post(
        f"/loyalty/subscriptions/{sub['id']}/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert denied_cancel.status_code == 403

    allowed_cancel = client.post(
        f"/loyalty/subscriptions/{sub['id']}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert allowed_cancel.status_code == 200
    assert allowed_cancel.json()["status"] == "cancelled"
