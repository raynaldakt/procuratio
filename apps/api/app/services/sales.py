from datetime import datetime, timezone
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models.product_item import ProductItem
from app.models.sale_ticket import SaleTicket
from app.models.sale_ticket_line import SaleTicketLine
from app.models.service_offering import ServiceOffering
from app.models.user import User
from app.services.appointments import ensure_appointments_schema
from app.services.customer import register_purchase

_schema_lock = Lock()
_schema_ready = False
EDITABLE_TICKET_STATUSES = {"draft", "suspended"}


def ensure_sales_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    ensure_appointments_schema()
    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(
            bind=engine,
            tables=[ProductItem.__table__, SaleTicket.__table__, SaleTicketLine.__table__],
            checkfirst=True,
        )
        _schema_ready = True


def create_product(
    db: Session,
    name: str,
    brand: str | None,
    product_type: str | None,
    sku: str | None,
    description: str | None,
    price_cents: int,
    stock_quantity: int,
) -> ProductItem:
    ensure_sales_schema()
    product = ProductItem(
        name=name.strip(),
        brand=brand,
        product_type=product_type,
        sku=sku,
        description=description,
        price_cents=price_cents,
        stock_quantity=stock_quantity,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def search_products(
    db: Session,
    q: str | None,
    brand: str | None,
    product_type: str | None,
    min_price_cents: int | None,
    max_price_cents: int | None,
) -> list[ProductItem]:
    ensure_sales_schema()
    stmt = select(ProductItem).where(ProductItem.is_active.is_(True))

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((ProductItem.name.ilike(like)) | (ProductItem.description.ilike(like)))
    if brand:
        stmt = stmt.where(ProductItem.brand == brand)
    if product_type:
        stmt = stmt.where(ProductItem.product_type == product_type)
    if min_price_cents is not None:
        stmt = stmt.where(ProductItem.price_cents >= min_price_cents)
    if max_price_cents is not None:
        stmt = stmt.where(ProductItem.price_cents <= max_price_cents)

    stmt = stmt.order_by(ProductItem.name.asc()).limit(300)
    return list(db.scalars(stmt).all())


def _assert_ticket_editable(ticket: SaleTicket) -> None:
    if ticket.status not in EDITABLE_TICKET_STATUSES:
        raise ValueError("Ticket is not editable")


def create_ticket(db: Session, seller_user_id: int, notes: str | None) -> SaleTicket:
    ensure_sales_schema()
    seller = db.get(User, seller_user_id)
    if seller is None or not seller.is_active:
        raise ValueError("Seller not found")

    ticket = SaleTicket(seller_user_id=seller_user_id, notes=notes, status="draft")
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_or_none(db: Session, ticket_id: int) -> SaleTicket | None:
    ensure_sales_schema()
    return db.get(SaleTicket, ticket_id)


def list_tickets(db: Session, seller_user_id: int | None, status: str | None) -> list[SaleTicket]:
    ensure_sales_schema()
    stmt = select(SaleTicket)
    if seller_user_id is not None:
        stmt = stmt.where(SaleTicket.seller_user_id == seller_user_id)
    if status is not None:
        stmt = stmt.where(SaleTicket.status == status)
    stmt = stmt.order_by(SaleTicket.created_at.desc()).limit(200)
    return list(db.scalars(stmt).all())


def get_ticket_lines(db: Session, ticket_id: int) -> list[SaleTicketLine]:
    ensure_sales_schema()
    stmt = select(SaleTicketLine).where(SaleTicketLine.ticket_id == ticket_id).order_by(SaleTicketLine.id.asc())
    return list(db.scalars(stmt).all())


def compute_ticket_totals(ticket: SaleTicket, lines: list[SaleTicketLine]) -> tuple[int, int]:
    subtotal = sum(line.total_price_cents for line in lines)
    total = max(0, subtotal - ticket.discount_cents)
    return subtotal, total


def add_product_line(db: Session, ticket_id: int, product_item_id: int, quantity: int) -> SaleTicketLine:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise ValueError("Ticket not found")
    _assert_ticket_editable(ticket)

    product = db.get(ProductItem, product_item_id)
    if product is None or not product.is_active:
        raise ValueError("Product not found")
    if quantity > product.stock_quantity:
        raise ValueError("Insufficient stock")

    line = SaleTicketLine(
        ticket_id=ticket_id,
        line_type="product",
        product_item_id=product_item_id,
        quantity=quantity,
        unit_price_cents=product.price_cents,
        total_price_cents=product.price_cents * quantity,
        description=product.name,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def add_service_line(db: Session, ticket_id: int, service_offering_id: int, quantity: int) -> SaleTicketLine:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise ValueError("Ticket not found")
    _assert_ticket_editable(ticket)

    service = db.get(ServiceOffering, service_offering_id)
    if service is None or not service.is_active:
        raise ValueError("Service offering not found")

    line = SaleTicketLine(
        ticket_id=ticket_id,
        line_type="service",
        service_offering_id=service_offering_id,
        quantity=quantity,
        unit_price_cents=service.price_cents,
        total_price_cents=service.price_cents * quantity,
        description=service.name,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def set_ticket_customer(db: Session, ticket_id: int, customer_user_id: int | None) -> SaleTicket:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise ValueError("Ticket not found")
    _assert_ticket_editable(ticket)

    if customer_user_id is not None:
        customer = db.get(User, customer_user_id)
        if customer is None or not customer.is_active:
            raise ValueError("Customer not found")
        ticket.customer_user_id = customer_user_id
    else:
        ticket.customer_user_id = None

    db.commit()
    db.refresh(ticket)
    return ticket


def set_ticket_discount(db: Session, ticket_id: int, discount_cents: int) -> SaleTicket:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise ValueError("Ticket not found")
    _assert_ticket_editable(ticket)
    ticket.discount_cents = discount_cents
    db.commit()
    db.refresh(ticket)
    return ticket


def set_ticket_status(db: Session, ticket_id: int, status: str) -> SaleTicket:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise ValueError("Ticket not found")

    allowed = {"draft", "suspended"}
    if status not in allowed:
        raise ValueError("Invalid ticket status")

    if ticket.status == "paid":
        raise ValueError("Paid ticket cannot change status")

    ticket.status = status
    db.commit()
    db.refresh(ticket)
    return ticket


def checkout_ticket(db: Session, ticket_id: int, payment_method: str) -> tuple[SaleTicket, int]:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise ValueError("Ticket not found")
    if ticket.status not in EDITABLE_TICKET_STATUSES:
        raise ValueError("Ticket is not payable")

    lines = get_ticket_lines(db, ticket_id)
    if not lines:
        raise ValueError("Ticket has no lines")

    for line in lines:
        if line.line_type == "product":
            if line.product_item_id is None:
                raise ValueError("Invalid product line")
            product = db.get(ProductItem, line.product_item_id)
            if product is None or not product.is_active:
                raise ValueError("Product not found")
            if product.stock_quantity < line.quantity:
                raise ValueError("Insufficient stock for checkout")

    subtotal, total = compute_ticket_totals(ticket, lines)

    for line in lines:
        if line.line_type == "product" and line.product_item_id is not None:
            product = db.get(ProductItem, line.product_item_id)
            if product is None:
                continue
            product.stock_quantity -= line.quantity

    ticket.payment_method = payment_method
    ticket.status = "paid"
    ticket.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)

    loyalty_points = 0
    if ticket.customer_user_id is not None and total > 0:
        txn = register_purchase(
            db=db,
            user_id=ticket.customer_user_id,
            amount_spent_cents=total,
            description=f"Ticket #{ticket.id}",
            created_by_user_id=ticket.seller_user_id,
        )
        loyalty_points = max(0, txn.points_delta)

    return ticket, loyalty_points
