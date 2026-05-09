from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.sales import ProductPublic
from app.schemas.shop import (
    ProductReservationPublic,
    ReservationSweepResponse,
    ShopCartAddLine,
    ShopCartCreate,
    ShopCheckoutPurchase,
    ShopCheckoutPurchaseResponse,
    ShopCheckoutReserve,
    ShopOrderDetails,
    ShopOrderPublic,
)
from app.services.sales import search_products
from app.services.shop import (
    add_line_to_cart,
    cancel_reservation,
    checkout_purchase,
    checkout_reservation,
    collect_reservation,
    get_order_details,
    get_order_for_customer_or_none,
    get_or_create_cart,
    list_customer_orders,
    list_customer_reservations,
    remove_line_from_cart,
    sweep_expired_reservations,
)

router = APIRouter(prefix="/shop", tags=["shop"])


@router.get("/products", response_model=list[ProductPublic])
def list_products(
    q: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    product_type: str | None = Query(default=None),
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
) -> list[ProductPublic]:
    rows = search_products(db, q, brand, product_type, min_price_cents, max_price_cents)
    return [ProductPublic.model_validate(row) for row in rows]


@router.post("/cart", response_model=ShopOrderPublic, status_code=status.HTTP_201_CREATED)
def create_or_get_cart(
    payload: ShopCartCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopOrderPublic:
    order = get_or_create_cart(db, current_user.id, notes=payload.notes)
    return ShopOrderPublic.model_validate(order)


@router.get("/cart", response_model=ShopOrderDetails)
def get_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ShopOrderDetails:
    order = get_or_create_cart(db, current_user.id)
    o, lines = get_order_details(db, order)
    return ShopOrderDetails(order=ShopOrderPublic.model_validate(o), lines=lines)


@router.post("/cart/lines", response_model=ShopOrderDetails)
def add_cart_line(
    payload: ShopCartAddLine,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopOrderDetails:
    order = get_or_create_cart(db, current_user.id)
    try:
        add_line_to_cart(db, order, payload.product_item_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    o, lines = get_order_details(db, order)
    return ShopOrderDetails(order=ShopOrderPublic.model_validate(o), lines=lines)


@router.delete("/cart/lines/{line_id}", response_model=ShopOrderDetails)
def remove_cart_line(
    line_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopOrderDetails:
    order = get_or_create_cart(db, current_user.id)
    try:
        order = remove_line_from_cart(db, order, line_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    o, lines = get_order_details(db, order)
    return ShopOrderDetails(order=ShopOrderPublic.model_validate(o), lines=lines)


@router.post("/cart/checkout/purchase", response_model=ShopCheckoutPurchaseResponse)
def checkout_cart_purchase(
    payload: ShopCheckoutPurchase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopCheckoutPurchaseResponse:
    order = get_or_create_cart(db, current_user.id)
    try:
        order, points = checkout_purchase(db, order, payload.payment_method)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    _, lines = get_order_details(db, order)
    return ShopCheckoutPurchaseResponse(order=ShopOrderPublic.model_validate(order), lines=lines, loyalty_points_earned=points)


@router.post("/cart/checkout/reserve", response_model=ShopOrderDetails)
def checkout_cart_reserve(
    payload: ShopCheckoutReserve,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopOrderDetails:
    order = get_or_create_cart(db, current_user.id)
    try:
        order, _ = checkout_reservation(db, order, expires_in_hours=payload.expires_in_hours)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    _, lines = get_order_details(db, order)
    return ShopOrderDetails(order=ShopOrderPublic.model_validate(order), lines=lines)


@router.get("/orders/me", response_model=list[ShopOrderPublic])
def my_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ShopOrderPublic]:
    rows = list_customer_orders(db, current_user.id)
    return [ShopOrderPublic.model_validate(row) for row in rows]


@router.get("/reservations/me", response_model=list[ProductReservationPublic])
def my_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProductReservationPublic]:
    rows = list_customer_reservations(db, current_user.id)
    return [ProductReservationPublic.model_validate(row) for row in rows]


@router.post("/reservations/{reservation_id}/collect", response_model=ProductReservationPublic)
def collect(
    reservation_id: int,
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> ProductReservationPublic:
    try:
        row = collect_reservation(db, reservation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return ProductReservationPublic.model_validate(row)


@router.post("/reservations/{reservation_id}/cancel", response_model=ProductReservationPublic)
def cancel(
    reservation_id: int,
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> ProductReservationPublic:
    try:
        row = cancel_reservation(db, reservation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return ProductReservationPublic.model_validate(row)


@router.post("/reservations/sweep-expired", response_model=ReservationSweepResponse)
def sweep_expired(
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> ReservationSweepResponse:
    count = sweep_expired_reservations(db)
    return ReservationSweepResponse(expired_count=count)
