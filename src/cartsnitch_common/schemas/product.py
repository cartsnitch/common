"""NormalizedProduct Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from cartsnitch_common.constants import ProductCategory, SizeUnit


class NormalizedProductCreate(BaseModel):
    canonical_name: str
    category: ProductCategory | None = None
    subcategory: str | None = None
    brand: str | None = None
    size: str | None = None
    size_unit: SizeUnit | None = None
    upc_variants: list[str] = []


class NormalizedProductRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    canonical_name: str
    category: ProductCategory | None
    subcategory: str | None
    brand: str | None
    size: str | None
    size_unit: SizeUnit | None
    upc_variants: list | None
    created_at: datetime
    updated_at: datetime
