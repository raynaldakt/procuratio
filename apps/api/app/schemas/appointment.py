from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

AppointmentStatus = Literal["scheduled", "confirmed", "cancelled", "completed", "no_show"]


class ServiceOfferingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    duration_minutes: int = Field(ge=5, le=360)
    price_cents: int = Field(ge=0)


class ServiceOfferingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    duration_minutes: int
    price_cents: int
    is_active: bool


class EmployeeProfileUpsert(BaseModel):
    is_bookable: bool = True
    workday_start_minute: int = Field(default=9 * 60, ge=0, le=24 * 60)
    workday_end_minute: int = Field(default=19 * 60, ge=0, le=24 * 60)
    slot_step_minutes: int = Field(default=15, ge=5, le=60)


class EmployeeProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    is_bookable: bool
    workday_start_minute: int
    workday_end_minute: int
    slot_step_minutes: int


class AppointmentCreateSelf(BaseModel):
    service_offering_id: int
    start_at: datetime
    employee_user_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    pay_in_store: bool = True


class AppointmentCreateStaff(AppointmentCreateSelf):
    customer_user_id: int


class AppointmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_user_id: int
    employee_user_id: int | None
    service_offering_id: int
    start_at: datetime
    end_at: datetime
    status: AppointmentStatus
    notes: str | None
    pay_in_store: bool
    created_by_user_id: int | None


class AvailabilityQuery(BaseModel):
    service_offering_id: int
    target_date: date
    employee_user_id: int


class AvailabilitySlot(BaseModel):
    start_at: datetime


class AppointmentCancelResponse(BaseModel):
    message: str
    appointment: AppointmentPublic


class AppointmentCheckoutStripeSessionCreate(BaseModel):
    success_url: HttpUrl
    cancel_url: HttpUrl


class AppointmentCheckoutStripeSessionResponse(BaseModel):
    appointment: AppointmentPublic
    session_id: str
    checkout_url: str


class AppointmentStripeWebhookEventIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    event_type: str = Field(min_length=1, max_length=120)
    appointment_id: int | None = None
    payment_status: Literal["paid", "failed"]
    provider_payment_reference: str | None = Field(default=None, max_length=255)
    amount_total_cents: int | None = Field(default=None, ge=0)


class AppointmentStripeWebhookEventProcessResponse(BaseModel):
    result: Literal["processed", "duplicate", "ignored", "failed"]
    detail: str
