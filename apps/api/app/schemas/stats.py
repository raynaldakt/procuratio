from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

StatsPeriod = Literal["day", "week", "month", "year"]


class TopItem(BaseModel):
    id: int
    name: str
    quantity: int


class StatsOverview(BaseModel):
    period: str
    start_at: datetime
    end_at: datetime
    gross_revenue_cents: int
    net_revenue_cents: int
    discount_total_cents: int
    tickets_paid_count: int
    appointments_count: int
    new_customers_count: int
    loyalty_points_earned: int
    gift_vouchers_sold_count: int
    gift_vouchers_sold_value_cents: int
    gift_vouchers_redeemed_value_cents: int
    top_services: list[TopItem]
    top_products: list[TopItem]


class StatsTimeseriesPoint(BaseModel):
    date: date
    revenue_cents: int
    tickets_paid_count: int
    appointments_count: int


class StatsTimeseries(BaseModel):
    period: str
    start_at: datetime
    end_at: datetime
    points: list[StatsTimeseriesPoint]
