"""Purchase and PurchaseItem models."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cartsnitch_common.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from cartsnitch_common.models.price import PriceHistory
    from cartsnitch_common.models.product import NormalizedProduct
    from cartsnitch_common.models.store import Store, StoreLocation
    from cartsnitch_common.models.user import User


class Purchase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single shopping trip / receipt."""

    __tablename__ = "purchases"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    store_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("store_locations.id"))
    receipt_id: Mapped[str] = mapped_column(String(200), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    tax: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    savings_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    source_url: Mapped[str | None] = mapped_column(String(500))
    raw_data: Mapped[dict | None] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="purchases")
    store: Mapped["Store"] = relationship(back_populates="purchases")
    store_location: Mapped["StoreLocation | None"] = relationship(back_populates="purchases")
    items: Mapped[list["PurchaseItem"]] = relationship(back_populates="purchase")

    __table_args__ = (
        Index("ix_purchases_user_store", "user_id", "store_id"),
        UniqueConstraint("user_id", "store_id", "receipt_id", name="uq_purchase_receipt"),
    )


class PurchaseItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Individual line item on a receipt."""

    __tablename__ = "purchase_items"

    purchase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchases.id"), nullable=False)
    product_name_raw: Mapped[str] = mapped_column(String(300), nullable=False)
    upc: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    extended_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    regular_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    coupon_discount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    loyalty_discount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    category_raw: Mapped[str | None] = mapped_column(String(100))
    normalized_product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("normalized_products.id")
    )

    # Relationships
    purchase: Mapped["Purchase"] = relationship(back_populates="items")
    normalized_product: Mapped["NormalizedProduct | None"] = relationship(
        back_populates="purchase_items"
    )
    price_history_entries: Mapped[list["PriceHistory"]] = relationship(
        back_populates="purchase_item"
    )
