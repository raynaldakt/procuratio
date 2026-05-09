from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SaleTicketLine(Base):
    __tablename__ = "sale_ticket_lines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("sale_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    line_type: Mapped[str] = mapped_column(String(24), nullable=False)
    product_item_id: Mapped[int | None] = mapped_column(ForeignKey("product_items.id", ondelete="RESTRICT"), nullable=True)
    service_offering_id: Mapped[int | None] = mapped_column(ForeignKey("service_offerings.id", ondelete="RESTRICT"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
