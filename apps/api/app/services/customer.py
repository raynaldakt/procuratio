from datetime import datetime, timezone
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models.customer_profile import CustomerProfile
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
            tables=[CustomerProfile.__table__, LoyaltyTransaction.__table__],
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
