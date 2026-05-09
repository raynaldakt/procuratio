from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    marketing_email_opt_in: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    marketing_sms_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    staff_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    total_visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
