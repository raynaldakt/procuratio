from datetime import date, datetime, time, timedelta, timezone
import json
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models.appointment import Appointment
from app.models.appointment_payment_state import AppointmentPaymentState
from app.models.appointment_payment_webhook_event import AppointmentPaymentWebhookEvent
from app.models.employee_profile import EmployeeProfile
from app.models.service_offering import ServiceOffering
from app.models.user import User
from app.services.auth import ensure_auth_schema

_schema_lock = Lock()
_schema_ready = False
ACTIVE_APPOINTMENT_STATUSES = {"scheduled", "confirmed"}


def ensure_appointments_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    ensure_auth_schema()
    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(
            bind=engine,
            tables=[
                ServiceOffering.__table__,
                EmployeeProfile.__table__,
                Appointment.__table__,
                AppointmentPaymentState.__table__,
                AppointmentPaymentWebhookEvent.__table__,
            ],
            checkfirst=True,
        )
        _schema_ready = True


def list_active_service_offerings(db: Session) -> list[ServiceOffering]:
    ensure_appointments_schema()
    stmt = select(ServiceOffering).where(ServiceOffering.is_active.is_(True)).order_by(ServiceOffering.name.asc())
    return list(db.scalars(stmt).all())


def create_service_offering(
    db: Session,
    name: str,
    description: str | None,
    duration_minutes: int,
    price_cents: int,
) -> ServiceOffering:
    ensure_appointments_schema()
    service = ServiceOffering(
        name=name.strip(),
        description=description,
        duration_minutes=duration_minutes,
        price_cents=price_cents,
        is_active=True,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def set_employee_profile(
    db: Session,
    user_id: int,
    is_bookable: bool,
    workday_start_minute: int,
    workday_end_minute: int,
    slot_step_minutes: int,
) -> EmployeeProfile:
    ensure_appointments_schema()
    user = db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")

    profile = db.get(EmployeeProfile, user_id)
    if profile is None:
        profile = EmployeeProfile(user_id=user_id)
        db.add(profile)

    profile.is_bookable = is_bookable
    profile.workday_start_minute = workday_start_minute
    profile.workday_end_minute = workday_end_minute
    profile.slot_step_minutes = slot_step_minutes
    db.commit()
    db.refresh(profile)
    return profile


def list_bookable_employees(db: Session) -> list[EmployeeProfile]:
    ensure_appointments_schema()
    stmt = (
        select(EmployeeProfile)
        .join(User, User.id == EmployeeProfile.user_id)
        .where(
            EmployeeProfile.is_bookable.is_(True),
            User.is_active.is_(True),
            User.role.in_(["staff", "manager", "admin"]),
        )
        .order_by(EmployeeProfile.user_id.asc())
    )
    return list(db.scalars(stmt).all())


def _validate_datetime(start_at: datetime) -> datetime:
    if start_at.tzinfo is None:
        raise ValueError("start_at must include timezone information")
    return start_at.astimezone(timezone.utc)


def _get_or_create_payment_state(db: Session, appointment_id: int, amount_cents: int) -> AppointmentPaymentState:
    row = db.get(AppointmentPaymentState, appointment_id)
    if row is None:
        row = AppointmentPaymentState(
            appointment_id=appointment_id,
            amount_cents=amount_cents,
            status="unpaid",
        )
        db.add(row)
        db.flush()
        return row

    row.amount_cents = amount_cents
    return row


def _has_overlap(db: Session, user_field, user_id: int, start_at: datetime, end_at: datetime) -> bool:
    stmt = select(Appointment.id).where(
        user_field == user_id,
        Appointment.status.in_(list(ACTIVE_APPOINTMENT_STATUSES)),
        and_(Appointment.start_at < end_at, Appointment.end_at > start_at),
    )
    return db.scalar(stmt) is not None


def create_appointment(
    db: Session,
    customer_user_id: int,
    service_offering_id: int,
    start_at: datetime,
    employee_user_id: int | None,
    notes: str | None,
    pay_in_store: bool,
    created_by_user_id: int,
) -> Appointment:
    ensure_appointments_schema()

    customer = db.get(User, customer_user_id)
    if customer is None or not customer.is_active:
        raise ValueError("Customer not found")

    service = db.get(ServiceOffering, service_offering_id)
    if service is None or not service.is_active:
        raise ValueError("Service offering not found")

    start_utc = _validate_datetime(start_at)
    end_utc = start_utc + timedelta(minutes=service.duration_minutes)

    if _has_overlap(db, Appointment.customer_user_id, customer_user_id, start_utc, end_utc):
        raise ValueError("Customer already has an overlapping appointment")

    if employee_user_id is not None:
        employee = db.get(User, employee_user_id)
        profile = db.get(EmployeeProfile, employee_user_id)
        if employee is None or not employee.is_active:
            raise ValueError("Employee not found")
        if profile is None or not profile.is_bookable:
            raise ValueError("Employee is not bookable")

        if _has_overlap(db, Appointment.employee_user_id, employee_user_id, start_utc, end_utc):
            raise ValueError("Employee already has an overlapping appointment")

    appt = Appointment(
        customer_user_id=customer_user_id,
        employee_user_id=employee_user_id,
        service_offering_id=service_offering_id,
        start_at=start_utc,
        end_at=end_utc,
        status="scheduled",
        notes=notes,
        pay_in_store=pay_in_store,
        created_by_user_id=created_by_user_id,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def create_appointment_stripe_checkout_session(
    db: Session,
    *,
    appointment_id: int,
    customer_user_id: int,
    success_url: str,
    cancel_url: str,
) -> tuple[Appointment, str, str]:
    ensure_appointments_schema()
    settings = get_settings()

    if not settings.stripe_secret_key:
        raise ValueError("Stripe is not configured (missing STRIPE_SECRET_KEY)")

    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise ValueError("Appointment not found")
    if appt.customer_user_id != customer_user_id:
        raise ValueError("Appointment not found")
    if appt.status in {"cancelled", "completed", "no_show"}:
        raise ValueError("Appointment is not payable")

    service = db.get(ServiceOffering, appt.service_offering_id)
    if service is None or not service.is_active:
        raise ValueError("Service offering not found")

    payment_state = _get_or_create_payment_state(db, appointment_id=appt.id, amount_cents=service.price_cents)
    if payment_state.status == "paid":
        raise ValueError("Appointment is already paid")

    form: list[tuple[str, str]] = [
        ("mode", "payment"),
        ("success_url", success_url),
        ("cancel_url", cancel_url),
        ("client_reference_id", f"appointment:{appt.id}"),
        ("metadata[appointment_id]", str(appt.id)),
        ("metadata[payment_target]", "appointment"),
        ("payment_intent_data[metadata][appointment_id]", str(appt.id)),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", settings.stripe_checkout_currency),
        ("line_items[0][price_data][unit_amount]", str(service.price_cents)),
        ("line_items[0][price_data][product_data][name]", service.name),
        (
            "line_items[0][price_data][product_data][description]",
            (service.description or "Appointment service")[:250],
        ),
    ]

    body = urlencode(form).encode("utf-8")
    req = Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.stripe_secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Stripe session creation failed ({exc.code}): {detail[:250]}") from exc
    except URLError as exc:
        raise ValueError(f"Stripe session request failed: {exc.reason}") from exc

    session_id = payload.get("id")
    checkout_url = payload.get("url")
    if not isinstance(session_id, str) or not isinstance(checkout_url, str):
        raise ValueError("Stripe returned an invalid session payload")

    payment_state.status = "pending"
    payment_state.payment_method = "card"
    payment_state.checkout_session_id = session_id
    appt.pay_in_store = False
    db.commit()
    db.refresh(appt)
    return appt, session_id, checkout_url


def process_stripe_appointment_payment_event(
    db: Session,
    *,
    event_id: str,
    event_type: str,
    appointment_id: int | None,
    payment_status: str,
    provider_payment_reference: str | None,
    amount_total_cents: int | None,
) -> tuple[str, str]:
    ensure_appointments_schema()

    if payment_status not in {"paid", "failed"}:
        return "ignored", "Unsupported payment status"
    if appointment_id is None:
        return "ignored", "Missing appointment_id"

    event = AppointmentPaymentWebhookEvent(
        provider="stripe",
        event_id=event_id,
        event_type=event_type,
        appointment_id=appointment_id,
        status="received",
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return "duplicate", "Event already processed"

    appt = db.get(Appointment, appointment_id)
    if appt is None:
        event.status = "ignored"
        event.detail = "Appointment not found"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "ignored", "Appointment not found"

    service = db.get(ServiceOffering, appt.service_offering_id)
    if service is None:
        event.status = "ignored"
        event.detail = "Service offering not found"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "ignored", "Service offering not found"

    payment_state = _get_or_create_payment_state(db, appointment_id=appt.id, amount_cents=service.price_cents)

    if amount_total_cents is not None and amount_total_cents != payment_state.amount_cents:
        event.status = "failed"
        event.detail = "Amount mismatch"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "failed", "Amount mismatch"

    if payment_status == "failed":
        payment_state.status = "failed"
        payment_state.payment_method = "card"
        payment_state.payment_reference = provider_payment_reference
        event.status = "processed"
        event.detail = "Payment failure recorded"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "processed", "Payment failure recorded"

    if payment_state.status == "paid":
        event.status = "processed"
        event.detail = "Appointment already paid"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "processed", "Appointment already paid"

    if appt.status in {"cancelled", "completed", "no_show"}:
        event.status = "ignored"
        event.detail = f"Appointment not payable in status={appt.status}"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "ignored", event.detail

    payment_state.status = "paid"
    payment_state.payment_method = "card"
    payment_state.payment_reference = provider_payment_reference
    appt.pay_in_store = False
    if appt.status == "scheduled":
        appt.status = "confirmed"

    event.status = "processed"
    event.detail = "Appointment marked as paid"
    event.processed_at = datetime.now(timezone.utc)
    db.commit()
    return "processed", "Appointment marked as paid"


def list_user_appointments(db: Session, user_id: int) -> list[Appointment]:
    ensure_appointments_schema()
    stmt = (
        select(Appointment)
        .where(Appointment.customer_user_id == user_id)
        .order_by(Appointment.start_at.desc())
        .limit(200)
    )
    return list(db.scalars(stmt).all())


def list_any_user_appointments(db: Session, user_id: int) -> list[Appointment]:
    ensure_appointments_schema()
    stmt = (
        select(Appointment)
        .where(
            (Appointment.customer_user_id == user_id) | (Appointment.employee_user_id == user_id),
        )
        .order_by(Appointment.start_at.desc())
        .limit(200)
    )
    return list(db.scalars(stmt).all())


def cancel_appointment(db: Session, appointment_id: int) -> Appointment | None:
    ensure_appointments_schema()
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        return None

    if appt.status == "cancelled":
        return appt

    appt.status = "cancelled"
    db.commit()
    db.refresh(appt)
    return appt


def get_appointment_by_id(db: Session, appointment_id: int) -> Appointment | None:
    ensure_appointments_schema()
    return db.get(Appointment, appointment_id)


def search_availability(
    db: Session,
    service_offering_id: int,
    target_date: date,
    customer_user_id: int,
    employee_user_id: int,
) -> list[datetime]:
    ensure_appointments_schema()

    service = db.get(ServiceOffering, service_offering_id)
    if service is None or not service.is_active:
        raise ValueError("Service offering not found")

    employee = db.get(User, employee_user_id)
    profile = db.get(EmployeeProfile, employee_user_id)
    if employee is None or profile is None or not profile.is_bookable:
        raise ValueError("Employee is not available")

    day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    start_window = day_start + timedelta(minutes=profile.workday_start_minute)
    end_window = day_start + timedelta(minutes=profile.workday_end_minute)

    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=profile.slot_step_minutes)

    slots: list[datetime] = []
    current = start_window
    while current + duration <= end_window:
        end = current + duration
        employee_busy = _has_overlap(db, Appointment.employee_user_id, employee_user_id, current, end)
        customer_busy = _has_overlap(db, Appointment.customer_user_id, customer_user_id, current, end)
        if not employee_busy and not customer_busy:
            slots.append(current)
        current += step

    return slots
