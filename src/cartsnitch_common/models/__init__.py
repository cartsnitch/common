"""SQLAlchemy ORM models — re-exports all models for convenience."""

from cartsnitch_common.models.base import Base, TimestampMixin
from cartsnitch_common.models.coupon import Coupon
from cartsnitch_common.models.price import PriceHistory
from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.models.purchase import Purchase, PurchaseItem
from cartsnitch_common.models.shrinkflation import ShrinkflationEvent
from cartsnitch_common.models.store import Store, StoreLocation
from cartsnitch_common.models.user import User, UserStoreAccount

__all__ = [
    "Base",
    "TimestampMixin",
    "Store",
    "StoreLocation",
    "User",
    "UserStoreAccount",
    "Purchase",
    "PurchaseItem",
    "NormalizedProduct",
    "PriceHistory",
    "Coupon",
    "ShrinkflationEvent",
]
