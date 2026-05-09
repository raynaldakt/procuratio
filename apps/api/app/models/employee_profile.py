from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    is_bookable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    workday_start_minute: Mapped[int] = mapped_column(Integer, default=9 * 60, nullable=False)
    workday_end_minute: Mapped[int] = mapped_column(Integer, default=19 * 60, nullable=False)
    slot_step_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
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
