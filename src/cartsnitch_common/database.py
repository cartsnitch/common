"""Database engine and session factories for sync and async usage."""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from cartsnitch_common.config import settings


def get_async_engine(url: str | None = None):
    """Create an async SQLAlchemy engine."""
    return create_async_engine(url or settings.database_url, echo=settings.debug)


def get_sync_engine(url: str | None = None):
    """Create a sync SQLAlchemy engine."""
    return create_engine(url or settings.database_url_sync, echo=settings.debug)


def get_async_session_factory(url: str | None = None) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    engine = get_async_engine(url)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_sync_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Create a sync session factory."""
    engine = get_sync_engine(url)
    return sessionmaker(engine, expire_on_commit=False)


async def get_async_session(url: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Dependency for async session injection."""
    factory = get_async_session_factory(url)
    async with factory() as session:
        yield session


def get_sync_session(url: str | None = None) -> Generator[Session, None, None]:
    """Dependency for sync session injection."""
    factory = get_sync_session_factory(url)
    with factory() as session:
        yield session
