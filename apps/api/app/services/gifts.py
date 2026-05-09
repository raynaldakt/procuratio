from datetime import date, datetime, time, timedelta, timezone
from secrets import token_hex
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models.gift_voucher import GiftVoucher
from app.models.gift_voucher_redemption import GiftVoucherRedemption
from app.models.service_offering import ServiceOffering
from app.services.sales import ensure_sales_schema

_schema_lock = Lock()
_schema_ready = False


def ensure_gifts_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    ensure_sales_schema()
    with _schema_lock:
        if _schema_ready:
            return
        Base.metadata.create_all(
            bind=engine,
            tables=[GiftVoucher.__table__, GiftVoucherRedemption.__table__],
            checkfirst=True,
        )
        _schema_ready = True


def _generate_code() -> str:
    return f"GV-{token_hex(6).upper()}"


def _next_unique_code(db: Session) -> str:
    for _ in range(20):
        code = _generate_code()
        exists = db.scalar(select(GiftVoucher.id).where(GiftVoucher.code == code))
        if exists is None:
            return code
    raise ValueError("Could not generate a unique voucher code")


def _compute_expiry(effective_date: date, duration_days: int) -> datetime:
    end_date = effective_date + timedelta(days=duration_days)
    return datetime.combine(end_date, time.max, tzinfo=timezone.utc)


def create_voucher(
    db: Session,
    *,
    voucher_type: str,
    service_offering_id: int | None,
    amount_cents: int | None,
    purchaser_name: str,
    recipient_name: str,
    recipient_email: str | None,
    effective_date: date,
    duration_days: int,
    created_by_user_id: int,
) -> GiftVoucher:
    ensure_gifts_schema()

    if voucher_type not in {"amount", "service"}:
        raise ValueError("Unsupported voucher type")

    initial_amount = 0
    if voucher_type == "amount":
        if amount_cents is None or amount_cents <= 0:
            raise ValueError("amount_cents is required for amount voucher")
        initial_amount = amount_cents
    else:
        if service_offering_id is None:
            raise ValueError("service_offering_id is required for service voucher")
        service = db.get(ServiceOffering, service_offering_id)
        if service is None or not service.is_active:
            raise ValueError("Service offering not found")
        initial_amount = service.price_cents

    code = _next_unique_code(db)
    expires_at = _compute_expiry(effective_date, duration_days)

    voucher = GiftVoucher(
        code=code,
        voucher_type=voucher_type,
        service_offering_id=service_offering_id,
        initial_amount_cents=initial_amount,
        remaining_amount_cents=initial_amount,
        purchaser_name=purchaser_name.strip(),
        recipient_name=recipient_name.strip(),
        recipient_email=recipient_email,
        effective_date=effective_date,
        expires_at=expires_at,
        status="active",
        created_by_user_id=created_by_user_id,
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return voucher


def list_vouchers(db: Session, status: str | None, code: str | None) -> list[GiftVoucher]:
    ensure_gifts_schema()
    stmt = select(GiftVoucher)
    if status:
        stmt = stmt.where(GiftVoucher.status == status)
    if code:
        stmt = stmt.where(GiftVoucher.code == code)
    stmt = stmt.order_by(GiftVoucher.created_at.desc()).limit(300)
    return list(db.scalars(stmt).all())


def _is_expired(voucher: GiftVoucher) -> bool:
    return datetime.now(timezone.utc) > voucher.expires_at


def validate_voucher(voucher: GiftVoucher) -> None:
    if voucher.status == "cancelled":
        raise ValueError("Voucher is cancelled")
    if _is_expired(voucher):
        voucher.status = "expired"
        raise ValueError("Voucher is expired")
    if datetime.now(timezone.utc).date() < voucher.effective_date:
        raise ValueError("Voucher is not active yet")
    if voucher.remaining_amount_cents <= 0:
        voucher.status = "redeemed"
        raise ValueError("Voucher has no remaining amount")


def redeem_voucher(
    db: Session,
    *,
    voucher_id: int,
    amount_cents: int | None,
    notes: str | None,
    redeemed_by_user_id: int,
) -> tuple[GiftVoucher, GiftVoucherRedemption]:
    ensure_gifts_schema()

    voucher = db.get(GiftVoucher, voucher_id)
    if voucher is None:
        raise ValueError("Voucher not found")

    validate_voucher(voucher)

    redeem_amount = voucher.remaining_amount_cents if amount_cents is None else amount_cents
    if redeem_amount <= 0:
        raise ValueError("Redeem amount must be positive")
    if redeem_amount > voucher.remaining_amount_cents:
        raise ValueError("Redeem amount exceeds remaining amount")

    voucher.remaining_amount_cents -= redeem_amount
    if voucher.remaining_amount_cents == 0:
        voucher.status = "redeemed"

    redemption = GiftVoucherRedemption(
        voucher_id=voucher.id,
        redeemed_amount_cents=redeem_amount,
        notes=notes,
        redeemed_by_user_id=redeemed_by_user_id,
    )
    db.add(redemption)
    db.commit()
    db.refresh(voucher)
    db.refresh(redemption)
    return voucher, redemption


def list_redemptions(db: Session, voucher_id: int) -> list[GiftVoucherRedemption]:
    ensure_gifts_schema()
    stmt = (
        select(GiftVoucherRedemption)
        .where(GiftVoucherRedemption.voucher_id == voucher_id)
        .order_by(GiftVoucherRedemption.created_at.desc())
        .limit(200)
    )
    return list(db.scalars(stmt).all())


def cancel_voucher(db: Session, voucher_id: int) -> GiftVoucher | None:
    ensure_gifts_schema()
    voucher = db.get(GiftVoucher, voucher_id)
    if voucher is None:
        return None

    if voucher.status == "redeemed":
        raise ValueError("Redeemed voucher cannot be cancelled")

    voucher.status = "cancelled"
    db.commit()
    db.refresh(voucher)
    return voucher
