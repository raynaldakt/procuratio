from datetime import date, datetime, time, timedelta, timezone
from threading import Lock

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models.appointment import Appointment
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
            tables=[ServiceOffering.__table__, EmployeeProfile.__table__, Appointment.__table__],
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
