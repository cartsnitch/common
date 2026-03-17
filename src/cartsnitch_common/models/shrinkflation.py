"""ShrinkflationEvent model."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cartsnitch_common.constants import SizeUnit
from cartsnitch_common.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from cartsnitch_common.models.product import NormalizedProduct


class ShrinkflationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Detected shrinkflation event — product size changed while price held or rose."""

    __tablename__ = "shrinkflation_events"

    normalized_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normalized_products.id"), nullable=False
    )
    detected_date: Mapped[date] = mapped_column(Date, nullable=False)
    old_size: Mapped[str] = mapped_column(String(50), nullable=False)
    new_size: Mapped[str] = mapped_column(String(50), nullable=False)
    old_unit: Mapped[SizeUnit] = mapped_column(String(10), nullable=False)
    new_unit: Mapped[SizeUnit] = mapped_column(String(10), nullable=False)
    price_at_old_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_at_new_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("1.00")
    )
    notes: Mapped[str | None] = mapped_column(String(1000))

    # Relationships
    normalized_product: Mapped["NormalizedProduct"] = relationship(
        back_populates="shrinkflation_events"
    )
