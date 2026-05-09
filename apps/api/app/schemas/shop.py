from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ShopCartCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=500)


class ShopCartAddLine(BaseModel):
    product_item_id: int
    quantity: int = Field(ge=1, le=1000)


class ShopCheckoutPurchase(BaseModel):
    payment_method: Literal["card", "transfer", "wallet"]


class ShopCheckoutReserve(BaseModel):
    expires_in_hours: int = Field(default=48, ge=1, le=168)


class ShopOrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_user_id: int
    status: str
    fulfillment_mode: str | None
    payment_method: str | None
    payment_status: str
    subtotal_cents: int
    total_cents: int
    notes: str | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ShopOrderLinePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_item_id: int
    quantity: int
    unit_price_cents: int
    total_price_cents: int


class ShopOrderDetails(BaseModel):
    order: ShopOrderPublic
    lines: list[ShopOrderLinePublic]


class ProductReservationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    customer_user_id: int
    product_item_id: int
    quantity: int
    status: str
    expires_at: datetime
    created_at: datetime


class ShopCheckoutPurchaseResponse(BaseModel):
    order: ShopOrderPublic
    lines: list[ShopOrderLinePublic]
    loyalty_points_earned: int


class ReservationSweepResponse(BaseModel):
    expired_count: int
