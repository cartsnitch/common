"""NormalizedProduct model — the canonical product identity."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cartsnitch_common.constants import ProductCategory, SizeUnit
from cartsnitch_common.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from cartsnitch_common.models.coupon import Coupon
    from cartsnitch_common.models.price import PriceHistory
    from cartsnitch_common.models.purchase import PurchaseItem
    from cartsnitch_common.models.shrinkflation import ShrinkflationEvent


class NormalizedProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canonical product identity — matches products across retailers."""

    __tablename__ = "normalized_products"

    canonical_name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[ProductCategory | None] = mapped_column(String(50))
    subcategory: Mapped[str | None] = mapped_column(String(100))
    brand: Mapped[str | None] = mapped_column(String(200))
    size: Mapped[str | None] = mapped_column(String(50))
    size_unit: Mapped[SizeUnit | None] = mapped_column(String(10))
    upc_variants: Mapped[list[str] | None] = mapped_column(JSON, default=list)

    # Relationships
    purchase_items: Mapped[list["PurchaseItem"]] = relationship(back_populates="normalized_product")
    price_histories: Mapped[list["PriceHistory"]] = relationship(
        back_populates="normalized_product"
    )
    coupons: Mapped[list["Coupon"]] = relationship(back_populates="normalized_product")
    shrinkflation_events: Mapped[list["ShrinkflationEvent"]] = relationship(
        back_populates="normalized_product"
    )
