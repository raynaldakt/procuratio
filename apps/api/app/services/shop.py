from datetime import datetime, timedelta, timezone
from threading import Lock

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
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
            tables=[ShopOrder.__table__, ShopOrderLine.__table__, ProductReservation.__table__],
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
