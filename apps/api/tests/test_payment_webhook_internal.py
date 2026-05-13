from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models.product_item import ProductItem
from app.models.shop_order import ShopOrder
from app.models.user import User


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def _register(client: TestClient, email: str) -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123!", "full_name": "Test User"},
    )
    assert response.status_code == 201


def _login(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123!"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _set_role(email: str, role: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()


def test_internal_payment_webhook_requires_token() -> None:
    client = TestClient(app)
    response = client.post(
        "/shop/internal/payments/stripe/event",
        json={
            "event_id": f"evt_{uuid4().hex}",
            "event_type": "checkout.session.completed",
            "order_id": 1,
            "payment_status": "paid",
        },
    )
    assert response.status_code == 401


def test_internal_payment_webhook_processes_and_is_idempotent() -> None:
    client = TestClient(app)
    settings = get_settings()

    staff_email = _unique_email("staff-int-pay")
    customer_email = _unique_email("customer-int-pay")
    _register(client, staff_email)
    _register(client, customer_email)
    _set_role(staff_email, "staff")

    staff_token = _login(client, staff_email)
    customer_token = _login(client, customer_email)

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Webhook Product",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "online",
            "price_cents": 1800,
            "stock_quantity": 7,
        },
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    client.post("/shop/cart", headers={"Authorization": f"Bearer {customer_token}"}, json={})
    add_line = client.post(
        "/shop/cart/lines",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"product_item_id": product_id, "quantity": 2},
    )
    assert add_line.status_code == 200
    order_id = add_line.json()["order"]["id"]
    total_cents = add_line.json()["order"]["total_cents"]

    event_id = f"evt_{uuid4().hex}"
    payload = {
        "event_id": event_id,
        "event_type": "checkout.session.completed",
        "order_id": order_id,
        "payment_status": "paid",
        "provider_payment_reference": f"pi_{uuid4().hex}",
        "amount_total_cents": total_cents,
    }
    first = client.post(
        "/shop/internal/payments/stripe/event",
        json=payload,
        headers={"X-Webhook-Token": settings.payment_webhook_token},
    )
    assert first.status_code == 200
    assert first.json()["result"] == "processed"

    second = client.post(
        "/shop/internal/payments/stripe/event",
        json=payload,
        headers={"X-Webhook-Token": settings.payment_webhook_token},
    )
    assert second.status_code == 200
    assert second.json()["result"] == "duplicate"

    with SessionLocal() as db:
        order = db.get(ShopOrder, order_id)
        assert order is not None
        assert order.status == "paid"
        assert order.payment_status == "paid"

        product_row = db.get(ProductItem, product_id)
        assert product_row is not None
        assert product_row.stock_quantity == 5


def test_internal_payment_webhook_amount_mismatch_is_rejected() -> None:
    client = TestClient(app)
    settings = get_settings()

    staff_email = _unique_email("staff-int-pay-mm")
    customer_email = _unique_email("customer-int-pay-mm")
    _register(client, staff_email)
    _register(client, customer_email)
    _set_role(staff_email, "staff")

    staff_token = _login(client, staff_email)
    customer_token = _login(client, customer_email)

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Mismatch Product",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "online",
            "price_cents": 1500,
            "stock_quantity": 4,
        },
    )
    product_id = product.json()["id"]

    client.post("/shop/cart", headers={"Authorization": f"Bearer {customer_token}"}, json={})
    add_line = client.post(
        "/shop/cart/lines",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"product_item_id": product_id, "quantity": 1},
    )
    order_id = add_line.json()["order"]["id"]

    response = client.post(
        "/shop/internal/payments/stripe/event",
        json={
            "event_id": f"evt_{uuid4().hex}",
            "event_type": "checkout.session.completed",
            "order_id": order_id,
            "payment_status": "paid",
            "amount_total_cents": 999999,
        },
        headers={"X-Webhook-Token": settings.payment_webhook_token},
    )
    assert response.status_code == 200
    assert response.json()["result"] == "failed"

    with SessionLocal() as db:
        order = db.get(ShopOrder, order_id)
        assert order is not None
        assert order.status == "cart"
        assert order.payment_status == "unpaid"
