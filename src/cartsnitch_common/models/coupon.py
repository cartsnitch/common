"""Coupon model."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cartsnitch_common.constants import DiscountType
from cartsnitch_common.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from cartsnitch_common.models.product import NormalizedProduct
    from cartsnitch_common.models.store import Store


class Coupon(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A coupon or deal for a product at a store."""

    __tablename__ = "coupons"

    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id"), nullable=False
    )
    normalized_product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("normalized_products.id")
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    discount_type: Mapped[DiscountType] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    min_purchase: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    requires_clip: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(500))
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="coupons")
    normalized_product: Mapped["NormalizedProduct | None"] = relationship(
        back_populates="coupons"
    )
