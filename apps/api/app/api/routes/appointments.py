import hmac
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCheckoutStripeSessionCreate,
    AppointmentCheckoutStripeSessionResponse,
    AppointmentCancelResponse,
    AppointmentCreateSelf,
    AppointmentCreateStaff,
    AppointmentPublic,
    AppointmentStripeWebhookEventIn,
    AppointmentStripeWebhookEventProcessResponse,
    AvailabilitySlot,
    EmployeeProfilePublic,
    EmployeeProfileUpsert,
    ServiceOfferingCreate,
    ServiceOfferingPublic,
)
from app.services.appointments import (
    cancel_appointment,
    create_appointment,
    create_appointment_stripe_checkout_session,
    create_service_offering,
    get_appointment_by_id,
    list_active_service_offerings,
    list_any_user_appointments,
    list_bookable_employees,
    list_user_appointments,
    process_stripe_appointment_payment_event,
    search_availability,
    set_employee_profile,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])
settings = get_settings()


@router.get("/services", response_model=list[ServiceOfferingPublic])
def list_services(db: Session = Depends(get_db)) -> list[ServiceOfferingPublic]:
    return [ServiceOfferingPublic.model_validate(row) for row in list_active_service_offerings(db)]


@router.post("/services", response_model=ServiceOfferingPublic, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceOfferingCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "staff")),
) -> ServiceOfferingPublic:
    service = create_service_offering(
        db,
        name=payload.name,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        price_cents=payload.price_cents,
    )
    return ServiceOfferingPublic.model_validate(service)


@router.put("/employees/{user_id}/profile", response_model=EmployeeProfilePublic)
def upsert_employee_profile(
    user_id: int,
    payload: EmployeeProfileUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager")),
) -> EmployeeProfilePublic:
    if payload.workday_start_minute >= payload.workday_end_minute:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid workday range")

    try:
        profile = set_employee_profile(
            db,
            user_id=user_id,
            is_bookable=payload.is_bookable,
            workday_start_minute=payload.workday_start_minute,
            workday_end_minute=payload.workday_end_minute,
            slot_step_minutes=payload.slot_step_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return EmployeeProfilePublic.model_validate(profile)


@router.get("/employees", response_model=list[EmployeeProfilePublic])
def get_bookable_employees(db: Session = Depends(get_db)) -> list[EmployeeProfilePublic]:
    return [EmployeeProfilePublic.model_validate(row) for row in list_bookable_employees(db)]


@router.get("/availability", response_model=list[AvailabilitySlot])
def get_availability(
    service_offering_id: int = Query(...),
    target_date: date = Query(...),
    employee_user_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AvailabilitySlot]:
    try:
        slots = search_availability(
            db,
            service_offering_id=service_offering_id,
            target_date=target_date,
            customer_user_id=current_user.id,
            employee_user_id=employee_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [AvailabilitySlot(start_at=slot) for slot in slots]


@router.post("/book", response_model=AppointmentPublic, status_code=status.HTTP_201_CREATED)
def book_self(
    payload: AppointmentCreateSelf,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentPublic:
    try:
        appt = create_appointment(
            db=db,
            customer_user_id=current_user.id,
            service_offering_id=payload.service_offering_id,
            start_at=payload.start_at,
            employee_user_id=payload.employee_user_id,
            notes=payload.notes,
            pay_in_store=payload.pay_in_store,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return AppointmentPublic.model_validate(appt)


@router.post("/{appointment_id}/checkout/stripe-session", response_model=AppointmentCheckoutStripeSessionResponse)
def create_stripe_session_for_appointment(
    appointment_id: int,
    payload: AppointmentCheckoutStripeSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentCheckoutStripeSessionResponse:
    try:
        appt, session_id, checkout_url = create_appointment_stripe_checkout_session(
            db=db,
            appointment_id=appointment_id,
            customer_user_id=current_user.id,
            success_url=str(payload.success_url),
            cancel_url=str(payload.cancel_url),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return AppointmentCheckoutStripeSessionResponse(
        appointment=AppointmentPublic.model_validate(appt),
        session_id=session_id,
        checkout_url=checkout_url,
    )


@router.post("/book-for-customer", response_model=AppointmentPublic, status_code=status.HTTP_201_CREATED)
def book_for_customer(
    payload: AppointmentCreateStaff,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> AppointmentPublic:
    try:
        appt = create_appointment(
            db=db,
            customer_user_id=payload.customer_user_id,
            service_offering_id=payload.service_offering_id,
            start_at=payload.start_at,
            employee_user_id=payload.employee_user_id,
            notes=payload.notes,
            pay_in_store=payload.pay_in_store,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return AppointmentPublic.model_validate(appt)


@router.get("/me", response_model=list[AppointmentPublic])
def list_my_appointments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AppointmentPublic]:
    rows = list_user_appointments(db, current_user.id)
    return [AppointmentPublic.model_validate(row) for row in rows]


@router.get("/users/{user_id}", response_model=list[AppointmentPublic])
def list_user_related_appointments(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "staff")),
) -> list[AppointmentPublic]:
    rows = list_any_user_appointments(db, user_id)
    return [AppointmentPublic.model_validate(row) for row in rows]


@router.post("/{appointment_id}/cancel", response_model=AppointmentCancelResponse)
def cancel(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentCancelResponse:
    appt = get_appointment_by_id(db, appointment_id)
    if appt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    can_manage = current_user.role in {"admin", "manager", "staff"}
    if not can_manage and appt.customer_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    appt = cancel_appointment(db, appointment_id)
    if appt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    return AppointmentCancelResponse(message="Appointment cancelled", appointment=AppointmentPublic.model_validate(appt))


@router.post("/internal/payments/stripe/event", response_model=AppointmentStripeWebhookEventProcessResponse)
def process_appointment_stripe_event(
    payload: AppointmentStripeWebhookEventIn,
    db: Session = Depends(get_db),
    webhook_token: str | None = Header(default=None, alias="X-Webhook-Token"),
) -> AppointmentStripeWebhookEventProcessResponse:
    if webhook_token is None or not hmac.compare_digest(webhook_token, settings.payment_webhook_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal webhook token")

    result, detail = process_stripe_appointment_payment_event(
        db=db,
        event_id=payload.event_id,
        event_type=payload.event_type,
        appointment_id=payload.appointment_id,
        payment_status=payload.payment_status,
        provider_payment_reference=payload.provider_payment_reference,
        amount_total_cents=payload.amount_total_cents,
    )
    return AppointmentStripeWebhookEventProcessResponse(result=result, detail=detail)
