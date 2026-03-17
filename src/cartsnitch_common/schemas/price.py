"""PriceHistory Pydantic schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from cartsnitch_common.constants import PriceSource


class PriceHistoryCreate(BaseModel):
    normalized_product_id: uuid.UUID
    store_id: uuid.UUID
    observed_date: date
    regular_price: Decimal
    sale_price: Decimal | None = None
    loyalty_price: Decimal | None = None
    coupon_price: Decimal | None = None
    source: PriceSource
    purchase_item_id: uuid.UUID | None = None


class PriceHistoryRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    normalized_product_id: uuid.UUID
    store_id: uuid.UUID
    observed_date: date
    regular_price: Decimal
    sale_price: Decimal | None
    loyalty_price: Decimal | None
    coupon_price: Decimal | None
    source: PriceSource
    purchase_item_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
