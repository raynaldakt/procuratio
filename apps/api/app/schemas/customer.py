from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    phone: str | None
    birthdate: date | None
    marketing_email_opt_in: bool
    marketing_sms_opt_in: bool
    total_visits: int
    total_spent_cents: int
    points_balance: int
    last_visit_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CustomerProfileUpdateSelf(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    birthdate: date | None = None
    marketing_email_opt_in: bool | None = None
    marketing_sms_opt_in: bool | None = None


class CustomerProfileUpdateStaffNotes(BaseModel):
    staff_notes: str | None = Field(default=None, max_length=4000)


class LoyaltyPurchaseRequest(BaseModel):
    user_id: int
    amount_spent_cents: int = Field(ge=0)
    description: str | None = Field(default=None, max_length=255)


class LoyaltyVisitRequest(BaseModel):
    user_id: int
    bonus_points: int = Field(default=0, ge=0, le=500)
    description: str | None = Field(default=None, max_length=255)


class LoyaltyAdjustmentRequest(BaseModel):
    user_id: int
    points_delta: int = Field(ge=-5000, le=5000)
    description: str = Field(min_length=3, max_length=255)


class LoyaltyTransactionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    kind: str
    points_delta: int
    source_amount_cents: int | None
    description: str | None
    created_by_user_id: int | None
    created_at: datetime
