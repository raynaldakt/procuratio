from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def _register(client: TestClient, email: str) -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123!", "full_name": "Test User"},
    )
    assert response.status_code == 201


def _login_token(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _set_role(email: str, role: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()
        return user.id


def test_stats_overview_and_timeseries() -> None:
    client = TestClient(app)

    manager_email = _unique_email("manager-stats")
    staff_email = _unique_email("staff-stats")
    customer_email = _unique_email("customer-stats")

    _register(client, manager_email)
    _register(client, staff_email)
    _register(client, customer_email)

    _set_role(manager_email, "manager")
    staff_id = _set_role(staff_email, "staff")

    manager_token = _login_token(client, manager_email)
    staff_token = _login_token(client, staff_email)
    customer_token = _login_token(client, customer_email)

    with SessionLocal() as db:
        customer = db.scalar(select(User).where(User.email == customer_email))
        assert customer is not None
        customer_id = customer.id

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Stats Product",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "for stats",
            "price_cents": 2000,
            "stock_quantity": 20,
        },
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Stats Service", "description": "for stats", "duration_minutes": 30, "price_cents": 3000},
    )
    assert service.status_code == 201
    service_id = service.json()["id"]

    set_emp = client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"is_bookable": True, "workday_start_minute": 0, "workday_end_minute": 24 * 60, "slot_step_minutes": 15},
    )
    assert set_emp.status_code == 200

    start_at = datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat()
    book = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"service_offering_id": service_id, "start_at": start_at, "employee_user_id": staff_id},
    )
    assert book.status_code == 201

    ticket = client.post(
        "/sales/tickets",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"notes": "stats ticket"},
    )
    assert ticket.status_code == 201
    ticket_id = ticket.json()["id"]

    set_customer = client.patch(
        f"/sales/tickets/{ticket_id}/customer",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"customer_user_id": customer_id},
    )
    assert set_customer.status_code == 200

    add_product = client.post(
        f"/sales/tickets/{ticket_id}/lines/product",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"product_item_id": product_id, "quantity": 2},
    )
    assert add_product.status_code == 200

    add_service = client.post(
        f"/sales/tickets/{ticket_id}/lines/service",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"service_offering_id": service_id, "quantity": 1},
    )
    assert add_service.status_code == 200

    checkout = client.post(
        f"/sales/tickets/{ticket_id}/checkout",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"payment_method": "card"},
    )
    assert checkout.status_code == 200

    voucher = client.post(
        "/gifts/vouchers",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "voucher_type": "amount",
            "amount_cents": 5000,
            "purchaser_name": "Alice",
            "recipient_name": "Bob",
            "effective_date": datetime.now(timezone.utc).date().isoformat(),
            "duration_days": 365,
        },
    )
    assert voucher.status_code == 201
    voucher_id = voucher.json()["id"]

    redeem = client.post(
        f"/gifts/vouchers/{voucher_id}/redeem",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"amount_cents": 1000},
    )
    assert redeem.status_code == 200

    overview = client.get("/stats/overview?period=month", headers={"Authorization": f"Bearer {manager_token}"})
    assert overview.status_code == 200
    body = overview.json()
    assert body["tickets_paid_count"] >= 1
    assert body["net_revenue_cents"] >= 7000
    assert body["appointments_count"] >= 1
    assert body["gift_vouchers_sold_count"] >= 1
    assert body["gift_vouchers_redeemed_value_cents"] >= 1000
    assert any(item["name"] == "Stats Product" for item in body["top_products"])

    timeseries = client.get("/stats/timeseries?period=month", headers={"Authorization": f"Bearer {manager_token}"})
    assert timeseries.status_code == 200
    ts = timeseries.json()
    assert len(ts["points"]) >= 1
    assert sum(point["revenue_cents"] for point in ts["points"]) >= 7000


def test_stats_requires_staff_or_manager() -> None:
    client = TestClient(app)

    customer_email = _unique_email("cust-stats-deny")
    _register(client, customer_email)
    customer_token = _login_token(client, customer_email)

    denied = client.get("/stats/overview?period=month", headers={"Authorization": f"Bearer {customer_token}"})
    assert denied.status_code == 403
