"""Store and StoreLocation Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from cartsnitch_common.constants import StoreSlug


class StoreCreate(BaseModel):
    name: str
    slug: StoreSlug
    logo_url: str | None = None
    website_url: str | None = None


class StoreRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: StoreSlug
    logo_url: str | None
    website_url: str | None
    created_at: datetime
    updated_at: datetime


class StoreLocationCreate(BaseModel):
    store_id: uuid.UUID
    address: str
    city: str
    state: str
    zip: str
    lat: float | None = None
    lng: float | None = None


class StoreLocationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    address: str
    city: str
    state: str
    zip: str
    lat: float | None
    lng: float | None
    created_at: datetime
    updated_at: datetime
