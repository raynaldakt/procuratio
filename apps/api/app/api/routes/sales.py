from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.sales import (
    ProductCreate,
    ProductPublic,
    SaleCheckoutReceipt,
    SaleTicketCheckout,
    SaleTicketCreate,
    SaleTicketDetails,
    SaleTicketLineAddProduct,
    SaleTicketLineAddService,
    SaleTicketPublic,
    SaleTicketSetCustomer,
    SaleTicketSetDiscount,
)
from app.services.sales import (
    add_product_line,
    add_service_line,
    checkout_ticket,
    compute_ticket_totals,
    create_product,
    create_ticket,
    get_ticket_lines,
    get_ticket_or_none,
    list_tickets,
    search_products,
    set_ticket_customer,
    set_ticket_discount,
    set_ticket_status,
)

router = APIRouter(prefix="/sales", tags=["sales"])


def _assert_ticket_owner_or_manager(current_user: User, ticket) -> None:
    if current_user.id == ticket.seller_user_id:
        return
    if current_user.role in {"admin", "manager"}:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.post("/products", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product_item(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "staff")),
) -> ProductPublic:
    product = create_product(
        db=db,
        name=payload.name,
        brand=payload.brand,
        product_type=payload.product_type,
        sku=payload.sku,
        description=payload.description,
        price_cents=payload.price_cents,
        stock_quantity=payload.stock_quantity,
    )
    return ProductPublic.model_validate(product)


@router.get("/products", response_model=list[ProductPublic])
def list_product_items(
    q: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    product_type: str | None = Query(default=None),
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
) -> list[ProductPublic]:
    rows = search_products(db, q, brand, product_type, min_price_cents, max_price_cents)
    return [ProductPublic.model_validate(row) for row in rows]


@router.post("/tickets", response_model=SaleTicketPublic, status_code=status.HTTP_201_CREATED)
def create_sale_ticket(
    payload: SaleTicketCreate,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketPublic:
    try:
        ticket = create_ticket(db, seller_user_id=current_user.id, notes=payload.notes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SaleTicketPublic.model_validate(ticket)


@router.get("/tickets", response_model=list[SaleTicketPublic])
def list_sale_tickets(
    seller_user_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> list[SaleTicketPublic]:
    rows = list_tickets(db, seller_user_id=seller_user_id, status=status_filter)
    return [SaleTicketPublic.model_validate(row) for row in rows]


@router.get("/tickets/{ticket_id}", response_model=SaleTicketDetails)
def get_ticket_details(
    ticket_id: int,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketDetails:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    lines = get_ticket_lines(db, ticket_id)
    subtotal, total = compute_ticket_totals(ticket, lines)
    return SaleTicketDetails(
        ticket=SaleTicketPublic.model_validate(ticket),
        lines=[line for line in lines],
        subtotal_cents=subtotal,
        total_cents=total,
    )


@router.post("/tickets/{ticket_id}/lines/product", response_model=SaleTicketDetails)
def add_ticket_product_line(
    ticket_id: int,
    payload: SaleTicketLineAddProduct,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketDetails:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    try:
        add_product_line(db, ticket_id, payload.product_item_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    lines = get_ticket_lines(db, ticket_id)
    subtotal, total = compute_ticket_totals(ticket, lines)
    return SaleTicketDetails(
        ticket=SaleTicketPublic.model_validate(ticket),
        lines=[line for line in lines],
        subtotal_cents=subtotal,
        total_cents=total,
    )


@router.post("/tickets/{ticket_id}/lines/service", response_model=SaleTicketDetails)
def add_ticket_service_line(
    ticket_id: int,
    payload: SaleTicketLineAddService,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketDetails:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    try:
        add_service_line(db, ticket_id, payload.service_offering_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    lines = get_ticket_lines(db, ticket_id)
    subtotal, total = compute_ticket_totals(ticket, lines)
    return SaleTicketDetails(
        ticket=SaleTicketPublic.model_validate(ticket),
        lines=[line for line in lines],
        subtotal_cents=subtotal,
        total_cents=total,
    )


@router.patch("/tickets/{ticket_id}/customer", response_model=SaleTicketPublic)
def update_ticket_customer(
    ticket_id: int,
    payload: SaleTicketSetCustomer,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketPublic:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    try:
        ticket = set_ticket_customer(db, ticket_id, payload.customer_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SaleTicketPublic.model_validate(ticket)


@router.patch("/tickets/{ticket_id}/discount", response_model=SaleTicketDetails)
def update_ticket_discount(
    ticket_id: int,
    payload: SaleTicketSetDiscount,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketDetails:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    try:
        ticket = set_ticket_discount(db, ticket_id, payload.discount_cents)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    lines = get_ticket_lines(db, ticket_id)
    subtotal, total = compute_ticket_totals(ticket, lines)
    return SaleTicketDetails(
        ticket=SaleTicketPublic.model_validate(ticket),
        lines=[line for line in lines],
        subtotal_cents=subtotal,
        total_cents=total,
    )


@router.post("/tickets/{ticket_id}/suspend", response_model=SaleTicketPublic)
def suspend_ticket(
    ticket_id: int,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketPublic:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    try:
        ticket = set_ticket_status(db, ticket_id, "suspended")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SaleTicketPublic.model_validate(ticket)


@router.post("/tickets/{ticket_id}/resume", response_model=SaleTicketPublic)
def resume_ticket(
    ticket_id: int,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleTicketPublic:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    try:
        ticket = set_ticket_status(db, ticket_id, "draft")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return SaleTicketPublic.model_validate(ticket)


@router.post("/tickets/{ticket_id}/checkout", response_model=SaleCheckoutReceipt)
def checkout(
    ticket_id: int,
    payload: SaleTicketCheckout,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> SaleCheckoutReceipt:
    ticket = get_ticket_or_none(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    _assert_ticket_owner_or_manager(current_user, ticket)

    lines = get_ticket_lines(db, ticket_id)
    subtotal_before, _ = compute_ticket_totals(ticket, lines)

    try:
        paid_ticket, loyalty_points = checkout_ticket(db, ticket_id, payload.payment_method)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    paid_lines = get_ticket_lines(db, ticket_id)
    subtotal, total = compute_ticket_totals(paid_ticket, paid_lines)
    if subtotal == 0:
        subtotal = subtotal_before

    return SaleCheckoutReceipt(
        ticket=SaleTicketPublic.model_validate(paid_ticket),
        lines=[line for line in paid_lines],
        subtotal_cents=subtotal,
        discount_cents=paid_ticket.discount_cents,
        total_cents=total,
        loyalty_points_earned=loyalty_points,
    )
