"""Purchase and PurchaseItem Pydantic schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PurchaseItemCreate(BaseModel):
    product_name_raw: str
    upc: str | None = None
    quantity: Decimal = Decimal("1")
    unit_price: Decimal
    extended_price: Decimal
    regular_price: Decimal | None = None
    sale_price: Decimal | None = None
    coupon_discount: Decimal | None = None
    loyalty_discount: Decimal | None = None
    category_raw: str | None = None
    normalized_product_id: uuid.UUID | None = None


class PurchaseItemRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    purchase_id: uuid.UUID
    product_name_raw: str
    upc: str | None
    quantity: Decimal
    unit_price: Decimal
    extended_price: Decimal
    regular_price: Decimal | None
    sale_price: Decimal | None
    coupon_discount: Decimal | None
    loyalty_discount: Decimal | None
    category_raw: str | None
    normalized_product_id: uuid.UUID | None


class PurchaseCreate(BaseModel):
    user_id: uuid.UUID
    store_id: uuid.UUID
    store_location_id: uuid.UUID | None = None
    receipt_id: str
    purchase_date: date
    total: Decimal
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    savings_total: Decimal | None = None
    source_url: str | None = None
    raw_data: dict | None = None
    items: list[PurchaseItemCreate] = []


class PurchaseRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    store_id: uuid.UUID
    store_location_id: uuid.UUID | None
    receipt_id: str
    purchase_date: date
    total: Decimal
    subtotal: Decimal | None
    tax: Decimal | None
    savings_total: Decimal | None
    source_url: str | None
    ingested_at: datetime
    created_at: datetime
    updated_at: datetime
