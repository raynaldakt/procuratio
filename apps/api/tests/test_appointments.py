from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models.notification_message import NotificationMessage
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


def _next_day_at_utc(hour: int, minute: int = 0) -> datetime:
    now = datetime.now(timezone.utc)
    target = (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target


def test_customer_can_search_and_book_appointment() -> None:
    client = TestClient(app)
    customer_email = _unique_email("cust-book")
    staff_email = _unique_email("staff-book")

    _register(client, customer_email)
    _register(client, staff_email)

    staff_id = _set_role(staff_email, "staff")
    customer_token = _login_token(client, customer_email)
    staff_token = _login_token(client, staff_email)

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Hair Cut", "description": "Classic cut", "duration_minutes": 30, "price_cents": 2500},
    )
    assert service.status_code == 201
    service_id = service.json()["id"]

    profile = client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"is_bookable": True, "workday_start_minute": 540, "workday_end_minute": 1020, "slot_step_minutes": 15},
    )
    assert profile.status_code == 403

    manager_email = _unique_email("manager-book")
    _register(client, manager_email)
    _set_role(manager_email, "manager")
    manager_token = _login_token(client, manager_email)

    profile = client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"is_bookable": True, "workday_start_minute": 540, "workday_end_minute": 1020, "slot_step_minutes": 15},
    )
    assert profile.status_code == 200

    day = _next_day_at_utc(0, 0).date().isoformat()
    slots = client.get(
        f"/appointments/availability?service_offering_id={service_id}&target_date={day}&employee_user_id={staff_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert slots.status_code == 200
    assert len(slots.json()) > 0

    start_at = slots.json()[0]["start_at"]
    booked = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "service_offering_id": service_id,
            "start_at": start_at,
            "employee_user_id": staff_id,
            "notes": "Please be on time",
            "pay_in_store": True,
        },
    )
    assert booked.status_code == 201
    assert booked.json()["status"] == "scheduled"


def test_prevent_overlapping_customer_or_employee_appointments() -> None:
    client = TestClient(app)
    customer_a = _unique_email("cust-a")
    customer_b = _unique_email("cust-b")
    staff_email = _unique_email("staff-overlap")
    manager_email = _unique_email("manager-overlap")

    _register(client, customer_a)
    _register(client, customer_b)
    _register(client, staff_email)
    _register(client, manager_email)

    staff_id = _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    token_a = _login_token(client, customer_a)
    token_b = _login_token(client, customer_b)
    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Color", "description": "Color service", "duration_minutes": 60, "price_cents": 6000},
    )
    service_id = service.json()["id"]

    client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"is_bookable": True, "workday_start_minute": 540, "workday_end_minute": 1080, "slot_step_minutes": 15},
    )

    start = _next_day_at_utc(10, 0).isoformat()

    first = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"service_offering_id": service_id, "start_at": start, "employee_user_id": staff_id},
    )
    assert first.status_code == 201

    overlap_employee = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"service_offering_id": service_id, "start_at": start, "employee_user_id": staff_id},
    )
    assert overlap_employee.status_code == 422

    overlap_customer = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"service_offering_id": service_id, "start_at": start, "employee_user_id": None},
    )
    assert overlap_customer.status_code == 422


def test_cancel_permissions_for_customer_and_staff() -> None:
    client = TestClient(app)
    customer_email = _unique_email("cust-cancel")
    other_customer = _unique_email("cust-other")
    staff_email = _unique_email("staff-cancel")
    manager_email = _unique_email("manager-cancel")

    _register(client, customer_email)
    _register(client, other_customer)
    _register(client, staff_email)
    _register(client, manager_email)

    staff_id = _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    customer_token = _login_token(client, customer_email)
    other_token = _login_token(client, other_customer)
    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Blow Dry", "description": "Drying", "duration_minutes": 30, "price_cents": 3000},
    )
    service_id = service.json()["id"]

    client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"is_bookable": True, "workday_start_minute": 540, "workday_end_minute": 1080, "slot_step_minutes": 15},
    )

    booking = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"service_offering_id": service_id, "start_at": _next_day_at_utc(11, 0).isoformat(), "employee_user_id": staff_id},
    )
    appointment_id = booking.json()["id"]

    forbidden = client.post(
        f"/appointments/{appointment_id}/cancel",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert forbidden.status_code == 403

    allowed = client.post(
        f"/appointments/{appointment_id}/cancel",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["appointment"]["status"] == "cancelled"


def test_appointment_stripe_checkout_session(monkeypatch) -> None:
    client = TestClient(app)
    customer_email = _unique_email("cust-appt-pay")
    staff_email = _unique_email("staff-appt-pay")
    manager_email = _unique_email("manager-appt-pay")

    _register(client, customer_email)
    _register(client, staff_email)
    _register(client, manager_email)

    staff_id = _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    customer_token = _login_token(client, customer_email)
    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Premium Cut", "description": "Cut and care", "duration_minutes": 45, "price_cents": 4800},
    )
    service_id = service.json()["id"]

    client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"is_bookable": True, "workday_start_minute": 540, "workday_end_minute": 1080, "slot_step_minutes": 15},
    )

    slot = _next_day_at_utc(13, 0).isoformat()
    booking = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"service_offering_id": service_id, "start_at": slot, "employee_user_id": staff_id, "pay_in_store": False},
    )
    assert booking.status_code == 201
    appointment_id = booking.json()["id"]

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
                    "id": "cs_test_appt_123",
                    "url": "https://checkout.stripe.com/c/pay/cs_test_appt_123",
                }
            ).encode("utf-8")

    monkeypatch.setattr("app.services.appointments.get_settings", lambda: DummySettings())
    monkeypatch.setattr("app.services.appointments.urlopen", lambda req, timeout=20: DummyResponse())

    checkout = client.post(
        f"/appointments/{appointment_id}/checkout/stripe-session",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"success_url": "https://example.com/success", "cancel_url": "https://example.com/cancel"},
    )
    assert checkout.status_code == 200
    body = checkout.json()
    assert body["session_id"] == "cs_test_appt_123"
    assert body["checkout_url"].startswith("https://checkout.stripe.com/")


def test_internal_appointment_payment_webhook_idempotent() -> None:
    client = TestClient(app)
    settings = get_settings()

    customer_email = _unique_email("cust-appt-webhook")
    staff_email = _unique_email("staff-appt-webhook")
    manager_email = _unique_email("manager-appt-webhook")

    _register(client, customer_email)
    _register(client, staff_email)
    _register(client, manager_email)

    staff_id = _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    customer_token = _login_token(client, customer_email)
    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Care Session", "description": "Hair care", "duration_minutes": 30, "price_cents": 3500},
    )
    service_id = service.json()["id"]

    client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"is_bookable": True, "workday_start_minute": 540, "workday_end_minute": 1080, "slot_step_minutes": 15},
    )

    booking = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "service_offering_id": service_id,
            "start_at": _next_day_at_utc(15, 0).isoformat(),
            "employee_user_id": staff_id,
            "pay_in_store": False,
        },
    )
    assert booking.status_code == 201
    appointment_id = booking.json()["id"]

    event_id = f"evt_{uuid4().hex}"
    payload = {
        "event_id": event_id,
        "event_type": "checkout.session.completed",
        "appointment_id": appointment_id,
        "payment_status": "paid",
        "provider_payment_reference": f"pi_{uuid4().hex}",
        "amount_total_cents": 3500,
    }
    first = client.post(
        "/appointments/internal/payments/stripe/event",
        headers={"X-Webhook-Token": settings.payment_webhook_token},
        json=payload,
    )
    assert first.status_code == 200
    assert first.json()["result"] == "processed"

    second = client.post(
        "/appointments/internal/payments/stripe/event",
        headers={"X-Webhook-Token": settings.payment_webhook_token},
        json=payload,
    )
    assert second.status_code == 200
    assert second.json()["result"] == "duplicate"


def test_booking_queues_automatic_appointment_reminders() -> None:
    client = TestClient(app)
    customer_email = _unique_email("cust-reminder")
    staff_email = _unique_email("staff-reminder")
    manager_email = _unique_email("manager-reminder")

    _register(client, customer_email)
    _register(client, staff_email)
    _register(client, manager_email)

    staff_id = _set_role(staff_email, "staff")
    _set_role(manager_email, "manager")

    customer_token = _login_token(client, customer_email)
    staff_token = _login_token(client, staff_email)
    manager_token = _login_token(client, manager_email)

    service = client.post(
        "/appointments/services",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"name": "Reminder Test Service", "description": "Reminder flow", "duration_minutes": 30, "price_cents": 2100},
    )
    service_id = service.json()["id"]

    client.put(
        f"/appointments/employees/{staff_id}/profile",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"is_bookable": True, "workday_start_minute": 540, "workday_end_minute": 1080, "slot_step_minutes": 15},
    )

    booking = client.post(
        "/appointments/book",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "service_offering_id": service_id,
            "start_at": _next_day_at_utc(16, 0).isoformat(),
            "employee_user_id": staff_id,
            "pay_in_store": True,
        },
    )
    assert booking.status_code == 201
    customer_id = booking.json()["customer_user_id"]

    with SessionLocal() as db:
        stmt = (
            select(NotificationMessage)
            .where(
                NotificationMessage.user_id == customer_id,
                NotificationMessage.kind == "appointment_reminder",
            )
            .order_by(NotificationMessage.created_at.desc())
        )
        rows = list(db.scalars(stmt).all())
        assert len(rows) >= 1
        assert all(row.channel in {"email", "sms"} for row in rows)
