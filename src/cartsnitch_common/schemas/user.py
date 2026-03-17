"""User and UserStoreAccount Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from cartsnitch_common.constants import AccountStatus


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    display_name: str | None
    created_at: datetime
    updated_at: datetime


class UserStoreAccountCreate(BaseModel):
    user_id: uuid.UUID
    store_id: uuid.UUID
    session_data: dict | None = None
    status: AccountStatus = AccountStatus.ACTIVE


class UserStoreAccountRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    store_id: uuid.UUID
    status: AccountStatus
    session_expires_at: datetime | None
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime
