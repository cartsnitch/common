"""PriceHistory model — tracks product prices over time."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cartsnitch_common.constants import PriceSource
from cartsnitch_common.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from cartsnitch_common.models.product import NormalizedProduct
    from cartsnitch_common.models.purchase import PurchaseItem
    from cartsnitch_common.models.store import Store


class PriceHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single price observation for a product at a store on a date."""

    __tablename__ = "price_history"
    __table_args__ = (
        Index(
            "ix_price_history_product_store_date",
            "normalized_product_id",
            "store_id",
            "observed_date",
        ),
    )

    normalized_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("normalized_products.id"), nullable=False
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id"), nullable=False
    )
    observed_date: Mapped[date] = mapped_column(Date, nullable=False)
    regular_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    loyalty_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    coupon_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    source: Mapped[PriceSource] = mapped_column(String(20), nullable=False)
    purchase_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("purchase_items.id")
    )

    # Relationships
    normalized_product: Mapped["NormalizedProduct"] = relationship(
        back_populates="price_histories"
    )
    store: Mapped["Store"] = relationship(back_populates="price_histories")
    purchase_item: Mapped["PurchaseItem | None"] = relationship(
        back_populates="price_history_entries"
    )
