from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.gift_voucher import GiftVoucher
from app.models.gift_voucher_redemption import GiftVoucherRedemption
from app.models.loyalty_transaction import LoyaltyTransaction
from app.models.product_item import ProductItem
from app.models.sale_ticket import SaleTicket
from app.models.sale_ticket_line import SaleTicketLine
from app.models.service_offering import ServiceOffering
from app.models.user import User
from app.schemas.stats import StatsOverview, StatsTimeseries, StatsTimeseriesPoint, TopItem
from app.services.gifts import ensure_gifts_schema


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _period_bounds(period: str, date_from: date | None, date_to: date | None) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)

    if date_from and date_to:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        return start, end

    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = (now - timedelta(days=364)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError("Unsupported period")

    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _paid_tickets_in_range(db: Session, start_at: datetime, end_at: datetime) -> list[SaleTicket]:
    stmt = select(SaleTicket).where(
        SaleTicket.status == "paid",
        SaleTicket.paid_at.is_not(None),
        SaleTicket.paid_at >= start_at,
        SaleTicket.paid_at <= end_at,
    )
    return list(db.scalars(stmt).all())


def _ticket_totals_map(db: Session, ticket_ids: list[int]) -> dict[int, int]:
    if not ticket_ids:
        return {}
    stmt = select(SaleTicketLine).where(SaleTicketLine.ticket_id.in_(ticket_ids))
    lines = list(db.scalars(stmt).all())
    totals: dict[int, int] = defaultdict(int)
    for line in lines:
        totals[line.ticket_id] += line.total_price_cents
    return totals


def _top_items_from_lines(db: Session, ticket_ids: list[int], kind: str) -> list[TopItem]:
    if not ticket_ids:
        return []
    stmt = select(SaleTicketLine).where(
        SaleTicketLine.ticket_id.in_(ticket_ids),
        SaleTicketLine.line_type == kind,
    )
    lines = list(db.scalars(stmt).all())

    counter: dict[int, int] = defaultdict(int)
    for line in lines:
        item_id = line.product_item_id if kind == "product" else line.service_offering_id
        if item_id is None:
            continue
        counter[item_id] += line.quantity

    if not counter:
        return []

    ids = list(counter.keys())
    if kind == "product":
        rows = list(db.scalars(select(ProductItem).where(ProductItem.id.in_(ids))).all())
        names = {row.id: row.name for row in rows}
    else:
        rows = list(db.scalars(select(ServiceOffering).where(ServiceOffering.id.in_(ids))).all())
        names = {row.id: row.name for row in rows}

    tops = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:5]
    return [TopItem(id=item_id, name=names.get(item_id, f"#{item_id}"), quantity=qty) for item_id, qty in tops]


def get_overview(db: Session, period: str, date_from: date | None, date_to: date | None) -> StatsOverview:
    ensure_gifts_schema()
    start_at, end_at = _period_bounds(period, date_from, date_to)

    paid_tickets = _paid_tickets_in_range(db, start_at, end_at)
    ticket_ids = [t.id for t in paid_tickets]
    subtotals = _ticket_totals_map(db, ticket_ids)

    gross_revenue = sum(subtotals.get(t.id, 0) for t in paid_tickets)
    discount_total = sum(t.discount_cents for t in paid_tickets)
    net_revenue = sum(max(0, subtotals.get(t.id, 0) - t.discount_cents) for t in paid_tickets)

    appt_stmt = select(Appointment).where(Appointment.start_at >= start_at, Appointment.start_at <= end_at)
    appointments = list(db.scalars(appt_stmt).all())

    new_customers_stmt = select(User.id).where(
        User.role == "customer",
        User.created_at >= start_at,
        User.created_at <= end_at,
    )
    new_customers = list(db.scalars(new_customers_stmt).all())

    points_stmt = select(LoyaltyTransaction).where(
        LoyaltyTransaction.kind == "purchase",
        LoyaltyTransaction.created_at >= start_at,
        LoyaltyTransaction.created_at <= end_at,
    )
    purchase_points = list(db.scalars(points_stmt).all())
    loyalty_points_earned = sum(max(0, row.points_delta) for row in purchase_points)

    vouchers_stmt = select(GiftVoucher).where(GiftVoucher.created_at >= start_at, GiftVoucher.created_at <= end_at)
    vouchers = list(db.scalars(vouchers_stmt).all())

    redemptions_stmt = select(GiftVoucherRedemption).where(
        GiftVoucherRedemption.created_at >= start_at,
        GiftVoucherRedemption.created_at <= end_at,
    )
    redemptions = list(db.scalars(redemptions_stmt).all())

    return StatsOverview(
        period=period,
        start_at=start_at,
        end_at=end_at,
        gross_revenue_cents=gross_revenue,
        net_revenue_cents=net_revenue,
        discount_total_cents=discount_total,
        tickets_paid_count=len(paid_tickets),
        appointments_count=len(appointments),
        new_customers_count=len(new_customers),
        loyalty_points_earned=loyalty_points_earned,
        gift_vouchers_sold_count=len(vouchers),
        gift_vouchers_sold_value_cents=sum(v.initial_amount_cents for v in vouchers),
        gift_vouchers_redeemed_value_cents=sum(r.redeemed_amount_cents for r in redemptions),
        top_services=_top_items_from_lines(db, ticket_ids, "service"),
        top_products=_top_items_from_lines(db, ticket_ids, "product"),
    )


def get_timeseries(db: Session, period: str, date_from: date | None, date_to: date | None) -> StatsTimeseries:
    ensure_gifts_schema()
    start_at, end_at = _period_bounds(period, date_from, date_to)

    paid_tickets = _paid_tickets_in_range(db, start_at, end_at)
    ticket_ids = [t.id for t in paid_tickets]
    subtotals = _ticket_totals_map(db, ticket_ids)

    revenue_by_day: dict[date, int] = defaultdict(int)
    tickets_by_day: dict[date, int] = defaultdict(int)
    for ticket in paid_tickets:
        if ticket.paid_at is None:
            continue
        day = _to_utc(ticket.paid_at).date()
        total = max(0, subtotals.get(ticket.id, 0) - ticket.discount_cents)
        revenue_by_day[day] += total
        tickets_by_day[day] += 1

    appt_stmt = select(Appointment).where(Appointment.start_at >= start_at, Appointment.start_at <= end_at)
    appointments = list(db.scalars(appt_stmt).all())
    appts_by_day: dict[date, int] = defaultdict(int)
    for appt in appointments:
        appts_by_day[_to_utc(appt.start_at).date()] += 1

    points: list[StatsTimeseriesPoint] = []
    current = start_at.date()
    end_day = end_at.date()
    while current <= end_day:
        points.append(
            StatsTimeseriesPoint(
                date=current,
                revenue_cents=revenue_by_day.get(current, 0),
                tickets_paid_count=tickets_by_day.get(current, 0),
                appointments_count=appts_by_day.get(current, 0),
            )
        )
        current += timedelta(days=1)

    return StatsTimeseries(period=period, start_at=start_at, end_at=end_at, points=points)
