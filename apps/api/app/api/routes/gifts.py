from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.gifts import (
    GiftVoucherCreate,
    GiftVoucherPublic,
    GiftVoucherRedeemRequest,
    GiftVoucherRedeemResponse,
    GiftVoucherRedemptionPublic,
)
from app.services.gifts import cancel_voucher, create_voucher, list_redemptions, list_vouchers, redeem_voucher

router = APIRouter(prefix="/gifts", tags=["gifts"])


@router.post("/vouchers", response_model=GiftVoucherPublic, status_code=status.HTTP_201_CREATED)
def create_gift_voucher(
    payload: GiftVoucherCreate,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> GiftVoucherPublic:
    try:
        voucher = create_voucher(
            db,
            voucher_type=payload.voucher_type,
            service_offering_id=payload.service_offering_id,
            amount_cents=payload.amount_cents,
            purchaser_name=payload.purchaser_name,
            recipient_name=payload.recipient_name,
            recipient_email=payload.recipient_email,
            effective_date=payload.effective_date,
            duration_days=payload.duration_days,
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return GiftVoucherPublic.model_validate(voucher)


@router.get("/vouchers", response_model=list[GiftVoucherPublic])
def get_vouchers(
    status_filter: str | None = Query(default=None, alias="status"),
    code: str | None = Query(default=None),
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> list[GiftVoucherPublic]:
    rows = list_vouchers(db, status_filter, code)
    return [GiftVoucherPublic.model_validate(row) for row in rows]


@router.post("/vouchers/{voucher_id}/redeem", response_model=GiftVoucherRedeemResponse)
def redeem_gift_voucher(
    voucher_id: int,
    payload: GiftVoucherRedeemRequest,
    current_user: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> GiftVoucherRedeemResponse:
    try:
        voucher, redemption = redeem_voucher(
            db,
            voucher_id=voucher_id,
            amount_cents=payload.amount_cents,
            notes=payload.notes,
            redeemed_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return GiftVoucherRedeemResponse(
        voucher=GiftVoucherPublic.model_validate(voucher),
        redemption=GiftVoucherRedemptionPublic.model_validate(redemption),
    )


@router.get("/vouchers/{voucher_id}/redemptions", response_model=list[GiftVoucherRedemptionPublic])
def get_voucher_redemptions(
    voucher_id: int,
    _: User = Depends(require_roles("admin", "manager", "staff")),
    db: Session = Depends(get_db),
) -> list[GiftVoucherRedemptionPublic]:
    rows = list_redemptions(db, voucher_id)
    return [GiftVoucherRedemptionPublic.model_validate(row) for row in rows]


@router.post("/vouchers/{voucher_id}/cancel", response_model=GiftVoucherPublic)
def cancel_gift_voucher(
    voucher_id: int,
    _: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
) -> GiftVoucherPublic:
    try:
        voucher = cancel_voucher(db, voucher_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if voucher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found")
    return GiftVoucherPublic.model_validate(voucher)
