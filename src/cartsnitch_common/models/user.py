"""User and UserStoreAccount models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cartsnitch_common.constants import AccountStatus
from cartsnitch_common.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from cartsnitch_common.models.purchase import Purchase
    from cartsnitch_common.models.store import Store


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Application user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    store_accounts: Mapped[list["UserStoreAccount"]] = relationship(back_populates="user")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="user")


class UserStoreAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Link between a user and their retailer account credentials."""

    __tablename__ = "user_store_accounts"
    __table_args__ = (UniqueConstraint("user_id", "store_id", name="uq_user_store_account"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    store_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    # WARNING: Contains retailer session cookies/tokens. Encryption-at-rest
    # required before production deployment (e.g., pgcrypto or app-level encryption).
    session_data: Mapped[dict | None] = mapped_column(JSON)
    session_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[AccountStatus] = mapped_column(
        String(20), nullable=False, default=AccountStatus.ACTIVE
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="store_accounts")
    store: Mapped["Store"] = relationship(back_populates="user_accounts")
