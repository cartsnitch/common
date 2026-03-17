"""Pydantic v2 schemas for inter-service API contracts."""

from cartsnitch_common.schemas.coupon import CouponCreate, CouponRead
from cartsnitch_common.schemas.events import EventEnvelope
from cartsnitch_common.schemas.price import PriceHistoryCreate, PriceHistoryRead
from cartsnitch_common.schemas.product import NormalizedProductCreate, NormalizedProductRead
from cartsnitch_common.schemas.purchase import (
    PurchaseCreate,
    PurchaseItemCreate,
    PurchaseItemRead,
    PurchaseRead,
)
from cartsnitch_common.schemas.shrinkflation import ShrinkflationEventCreate, ShrinkflationEventRead
from cartsnitch_common.schemas.store import (
    StoreCreate,
    StoreLocationCreate,
    StoreLocationRead,
    StoreRead,
)
from cartsnitch_common.schemas.user import (
    UserCreate,
    UserRead,
    UserStoreAccountCreate,
    UserStoreAccountRead,
)

__all__ = [
    "StoreCreate",
    "StoreRead",
    "StoreLocationCreate",
    "StoreLocationRead",
    "UserCreate",
    "UserRead",
    "UserStoreAccountCreate",
    "UserStoreAccountRead",
    "PurchaseCreate",
    "PurchaseRead",
    "PurchaseItemCreate",
    "PurchaseItemRead",
    "NormalizedProductCreate",
    "NormalizedProductRead",
    "PriceHistoryCreate",
    "PriceHistoryRead",
    "CouponCreate",
    "CouponRead",
    "ShrinkflationEventCreate",
    "ShrinkflationEventRead",
    "EventEnvelope",
]
