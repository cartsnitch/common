"""Store and StoreLocation models."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cartsnitch_common.constants import StoreSlug
from cartsnitch_common.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from cartsnitch_common.models.coupon import Coupon
    from cartsnitch_common.models.price import PriceHistory
    from cartsnitch_common.models.purchase import Purchase
    from cartsnitch_common.models.user import UserStoreAccount


class Store(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Supported retailer."""

    __tablename__ = "stores"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[StoreSlug] = mapped_column(String(20), nullable=False, unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    locations: Mapped[list["StoreLocation"]] = relationship(back_populates="store")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="store")
    user_accounts: Mapped[list["UserStoreAccount"]] = relationship(back_populates="store")
    price_histories: Mapped[list["PriceHistory"]] = relationship(back_populates="store")
    coupons: Mapped[list["Coupon"]] = relationship(back_populates="store")


class StoreLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical store location."""

    __tablename__ = "store_locations"

    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip: Mapped[str] = mapped_column(String(10), nullable=False)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="locations")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="store_location")
