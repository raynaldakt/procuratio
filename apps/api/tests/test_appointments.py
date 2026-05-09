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
