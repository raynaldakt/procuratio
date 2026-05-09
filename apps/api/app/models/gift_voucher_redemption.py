from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GiftVoucherRedemption(Base):
    __tablename__ = "gift_voucher_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    voucher_id: Mapped[int] = mapped_column(ForeignKey("gift_vouchers.id", ondelete="CASCADE"), index=True, nullable=False)
    redeemed_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    redeemed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
