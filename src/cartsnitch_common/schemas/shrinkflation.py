"""ShrinkflationEvent Pydantic schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from cartsnitch_common.constants import SizeUnit


class ShrinkflationEventCreate(BaseModel):
    normalized_product_id: uuid.UUID
    detected_date: date
    old_size: str
    new_size: str
    old_unit: SizeUnit
    new_unit: SizeUnit
    price_at_old_size: Decimal | None = None
    price_at_new_size: Decimal | None = None
    confidence: Decimal = Decimal("1.00")
    notes: str | None = None


class ShrinkflationEventRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    normalized_product_id: uuid.UUID
    detected_date: date
    old_size: str
    new_size: str
    old_unit: SizeUnit
    new_unit: SizeUnit
    price_at_old_size: Decimal | None
    price_at_new_size: Decimal | None
    confidence: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
