from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer import (
    LoyaltySubscriptionCreate,
    LoyaltySubscriptionPublic,
    LoyaltyAdjustmentRequest,
    LoyaltyPurchaseRequest,
    LoyaltyTransactionPublic,
    LoyaltyVisitRequest,
)
from app.services.customer import adjust_points, get_loyalty_transactions_for_user, register_purchase, register_visit
from app.services.customer import cancel_subscription, create_subscription, list_subscriptions_for_user

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("/me/transactions", response_model=list[LoyaltyTransactionPublic])
def list_my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LoyaltyTransactionPublic]:
    rows = get_loyalty_transactions_for_user(db, current_user.id)
    return [LoyaltyTransactionPublic.model_validate(row) for row in rows]


@router.get("/users/{user_id}/transactions", response_model=list[LoyaltyTransactionPublic])
def list_user_transactions(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "staff")),
) -> list[LoyaltyTransactionPublic]:
    rows = get_loyalty_transactions_for_user(db, user_id)
    return [LoyaltyTransactionPublic.model_validate(row) for row in rows]


@router.post("/earn-purchase", response_model=LoyaltyTransactionPublic)
def earn_purchase_points(
    payload: LoyaltyPurchaseRequest,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> LoyaltyTransactionPublic:
    try:
        txn = register_purchase(
            db=db,
            user_id=payload.user_id,
            amount_spent_cents=payload.amount_spent_cents,
            description=payload.description,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LoyaltyTransactionPublic.model_validate(txn)


@router.post("/register-visit", response_model=LoyaltyTransactionPublic)
def register_visit_loyalty(
    payload: LoyaltyVisitRequest,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> LoyaltyTransactionPublic:
    try:
        txn = register_visit(
            db=db,
            user_id=payload.user_id,
            bonus_points=payload.bonus_points,
            description=payload.description,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LoyaltyTransactionPublic.model_validate(txn)


@router.post("/adjust-points", response_model=LoyaltyTransactionPublic)
def adjust_loyalty_points(
    payload: LoyaltyAdjustmentRequest,
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
) -> LoyaltyTransactionPublic:
    try:
        txn = adjust_points(
            db=db,
            user_id=payload.user_id,
            points_delta=payload.points_delta,
            description=payload.description,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LoyaltyTransactionPublic.model_validate(txn)


@router.get("/me/subscriptions", response_model=list[LoyaltySubscriptionPublic])
def list_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LoyaltySubscriptionPublic]:
    rows = list_subscriptions_for_user(db, current_user.id)
    return [LoyaltySubscriptionPublic.model_validate(row) for row in rows]


@router.get("/users/{user_id}/subscriptions", response_model=list[LoyaltySubscriptionPublic])
def list_user_subscriptions(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager", "staff")),
) -> list[LoyaltySubscriptionPublic]:
    rows = list_subscriptions_for_user(db, user_id)
    return [LoyaltySubscriptionPublic.model_validate(row) for row in rows]


@router.post("/subscriptions", response_model=LoyaltySubscriptionPublic, status_code=status.HTTP_201_CREATED)
def create_loyalty_subscription(
    payload: LoyaltySubscriptionCreate,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> LoyaltySubscriptionPublic:
    try:
        row = create_subscription(
            db=db,
            user_id=payload.user_id,
            plan_name=payload.plan_name,
            amount_cents=payload.amount_cents,
            duration_days=payload.duration_days,
            starts_on=payload.starts_on,
            payment_method=payload.payment_method,
            bonus_points_granted=payload.bonus_points_granted,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return LoyaltySubscriptionPublic.model_validate(row)


@router.post("/subscriptions/{subscription_id}/cancel", response_model=LoyaltySubscriptionPublic)
def cancel_loyalty_subscription(
    subscription_id: int,
    _: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
) -> LoyaltySubscriptionPublic:
    row = cancel_subscription(db, subscription_id=subscription_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return LoyaltySubscriptionPublic.model_validate(row)
