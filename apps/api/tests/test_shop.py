from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.product_item import ProductItem
from app.models.product_reservation import ProductReservation
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


def test_shop_purchase_flow_updates_stock_and_loyalty() -> None:
    client = TestClient(app)

    staff_email = _unique_email("staff-shop")
    customer_email = _unique_email("customer-shop")

    _register(client, staff_email)
    _register(client, customer_email)
    _set_role(staff_email, "staff")

    staff_token = _login(client, staff_email)
    customer_token = _login(client, customer_email)

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Shop Product",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "online",
            "price_cents": 2500,
            "stock_quantity": 10,
        },
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    create_cart = client.post("/shop/cart", headers={"Authorization": f"Bearer {customer_token}"}, json={})
    assert create_cart.status_code == 201

    add_line = client.post(
        "/shop/cart/lines",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"product_item_id": product_id, "quantity": 2},
    )
    assert add_line.status_code == 200

    checkout = client.post(
        "/shop/cart/checkout/purchase",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"payment_method": "card"},
    )
    assert checkout.status_code == 200
    body = checkout.json()
    assert body["order"]["status"] == "paid"
    assert body["loyalty_points_earned"] == 50

    products = client.get("/shop/products", headers={"Authorization": f"Bearer {customer_token}"})
    assert products.status_code == 200
    updated = next(row for row in products.json() if row["id"] == product_id)
    assert updated["stock_quantity"] == 8


def test_shop_reservation_and_sweep_expired_restock() -> None:
    client = TestClient(app)

    staff_email = _unique_email("staff-res")
    customer_email = _unique_email("customer-res")

    _register(client, staff_email)
    _register(client, customer_email)
    _set_role(staff_email, "staff")

    staff_token = _login(client, staff_email)
    customer_token = _login(client, customer_email)

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Reserve Product",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "reserve",
            "price_cents": 1200,
            "stock_quantity": 5,
        },
    )
    product_id = product.json()["id"]

    client.post("/shop/cart", headers={"Authorization": f"Bearer {customer_token}"}, json={})
    client.post(
        "/shop/cart/lines",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"product_item_id": product_id, "quantity": 2},
    )

    reserve = client.post(
        "/shop/cart/checkout/reserve",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"expires_in_hours": 48},
    )
    assert reserve.status_code == 200
    assert reserve.json()["order"]["status"] == "reserved"

    reservations = client.get("/shop/reservations/me", headers={"Authorization": f"Bearer {customer_token}"})
    assert reservations.status_code == 200
    assert len(reservations.json()) >= 1

    # Force expiration in DB, then sweep.
    with SessionLocal() as db:
        row = db.scalar(select(ProductReservation).where(ProductReservation.product_item_id == product_id))
        assert row is not None
        row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        product_before = db.get(ProductItem, product_id)
        assert product_before is not None
        assert product_before.stock_quantity == 3

    sweep = client.post(
        "/shop/reservations/sweep-expired",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert sweep.status_code == 200
    assert sweep.json()["expired_count"] >= 1

    with SessionLocal() as db:
        product_after = db.get(ProductItem, product_id)
        assert product_after is not None
        assert product_after.stock_quantity == 5


def test_shop_checkout_stripe_session_marks_order_pending(monkeypatch) -> None:
    client = TestClient(app)

    staff_email = _unique_email("staff-stripe")
    customer_email = _unique_email("customer-stripe")

    _register(client, staff_email)
    _register(client, customer_email)
    _set_role(staff_email, "staff")

    staff_token = _login(client, staff_email)
    customer_token = _login(client, customer_email)

    product = client.post(
        "/sales/products",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "name": "Stripe Product",
            "brand": "Seanergy",
            "product_type": "care",
            "sku": f"SKU-{uuid4().hex[:8]}",
            "description": "stripe checkout",
            "price_cents": 3200,
            "stock_quantity": 6,
        },
    )
    product_id = product.json()["id"]

    client.post("/shop/cart", headers={"Authorization": f"Bearer {customer_token}"}, json={})
    add_line = client.post(
        "/shop/cart/lines",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"product_item_id": product_id, "quantity": 1},
    )
    assert add_line.status_code == 200

    class DummySettings:
        stripe_secret_key = "sk_test_dummy"
        stripe_checkout_currency = "eur"

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "id": "cs_test_123",
                    "url": "https://checkout.stripe.com/c/pay/cs_test_123",
                }
            ).encode("utf-8")

    monkeypatch.setattr("app.services.shop.get_settings", lambda: DummySettings())
    monkeypatch.setattr("app.services.shop.urlopen", lambda req, timeout=20: DummyResponse())

    response = client.post(
        "/shop/cart/checkout/stripe-session",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "cs_test_123"
    assert body["checkout_url"].startswith("https://checkout.stripe.com/")
    assert body["order"]["status"] == "payment_pending"
    assert body["order"]["payment_status"] == "pending"
