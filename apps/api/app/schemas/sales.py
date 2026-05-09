from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TicketStatus = Literal["draft", "suspended", "paid", "cancelled"]


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    brand: str | None = Field(default=None, max_length=120)
    product_type: str | None = Field(default=None, max_length=80)
    sku: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    price_cents: int = Field(ge=0)
    stock_quantity: int = Field(ge=0)


class ProductPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str | None
    product_type: str | None
    sku: str | None
    description: str | None
    price_cents: int
    stock_quantity: int
    is_active: bool


class SaleTicketCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=500)


class SaleTicketLineAddProduct(BaseModel):
    product_item_id: int
    quantity: int = Field(ge=1, le=1000)


class SaleTicketLineAddService(BaseModel):
    service_offering_id: int
    quantity: int = Field(default=1, ge=1, le=20)


class SaleTicketSetCustomer(BaseModel):
    customer_user_id: int | None = None


class SaleTicketSetDiscount(BaseModel):
    discount_cents: int = Field(ge=0)


class SaleTicketCheckout(BaseModel):
    payment_method: Literal["card", "cash", "transfer", "mixed"]


class SaleTicketLinePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    line_type: str
    product_item_id: int | None
    service_offering_id: int | None
    quantity: int
    unit_price_cents: int
    total_price_cents: int
    description: str | None


class SaleTicketPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_user_id: int
    customer_user_id: int | None
    status: TicketStatus
    discount_cents: int
    payment_method: str | None
    notes: str | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SaleTicketDetails(BaseModel):
    ticket: SaleTicketPublic
    lines: list[SaleTicketLinePublic]
    subtotal_cents: int
    total_cents: int


class SaleCheckoutReceipt(BaseModel):
    ticket: SaleTicketPublic
    lines: list[SaleTicketLinePublic]
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    loyalty_points_earned: int
