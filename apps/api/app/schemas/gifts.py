from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VoucherType = Literal["amount", "service"]
VoucherStatus = Literal["active", "redeemed", "expired", "cancelled"]


class GiftVoucherCreate(BaseModel):
    voucher_type: VoucherType
    service_offering_id: int | None = None
    amount_cents: int | None = Field(default=None, ge=0)
    purchaser_name: str = Field(min_length=2, max_length=160)
    recipient_name: str = Field(min_length=2, max_length=160)
    recipient_email: str | None = Field(default=None, max_length=255)
    effective_date: date
    duration_days: int = Field(ge=1, le=3650)


class GiftVoucherPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    voucher_type: str
    service_offering_id: int | None
    initial_amount_cents: int
    remaining_amount_cents: int
    purchaser_name: str
    recipient_name: str
    recipient_email: str | None
    effective_date: date
    expires_at: datetime
    status: VoucherStatus
    created_by_user_id: int
    created_at: datetime


class GiftVoucherRedeemRequest(BaseModel):
    amount_cents: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=255)


class GiftVoucherRedemptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voucher_id: int
    redeemed_amount_cents: int
    notes: str | None
    redeemed_by_user_id: int
    created_at: datetime


class GiftVoucherRedeemResponse(BaseModel):
    voucher: GiftVoucherPublic
    redemption: GiftVoucherRedemptionPublic
