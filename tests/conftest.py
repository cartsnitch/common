"""Shared test fixtures for cartsnitch-common tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cartsnitch_common.models.base import Base


@pytest.fixture
def engine():
    """In-memory SQLite engine for unit tests."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    """SQLAlchemy session bound to in-memory SQLite."""
    factory = sessionmaker(bind=engine)
    with factory() as sess:
        yield sess
