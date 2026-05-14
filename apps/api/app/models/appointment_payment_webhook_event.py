from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppointmentPaymentWebhookEvent(Base):
    __tablename__ = "appointment_payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_appt_payment_webhook_provider_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    detail: Mapped[str | None] = mapped_column(String(250), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
