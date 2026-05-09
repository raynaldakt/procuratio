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


def _get_user_id(email: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return user.id


def test_sales_pos_flow_with_suspend_resume_and_checkout() -> None:
    client = TestClient(app)
    staff_email = _unique_email("staff-sales")
    customer_email = _unique_email("customer-sales")

    _register(client, staff_email)
    _register(client, customer_email)

    _set_role(staff_email, "staff")
    staff_token = _login_token(client, staff_email)
    customer_token = _login_token(client, customer_email)
    customer_id = _get_user_id(customer_email)

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Shampoo Pro",
            "brand": "Seanergy",
            "product_type": "haircare",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "Premium shampoo",
            "price_cents": 1000,
            "stock_quantity": 10,
        },
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Brushing", "description": "Brushing service", "duration_minutes": 30, "price_cents": 1500},
    )
    assert service.status_code == 201
    service_id = service.json()["id"]

    ticket = client.post(
        "/sales/tickets",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"notes": "POS desk 1"},
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

    set_discount = client.patch(
        f"/sales/tickets/{ticket_id}/discount",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"discount_cents": 500},
    )
    assert set_discount.status_code == 200
    assert set_discount.json()["subtotal_cents"] == 3500
    assert set_discount.json()["total_cents"] == 3000

    suspended = client.post(f"/sales/tickets/{ticket_id}/suspend", headers={"Authorization": f"Bearer {staff_token}"})
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    resumed = client.post(f"/sales/tickets/{ticket_id}/resume", headers={"Authorization": f"Bearer {staff_token}"})
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "draft"

    checkout = client.post(
        f"/sales/tickets/{ticket_id}/checkout",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"payment_method": "card"},
    )
    assert checkout.status_code == 200
    body = checkout.json()
    assert body["ticket"]["status"] == "paid"
    assert body["total_cents"] == 3000
    assert body["loyalty_points_earned"] == 30

    products = client.get("/sales/products", headers={"Authorization": f"Bearer {staff_token}"})
    assert products.status_code == 200
    updated = next(row for row in products.json() if row["id"] == product_id)
    assert updated["stock_quantity"] == 8

    profile = client.get("/customers/me/profile", headers={"Authorization": f"Bearer {customer_token}"})
    assert profile.status_code == 200
    assert profile.json()["points_balance"] >= 30
    assert profile.json()["total_spent_cents"] >= 3000


def test_cannot_edit_paid_ticket() -> None:
    client = TestClient(app)
    staff_email = _unique_email("staff-paid")
    _register(client, staff_email)
    _set_role(staff_email, "staff")
    staff_token = _login_token(client, staff_email)

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Mask",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "Hair mask",
            "price_cents": 1200,
            "stock_quantity": 5,
        },
    )
    product_id = product.json()["id"]

    ticket = client.post(
        "/sales/tickets",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"notes": "POS"},
    )
    ticket_id = ticket.json()["id"]

    client.post(
        f"/sales/tickets/{ticket_id}/lines/product",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"product_item_id": product_id, "quantity": 1},
    )

    checkout = client.post(
        f"/sales/tickets/{ticket_id}/checkout",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"payment_method": "cash"},
    )
    assert checkout.status_code == 200

    blocked = client.post(
        f"/sales/tickets/{ticket_id}/lines/product",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"product_item_id": product_id, "quantity": 1},
    )
    assert blocked.status_code == 422
