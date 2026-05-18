from datetime import date, datetime, timedelta, timezone
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models.customer_profile import CustomerProfile
from app.models.loyalty_subscription import LoyaltySubscription
from app.models.loyalty_transaction import LoyaltyTransaction
from app.models.user import User
from app.services.auth import ensure_auth_schema

_schema_lock = Lock()
_schema_ready = False

POINTS_PER_EURO = 1


def ensure_customer_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    ensure_auth_schema()
    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(
            bind=engine,
            tables=[CustomerProfile.__table__, LoyaltyTransaction.__table__, LoyaltySubscription.__table__],
            checkfirst=True,
        )
        _schema_ready = True


def _get_user_or_none(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_or_create_profile(db: Session, user_id: int) -> CustomerProfile:
    ensure_customer_schema()

    profile = db.get(CustomerProfile, user_id)
    if profile is not None:
        return profile

    if _get_user_or_none(db, user_id) is None:
        raise ValueError("User not found")

    profile = CustomerProfile(user_id=user_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_own_profile(
    db: Session,
    user_id: int,
    updates: dict,
) -> CustomerProfile:
    profile = get_or_create_profile(db, user_id)
    for key, value in updates.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


def update_staff_notes(db: Session, user_id: int, staff_notes: str | None) -> CustomerProfile:
    profile = get_or_create_profile(db, user_id)
    profile.staff_notes = staff_notes
    db.commit()
    db.refresh(profile)
    return profile


def _add_loyalty_transaction(
    db: Session,
    user_id: int,
    kind: str,
    points_delta: int,
    source_amount_cents: int | None,
    description: str | None,
    created_by_user_id: int | None,
) -> LoyaltyTransaction:
    if _get_user_or_none(db, user_id) is None:
        raise ValueError("User not found")

    profile = get_or_create_profile(db, user_id)
    profile.points_balance = max(0, profile.points_balance + points_delta)

    txn = LoyaltyTransaction(
        user_id=user_id,
        kind=kind,
        points_delta=points_delta,
        source_amount_cents=source_amount_cents,
        description=description,
        created_by_user_id=created_by_user_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def register_purchase(
    db: Session,
    user_id: int,
    amount_spent_cents: int,
    description: str | None,
    created_by_user_id: int,
) -> LoyaltyTransaction:
    profile = get_or_create_profile(db, user_id)

    points = (amount_spent_cents // 100) * POINTS_PER_EURO
    profile.total_spent_cents += amount_spent_cents

    txn = _add_loyalty_transaction(
        db=db,
        user_id=user_id,
        kind="purchase",
        points_delta=points,
        source_amount_cents=amount_spent_cents,
        description=description,
        created_by_user_id=created_by_user_id,
    )
    return txn


def register_visit(
    db: Session,
    user_id: int,
    bonus_points: int,
    description: str | None,
    created_by_user_id: int,
) -> LoyaltyTransaction:
    profile = get_or_create_profile(db, user_id)
    profile.total_visits += 1
    profile.last_visit_at = datetime.now(timezone.utc)

    txn = _add_loyalty_transaction(
        db=db,
        user_id=user_id,
        kind="visit",
        points_delta=bonus_points,
        source_amount_cents=None,
        description=description,
        created_by_user_id=created_by_user_id,
    )
    return txn


def adjust_points(
    db: Session,
    user_id: int,
    points_delta: int,
    description: str,
    created_by_user_id: int,
) -> LoyaltyTransaction:
    return _add_loyalty_transaction(
        db=db,
        user_id=user_id,
        kind="manual_adjustment",
        points_delta=points_delta,
        source_amount_cents=None,
        description=description,
        created_by_user_id=created_by_user_id,
    )


def get_loyalty_transactions_for_user(db: Session, user_id: int, limit: int = 50) -> list[LoyaltyTransaction]:
    ensure_customer_schema()
    stmt = (
        select(LoyaltyTransaction)
        .where(LoyaltyTransaction.user_id == user_id)
        .order_by(LoyaltyTransaction.created_at.desc(), LoyaltyTransaction.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def list_subscriptions_for_user(db: Session, user_id: int, limit: int = 50) -> list[LoyaltySubscription]:
    ensure_customer_schema()
    _refresh_subscription_statuses(db, user_id=user_id)
    stmt = (
        select(LoyaltySubscription)
        .where(LoyaltySubscription.user_id == user_id)
        .order_by(LoyaltySubscription.created_at.desc(), LoyaltySubscription.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def _refresh_subscription_statuses(db: Session, user_id: int | None = None) -> None:
    ensure_customer_schema()
    today = date.today()
    stmt = select(LoyaltySubscription)
    if user_id is not None:
        stmt = stmt.where(LoyaltySubscription.user_id == user_id)

    rows = list(db.scalars(stmt).all())
    changed = False
    for sub in rows:
        if sub.status == "cancelled":
            continue
        if sub.ends_on < today and sub.status != "expired":
            sub.status = "expired"
            changed = True
        elif sub.starts_on <= today <= sub.ends_on and sub.status != "active":
            sub.status = "active"
            changed = True
        elif today < sub.starts_on and sub.status != "scheduled":
            sub.status = "scheduled"
            changed = True
    if changed:
        db.commit()


def create_subscription(
    db: Session,
    *,
    user_id: int,
    plan_name: str,
    amount_cents: int,
    duration_days: int,
    starts_on: date | None,
    payment_method: str,
    bonus_points_granted: int,
    created_by_user_id: int,
) -> LoyaltySubscription:
    ensure_customer_schema()
    if _get_user_or_none(db, user_id) is None:
        raise ValueError("User not found")

    _refresh_subscription_statuses(db, user_id=user_id)

    effective_start = starts_on or date.today()
    effective_end = effective_start + timedelta(days=duration_days - 1)
    active_overlap_stmt = select(LoyaltySubscription.id).where(
        LoyaltySubscription.user_id == user_id,
        LoyaltySubscription.status.in_(["active", "scheduled"]),
        LoyaltySubscription.ends_on >= effective_start,
        LoyaltySubscription.starts_on <= effective_end,
    )
    if db.scalar(active_overlap_stmt) is not None:
        raise ValueError("An active or scheduled subscription already overlaps this period")

    today = date.today()
    if effective_end < today:
        status = "expired"
    elif effective_start > today:
        status = "scheduled"
    else:
        status = "active"

    sub = LoyaltySubscription(
        user_id=user_id,
        plan_name=plan_name.strip(),
        amount_cents=amount_cents,
        starts_on=effective_start,
        ends_on=effective_end,
        status=status,
        payment_method=payment_method,
        bonus_points_granted=bonus_points_granted,
        created_by_user_id=created_by_user_id,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    if bonus_points_granted > 0:
        _add_loyalty_transaction(
            db=db,
            user_id=user_id,
            kind="subscription_bonus",
            points_delta=bonus_points_granted,
            source_amount_cents=amount_cents,
            description=f"Subscription: {sub.plan_name}",
            created_by_user_id=created_by_user_id,
        )
        db.refresh(sub)

    return sub


def cancel_subscription(
    db: Session,
    *,
    subscription_id: int,
) -> LoyaltySubscription | None:
    ensure_customer_schema()
    sub = db.get(LoyaltySubscription, subscription_id)
    if sub is None:
        return None
    if sub.status == "cancelled":
        return sub

    sub.status = "cancelled"
    sub.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sub)
    return sub
