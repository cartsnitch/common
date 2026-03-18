"""Tests for price history tracking pipeline."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from cartsnitch_common.constants import PriceSource, StoreSlug
from cartsnitch_common.models.price import PriceHistory
from cartsnitch_common.models.product import NormalizedProduct
from cartsnitch_common.models.store import Store
from cartsnitch_common.pipeline.price_tracking import (
    PriceDelta,
    get_latest_price,
    get_price_trend,
    record_price_from_item,
)


def _make_store(session, slug=StoreSlug.MEIJER) -> Store:
    store = Store(
        id=uuid.uuid4(),
        name="Meijer",
        slug=slug,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(store)
    session.flush()
    return store


def _make_product(session, name="Test Product") -> NormalizedProduct:
    product = NormalizedProduct(
        id=uuid.uuid4(),
        canonical_name=name,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(product)
    session.flush()
    return product


class TestGetLatestPrice:
    def test_no_history(self, session):
        product = _make_product(session)
        store = _make_store(session)
        result = get_latest_price(session, product.id, store.id)
        assert result is None

    def test_returns_newest(self, session):
        product = _make_product(session)
        store = _make_store(session)

        # Add two entries
        old = PriceHistory(
            id=uuid.uuid4(),
            normalized_product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 1),
            regular_price=Decimal("3.99"),
            source=PriceSource.RECEIPT,
        )
        new = PriceHistory(
            id=uuid.uuid4(),
            normalized_product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 10),
            regular_price=Decimal("4.29"),
            source=PriceSource.RECEIPT,
        )
        session.add_all([old, new])
        session.flush()

        result = get_latest_price(session, product.id, store.id)
        assert result is not None
        assert result.regular_price == Decimal("4.29")


class TestRecordPriceFromItem:
    def test_first_price_no_delta(self, session):
        product = _make_product(session)
        store = _make_store(session)

        entry, delta = record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("3.99"),
        )
        assert entry is not None
        assert entry.regular_price == Decimal("3.99")
        assert entry.source == PriceSource.RECEIPT
        assert delta is None

    def test_price_increase_detected(self, session):
        product = _make_product(session)
        store = _make_store(session)

        # First price
        record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 1),
            regular_price=Decimal("3.99"),
        )

        # Price increase
        entry, delta = record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("4.49"),
        )

        assert delta is not None
        assert delta.old_price == Decimal("3.99")
        assert delta.new_price == Decimal("4.49")
        assert delta.change_amount == Decimal("0.50")
        assert delta.is_increase is True
        assert delta.is_decrease is False
        assert delta.change_percent > Decimal("0")

    def test_price_decrease_detected(self, session):
        product = _make_product(session)
        store = _make_store(session)

        record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 1),
            regular_price=Decimal("5.00"),
        )

        _, delta = record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("4.00"),
        )

        assert delta is not None
        assert delta.is_decrease is True
        assert delta.change_amount == Decimal("-1.00")

    def test_same_price_no_delta(self, session):
        product = _make_product(session)
        store = _make_store(session)

        record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 1),
            regular_price=Decimal("3.99"),
        )

        _, delta = record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("3.99"),
        )
        assert delta is None

    def test_sale_and_loyalty_prices_recorded(self, session):
        product = _make_product(session)
        store = _make_store(session)

        entry, _ = record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("5.99"),
            sale_price=Decimal("4.99"),
            loyalty_price=Decimal("4.49"),
            coupon_price=Decimal("3.99"),
        )
        assert entry.sale_price == Decimal("4.99")
        assert entry.loyalty_price == Decimal("4.49")
        assert entry.coupon_price == Decimal("3.99")

    def test_custom_source(self, session):
        product = _make_product(session)
        store = _make_store(session)

        entry, _ = record_price_from_item(
            session,
            product_id=product.id,
            store_id=store.id,
            observed_date=date(2026, 3, 15),
            regular_price=Decimal("3.99"),
            source=PriceSource.CATALOG,
        )
        assert entry.source == PriceSource.CATALOG


class TestGetPriceTrend:
    def test_empty_trend(self, session):
        product = _make_product(session)
        store = _make_store(session)
        trend = get_price_trend(session, product.id, store.id)
        assert trend == []

    def test_returns_newest_first(self, session):
        product = _make_product(session)
        store = _make_store(session)

        for day in [1, 5, 10, 15]:
            session.add(
                PriceHistory(
                    id=uuid.uuid4(),
                    normalized_product_id=product.id,
                    store_id=store.id,
                    observed_date=date(2026, 3, day),
                    regular_price=Decimal(str(3 + day * 0.1)),
                    source=PriceSource.RECEIPT,
                )
            )
        session.flush()

        trend = get_price_trend(session, product.id, store.id)
        assert len(trend) == 4
        assert trend[0].observed_date == date(2026, 3, 15)
        assert trend[-1].observed_date == date(2026, 3, 1)

    def test_respects_limit(self, session):
        product = _make_product(session)
        store = _make_store(session)

        for day in range(1, 11):
            session.add(
                PriceHistory(
                    id=uuid.uuid4(),
                    normalized_product_id=product.id,
                    store_id=store.id,
                    observed_date=date(2026, 3, day),
                    regular_price=Decimal("3.99"),
                    source=PriceSource.RECEIPT,
                )
            )
        session.flush()

        trend = get_price_trend(session, product.id, store.id, limit=3)
        assert len(trend) == 3


class TestPriceDelta:
    def test_delta_properties(self):
        delta = PriceDelta(
            product_id=uuid.uuid4(),
            store_id=uuid.uuid4(),
            old_price=Decimal("3.99"),
            new_price=Decimal("4.49"),
            change_amount=Decimal("0.50"),
            change_percent=Decimal("12.53"),
            old_date=date(2026, 3, 1),
            new_date=date(2026, 3, 15),
        )
        assert delta.is_increase is True
        assert delta.is_decrease is False

    def test_decrease_properties(self):
        delta = PriceDelta(
            product_id=uuid.uuid4(),
            store_id=uuid.uuid4(),
            old_price=Decimal("4.49"),
            new_price=Decimal("3.99"),
            change_amount=Decimal("-0.50"),
            change_percent=Decimal("-11.14"),
            old_date=date(2026, 3, 1),
            new_date=date(2026, 3, 15),
        )
        assert delta.is_decrease is True
        assert delta.is_increase is False
