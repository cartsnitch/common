"""Price history tracking — record prices and detect deltas.

On each purchase ingestion, writes price_history records and detects
price changes from previous entries for the same product+store.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from cartsnitch_common.constants import PriceSource
from cartsnitch_common.models.price import PriceHistory


@dataclass(frozen=True)
class PriceDelta:
    """A detected price change for a product at a store."""

    product_id: uuid.UUID
    store_id: uuid.UUID
    old_price: Decimal
    new_price: Decimal
    change_amount: Decimal
    change_percent: Decimal
    old_date: date
    new_date: date

    @property
    def is_increase(self) -> bool:
        return self.change_amount > 0

    @property
    def is_decrease(self) -> bool:
        return self.change_amount < 0


def get_latest_price(
    session: Session,
    product_id: uuid.UUID,
    store_id: uuid.UUID,
) -> PriceHistory | None:
    """Get the most recent price entry for a product at a store."""
    stmt = (
        select(PriceHistory)
        .where(
            and_(
                PriceHistory.normalized_product_id == product_id,
                PriceHistory.store_id == store_id,
            )
        )
        .order_by(PriceHistory.observed_date.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def record_price_from_item(
    session: Session,
    product_id: uuid.UUID,
    store_id: uuid.UUID,
    observed_date: date,
    regular_price: Decimal,
    sale_price: Decimal | None = None,
    loyalty_price: Decimal | None = None,
    coupon_price: Decimal | None = None,
    purchase_item_id: uuid.UUID | None = None,
    source: PriceSource = PriceSource.RECEIPT,
) -> tuple[PriceHistory, PriceDelta | None]:
    """Record a price observation and return any detected delta.

    Returns (price_history_entry, price_delta_or_none).
    """
    previous = get_latest_price(session, product_id, store_id)

    entry = PriceHistory(
        id=uuid.uuid4(),
        normalized_product_id=product_id,
        store_id=store_id,
        observed_date=observed_date,
        regular_price=regular_price,
        sale_price=sale_price,
        loyalty_price=loyalty_price,
        coupon_price=coupon_price,
        source=source,
        purchase_item_id=purchase_item_id,
    )
    session.add(entry)
    session.flush()

    delta = None
    if previous and previous.regular_price != regular_price:
        change = regular_price - previous.regular_price
        pct = (change / previous.regular_price * 100) if previous.regular_price else Decimal("0")
        delta = PriceDelta(
            product_id=product_id,
            store_id=store_id,
            old_price=previous.regular_price,
            new_price=regular_price,
            change_amount=change,
            change_percent=pct.quantize(Decimal("0.01")),
            old_date=previous.observed_date,
            new_date=observed_date,
        )

    return entry, delta


def get_price_trend(
    session: Session,
    product_id: uuid.UUID,
    store_id: uuid.UUID,
    limit: int = 30,
) -> list[PriceHistory]:
    """Get recent price history for a product at a store, newest first."""
    stmt = (
        select(PriceHistory)
        .where(
            and_(
                PriceHistory.normalized_product_id == product_id,
                PriceHistory.store_id == store_id,
            )
        )
        .order_by(PriceHistory.observed_date.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().all())
