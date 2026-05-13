from datetime import datetime, timedelta, timezone
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
from app.models.payment_webhook_event import PaymentWebhookEvent
from app.models.product_item import ProductItem
from app.models.product_reservation import ProductReservation
from app.models.shop_order import ShopOrder
from app.models.shop_order_line import ShopOrderLine
from app.models.user import User
from app.services.customer import register_purchase
from app.services.sales import ensure_sales_schema

_schema_lock = Lock()
_schema_ready = False


def ensure_shop_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    ensure_sales_schema()
    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(
            bind=engine,
            tables=[
                ShopOrder.__table__,
                ShopOrderLine.__table__,
                ProductReservation.__table__,
                PaymentWebhookEvent.__table__,
            ],
            checkfirst=True,
        )
        _schema_ready = True


def _order_lines(db: Session, order_id: int) -> list[ShopOrderLine]:
    stmt = select(ShopOrderLine).where(ShopOrderLine.order_id == order_id).order_by(ShopOrderLine.id.asc())
    return list(db.scalars(stmt).all())


def _recompute_order_totals(db: Session, order: ShopOrder) -> ShopOrder:
    lines = _order_lines(db, order.id)
    subtotal = sum(line.total_price_cents for line in lines)
    order.subtotal_cents = subtotal
    order.total_cents = subtotal
    db.commit()
    db.refresh(order)
    return order


def _append_order_note(order: ShopOrder, line: str) -> None:
    existing = order.notes or ""
    combined = f"{existing}\n{line}".strip() if existing else line
    order.notes = combined[:500]


def get_or_create_cart(db: Session, customer_user_id: int, notes: str | None = None) -> ShopOrder:
    ensure_shop_schema()
    customer = db.get(User, customer_user_id)
    if customer is None or not customer.is_active:
        raise ValueError("Customer not found")

    stmt = select(ShopOrder).where(ShopOrder.customer_user_id == customer_user_id, ShopOrder.status == "cart")
    existing = db.scalar(stmt)
    if existing is not None:
        if notes is not None:
            existing.notes = notes
            db.commit()
            db.refresh(existing)
        return existing

    order = ShopOrder(customer_user_id=customer_user_id, status="cart", notes=notes)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order_for_customer_or_none(db: Session, order_id: int, customer_user_id: int) -> ShopOrder | None:
    ensure_shop_schema()
    order = db.get(ShopOrder, order_id)
    if order is None:
        return None
    if order.customer_user_id != customer_user_id:
        return None
    return order


def add_line_to_cart(db: Session, order: ShopOrder, product_item_id: int, quantity: int) -> ShopOrderLine:
    if order.status != "cart":
        raise ValueError("Order is not editable")

    product = db.get(ProductItem, product_item_id)
    if product is None or not product.is_active:
        raise ValueError("Product not found")

    if quantity > product.stock_quantity:
        raise ValueError("Insufficient stock")

    line = ShopOrderLine(
        order_id=order.id,
        product_item_id=product_item_id,
        quantity=quantity,
        unit_price_cents=product.price_cents,
        total_price_cents=product.price_cents * quantity,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    _recompute_order_totals(db, order)
    return line


def remove_line_from_cart(db: Session, order: ShopOrder, line_id: int) -> ShopOrder:
    if order.status != "cart":
        raise ValueError("Order is not editable")

    line = db.get(ShopOrderLine, line_id)
    if line is None or line.order_id != order.id:
        raise ValueError("Line not found")

    db.delete(line)
    db.commit()
    return _recompute_order_totals(db, order)


def list_customer_orders(db: Session, customer_user_id: int) -> list[ShopOrder]:
    ensure_shop_schema()
    stmt = (
        select(ShopOrder)
        .where(ShopOrder.customer_user_id == customer_user_id)
        .order_by(ShopOrder.created_at.desc())
        .limit(200)
    )
    return list(db.scalars(stmt).all())


def checkout_purchase(db: Session, order: ShopOrder, payment_method: str) -> tuple[ShopOrder, int]:
    if order.status != "cart":
        raise ValueError("Order is not payable")

    lines = _order_lines(db, order.id)
    if not lines:
        raise ValueError("Cart is empty")

    for line in lines:
        product = db.get(ProductItem, line.product_item_id)
        if product is None or not product.is_active:
            raise ValueError("Product not found")
        if product.stock_quantity < line.quantity:
            raise ValueError("Insufficient stock")

    for line in lines:
        product = db.get(ProductItem, line.product_item_id)
        if product is None:
            continue
        product.stock_quantity -= line.quantity

    _recompute_order_totals(db, order)
    order.status = "paid"
    order.fulfillment_mode = "purchase"
    order.payment_status = "paid"
    order.payment_method = payment_method
    order.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    loyalty_points = 0
    if order.total_cents > 0:
        txn = register_purchase(
            db=db,
            user_id=order.customer_user_id,
            amount_spent_cents=order.total_cents,
            description=f"Shop order #{order.id}",
            created_by_user_id=order.customer_user_id,
        )
        loyalty_points = max(0, txn.points_delta)

    return order, loyalty_points


def _apply_paid_transition(db: Session, order: ShopOrder, payment_method: str, payment_reference: str | None) -> int:
    lines = _order_lines(db, order.id)
    if not lines:
        raise ValueError("Cart is empty")

    for line in lines:
        product = db.get(ProductItem, line.product_item_id)
        if product is None or not product.is_active:
            raise ValueError("Product not found")
        if product.stock_quantity < line.quantity:
            raise ValueError("Insufficient stock")

    for line in lines:
        product = db.get(ProductItem, line.product_item_id)
        if product is None:
            continue
        product.stock_quantity -= line.quantity

    _recompute_order_totals(db, order)
    order.status = "paid"
    order.fulfillment_mode = "purchase"
    order.payment_status = "paid"
    if payment_reference:
        _append_order_note(order, f"payment_ref:{payment_reference}")
    order.payment_method = payment_method
    order.confirmed_at = datetime.now(timezone.utc)

    loyalty_points = 0
    if order.total_cents > 0:
        txn = register_purchase(
            db=db,
            user_id=order.customer_user_id,
            amount_spent_cents=order.total_cents,
            description=f"Shop order #{order.id}",
            created_by_user_id=order.customer_user_id,
        )
        loyalty_points = max(0, txn.points_delta)

    return loyalty_points


def create_stripe_checkout_session(
    db: Session,
    *,
    order: ShopOrder,
    success_url: str,
    cancel_url: str,
) -> tuple[ShopOrder, str, str]:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise ValueError("Stripe is not configured (missing STRIPE_SECRET_KEY)")
    if order.status != "cart":
        raise ValueError("Order is not payable")

    lines = _order_lines(db, order.id)
    if not lines:
        raise ValueError("Cart is empty")

    for line in lines:
        product = db.get(ProductItem, line.product_item_id)
        if product is None or not product.is_active:
            raise ValueError("Product not found")
        if product.stock_quantity < line.quantity:
            raise ValueError("Insufficient stock")

    _recompute_order_totals(db, order)
    order.status = "payment_pending"
    order.fulfillment_mode = "purchase"
    order.payment_status = "pending"
    order.payment_method = "card"
    db.commit()
    db.refresh(order)

    form: list[tuple[str, str]] = [
        ("mode", "payment"),
        ("success_url", success_url),
        ("cancel_url", cancel_url),
        ("client_reference_id", str(order.id)),
        ("metadata[order_id]", str(order.id)),
        ("payment_intent_data[metadata][order_id]", str(order.id)),
    ]

    for idx, line in enumerate(lines):
        product = db.get(ProductItem, line.product_item_id)
        if product is None:
            continue
        form.extend(
            [
                (f"line_items[{idx}][quantity]", str(line.quantity)),
                (f"line_items[{idx}][price_data][currency]", settings.stripe_checkout_currency),
                (f"line_items[{idx}][price_data][unit_amount]", str(line.unit_price_cents)),
                (f"line_items[{idx}][price_data][product_data][name]", product.name),
                (
                    f"line_items[{idx}][price_data][product_data][description]",
                    (product.description or product.product_type or "Procuratio product")[:250],
                ),
            ]
        )

    body = urlencode(form).encode("utf-8")
    request = Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.stripe_secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
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

    _append_order_note(order, f"stripe_session_id:{session_id}")
    db.commit()
    db.refresh(order)
    return order, session_id, checkout_url


def process_stripe_payment_event(
    db: Session,
    *,
    event_id: str,
    event_type: str,
    order_id: int | None,
    payment_status: str,
    provider_payment_reference: str | None,
    amount_total_cents: int | None,
) -> tuple[str, str]:
    ensure_shop_schema()
    if payment_status not in {"paid", "failed"}:
        return "ignored", "Unsupported payment status"
    if order_id is None:
        return "ignored", "Missing order_id"

    event = PaymentWebhookEvent(
        provider="stripe",
        event_id=event_id,
        event_type=event_type,
        order_id=order_id,
        status="received",
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return "duplicate", "Event already processed"

    order = db.get(ShopOrder, order_id)
    if order is None:
        event.status = "ignored"
        event.detail = "Order not found"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "ignored", "Order not found"

    if amount_total_cents is not None and amount_total_cents != order.total_cents:
        event.status = "failed"
        event.detail = "Amount mismatch"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "failed", "Amount mismatch"

    if payment_status == "failed":
        if order.status == "payment_pending":
            order.status = "cart"
        order.payment_status = "failed"
        order.payment_method = "card"
        event.status = "processed"
        event.detail = "Payment failure recorded"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "processed", "Payment failure recorded"

    if order.status == "paid" and order.payment_status == "paid":
        event.status = "processed"
        event.detail = "Order already paid"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "processed", "Order already paid"

    if order.status not in {"cart", "payment_pending"}:
        event.status = "ignored"
        event.detail = f"Order not payable in status={order.status}"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return "ignored", event.detail

    _apply_paid_transition(
        db,
        order,
        payment_method="card",
        payment_reference=provider_payment_reference,
    )
    event.status = "processed"
    event.detail = "Order marked as paid"
    event.processed_at = datetime.now(timezone.utc)
    db.commit()
    return "processed", "Order marked as paid"


def checkout_reservation(db: Session, order: ShopOrder, expires_in_hours: int) -> tuple[ShopOrder, list[ProductReservation]]:
    if order.status != "cart":
        raise ValueError("Order is not reservable")

    lines = _order_lines(db, order.id)
    if not lines:
        raise ValueError("Cart is empty")

    for line in lines:
        product = db.get(ProductItem, line.product_item_id)
        if product is None or not product.is_active:
            raise ValueError("Product not found")
        if product.stock_quantity < line.quantity:
            raise ValueError("Insufficient stock")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=expires_in_hours)

    reservations: list[ProductReservation] = []
    for line in lines:
        product = db.get(ProductItem, line.product_item_id)
        if product is None:
            continue
        product.stock_quantity -= line.quantity
        reservation = ProductReservation(
            order_id=order.id,
            customer_user_id=order.customer_user_id,
            product_item_id=line.product_item_id,
            quantity=line.quantity,
            status="active",
            expires_at=expires_at,
        )
        db.add(reservation)
        reservations.append(reservation)

    _recompute_order_totals(db, order)
    order.status = "reserved"
    order.fulfillment_mode = "pickup_reservation"
    order.payment_status = "unpaid"
    order.confirmed_at = now
    db.commit()

    for reservation in reservations:
        db.refresh(reservation)
    db.refresh(order)
    return order, reservations


def list_customer_reservations(db: Session, customer_user_id: int) -> list[ProductReservation]:
    ensure_shop_schema()
    stmt = (
        select(ProductReservation)
        .where(ProductReservation.customer_user_id == customer_user_id)
        .order_by(ProductReservation.created_at.desc())
        .limit(200)
    )
    return list(db.scalars(stmt).all())


def collect_reservation(db: Session, reservation_id: int) -> ProductReservation | None:
    reservation = db.get(ProductReservation, reservation_id)
    if reservation is None:
        return None
    if reservation.status != "active":
        raise ValueError("Reservation is not active")

    reservation.status = "collected"
    db.commit()
    db.refresh(reservation)
    return reservation


def cancel_reservation(db: Session, reservation_id: int) -> ProductReservation | None:
    reservation = db.get(ProductReservation, reservation_id)
    if reservation is None:
        return None
    if reservation.status != "active":
        raise ValueError("Reservation is not active")

    product = db.get(ProductItem, reservation.product_item_id)
    if product is not None:
        product.stock_quantity += reservation.quantity

    reservation.status = "cancelled"
    db.commit()
    db.refresh(reservation)
    return reservation


def sweep_expired_reservations(db: Session) -> int:
    ensure_shop_schema()
    now = datetime.now(timezone.utc)
    stmt = select(ProductReservation).where(
        ProductReservation.status == "active",
        ProductReservation.expires_at <= now,
    )
    rows = list(db.scalars(stmt).all())

    for row in rows:
        product = db.get(ProductItem, row.product_item_id)
        if product is not None:
            product.stock_quantity += row.quantity
        row.status = "expired"

    db.commit()
    return len(rows)


def get_order_details(db: Session, order: ShopOrder) -> tuple[ShopOrder, list[ShopOrderLine]]:
    return order, _order_lines(db, order.id)
