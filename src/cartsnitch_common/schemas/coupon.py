"""Coupon Pydantic schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from cartsnitch_common.constants import DiscountType


class CouponCreate(BaseModel):
    store_id: uuid.UUID
    normalized_product_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    discount_type: DiscountType
    discount_value: Decimal | None = None
    min_purchase: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    requires_clip: bool = False
    coupon_code: str | None = None
    source_url: str | None = None


class CouponRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    normalized_product_id: uuid.UUID | None
    title: str
    description: str | None
    discount_type: DiscountType
    discount_value: Decimal | None
    min_purchase: Decimal | None
    valid_from: date | None
    valid_to: date | None
    requires_clip: bool
    coupon_code: str | None
    source_url: str | None
    scraped_at: datetime | None
    created_at: datetime
    updated_at: datetime
